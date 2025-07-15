#!/bin/bash
# Database schema update script for Plex Technician Scheduler
# This script should be run after a PostgreSQL upgrade or when database schema changes are needed

set -e  # Exit immediately if a command exits with a non-zero status

echo "=== Plex Technician Scheduler Database Update ==="
echo "This script will update your database schema to match the current application version."
echo

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed or not in the PATH"
    exit 1
fi

# Check if the containers are running
if ! docker-compose ps | grep -q "db.*Up"; then
    echo "Starting database container..."
    docker-compose up -d db
    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    sleep 10
fi

echo "Applying schema updates..."
# Run the SQL update script
cat update_schema.sql | docker-compose exec -T db psql -U technician_scheduler_user -d technician_scheduler

echo
echo "Schema update completed."
echo "You can now restart your application with:"
echo "  docker-compose down && docker-compose up -d"
echo