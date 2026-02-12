# Database Migrations

Manual SQL migrations for the AI Governance Platform.

## Running Migrations

**1. Connect to your database:**
```bash
psql -U ahadbokhari -d audit_db
```

**2. Run the migration:**

**From command line (recommended):**
```bash
psql -U ahadbokhari -d audit_db -f migrations/001_create_audit_events_table.sql
```

**Or from within psql (use full path):**
```sql
\i /Users/ahadbokhari/projects/ai-governance-platform/migrations/001_create_audit_events_table.sql
```

**Or copy/paste the SQL directly:**
```sql
CREATE TABLE audit_events (
    id BIGSERIAL PRIMARY KEY,
    trace_id UUID,
    request_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- ... (rest of the SQL from the file)
```

## Migration Files

- `001_create_audit_events_table.sql` - Creates audit_events table and indexes

## Rollback

To rollback a migration, manually drop the table:
```sql
DROP TABLE IF EXISTS audit_events CASCADE;
```

