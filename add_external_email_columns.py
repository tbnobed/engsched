#!/usr/bin/env python3
"""
Add external email columns to the ticket table for Option 3 implementation
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def add_external_email_columns():
    """Add external email tracking columns to ticket table"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Create engine and connect
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                print("Adding external email columns to ticket table...")
                
                # Add new columns for external user tracking
                conn.execute(text("""
                    ALTER TABLE ticket 
                    ADD COLUMN IF NOT EXISTS external_email VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS external_name VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS email_notifications BOOLEAN DEFAULT TRUE,
                    ADD COLUMN IF NOT EXISTS email_thread_id VARCHAR(50);
                """))
                
                # Create index for email lookups
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_ticket_external_email 
                    ON ticket(external_email);
                """))
                
                # Create index for thread ID lookups
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_ticket_email_thread_id 
                    ON ticket(email_thread_id);
                """))
                
                trans.commit()
                print("✓ Successfully added external email columns")
                print("✓ Created indexes for email lookups")
                
            except Exception as e:
                trans.rollback()
                print(f"ERROR: Failed to add columns: {e}")
                sys.exit(1)
                
    except SQLAlchemyError as e:
        print(f"ERROR: Database connection failed: {e}")
        sys.exit(1)
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    add_external_email_columns()