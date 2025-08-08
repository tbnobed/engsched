#!/bin/bash
# Production sequence fix script
# Usage: ./fix_sequences.sh

echo "Fixing PostgreSQL sequences..."

docker exec -it postschedv3-db-1 psql -U technician_scheduler_user -d technician_scheduler -f /docker-entrypoint-initdb.d/fix_sequences.sql

echo "Sequence fix completed!"

# Verify the fix worked
echo "Verifying sequences..."
docker exec -it postschedv3-db-1 psql -U technician_scheduler_user -d technician_scheduler -c "
SELECT 'ticket_comment' as table_name, 
       (SELECT MAX(id) FROM ticket_comment) as max_id,
       nextval('ticket_comment_id_seq') as next_sequence_value;"