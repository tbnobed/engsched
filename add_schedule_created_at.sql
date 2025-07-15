-- SQL script to add missing columns to the schedule table
-- This fixes the error: "sqlalchemy.exc.ProgrammingError: column schedule.created_at does not exist"

-- Add location_id column to schedule table if it doesn't exist
ALTER TABLE schedule ADD COLUMN IF NOT EXISTS location_id INTEGER REFERENCES location(id);

-- Add created_at column to schedule table if it doesn't exist
ALTER TABLE schedule ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Update any NULL created_at values to the current timestamp
UPDATE schedule SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;

-- Check if columns were added successfully
DO $$
BEGIN
    RAISE NOTICE 'Schema update completed.';
    RAISE NOTICE 'Checking if columns exist:';
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'schedule' AND column_name = 'created_at') THEN
        RAISE NOTICE 'schedule.created_at: EXISTS';
    ELSE
        RAISE NOTICE 'schedule.created_at: MISSING';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'schedule' AND column_name = 'location_id') THEN
        RAISE NOTICE 'schedule.location_id: EXISTS';
    ELSE
        RAISE NOTICE 'schedule.location_id: MISSING';
    END IF;
END $$;