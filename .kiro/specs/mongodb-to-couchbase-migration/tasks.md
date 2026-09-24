# Implementation Plan: MongoDB-to-Couchbase Migration

## Overview

This plan completes, hardens, verifies, and prepares safe cutover for the already-partially-built
MongoDB-to-Couchbase migration. The abstraction layer, both adapters, adapter selection, the
provisioning script, the migration script, and startup wiring already exist. The tasks below close
the remaining behavioral and operational gaps, add the missing Verification_Tool, rework the
connection-readiness check, correct documentation drift, pin the 21 correctness properties with
Hypothesis property-based tests, and produce the Operational_Runbook.

Implementation language is **Python** (matching the existing `backend/` FastAPI codebase).
Property-based tests use **Hypothesis** (added to `backend/requirements.txt`). Each property test
runs a minimum of 100 iterations and is tagged with its design property number.

## Tasks

- [ ] 1. Set up test infrastructure and shared reference model
  - [ ] 1.1 Add Hypothesis dependency and test package scaffolding
    - Add `hypothesis` to `backend/requirements.txt`
    - Create `backend/tests/__init__.py` and `backend/tests/integration/__init__.py`
    - Configure pytest (ensure `pytest`/`pytest-asyncio` are available for async adapter tests)
    - _Requirements: 1.1, 2.1, 3.1_

  - [ ] 1.2 Implement the in-memory MongoDB reference model evaluator
    - Create `backend/tests/reference_model.py` with a small, obviously-correct in-memory
      implementation of MongoDB filter semantics (`$in`, `$nin`, `$ne`, `$gt/$gte/$lt/$lte`,
      `$exists`, `$regex`+`$options`, scalar-vs-array containment, plain-scalar equality)
    - Implement reference sort-then-skip-then-limit and reference update-operator application
      (`$set`, `$inc` missing=0, `$addToSet`+`$each` de-duplicated, `$unset`) for use by property tests
    - Implement an equivalent in-memory interpreter of the adapter's emitted N1QL `WHERE` fragment +
      params so query-operator translation can be validated without a live cluster
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.1, 2.2, 2.3, 2.4, 2.5, 3.2_

- [ ] 2. Harden the Couchbase query translation (`_N1qlBuilder`)
  - [ ] 2.1 Lock down operator translation and fail-loud behavior in `_N1qlBuilder`
    - Review `backend/database/couchbase_db.py` `_N1qlBuilder._condition` and confirm/repair
      `$in`, `$nin`, `$ne` (expanded to `IS MISSING OR IS NULL OR != value`), range operators,
      `$exists`, `$regex` with `$options` folded into an RE2 `(?ism)` inline-flag prefix using
      `REGEXP_CONTAINS`, and scalar-vs-array containment (`` (`field` = $p OR $p IN `field`) ``)
    - Ensure any unsupported query operator raises `ValueError` whose message names the operator
    - Ensure per-condition mutation of `value`/`params` cannot leak across conditions
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [ ]* 2.2 Write property test for `$in` selection
    - **Property 1: `$in` selection matches MongoDB semantics**
    - **Validates: Requirements 1.1**
    - File: `backend/tests/test_query_operators_property.py`

  - [ ]* 2.3 Write property test for `$nin` selection
    - **Property 2: `$nin` selection matches MongoDB semantics**
    - **Validates: Requirements 1.2**
    - File: `backend/tests/test_query_operators_property.py`

  - [ ]* 2.4 Write property test for `$ne` selection
    - **Property 3: `$ne` matches missing, null, or unequal values**
    - **Validates: Requirements 1.3**
    - File: `backend/tests/test_query_operators_property.py`

  - [ ]* 2.5 Write property test for range comparisons
    - **Property 4: Range comparisons match MongoDB semantics**
    - **Validates: Requirements 1.4**
    - File: `backend/tests/test_query_operators_property.py`

  - [ ]* 2.6 Write property test for `$exists`
    - **Property 5: `$exists` matches presence and absence**
    - **Validates: Requirements 1.5**
    - File: `backend/tests/test_query_operators_property.py`

  - [ ]* 2.7 Write property test for `$regex` flagged substring matching
    - **Property 6: `$regex` performs flagged substring matching**
    - **Validates: Requirements 1.6**
    - File: `backend/tests/test_query_operators_property.py`

  - [ ]* 2.8 Write property test for scalar-vs-array containment
    - **Property 7: Scalar filters match array-valued fields by containment**
    - **Validates: Requirements 1.7**
    - File: `backend/tests/test_query_operators_property.py`

  - [ ]* 2.9 Write property test for unsupported query operator errors
    - **Property 8: Unsupported query operators raise a naming error**
    - **Validates: Requirements 1.8**
    - File: `backend/tests/test_query_operators_property.py`

- [ ] 3. Harden the Couchbase update and projection logic
  - [ ] 3.1 Lock down `_apply_update` operator semantics and fail-loud behavior
    - Review/repair `_apply_update` in `backend/database/couchbase_db.py`: `$set`, `$inc`
      (missing=0), `$addToSet` with `$each` de-duplicated, `$unset`, and plain-document
      replacement merge (no `$` keys)
    - Ensure any unsupported update operator raises `ValueError` naming the operator
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ] 3.2 Lock down `_apply_projection` include/exclude semantics
    - Review/repair `_apply_projection`: honor inclusion and exclusion semantics and always strip
      `_id` regardless of projection
    - _Requirements: 3.3_

  - [ ]* 3.3 Write property test for update operators
    - **Property 9: Update operators produce MongoDB-equivalent document state**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
    - File: `backend/tests/test_update_operators_property.py`

  - [ ]* 3.4 Write property test for unsupported update operator errors
    - **Property 10: Unsupported update operators raise a naming error**
    - **Validates: Requirements 2.6**
    - File: `backend/tests/test_update_operators_property.py`

  - [ ]* 3.5 Write property test for projection include/exclude and `_id` stripping
    - **Property 11: Projection includes/excludes correctly and always strips `_id`**
    - **Validates: Requirements 3.3**
    - File: `backend/tests/test_projection_property.py`

- [ ] 4. Harden collection operations and cursor composition
  - [ ] 4.1 Verify and repair cursor `sort`/`skip`/`limit` composition
    - Review `CouchbaseCursor` in `backend/database/couchbase_db.py`; ensure `to_list()` builds
      `SELECT ... WHERE ... [ORDER BY] [LIMIT] [OFFSET]` applying sort-then-skip-then-limit
    - _Requirements: 3.2_

  - [ ] 4.2 Verify and repair `find_one_and_update` snapshot and upsert derivation
    - Ensure `find_one_and_update` returns the pre-update document by default and the post-update
      document when the after preference is set; ensure upsert (on `update_one`/`find_one_and_update`
      with no match) creates a document derived from filter merged with the applied update and
      carrying an `id`; raise `ValueError` when no `id` can be derived
    - Ensure a failed `find_one_and_update` replace and a failed upsert creation propagate the error
    - _Requirements: 3.4, 3.5, 3.6, 3.7_

  - [ ] 4.3 Verify KV fast-path equivalence for `{"id": <scalar>}` filters
    - Confirm `CouchbaseCollection` uses a KV `get`/`replace`/`remove` fast-path for exactly
      `{"id": <scalar>}` and returns results equivalent to the N1QL general path
    - _Requirements: 3.8_

  - [ ]* 4.4 Write property test for cursor sort/skip/limit composition
    - **Property 12: Sort, skip, and limit compose like MongoDB**
    - **Validates: Requirements 3.2**
    - File: `backend/tests/test_cursor_sort_skip_limit_property.py`

  - [ ]* 4.5 Write property test for `find_one_and_update` snapshot behavior
    - **Property 13: `find_one_and_update` returns the correct snapshot**
    - **Validates: Requirements 3.4**
    - File: `backend/tests/test_find_one_and_update_property.py`

  - [ ]* 4.6 Write property test for upsert document derivation
    - **Property 14: Upsert derives the new document from filter and update**
    - **Validates: Requirements 3.6**
    - File: `backend/tests/test_find_one_and_update_property.py`

  - [ ]* 4.7 Write property test for KV fast-path equivalence
    - **Property 15: KV fast-path equals the N1QL general path**
    - **Validates: Requirements 3.8**
    - File: `backend/tests/test_kv_fastpath_equivalence_property.py`

  - [ ]* 4.8 Write example/unit tests for method return-shape and failure propagation
    - Assert Motor-compatible return shapes for `find_one`, `find`, `insert_one`, `insert_many`,
      `update_one`, `update_many`, `delete_one`, `delete_many`, `count_documents`,
      `find_one_and_update`, `find_one_and_delete`
    - Assert `find_one_and_update` and upsert failures raise rather than return a document
    - _Requirements: 3.1, 3.5, 3.7_
    - File: `backend/tests/test_adapter_examples.py`

- [ ] 5. Resolve the `aggregate()` gap
  - [ ] 5.1 Make `aggregate()` raise `NotImplementedError`
    - Replace the placeholder `return []` in `CouchbaseDatabase`/`CouchbaseCollection`
      `aggregate()` with a `NotImplementedError` whose message explains aggregation is not
      implemented and to add pipeline stages if a caller is introduced
    - _Requirements: 4.2_

  - [ ]* 5.2 Add smoke/static guard confirming no `aggregate()` caller exists
    - Add a CI/test guard that greps the codebase for `.aggregate(` and asserts no route, service,
      or background task invokes it
    - Add a unit test asserting `aggregate()` raises `NotImplementedError`
    - _Requirements: 4.1, 4.2_
    - File: `backend/tests/test_adapter_examples.py`

- [ ] 6. Checkpoint - core adapter parity
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Harden provisioning and index parity
  - [ ] 7.1 Verify Provisioning_Script completeness and reporting
    - Review `backend/scripts/provision_couchbase_collections.py`; ensure it creates all 18
      collections under `_default`, treats `CollectionAlreadyExistsException`/`"already exist"` as
      existing, reports created/existing/errors, and exits non-zero on any real error
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ] 7.2 Verify Couchbase index parity against MongoDB index set
    - Review `CouchbaseDatabase.create_indexes()` and `MongoDBDatabase.create_indexes()`; ensure a
      primary index for all 18 collections and secondary GSIs mirroring every MongoDB-indexed field
      per the design Index Parity Map, all using `IF NOT EXISTS`
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 7.3 Write index DDL smoke checks
    - Assert `create_indexes` emits a primary index for all 18 collections and every required
      secondary index from the parity map
    - _Requirements: 6.1, 6.2_
    - File: `backend/tests/test_indexes.py`

  - [ ]* 7.4 Write provisioning unit tests for reporting and error handling
    - Test created/existing counting, already-exists handling, and non-zero exit on real error
    - _Requirements: 5.3, 5.4_
    - File: `backend/tests/test_provisioning.py`

- [ ] 8. Correct migration tooling and pin migration behavior
  - [ ] 8.1 Fix Migration_Script docstring to match actual key strategy
    - Update the module docstring in `backend/scripts/migrate_mongo_to_couchbase.py` to state:
      key = bare document `id`; no key prefix; no added `type` field; body = document with a
      guaranteed `id`
    - _Requirements: 15.1, 15.2_

  - [ ] 8.2 Verify migration selection, key derivation, dry-run, wipe, and reporting
    - Review the script: no-filter migrates all 18 collections; named collections migrate only
      those; key = bare `id` with generated UUID when missing; unkeyable document skipped and
      migration continues; dry-run reports counts without writing; wipe removes target docs first;
      final report includes read/written/empty/errors and exits non-zero on any error
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6, 7.7, 7.8_

  - [ ]* 8.3 Write property test for migration key derivation
    - **Property 16: Migration key derivation uses the bare `id`**
    - **Validates: Requirements 7.3, 15.1, 15.2**
    - File: `backend/tests/test_migration_property.py`

  - [ ]* 8.4 Write property test for migration idempotence
    - **Property 17: Migration is idempotent**
    - **Validates: Requirements 7.5**
    - File: `backend/tests/test_migration_property.py`

  - [ ]* 8.5 Write property test for migrate-then-read round-trip fidelity
    - **Property 18: Migrate-then-read round-trip preserves the document**
    - **Validates: Requirements 15.3**
    - File: `backend/tests/test_migration_property.py`

  - [ ]* 8.6 Write example/unit tests for migration selection and reporting
    - Test named-collection selection, dry-run no-write behavior, and read/written/empty/error
      reporting with non-zero exit on error
    - _Requirements: 7.2, 7.6, 7.8_
    - File: `backend/tests/test_adapter_examples.py`

  - [ ]* 8.7 Add docstring accuracy static check for the migration script
    - Assert the migration docstring describes the bare-`id` key strategy and contains no key-prefix
      or `type`-field language
    - _Requirements: 15.1, 15.2_
    - File: `backend/tests/test_adapter_examples.py`

- [ ] 9. Build the Verification_Tool
  - [ ] 9.1 Implement `verify_migration.py`
    - Create `backend/scripts/verify_migration.py` supporting all-collections, named-collections,
      and `--counts-only` modes
    - Compare per-collection counts and report discrepancies with collection name, source count,
      and target count
    - Stream each source document, fetch the target by `id`, and compare field values excluding `_id`
    - Report overall PASS only if the run completes AND every compared target document matches its
      source; otherwise report FAIL listing all field-value discrepancies
    - Exit non-zero on FAIL or any error; never print PASS if the run aborts early
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 9.2 Write property test for verification count comparison
    - **Property 19: Verification count comparison flags exactly the mismatched collections**
    - **Validates: Requirements 8.1, 8.2**
    - File: `backend/tests/test_verification_property.py`

  - [ ]* 9.3 Write property test for verification field comparison PASS/FAIL
    - **Property 20: Verification field comparison yields PASS only on full equality**
    - **Validates: Requirements 8.3, 8.4**
    - File: `backend/tests/test_verification_property.py`

- [ ] 10. Checkpoint - tooling complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Harden adapter selection and connection configuration
  - [ ] 11.1 Verify Adapter_Selector `DB_TYPE` mapping
    - Review `backend/database/__init__.py` `_build_database()`; ensure `couchbase` builds the
      Couchbase adapter, `mongodb`/unset builds the MongoDB adapter, and any other value raises an
      error naming the unsupported value
    - _Requirements: 9.1, 9.2, 9.3, 10.1_

  - [ ] 11.2 Verify TLS/deployment configuration mapping in Couchbase_Adapter
    - Review `CouchbaseDatabase` connection setup: read connection string/bucket/username/password
      from env; apply cloud tuning for `capella` and none for `enterprise`; use configured trust
      store for TLS and fail (never fall back) when it is unusable; present client cert for mutual
      TLS when configured; skip verification when `tls_verify=none`; bound readiness with
      `wait_until_ready` and let a not-ready cluster surface the failure on the next operation
    - Only pass options the operator actually set to `ClusterOptions`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8_

  - [ ]* 11.3 Write property test for adapter selection
    - **Property 21: Adapter selection maps `DB_TYPE` deterministically**
    - **Validates: Requirements 9.1, 9.2, 9.3, 10.1**
    - File: `backend/tests/test_adapter_selector_property.py`

  - [ ]* 11.4 Write unit tests for TLS/deployment config mapping
    - Test capella vs enterprise tuning, trust-store use and no-fallback failure, client cert
      presentation, `tls_verify=none`, and that only set options reach the SDK
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_
    - File: `backend/tests/test_connection_config.py`

- [ ] 12. Verify startup wiring and rework connection readiness check
  - [ ] 12.1 Verify startup sequence and resilience
    - Review `backend/server.py`; ensure Couchbase-active startup connects, ensures indexes, runs
      one-time startup migrations, and seeds the default admin using the same sequence as MongoDB,
      and that a failure in an individual post-connection step is logged while remaining steps proceed
    - _Requirements: 9.4, 9.5, 6.4_

  - [ ] 12.2 Rework `test_couchbase_connection.py` to remove hardcoded credentials
    - Read connection string, bucket, username, password, and TLS/deployment settings from env
    - Authenticate, open the bucket, perform a scoped `_default` KV write→read→remove round trip,
      and run a N1QL `COUNT(*)` query
    - On any step failure, print the failing step and exit non-zero
    - _Requirements: 13.1, 13.2, 13.3_

  - [ ]* 12.3 Write startup wiring and resilience tests
    - Test the Couchbase-active startup sequence and that a failing post-connection step is logged
      while startup continues
    - _Requirements: 9.4, 9.5, 6.4_
    - File: `backend/tests/test_startup.py`

  - [ ]* 12.4 Write connection-check failure reporting test and credential-literal guard
    - Test that each failing step is reported with a non-zero exit; assert the connection check
      reads credentials from the environment and contains no credential literals
    - _Requirements: 13.2, 13.3_
    - File: `backend/tests/test_connection_config.py`

- [ ] 13. Author the Operational_Runbook
  - [ ] 13.1 Write the Operational_Runbook document
    - Create the runbook (e.g. `backend/scripts/RUNBOOK.md` or docs location) documenting: required
      env vars for capella and enterprise (connection, bucket, credentials, TLS); ordered commands
      for connection validation, provisioning, dry-run migration, full migration, verification,
      cutover, and rollback, each referencing prerequisite env vars; expected outputs and pass
      criteria per verification step; how to migrate/re-migrate a single collection on discrepancy;
      the write-quiesce/drain procedure and the required final verification gate before finalizing
      cutover; the rollback condition treating Source_Database as authoritative and the steps to
      reconcile post-cutover writes on rollback; and a note that Couchbase does not enforce MongoDB
      `unique=True` constraints (uniqueness stays in application logic)
    - _Requirements: 10.2, 10.3, 11.1, 11.2, 11.3, 14.1, 14.2, 14.3, 14.4_

- [ ] 14. Integration tests against a real or mocked cluster
  - [ ]* 14.1 Write provisioning and index idempotence integration tests
    - Provision against a bucket and confirm all 18 collections; re-run index creation and confirm
      existing indexes are unchanged
    - _Requirements: 5.1, 5.2, 6.3_
    - File: `backend/tests/integration/test_provisioning_integration.py`

  - [ ]* 14.2 Write migration and connection-readiness integration tests
    - Run full and wipe migration end-to-end; run connection readiness end-to-end; confirm a
      cluster-timeout surfaces as a failure on the next operation
    - _Requirements: 7.1, 7.7, 13.1, 12.8_
    - File: `backend/tests/integration/test_migration_integration.py`

- [ ] 15. Final checkpoint - full migration readiness
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP.
- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation.
- Property tests validate the 21 universal correctness properties; each property is one dedicated
  Hypothesis test running at least 100 iterations and tagged with its property number.
- Unit, example, smoke/static, and integration tests cover the infrastructure and operational
  requirements that are not property-based.
- Requirements 10.2, 10.3, 11.1, 11.2, 11.3, 14.1, 14.2, 14.3, 14.4 are satisfied by the written
  Operational_Runbook (task 13.1) and verified by review.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "3.1", "3.2", "4.1", "4.2", "4.3", "5.1", "7.1", "7.2", "8.1", "8.2", "9.1", "11.1", "11.2", "12.1", "12.2", "13.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "3.3", "3.4", "3.5", "4.4", "4.5", "4.6", "4.7", "4.8", "5.2", "7.3", "7.4", "8.3", "8.4", "8.5", "8.6", "8.7", "9.2", "9.3", "11.3", "11.4", "12.3", "12.4"] },
    { "id": 3, "tasks": ["14.1", "14.2"] }
  ]
}
```
