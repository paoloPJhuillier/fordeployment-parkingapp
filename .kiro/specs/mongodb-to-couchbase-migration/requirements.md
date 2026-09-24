# Requirements Document

## Introduction

The `pjli-parking-app-CCE` FastAPI parking reservation application currently runs on MongoDB (via Motor) and must migrate to Couchbase. The migration is **already partially built**: a Motor-shaped database abstraction layer, a Couchbase adapter, a MongoDB adapter, adapter selection via the `DB_TYPE` environment variable, a collection provisioning script, a data migration script, and startup wiring all exist in the codebase.

This specification covers the work needed to **complete, harden, verify, and safely cut over** the migration — not to build it from scratch. The focus areas are: data integrity and completeness verification between source and target, behavioral parity of the abstraction layer for every MongoDB operation the application actually uses, index parity, a controlled cutover strategy driven by the `DB_TYPE` switch, rollback capability, minimal-downtime considerations, handling the `aggregate()` placeholder gap, operational runbook production, and environment/configuration correctness for both Couchbase Capella and Enterprise deployments (including TLS).

The application uses 18 logical collections: `users`, `sessions`, `buildings`, `floors`, `parking_slots`, `vehicles`, `zones`, `parking_configs`, `building_policies`, `slot_registrations`, `reservations`, `waitlist_entries`, `event_blocks`, `notifications`, `site_content`, `templates`, `ai_insights`, and `migrations`.

## Glossary

- **Migration_System**: The complete set of scripts, adapters, and procedures that move the application from MongoDB to Couchbase, including verification and cutover tooling.
- **Source_Database**: The existing MongoDB database accessed via the Motor driver.
- **Target_Database**: The destination Couchbase cluster (Capella or Enterprise) accessed via the Couchbase Python SDK.
- **Abstraction_Layer**: The Motor-shaped interfaces in `backend/database/interface.py` (`DatabaseInterface`, `CollectionInterface`, `CursorInterface`) behind which both adapters are interchangeable.
- **MongoDB_Adapter**: The passthrough Motor wrapper in `backend/database/mongodb.py`.
- **Couchbase_Adapter**: The adapter in `backend/database/couchbase_db.py` that translates MongoDB-style operations to Couchbase KV and N1QL.
- **Adapter_Selector**: The logic in `backend/database/__init__.py` that chooses the active adapter from the `DB_TYPE` environment variable.
- **Provisioning_Script**: `backend/scripts/provision_couchbase_collections.py`, which creates the 18 collections under the `_default` scope.
- **Migration_Script**: `backend/scripts/migrate_mongo_to_couchbase.py`, which copies documents from Source_Database to Target_Database.
- **Verification_Tool**: The tooling that compares Source_Database and Target_Database to confirm data completeness and integrity after migration.
- **Cutover**: The act of switching the running application from Source_Database to Target_Database by changing `DB_TYPE` to `couchbase`.
- **Rollback**: The act of reverting the running application from Target_Database back to Source_Database by changing `DB_TYPE` to `mongodb`.
- **Query_Operator**: A MongoDB-style filter operator: `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`, `$ne`, `$exists`, `$regex` (with `$options`).
- **Update_Operator**: A MongoDB-style update operator: `$set`, `$inc`, `$addToSet` (with `$each`), `$unset`.
- **KV_Fast_Path**: The Couchbase key-value code path the Couchbase_Adapter uses when a filter is exactly `{"id": <scalar>}`.
- **Deployment_Mode**: The Couchbase deployment target, either `capella` or `enterprise`, controlled by `COUCHBASE_DEPLOYMENT`.
- **Operational_Runbook**: The written, step-by-step operator procedure for provisioning, migrating, verifying, cutting over, and rolling back.

## Requirements

### Requirement 1: Behavioral Parity of Query Operators

**User Story:** As a backend developer, I want the Couchbase_Adapter to evaluate every query operator the application uses exactly as MongoDB does, so that endpoints return identical result sets regardless of the active database.

#### Acceptance Criteria

1. WHEN a filter containing the `$in` operator is executed, THE Couchbase_Adapter SHALL return the set of documents whose field value is contained in the supplied list, and SHALL treat a missing field as a non-match.
2. WHEN a filter containing the `$nin` operator is executed, THE Couchbase_Adapter SHALL return the set of documents whose field value is not contained in the supplied list, and SHALL treat a missing field as a match.
3. WHEN a filter containing the `$ne` operator is executed, THE Couchbase_Adapter SHALL return documents where the field is missing, is null, or has a value not equal to the supplied value.
4. WHEN a filter containing `$gt`, `$gte`, `$lt`, or `$lte` is executed, THE Couchbase_Adapter SHALL return documents whose field value satisfies the corresponding comparison against the supplied value, and SHALL treat a missing field as a non-match.
5. WHEN a filter containing the `$exists` operator is executed, THE Couchbase_Adapter SHALL return documents where the field is present (for a true value) or absent (for a false value).
6. WHEN a filter containing `$regex` with `$options` is executed, THE Couchbase_Adapter SHALL perform substring matching equivalent to MongoDB `$regex`, SHALL honor the `i`, `s`, and `m` flags, and SHALL treat a missing field as a non-match.
7. WHEN a filter matches a scalar value against a field whose document value is an array, THE Couchbase_Adapter SHALL return the document when the array contains the scalar.
8. IF a filter contains a query operator that the Couchbase_Adapter does not support, THEN THE Couchbase_Adapter SHALL raise an error identifying the unsupported operator.

### Requirement 2: Behavioral Parity of Update Operators

**User Story:** As a backend developer, I want the Couchbase_Adapter to apply every update operator the application uses exactly as MongoDB does, so that writes produce identical document state regardless of the active database.

#### Acceptance Criteria

1. WHEN an update containing the `$set` operator is applied, THE Couchbase_Adapter SHALL assign each supplied field to the supplied value on the target document.
2. WHEN an update containing the `$inc` operator is applied, THE Couchbase_Adapter SHALL increment each supplied field by the supplied amount, treating a missing field as zero before incrementing.
3. WHEN an update containing the `$addToSet` operator is applied, THE Couchbase_Adapter SHALL append each supplied value to the target array only when the value is not already present.
4. WHEN an update containing `$addToSet` with `$each` is applied, THE Couchbase_Adapter SHALL append each element of the `$each` list to the target array only when that element is not already present.
5. WHEN an update containing the `$unset` operator is applied, THE Couchbase_Adapter SHALL remove each supplied field from the target document.
6. IF an update contains an update operator that the Couchbase_Adapter does not support, THEN THE Couchbase_Adapter SHALL raise an error identifying the unsupported operator.

### Requirement 3: Behavioral Parity of Collection Operations

**User Story:** As a backend developer, I want every collection method the application calls to behave identically across adapters, so that no endpoint or background task changes behavior after cutover.

#### Acceptance Criteria

1. THE Couchbase_Adapter SHALL implement `find_one`, `find`, `insert_one`, `insert_many`, `update_one`, `update_many`, `delete_one`, `delete_many`, `count_documents`, `find_one_and_update`, and `find_one_and_delete` with return shapes compatible with the Motor equivalents used by the application.
2. WHEN `find` results are chained with `sort`, `limit`, or `skip`, THE Couchbase_Adapter SHALL apply ordering, result-count limiting, and offset consistent with MongoDB behavior.
3. WHEN a MongoDB-style projection is supplied, THE Couchbase_Adapter SHALL include or exclude fields according to the projection and SHALL always exclude the `_id` field.
4. WHEN `find_one_and_update` is called with a return-document preference, THE Couchbase_Adapter SHALL return the pre-update document by default and the post-update document when the after-document preference is set.
5. IF a `find_one_and_update` operation fails, THEN THE Couchbase_Adapter SHALL raise an error rather than returning a document.
6. WHEN `update_one` or `find_one_and_update` is called with `upsert` set to true and no document matches the filter, THE Couchbase_Adapter SHALL create a document derived from the filter and update payload.
7. IF document creation during an upsert operation fails, THEN THE Couchbase_Adapter SHALL raise an error.
8. WHEN a filter is exactly `{"id": <scalar>}`, THE Couchbase_Adapter SHALL use the KV_Fast_Path and return results equivalent to the N1QL path.

### Requirement 4: Aggregate Operation Gap Handling

**User Story:** As a backend developer, I want the `aggregate()` gap in the Couchbase_Adapter to be explicitly resolved, so that the application does not silently receive empty results if an aggregation is introduced.

#### Acceptance Criteria

1. THE Migration_System SHALL confirm through codebase inspection that no application route, service, or background task invokes `aggregate()`, and the confirmation SHALL remain valid at all times once performed.
2. IF `aggregate()` is invoked on the Couchbase_Adapter while it returns a placeholder empty result, THEN THE Couchbase_Adapter SHALL raise an error indicating that aggregation is not implemented.
3. WHERE an aggregation capability is required by the application, THE Couchbase_Adapter SHALL implement the requested aggregation pipeline stages with results equivalent to MongoDB.

### Requirement 5: Collection Provisioning Completeness

**User Story:** As an operator, I want all required Couchbase collections to exist before data is migrated, so that the Migration_Script never writes to a missing collection.

#### Acceptance Criteria

1. WHEN the Provisioning_Script is executed, THE Provisioning_Script SHALL create all 18 required collections under the `_default` scope of the configured bucket.
2. WHEN the Provisioning_Script is executed against a bucket where some collections already exist, THE Provisioning_Script SHALL leave existing collections unchanged and report each as already existing.
3. IF collection creation fails for a reason other than the collection already existing, THEN THE Provisioning_Script SHALL report the failing collection, increment its error count, and terminate with a non-zero exit status.
4. WHEN the Provisioning_Script completes, THE Provisioning_Script SHALL report the count of collections created, the count already existing, and the count of errors.

### Requirement 6: Index Parity

**User Story:** As an operator, I want the Target_Database to carry index coverage equivalent to the Source_Database, so that query performance and the hot-path queries the application depends on remain intact after Cutover.

#### Acceptance Criteria

1. WHEN Couchbase index creation is executed, THE Couchbase_Adapter SHALL create a primary index for each of the 18 collections.
2. WHEN Couchbase index creation is executed, THE Couchbase_Adapter SHALL create secondary indexes covering the fields that the MongoDB_Adapter indexes, including `users.email`, `users.role`, `sessions.user_id`, `reservations.user_id`, `reservations.building_id`, the reservation slot/date/status combination, `reservations.qr_token`, `floors.building_id`, `parking_slots.floor_id`, `vehicles.user_id`, `notifications` by user and creation time, `parking_configs.building_id`, `building_policies.building_id`, the slot-registration status combinations, and the waitlist status combinations.
3. WHEN Couchbase index creation is executed more than once, THE Couchbase_Adapter SHALL leave existing indexes unchanged.
4. IF index creation fails during application startup, THEN THE application SHALL log the failure and continue startup.

### Requirement 7: Data Migration Completeness

**User Story:** As an operator, I want every document in every source collection copied to the Target_Database, so that no data is lost during migration.

#### Acceptance Criteria

1. WHEN the Migration_Script is executed without a collection filter, THE Migration_Script SHALL copy documents from all 18 collections.
2. WHEN the Migration_Script is executed with one or more named collections, THE Migration_Script SHALL copy documents only from the named collections.
3. WHEN the Migration_Script copies a document, THE Migration_Script SHALL use the document `id` as the Target_Database key and SHALL generate an `id` when the source document lacks one.
4. IF the Migration_Script cannot produce a Target_Database key for a document, THEN THE Migration_Script SHALL skip that document and continue migrating the remaining documents.
5. IF the Migration_Script detects that a repeated execution would produce a Target_Database document state differing from a single execution, THEN THE Migration_Script SHALL terminate with an error rather than silently reconciling the difference.
6. WHEN the Migration_Script is executed with the dry-run option, THE Migration_Script SHALL report per-collection document counts and SHALL NOT write to the Target_Database.
7. WHEN the Migration_Script is executed with the wipe option, THE Migration_Script SHALL remove existing documents from the target collections before copying.
8. WHEN the Migration_Script completes, THE Migration_Script SHALL report documents read, documents written, empty collections, and errors, and SHALL terminate with a non-zero exit status when any error occurred.

### Requirement 8: Data Integrity Verification

**User Story:** As an operator, I want to verify that migrated data in the Target_Database matches the Source_Database, so that I can trust the migration before Cutover.

#### Acceptance Criteria

1. WHEN the Verification_Tool is executed, THE Verification_Tool SHALL compare the document count of each collection in the Source_Database against the corresponding collection in the Target_Database.
2. IF a per-collection document count in the Target_Database differs from the Source_Database, THEN THE Verification_Tool SHALL report the collection, the source count, and the target count as a discrepancy.
3. WHEN the Verification_Tool compares documents, THE Verification_Tool SHALL confirm that each Target_Database document present for a source `id` has stored field values matching the source, excluding the MongoDB `_id` field.
4. WHEN the Verification_Tool completes successfully, THE Verification_Tool SHALL report an overall pass result when all documents present in the Target_Database match the Source_Database and SHALL report an overall fail result listing all field-value discrepancies otherwise.
5. IF the Verification_Tool does not run to completion, THEN THE Verification_Tool SHALL NOT report an overall pass result.

### Requirement 9: Cutover Control

**User Story:** As an operator, I want to switch the application between MongoDB and Couchbase through a single configuration value, so that Cutover is deterministic and low-risk.

#### Acceptance Criteria

1. WHEN the `DB_TYPE` environment variable is set to `couchbase`, THE Adapter_Selector SHALL construct the Couchbase_Adapter as the active database.
2. WHEN the `DB_TYPE` environment variable is set to `mongodb` or is unset, THE Adapter_Selector SHALL construct the MongoDB_Adapter as the active database.
3. IF the `DB_TYPE` environment variable holds a value other than `mongodb` or `couchbase`, THEN THE Adapter_Selector SHALL raise an error identifying the unsupported value.
4. WHEN the application starts with the Couchbase_Adapter active, THE application SHALL connect the Target_Database, ensure indexes, run one-time startup migrations, and seed the default admin using the same startup sequence used for MongoDB.
5. IF an individual startup step fails after connection is attempted, THEN THE application SHALL log the failure and allow the remaining startup steps to proceed.

### Requirement 10: Rollback Capability

**User Story:** As an operator, I want to revert to MongoDB quickly if Cutover reveals a problem, so that service can be restored without data recovery work.

#### Acceptance Criteria

1. WHEN the `DB_TYPE` environment variable is changed from `couchbase` back to `mongodb` and the application is restarted, THE application SHALL operate against the Source_Database.
2. WHILE the application runs against the Target_Database after Cutover, THE Operational_Runbook SHALL define the condition under which the Source_Database may be treated as an authoritative Rollback target.
3. THE Operational_Runbook SHALL document the steps required to reconcile data written to the Target_Database after Cutover when Rollback occurs.

### Requirement 11: Minimal-Downtime Cutover Procedure

**User Story:** As an operator, I want a Cutover procedure that minimizes downtime and prevents data divergence, so that users experience minimal disruption.

#### Acceptance Criteria

1. THE Operational_Runbook SHALL define the ordered sequence of provisioning, migrating, verifying, and switching `DB_TYPE` for Cutover.
2. THE Operational_Runbook SHALL specify how writes to the Source_Database are quiesced or drained during Cutover to prevent data divergence between Source_Database and Target_Database.
3. WHEN Cutover is performed, THE Migration_System SHALL require a final Verification_Tool pass after writes are quiesced and before the switch to the Target_Database is finalized.

### Requirement 12: Environment and Connection Configuration

**User Story:** As an operator, I want the Couchbase connection to be configurable for both Capella and Enterprise deployments including TLS, so that the same codebase serves cloud and on-premises clusters.

#### Acceptance Criteria

1. THE Couchbase_Adapter SHALL read connection string, bucket, username, and password from environment variables.
2. WHERE the Deployment_Mode is `capella`, THE Couchbase_Adapter SHALL apply the cloud latency tuning profile during connection.
3. WHERE the Deployment_Mode is `enterprise`, THE Couchbase_Adapter SHALL connect without applying the cloud latency tuning profile.
4. WHERE a trust-store path is configured, THE Couchbase_Adapter SHALL use the supplied certificate authority certificate for TLS validation.
5. IF a configured trust store cannot be used for TLS validation, THEN THE Couchbase_Adapter SHALL fail the connection rather than fall back to default certificate validation.
6. WHERE a client certificate path is configured, THE Couchbase_Adapter SHALL present the supplied client certificate for mutual TLS.
7. WHERE TLS verification is configured as `none`, THE Couchbase_Adapter SHALL skip TLS certificate verification.
8. WHEN a Couchbase connection is attempted, THE Couchbase_Adapter SHALL wait for the cluster to become ready within a bounded timeout, and SHALL allow the subsequent connection attempt to surface the failure when the cluster does not become ready within that timeout.

### Requirement 13: Connection Readiness Validation

**User Story:** As an operator, I want to validate Couchbase connectivity before migrating or cutting over, so that configuration errors are caught early.

#### Acceptance Criteria

1. WHEN the connection readiness check is executed, THE Migration_System SHALL authenticate to the Target_Database, open the configured bucket, perform a key-value write-read-remove round trip, and run a N1QL count query.
2. IF any step of the connection readiness check fails, THEN THE Migration_System SHALL report the failing step and terminate with a non-zero exit status.
3. THE connection readiness check SHALL read Target_Database credentials from environment variables rather than embedding them in source code, and MAY read non-sensitive connection details from environment variables or other configuration sources.

### Requirement 14: Operational Runbook

**User Story:** As an operator, I want a complete written runbook, so that I can execute the migration and Cutover repeatably and safely.

#### Acceptance Criteria

1. THE Operational_Runbook SHALL document the required environment variables for both Deployment_Modes, including connection, bucket, credentials, and TLS settings.
2. THE Operational_Runbook SHALL document the ordered commands for connection validation, provisioning, dry-run migration, full migration, verification, Cutover, and Rollback, and each command section SHALL reference or include its prerequisite environment variables.
3. THE Operational_Runbook SHALL document the expected outputs and pass criteria for each verification step.
4. THE Operational_Runbook SHALL document how to migrate or re-migrate a single collection when a discrepancy is found.

### Requirement 15: Migration Tooling Documentation Accuracy

**User Story:** As a developer, I want the Migration_Script documentation to match its actual behavior, so that operators are not misled about the key strategy or document shape.

#### Acceptance Criteria

1. THE Migration_Script documentation SHALL describe the Target_Database key strategy as the bare document `id` used by the Couchbase_Adapter.
2. THE Migration_Script documentation SHALL NOT describe key prefixes or an added `type` field that the Migration_Script does not produce.
3. WHEN the Migration_Script writes a document, THE stored document shape SHALL match the shape the Couchbase_Adapter reads, so that a migrated document is retrievable by the application without transformation.
