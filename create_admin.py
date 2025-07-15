from app import app, db
from models import User
import pytz
import sqlalchemy.exc
import logging

def create_admin():
    with app.app_context():
        try:
            # First approach: Try to find and update existing admin by username
            existing_admin_username = User.query.filter_by(username='admin').first()
            if existing_admin_username:
                print(f"Admin user with username 'admin' already exists. Updating credentials...")
                
                # Update the existing admin account
                existing_admin_username.email = 'admin@obedtv.com'
                existing_admin_username.is_admin = True
                existing_admin_username.set_password('TBN@dmin!!')
                existing_admin_username.color = '#3498db'
                existing_admin_username.timezone = 'America/Chicago'
                existing_admin_username.theme_preference = 'dark'
                db.session.commit()
                print("Admin account updated successfully.")
                return
                
            # Second approach: Try to find and update existing admin by email
            existing_admin_email = User.query.filter_by(email='admin@obedtv.com').first()
            if existing_admin_email:
                print(f"Admin user with email 'admin@obedtv.com' already exists. Updating credentials...")
                
                # Update the existing admin account
                existing_admin_email.username = 'admin'
                existing_admin_email.is_admin = True
                existing_admin_email.set_password('TBN@dmin!!')
                existing_admin_email.color = '#3498db'
                existing_admin_email.timezone = 'America/Chicago'
                existing_admin_email.theme_preference = 'dark'
                db.session.commit()
                print("Admin account updated successfully.")
                return

            # Third approach: Create a new admin account
            print("No admin account found. Creating new admin account...")
            admin = User(
                username='admin',
                email='admin@obedtv.com',
                is_admin=True,
                color='#3498db',  # Blue color
                timezone='America/Chicago',  # Default timezone
                theme_preference='dark'  # Default theme
            )
            admin.set_password('TBN@dmin!!')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully:")
            print(f"Username: admin")
            print(f"Email: admin@obedtv.com")
            print(f"Password: TBN@dmin!!")
            
        except sqlalchemy.exc.IntegrityError as e:
            # Handle the case where the unique constraint is violated
            db.session.rollback()
            print(f"Database integrity error: {e}")
            print("Attempting alternative approach...")
            
            # Since we have an integrity error, we know some part of the admin account exists
            # Let's use direct SQL to update the admin account safely
            try:
                print("Updating existing admin account via direct SQL...")
                from sqlalchemy import text
                
                # Update admin by username - safer approach
                query = text("""
                    UPDATE "user" 
                    SET email = 'admin@obedtv.com', 
                        is_admin = TRUE,
                        color = '#3498db',
                        timezone = 'America/Chicago',
                        theme_preference = 'dark'
                    WHERE username = 'admin'
                """)
                db.session.execute(query)
                
                # Now update the password - safe even if the above didn't match anything
                admin_user = User.query.filter_by(username='admin').first()
                if admin_user:
                    admin_user.set_password('TBN@dmin!!')
                    db.session.commit()
                    print("Admin password updated successfully.")
                else:
                    print("Could not find admin user to update password.")
                
                print("Admin account updated via direct SQL.")
                db.session.commit()
            except Exception as sql_error:
                db.session.rollback()
                print(f"Failed to update admin account: {sql_error}")
                raise
                
        except Exception as general_error:
            db.session.rollback()
            print(f"Unexpected error: {general_error}")
            raise

if __name__ == '__main__':
    create_admin()
