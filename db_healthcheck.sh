#!/bin/bash
# Script to check PostgreSQL database connectivity
# This is useful for troubleshooting database connection issues

set -e

# Source environment variables if .env file exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Check if required environment variables are set
if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
    echo "Error: Required environment variables not set."
    echo "Please make sure POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB are defined."
    exit 1
fi

echo "=== PostgreSQL Database Connection Check ==="

# Try connecting to the database using the Docker container
if command -v docker &> /dev/null; then
    echo "Checking database connection using Docker..."
    
    # Get the database container ID
    DB_CONTAINER=$(docker ps | grep postgres | awk '{print $1}')
    
    if [ -z "$DB_CONTAINER" ]; then
        echo "Error: No PostgreSQL container found."
        echo "Make sure the database container is running."
    else
        echo "Found PostgreSQL container: $DB_CONTAINER"
        
        # Test the database connection
        echo "Testing database connection..."
        docker exec -i $DB_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 'Connection successful!' as status;" || {
            echo "Error: Failed to connect to the database."
            exit 1
        }
    fi
else
    # If Docker is not available, try with psql directly
    echo "Docker not found, checking database connection using psql..."
    
    if command -v psql &> /dev/null; then
        # Check if DATABASE_URL is set
        if [ -n "$DATABASE_URL" ]; then
            echo "Testing database connection using DATABASE_URL..."
            PGPASSWORD=$POSTGRES_PASSWORD psql "$DATABASE_URL" -c "SELECT 'Connection successful!' as status;" || {
                echo "Error: Failed to connect to the database using DATABASE_URL."
                exit 1
            }
        else
            echo "Testing database connection using individual parameters..."
            PGPASSWORD=$POSTGRES_PASSWORD psql -h localhost -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 'Connection successful!' as status;" || {
                echo "Error: Failed to connect to the database."
                exit 1
            }
        fi
    else
        echo "Error: psql client not found."
        echo "Please install PostgreSQL client tools to use this script."
        exit 1
    fi
fi

echo ""
echo "Database connection check completed successfully!"
echo "The database is accessible and ready for use."