# Test Credentials

## Primary Test Accounts

| Role      | Email                         | Password   | Notes                                    |
|-----------|-------------------------------|------------|------------------------------------------|
| Admin     | admin.test@cebuana.com        | Test123!   | Seeded at startup; manages everything.   |
| User      | user.test@cebuana.com         | Test123!   | Standard employee user.                  |
| Attendant | attendant.test@cebuana.com    | Test123!   | On-site parking staff.                   |

## Database Abstraction

The active database backend is controlled by the `DB_TYPE` env var in `/app/backend/.env`:

- `DB_TYPE="mongodb"` — uses local MongoDB (default). Host: `localhost:27017`, DB: `test_database`.
- `DB_TYPE="couchbase"` — uses Couchbase Capella. Host: `cb.e6bams0qd8ow9578.cloud.couchbase.com`, bucket: `db_parking`.

**Couchbase Capella credentials (already in .env):**
- `COUCHBASE_CONNECTION_STRING="couchbases://cb.e6bams0qd8ow9578.cloud.couchbase.com"`
- `COUCHBASE_BUCKET="db_parking"`
- `COUCHBASE_USERNAME="parking_app"`
- `COUCHBASE_PASSWORD="Ce%lDtOtI-G4"`

**IP allowlist**: the preview pod egress IP `34.170.12.145` is whitelisted in the Capella cluster's Allowed IPs.

Switch between databases:
1. Edit `DB_TYPE` in `/app/backend/.env`
2. `sudo supervisorctl restart backend`
3. Admin UI sidebar badge shows active DB (green = MongoDB, red = Couchbase)

## Migration

Run mongo -> couchbase migration:
```
cd /app/backend
python scripts/migrate_mongo_to_couchbase.py --wipe
```
