"""
Add the 'archived' column to the ticket table
"""
from app import app, db
from models import Ticket

# Update the ticket table by adding the 'archived' column
with app.app_context():
    from sqlalchemy import Boolean
    from flask import current_app
    
    # Print current columns in the table
    print("Current columns in the ticket table:")
    for column in Ticket.__table__.columns:
        print(f"  - {column.name}: {column.type}")
    
    # Check if the column already exists in the database
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('ticket')]
    
    if 'archived' not in columns:
        print("\nThe 'archived' column does not exist in the database. Adding it now...")
        
        # Add the column with a direct SQL command
        sql = text("ALTER TABLE ticket ADD COLUMN archived BOOLEAN DEFAULT FALSE")
        db.session.execute(sql)
        db.session.commit()
        
        print("Column 'archived' added successfully!")
    else:
        print("\nThe 'archived' column already exists in the database.")
    
    # Verify the column exists now
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('ticket')]
    if 'archived' in columns:
        print("\nVerified: 'archived' column exists in the ticket table.")
    else:
        print("\nERROR: 'archived' column still does not exist in the ticket table.")