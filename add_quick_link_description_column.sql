-- Add description column to quick_link table if it doesn't exist
-- This script can be run safely multiple times

DO $$
BEGIN
    -- Check if the column exists before adding it
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'quick_link' 
        AND column_name = 'description'
    ) THEN
        -- Add the description column
        ALTER TABLE quick_link ADD COLUMN description VARCHAR(500) DEFAULT '';
        
        -- Log the change
        RAISE NOTICE 'Added description column to quick_link table';
    ELSE
        RAISE NOTICE 'Description column already exists in quick_link table';
    END IF;
END $$;