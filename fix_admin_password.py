from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def fix_admin_password():
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if admin:
            admin.password_hash = generate_password_hash('admin')
            db.session.commit()
            print(f"Updated admin password to 'admin'")
        else:
            print("Admin user not found. Please run create_admin.py first.")

if __name__ == '__main__':
    fix_admin_password()