-- Database schema update for External User Support (Option 3)
-- This script adds the necessary columns and indexes for email-only communication

-- Add external user columns to ticket table (with IF NOT EXISTS to avoid errors)
DO $$
BEGIN
    -- Add external_email column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ticket' AND column_name = 'external_email') THEN
        ALTER TABLE ticket ADD COLUMN external_email VARCHAR(255);
    END IF;
    
    -- Add external_name column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ticket' AND column_name = 'external_name') THEN
        ALTER TABLE ticket ADD COLUMN external_name VARCHAR(255);
    END IF;
    
    -- Add email_notifications column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ticket' AND column_name = 'email_notifications') THEN
        ALTER TABLE ticket ADD COLUMN email_notifications BOOLEAN DEFAULT TRUE;
    END IF;
    
    -- Add email_thread_id column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ticket' AND column_name = 'email_thread_id') THEN
        ALTER TABLE ticket ADD COLUMN email_thread_id VARCHAR(100);
    END IF;
END $$;

-- Create indexes for external user support (with IF NOT EXISTS to avoid errors)
CREATE INDEX IF NOT EXISTS idx_ticket_external_email ON ticket(external_email);
CREATE INDEX IF NOT EXISTS idx_ticket_email_thread_id ON ticket(email_thread_id);
CREATE INDEX IF NOT EXISTS idx_ticket_external_notifications ON ticket(email_notifications) WHERE external_email IS NOT NULL;

-- Update any existing tickets to have email_notifications = TRUE if they don't have a value
UPDATE ticket SET email_notifications = TRUE WHERE email_notifications IS NULL;