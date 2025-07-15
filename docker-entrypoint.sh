#!/bin/bash
set -e

# Function to wait for the PostgreSQL database to be ready
wait_for_postgres() {
  echo "Waiting for PostgreSQL to be ready..."
  
  local max_attempts=30
  local attempt=0
  local sleep_time=5
  
  while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt+1))
    echo "Attempt $attempt of $max_attempts..."
    
    if pg_isready -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
      echo "PostgreSQL is up and running!"
      return 0
    fi
    
    echo "PostgreSQL is not ready yet. Waiting $sleep_time seconds..."
    sleep $sleep_time
  done
  
  echo "Failed to connect to PostgreSQL after $max_attempts attempts."
  return 1
}

# Wait for PostgreSQL before starting the application
if [ "$1" = "gunicorn" ] || [ "$1" = "python" ] || [ "$1" = "flask" ]; then
  wait_for_postgres
  
  # Check if database schema needs updating
  echo "Checking database schema..."
  if [ -f "/app/update_database_schema.sql" ]; then
    echo "Running database schema updates..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /app/update_database_schema.sql
    if [ $? -eq 0 ]; then
      echo "Database schema updated successfully"
    else
      echo "Database schema update failed - continuing anyway"
    fi
  fi
  
  echo "Starting the application with: $@"
  exec "$@"
fi

# If the command does not start with application commands (e.g., bash, sh), execute it directly
exec "$@"