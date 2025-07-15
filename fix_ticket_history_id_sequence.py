"""
Fix the ticket_history table sequence to prevent duplicate key errors.
This script resets the sequence for ticket_history table's id column to the maximum ID + 1.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db = SQLAlchemy(app)

def fix_ticket_history_sequence():
    """Reset the ticket_history ID sequence to prevent ID conflicts"""
    with app.app_context():
        # Execute raw SQL to get the max ID
        result = db.session.execute(text("SELECT MAX(id) FROM ticket_history")).fetchone()
        max_id = result[0] if result and result[0] is not None else 0
        
        # Calculate the next ID
        next_id = max_id + 1
        print(f"Current max ticket_history ID: {max_id}")
        print(f"Setting sequence to start at: {next_id}")
        
        # Reset the sequence
        sql = text(f"SELECT setval('ticket_history_id_seq', {next_id}, false)")
        db.session.execute(sql)
        db.session.commit()
        
        # Verify the sequence was reset
        result = db.session.execute(text("SELECT last_value FROM ticket_history_id_seq")).fetchone()
        print(f"Sequence reset to: {result[0] if result else 'Unknown'}")
        
        print("Ticket history sequence has been fixed.")

if __name__ == "__main__":
    fix_ticket_history_sequence()