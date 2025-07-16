#!/usr/bin/env python3
"""
Create ticket_view table for tracking when users last viewed tickets
"""
import os
import sys
from sqlalchemy import create_engine, text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_ticket_view_table():
    """Create the ticket_view table in the database"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # SQL to create the ticket_view table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS ticket_view (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
            last_viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(user_id, ticket_id)
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_ticket_view_user_id ON ticket_view(user_id);
        CREATE INDEX IF NOT EXISTS idx_ticket_view_ticket_id ON ticket_view(ticket_id);
        CREATE INDEX IF NOT EXISTS idx_ticket_view_last_viewed ON ticket_view(last_viewed_at);
        """
        
        # Execute the SQL
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
        
        logger.info("✅ Successfully created ticket_view table with indexes")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating ticket_view table: {str(e)}")
        return False

if __name__ == "__main__":
    success = create_ticket_view_table()
    sys.exit(0 if success else 1)