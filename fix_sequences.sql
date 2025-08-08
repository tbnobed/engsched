-- PostgreSQL sequence fix script
-- Run this after any database import/restore

-- Fix ticket_comment sequence
SELECT setval('ticket_comment_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM ticket_comment), false);

-- Fix other sequences that might have the same issue
SELECT setval('ticket_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM ticket), false);
SELECT setval('user_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM "user"), false);
SELECT setval('ticket_history_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM ticket_history), false);
SELECT setval('ticket_category_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM ticket_category), false);

-- Display current sequence values for verification
SELECT 'ticket_comment' as table_name, currval('ticket_comment_id_seq') as current_value, (SELECT MAX(id) FROM ticket_comment) as max_id;
SELECT 'ticket' as table_name, currval('ticket_id_seq') as current_value, (SELECT MAX(id) FROM ticket) as max_id;
SELECT 'user' as table_name, currval('user_id_seq') as current_value, (SELECT MAX(id) FROM "user") as max_id;
SELECT 'ticket_history' as table_name, currval('ticket_history_id_seq') as current_value, (SELECT MAX(id) FROM ticket_history) as max_id;
SELECT 'ticket_category' as table_name, currval('ticket_category_id_seq') as current_value, (SELECT MAX(id) FROM ticket_category) as max_id;