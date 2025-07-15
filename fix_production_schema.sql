-- Fix production database table naming inconsistency
-- Run this SQL script in your production database

-- Rename the users table to user (with quotes for reserved word)
ALTER TABLE users RENAME TO "user";

-- Update foreign key constraint names if needed (PostgreSQL handles this automatically)
-- Verify the change worked
SELECT table_name FROM information_schema.tables WHERE table_name = 'user';