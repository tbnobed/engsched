from app import app, db
from models import User

with app.app_context():
    # Create the new theme_preference column
    db.create_all()
    print('Database updated with new theme_preference field')