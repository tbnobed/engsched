#!/bin/bash
set -e

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

if [ "$1" = "gunicorn" ] || [ "$1" = "python" ] || [ "$1" = "flask" ]; then
  wait_for_postgres
  
  echo "============================================"
  echo "Running comprehensive schema verification..."
  echo "============================================"
  if [ -f "/app/ensure_schema.sql" ]; then
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /app/ensure_schema.sql
    if [ $? -eq 0 ]; then
      echo "Schema verification completed successfully"
    else
      echo "WARNING: Schema verification had errors - continuing anyway"
    fi
  else
    echo "WARNING: ensure_schema.sql not found - skipping schema verification"
  fi
  echo "============================================"
  
  echo "Starting the application with: $@"
  exec "$@"
fi

exec "$@"
