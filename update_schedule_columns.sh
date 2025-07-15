#!/bin/bash
# Script to update the schedule table schema by adding missing columns
# This fixes the error: "sqlalchemy.exc.ProgrammingError: column schedule.created_at does not exist"

set -e  # Exit immediately if a command exits with a non-zero status

echo "=== Plex Technician Scheduler Database Schema Update ==="
echo "This script will add the missing created_at and location_id columns to the schedule table"
echo

# Check if the database container is running
if ! docker ps | grep -q "postgres"; then
    echo "Error: Database container is not running"
    echo "Please start your database container first"
    exit 1
fi

echo "Applying schema updates..."

# Get the database container name
DB_CONTAINER=$(docker ps | grep postgres | awk '{print $1}')

if [ -z "$DB_CONTAINER" ]; then
    echo "Error: Could not find the PostgreSQL container"
    exit 1
fi

# Run the SQL update script
cat add_schedule_created_at.sql | docker exec -i $DB_CONTAINER psql -U technician_scheduler_user -d technician_scheduler

echo
echo "Schema update completed successfully!"
echo "The missing 'created_at' and 'location_id' columns have been added to the schedule table."
echo
echo "You should now restart your application containers:"
echo "  docker-compose down"
echo "  docker-compose up -d"