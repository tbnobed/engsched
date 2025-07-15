-- SQL script to add timezone column to user table if it doesn't exist

DO $$
BEGIN
    -- Check if the timezone column exists
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'user'
        AND column_name = 'timezone'
    ) THEN
        -- Add the timezone column with default value
        ALTER TABLE "user" ADD COLUMN timezone VARCHAR(50) DEFAULT 'America/Los_Angeles';
        RAISE NOTICE 'Added timezone column to user table';
    ELSE
        RAISE NOTICE 'Timezone column already exists in user table';
    END IF;
END $$;