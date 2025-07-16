-- Update database schema for unread activity indicators feature
-- This script adds the ticket_view table if it doesn't exist

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

-- Log the update
DO $$
BEGIN
    RAISE NOTICE 'TicketView table and indexes created successfully for unread activity indicators';
END $$;