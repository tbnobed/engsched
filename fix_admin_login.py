#!/usr/bin/env python3
"""
Fix admin login by resetting password to admin123
"""
import os
from werkzeug.security import generate_password_hash
from app import app, db
from models import User

def fix_admin_login():
    with app.app_context():
        # Find admin user
        admin = User.query.filter_by(email='admin@obedtv.com').first()
        if not admin:
            print("Admin user not found!")
            return
            
        # Reset password to admin123
        new_password = 'admin123'
        admin.password_hash = generate_password_hash(new_password)
        
        try:
            db.session.commit()
            print(f"Successfully reset password for {admin.email}")
            print(f"Login with: admin@obedtv.com / {new_password}")
        except Exception as e:
            print(f"Error updating password: {e}")
            db.session.rollback()

if __name__ == '__main__':
    fix_admin_login()