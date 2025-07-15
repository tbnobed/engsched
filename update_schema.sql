-- Schema update script for Plex Technician Scheduler application
-- This script adds any missing columns required by the application

-- Add theme_preference column to user table if it doesn't exist
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS theme_preference VARCHAR(20) DEFAULT 'dark';

-- Add archived column to ticket table if it doesn't exist
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT false;

-- Add location_id column to schedule table if it doesn't exist
ALTER TABLE schedule ADD COLUMN IF NOT EXISTS location_id INTEGER REFERENCES location(id);

-- Add created_at column to schedule table if it doesn't exist
ALTER TABLE schedule ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Check if columns were added
DO $$
BEGIN
    RAISE NOTICE 'Schema update completed.';
    RAISE NOTICE 'Checking if columns exist:';
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'user' AND column_name = 'theme_preference') THEN
        RAISE NOTICE 'user.theme_preference: EXISTS';
    ELSE
        RAISE NOTICE 'user.theme_preference: MISSING';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'ticket' AND column_name = 'archived') THEN
        RAISE NOTICE 'ticket.archived: EXISTS';
    ELSE
        RAISE NOTICE 'ticket.archived: MISSING';
    END IF;
    
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

-- Run VACUUM to optimize the database after schema changes
VACUUM ANALYZE;