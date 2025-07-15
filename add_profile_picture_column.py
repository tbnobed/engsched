#!/usr/bin/env python3
"""
Add profile_picture column to the user table
"""
import os
import sys
import psycopg2
from psycopg2 import sql

def add_profile_picture_column():
    """Add profile_picture column to user table"""
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("ERROR: DATABASE_URL environment variable not set")
            return False
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("Adding profile_picture column to user table...")
        
        # Add the profile_picture column
        cursor.execute("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS profile_picture VARCHAR(255) NULL;
        """)
        
        conn.commit()
        print("Successfully added profile_picture column to user table")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error adding profile_picture column: {e}")
        return False

if __name__ == "__main__":
    success = add_profile_picture_column()
    if not success:
        sys.exit(1)
    print("Migration completed successfully!")