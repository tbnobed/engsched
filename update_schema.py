#!/usr/bin/env python3
"""
Database schema update script for Plex Technician Scheduler application.
This script checks for missing columns in the database schema and adds them if needed.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get database connection details from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set. Please set it before running this script.")
    sys.exit(1)

def check_column_exists(conn, table, column):
    """Check if a column exists in the specified table."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = %s
        """, (table, column))
        return cursor.fetchone() is not None

def add_column(conn, table, column, data_type, default=None):
    """Add a column to the specified table."""
    with conn.cursor() as cursor:
        if default is not None:
            cursor.execute(sql.SQL("""
                ALTER TABLE {} ADD COLUMN IF NOT EXISTS {} {} DEFAULT {}
            """).format(
                sql.Identifier(table),
                sql.Identifier(column),
                sql.SQL(data_type),
                sql.SQL(default)
            ))
        else:
            cursor.execute(sql.SQL("""
                ALTER TABLE {} ADD COLUMN IF NOT EXISTS {} {}
            """).format(
                sql.Identifier(table),
                sql.Identifier(column),
                sql.SQL(data_type)
            ))
        conn.commit()
        logger.info(f"Added column '{column}' to table '{table}'")

def main():
    """Main function to update the database schema."""
    conn = None
    try:
        logger.info("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        
        # Check and add any missing columns
        schema_updates = [
            # Table name, column name, data type, default value
            ("user", "theme_preference", "VARCHAR(20)", "'dark'"),
            ("ticket", "archived", "BOOLEAN", "false"),
            # Add any other missing columns here
        ]
        
        for table, column, data_type, default in schema_updates:
            if not check_column_exists(conn, table, column):
                logger.info(f"Column '{column}' does not exist in table '{table}'. Adding it...")
                add_column(conn, table, column, data_type, default)
            else:
                logger.info(f"Column '{column}' already exists in table '{table}'. Skipping.")
        
        # Run a VACUUM operation to optimize the database
        logger.info("Running VACUUM to optimize database...")
        # Need to run vacuum outside a transaction
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cursor:
            cursor.execute("VACUUM ANALYZE")
        
        logger.info("Database schema update completed successfully.")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    main()