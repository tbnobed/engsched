# Quick Link Schema Fix - Docker Deployment

## Issue
The production Docker deployment was missing the `description` column in the `quick_link` table, causing errors when accessing `/mobile/quick_links`:

```
psycopg2.errors.UndefinedColumn: column quick_link.description does not exist
```

## Root Cause
The `init.sql` file used for Docker deployments was out of sync with the `models.py` QuickLink model. The model includes a `description` field, but the database schema in `init.sql` was missing this column.

## Fix Applied

### 1. Updated init.sql
Added the missing `description` column to the `quick_link` table:
```sql
CREATE TABLE quick_link (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    description VARCHAR(500) DEFAULT '',  -- Added this line
    icon VARCHAR(50) DEFAULT 'link',
    category VARCHAR(100) NOT NULL,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Created Migration Script
Created `add_quick_link_description_column.sql` for existing deployments:
```sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'quick_link' 
        AND column_name = 'description'
    ) THEN
        ALTER TABLE quick_link ADD COLUMN description VARCHAR(500) DEFAULT '';
        RAISE NOTICE 'Added description column to quick_link table';
    ELSE
        RAISE NOTICE 'Description column already exists in quick_link table';
    END IF;
END $$;
```

### 3. Updated Docker Entry Point
Enhanced `docker-entrypoint.sh` to automatically run the migration:
- Checks for and runs `update_database_schema.sql` (existing)
- Checks for and runs `add_quick_link_description_column.sql` (new)

### 4. Updated Schema Migration File
Enhanced `update_database_schema.sql` to include the quick_link description column fix alongside the existing ticket_view table creation.

## Deployment Instructions

### For New Deployments
- New deployments will use the updated `init.sql` with the correct schema
- No additional steps needed

### For Existing Deployments
The migration will run automatically on container restart via the updated docker-entrypoint.sh script.

To manually apply the fix:
```bash
# Connect to your PostgreSQL database and run:
docker exec -it your_db_container psql -U your_user -d your_database -f /app/add_quick_link_description_column.sql
```

## Verification
After deployment, verify the fix by:
1. Accessing `/mobile/quick_links` - should load without errors
2. Checking the database schema:
```sql
\d quick_link
```
Should show the `description` column.

## Files Modified
- `init.sql` - Added description column to quick_link table definition
- `add_quick_link_description_column.sql` - New migration script (created)
- `docker-entrypoint.sh` - Added migration step for quick_link fix
- `update_database_schema.sql` - Enhanced to include quick_link description column migration
- `QUICK_LINK_SCHEMA_FIX.md` - This documentation (created)

## Prevention
This type of schema mismatch can be prevented by:
1. Keeping `init.sql` in sync with model definitions in `models.py`
2. Creating migration scripts for any schema changes
3. Running database schema validation tests before deployment