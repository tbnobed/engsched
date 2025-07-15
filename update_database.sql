-- Run these commands on your local PostgreSQL server

-- Step 1: Update timestamp columns in schedule table to be timezone-aware
ALTER TABLE schedule 
    ALTER COLUMN start_time TYPE timestamp with time zone USING start_time AT TIME ZONE 'UTC',
    ALTER COLUMN end_time TYPE timestamp with time zone USING end_time AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE timestamp with time zone USING created_at AT TIME ZONE 'UTC';

-- Step 2: Add required indexes for better performance
CREATE INDEX IF NOT EXISTS idx_schedule_technician ON schedule(technician_id);
CREATE INDEX IF NOT EXISTS idx_schedule_time ON schedule(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_quick_link_order ON quick_link("order");

-- Step 3: Add timestamp columns to quick_link table
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'quick_link' AND column_name = 'created_at') THEN
        ALTER TABLE quick_link ADD COLUMN created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'quick_link' AND column_name = 'updated_at') THEN
        ALTER TABLE quick_link ADD COLUMN updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;
