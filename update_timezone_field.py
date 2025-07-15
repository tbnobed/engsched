"""
Add the 'timezone' column to the user table if it doesn't exist
This is meant to be run as a standalone script when updating an existing database
"""
import logging
import os
import sys
from sqlalchemy import Column, String, MetaData, Table, inspect, create_engine
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Get the database URL from environment or configuration
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable is not set")
        sys.exit(1)

    # Create SQLAlchemy engine
    engine = create_engine(database_url)
    metadata = MetaData()
    
    # Get inspector for checking columns
    inspector = inspect(engine)

    try:
        # Check if 'timezone' column exists in user table
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        if 'timezone' not in columns:
            logger.info("Adding 'timezone' column to user table...")
            
            # Define the 'user' table with the existing schema
            # We only need to reference it for the alter table operation
            user_table = Table('user', metadata, autoload_with=engine)
            
            # Create a connection and execute the alter table command
            with engine.begin() as conn:
                # Add the timezone column with a default value
                conn.execute(f"ALTER TABLE \"user\" ADD COLUMN timezone VARCHAR(50) DEFAULT 'America/Los_Angeles'")
                logger.info("Added 'timezone' column to the user table")
        else:
            logger.info("The 'timezone' column already exists in the user table")
            
    except SQLAlchemyError as e:
        logger.error(f"Error updating database schema: {e}")
        sys.exit(1)

    logger.info("Database schema update completed successfully")

if __name__ == "__main__":
    main()