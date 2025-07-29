-- Update database schema for unread activity indicators feature and quick_link fixes
-- This script adds the ticket_view table and fixes the quick_link description column

-- Create ticket_view table for tracking when users last viewed tickets
CREATE TABLE IF NOT EXISTS ticket_view (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    last_viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, ticket_id)
);

-- Create indexes for performance (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_ticket_view_user_id ON ticket_view(user_id);
CREATE INDEX IF NOT EXISTS idx_ticket_view_ticket_id ON ticket_view(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_view_last_viewed ON ticket_view(last_viewed_at);

-- Add description column to quick_link table if it doesn't exist
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

-- Log the update
DO $$
BEGIN
    RAISE NOTICE 'Database schema updates completed: TicketView table and quick_link description column';
END $$;