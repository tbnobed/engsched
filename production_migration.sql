-- Complete production database migration script
-- This preserves all data while fixing table naming

-- Step 1: Add missing columns to existing tables if they don't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS theme_preference VARCHAR(20) DEFAULT 'light';
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_picture VARCHAR(500);

ALTER TABLE ticket ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;

ALTER TABLE quick_link ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE quick_link ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Step 2: Rename the table
ALTER TABLE users RENAME TO "user";

-- Step 3: Verify the changes
SELECT 'Table renamed successfully' as status, COUNT(*) as user_count FROM "user";
SELECT 'Columns added successfully' as status, 
       column_name 
FROM information_schema.columns 
WHERE table_name = 'user' 
  AND column_name IN ('theme_preference', 'profile_picture');