#!/bin/bash

# Script to update the user table in the database with a timezone column

# Ensure script errors aren't ignored
set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    source .env
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    # Try to build from components if available
    if [ -n "$POSTGRES_USER" ] && [ -n "$POSTGRES_PASSWORD" ] && [ -n "$POSTGRES_HOST" ] && [ -n "$POSTGRES_PORT" ] && [ -n "$POSTGRES_DB" ]; then
        DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
    else
        echo "Error: DATABASE_URL not set and cannot be constructed from components."
        echo "Please set DATABASE_URL environment variable or provide the database connection details."
        exit 1
    fi
fi

echo "Using database connection: $DATABASE_URL"
echo "Running timezone column update SQL script..."

# Execute the SQL script using psql
if [ -f "update_timezone_field.sql" ]; then
    psql "$DATABASE_URL" -f update_timezone_field.sql
else
    # Alternatively, execute the SQL directly
    psql "$DATABASE_URL" << EOF
    DO \$\$
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
    END \$\$;
EOF
fi

echo "Timezone column update complete."
echo
echo "Alternatively, you can run the Python update script with:"
echo "python update_timezone_field.py"