from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models import User
from forms import LoginForm, RegistrationForm

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Check if user is on mobile device and redirect appropriately
        from app import is_mobile_device
        if is_mobile_device():
            return redirect('/mobile/dashboard')
        else:
            return redirect(url_for('tickets.tickets_dashboard'))
    
    # Add debug logging for the session
    from app import app
    from flask import session
    app.logger.debug(f"Login attempt - Method: {request.method}")
    app.logger.debug(f"Session before login: {session}")
    
    form = LoginForm()
    if form.validate_on_submit():
        # Make input lowercase for case-insensitive login
        login_input = form.email.data if form.email.data else ""
        app.logger.debug(f"Login form submitted for email: {login_input}")
        
        # Initialize user to None
        user = None
        
        # Check if this is a username or email login
        if '@' in login_input:
            # Login with email (case-insensitive using SQL LOWER function)
            email_search = login_input.lower()
            app.logger.debug(f"Looking up by email (lowercase): {email_search}")
            
            # PostgreSQL LOWER function for proper case-insensitive compare
            query = User.query.filter(db.func.lower(User.email) == db.func.lower(email_search))
            app.logger.debug(f"SQL query: {query}")
            
            # Execute the query
            user = query.first()
            
            # If no user found, try to get all emails for debugging
            if not user:
                all_emails = [u.email for u in User.query.all()]
                app.logger.debug(f"All emails in database: {all_emails}")
                
                # Also try a direct query with LIKE for debugging
                like_users = User.query.filter(User.email.ilike(f"%{email_search}%")).all()
                app.logger.debug(f"Users with similar emails: {[u.email for u in like_users]}")
        else:
            # Case-insensitive username search using SQL LOWER function
            app.logger.debug(f"Looking up by username (case-insensitive): {login_input}")
            username_search = login_input.lower()
            
            # PostgreSQL LOWER function for proper case-insensitive compare
            query = User.query.filter(db.func.lower(User.username) == db.func.lower(username_search))
            app.logger.debug(f"SQL query: {query}")
            
            # Execute the query
            user = query.first()
            
            # If no user found, try to get all usernames for debugging
            if not user:
                all_usernames = [u.username for u in User.query.all()]
                app.logger.debug(f"All usernames in database: {all_usernames}")
                
                # Also try a direct query with LIKE for debugging
                like_users = User.query.filter(User.username.ilike(f"%{username_search}%")).all()
                app.logger.debug(f"Users with similar usernames: {[u.username for u in like_users]}")
            
        # Debug log what we found
        if user:
            app.logger.debug(f"Found user: {user.username}, {user.email}")
        else:
            app.logger.warning(f"Failed login attempt for email: {login_input}")
            
        # Try password check if we found a user
        if user and user.check_password(form.password.data):
            # Log the successful login with more details
            app.logger.info(f"User {user.username} logged in successfully")
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            app.logger.debug(f"Session after login: {session}")
            
            # Check if user is on mobile device and redirect appropriately
            from app import is_mobile_device
            mobile_detected = is_mobile_device()
            app.logger.debug(f"Login redirect decision - next_page: {next_page}, mobile_detected: {mobile_detected}")
            
            if next_page:
                app.logger.debug(f"Redirecting to next page: {next_page}")
                return redirect(next_page)
            elif mobile_detected:
                app.logger.debug("Mobile device detected after login - redirecting to mobile dashboard")
                return redirect('/mobile/dashboard')
            else:
                app.logger.debug("Desktop device detected after login - redirecting to tickets dashboard")
                return redirect(url_for('tickets.tickets_dashboard'))
            
        app.logger.warning(f"Invalid credentials for login input: {login_input}")
        flash('Invalid username/email or password')
        
    return render_template('login.html', form=form)

# Registration is disabled - only admins can create users
@auth.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect to login page
    flash('Self-registration is disabled. Please contact your administrator for access.', 'warning')
    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
    
@auth.route('/debug_users')
def debug_users():
    from app import app
    
    # Only allow this in development
    if not app.debug:
        return "Debug mode is disabled", 403
        
    # Get all users and format their info
    users = User.query.all()
    user_info = []
    for user in users:
        user_info.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        })
        
    import json
    return json.dumps(user_info, indent=2), 200, {'Content-Type': 'application/json'}
