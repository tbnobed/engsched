import os
import logging
import re
from datetime import timedelta, datetime
from flask import Flask, jsonify, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from sqlalchemy.orm import DeclarativeBase
import pytz
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

# Create the app
app = Flask(__name__)

# Custom Jinja2 filters
@app.template_filter('nl2br')
def nl2br_filter(s):
    """Convert newlines to HTML line breaks"""
    if not s:
        return ""
    return Markup(s.replace('\n', '<br>\n'))

@app.template_filter('rgb_values')
def hex_to_rgb_filter(hex_color):
    """Convert hex color to RGB values for CSS rgba()"""
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    try:
        return f"{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}"
    except (ValueError, IndexError):
        return "128, 128, 128"  # Default gray

# Function to detect mobile devices
def is_mobile_device():
    """Check if the user is using a mobile device"""
    from flask import request
    import re
    
    user_agent = request.headers.get('User-Agent', '').lower()
    # Pattern to match common mobile devices
    pattern = r"android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini|mobile"
    
    # Debug the detection logic
    app.logger.debug(f"User-Agent: {user_agent}")
    is_mobile = bool(re.search(pattern, user_agent))
    app.logger.debug(f"is_mobile_device detection result: {is_mobile}")
    
    return is_mobile

# Configuration
app.secret_key = os.environ.get("SESSION_SECRET") or "dev-secret-key-change-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# Configuration for URL generation outside of request context (used in emails)
# We're NOT setting SERVER_NAME directly as it breaks route matching in development
# Instead, we'll use these values in email_utils.py
app.config["APPLICATION_ROOT"] = "/"
app.config["PREFERRED_URL_SCHEME"] = "http"
app.config["EMAIL_DOMAIN"] = os.environ.get("EMAIL_DOMAIN", "localhost:5000")

# Site branding configuration
app.config["SITE_NAME"] = os.environ.get("SITE_NAME", "Plex Engineering")
app.config["SITE_TITLE"] = os.environ.get("SITE_TITLE", "Tech Scheduler")
app.config["SITE_DESCRIPTION"] = os.environ.get("SITE_DESCRIPTION", "Technician Scheduling and Management System")
app.config["COMPANY_NAME"] = os.environ.get("COMPANY_NAME", "Plex Engineering")
app.config["SITE_LOGO"] = os.environ.get("SITE_LOGO", "images/tbn_logo.webp")

# Set session configuration
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_PATH'] = '/'

# Set default timezone
app.config['TIMEZONE'] = pytz.timezone('UTC')

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    logger.debug(f"Loading user with ID: {user_id}")
    logger.debug(f"Current session data: {session}")
    logger.debug(f"Request cookies: {request.cookies}")
    logger.debug(f"Request path: {request.path}")
    logger.debug(f"Request headers: {request.headers}")

    try:
        user = User.query.get(int(user_id))
        if user:
            logger.debug(f"Successfully loaded user: {user.username}")
            logger.debug(f"User data: id={user.id}, email={user.email}, is_admin={getattr(user, 'is_admin', False)}")
        else:
            logger.warning(f"No user found with ID: {user_id}")
        return user
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {str(e)}")
        return None

# Custom unauthorized handler
@login_manager.unauthorized_handler
def unauthorized():
    logger.debug(f"Unauthorized access to path: {request.path}")
    logger.debug(f"Current user authenticated: {current_user.is_authenticated}")
    logger.debug(f"Session data: {session}")
    logger.debug(f"Request cookies: {request.cookies}")

    if request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('login', next=request.url))

# Favicon and Apple Touch Icon routes
@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='images/tbn_logo.webp'))

@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
@app.route('/apple-touch-icon-120x120.png')
@app.route('/apple-touch-icon-120x120-precomposed.png')
def apple_touch_icon():
    return redirect(url_for('static', filename='images/tbn_logo.webp'))

def attempt_db_connection_with_retry():
    """
    Attempt to connect to the database with retry logic
    This helps during container orchestration when the database might not be ready
    """
    import time
    import sqlalchemy.exc
    max_retries = 30  # Retry for up to 5 minutes (30 * 10 seconds)
    retry_count = 0
    
    logger.info("Attempting to connect to the database...")
    
    while retry_count < max_retries:
        try:
            # Attempt to connect to the database and create tables
            with app.app_context():
                import models
                engine = db.engine
                # Test connection
                conn = engine.connect()
                conn.close()
                logger.info("Successfully connected to the database!")
                
                # Create tables
                db.create_all()
                logger.info("Database tables created successfully!")
                return True
        except sqlalchemy.exc.OperationalError as e:
            retry_count += 1
            logger.warning(f"Database connection attempt {retry_count}/{max_retries} failed: {str(e)}")
            if retry_count < max_retries:
                logger.info(f"Retrying in 10 seconds...")
                time.sleep(10)
            else:
                logger.error("Maximum retry attempts reached. Could not connect to the database.")
                raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {str(e)}")
            raise
    
    return False

# Initialize database with retry logic
attempt_db_connection_with_retry()

# Import models after database is ready
with app.app_context():
    import models

# Initialize the automatic scheduler for recurring schedules
def auto_generate_recurring_schedules_job():
    """Background job to automatically generate recurring schedules"""
    from models import RecurringScheduleTemplate, Schedule
    
    with app.app_context():
        try:
            app.logger.info("Running automatic recurring schedule generation...")
            
            # Find all active templates that need schedule generation
            templates = RecurringScheduleTemplate.query.filter_by(active=True, auto_generate=True).all()
            
            total_generated = 0
            generated_templates = []
            
            for template in templates:
                # Check if it's time to generate new schedules
                should_generate = False
                
                if not template.last_generated:
                    should_generate = True
                    app.logger.info(f"Template '{template.template_name}' never generated, generating now")
                else:
                    # Calculate time since last generation
                    time_since_last = datetime.now(pytz.UTC) - template.last_generated
                    if time_since_last.days >= 7:  # Generate weekly
                        should_generate = True
                        app.logger.info(f"Template '{template.template_name}' last generated {time_since_last.days} days ago, generating now")
                
                if should_generate:
                    try:
                        schedules = template.generate_schedules()
                        
                        if schedules:
                            for schedule in schedules:
                                db.session.add(schedule)
                            
                            template.last_generated = datetime.now(pytz.UTC)
                            total_generated += len(schedules)
                            
                            generated_templates.append({
                                'template_name': template.template_name,
                                'technician': template.technician.username,
                                'schedules_generated': len(schedules)
                            })
                            app.logger.info(f"Generated {len(schedules)} schedules for template '{template.template_name}'")
                        else:
                            # Check for OOO conflicts to provide better logging
                            from datetime import date, timedelta
                            start_date = date.today()
                            end_date = start_date + timedelta(weeks=template.weeks_ahead or 2)
                            
                            ooo_conflicts = Schedule.query.filter(
                                Schedule.technician_id == template.technician_id,
                                Schedule.time_off == True,
                                Schedule.all_day == True,
                                Schedule.start_time >= pytz.UTC.localize(datetime.combine(start_date, datetime.min.time())),
                                Schedule.start_time <= pytz.UTC.localize(datetime.combine(end_date, datetime.max.time()))
                            ).count()
                            
                            if ooo_conflicts > 0:
                                app.logger.info(f"No schedules generated for template '{template.template_name}' - {ooo_conflicts} OOO conflicts prevented generation")
                            else:
                                app.logger.warning(f"No schedules generated for template '{template.template_name}' - all schedules may already exist")
                            
                    except Exception as template_error:
                        app.logger.error(f"Error generating schedules for template '{template.template_name}': {str(template_error)}")
                        continue
            
            db.session.commit()
            app.logger.info(f"Automatic schedule generation completed. Total schedules generated: {total_generated}")
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in automatic recurring schedule generation: {str(e)}")

# Set up the background scheduler
scheduler = BackgroundScheduler()

# Schedule the auto-generation to run every Sunday at 2:00 AM
scheduler.add_job(
    func=auto_generate_recurring_schedules_job,
    trigger="cron",
    day_of_week="sun",
    hour=2,
    minute=0,
    id='auto_generate_schedules',
    name='Auto-generate recurring schedules',
    replace_existing=True
)

# Start the scheduler
scheduler.start()
app.logger.info("Automatic recurring schedule generator started - runs every Sunday at 2:00 AM")

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

# Import and register blueprints
from routes import *
from ticket_routes import tickets, get_active_sidebar_tickets
# Register health check for container healthchecks
from health import health_bp
app.register_blueprint(tickets)
app.register_blueprint(health_bp)

# Register the get_active_sidebar_tickets function with the app context
@app.context_processor
def inject_active_sidebar_tickets():
    return dict(get_active_sidebar_tickets=get_active_sidebar_tickets)

@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.now()}

@app.context_processor
def inject_mobile_detection():
    """Inject mobile device detection function into templates"""
    return {'is_mobile': is_mobile_device}

@app.context_processor
def inject_site_branding():
    """Inject site branding configuration into templates"""
    return dict(
        site_name=app.config["SITE_NAME"],
        site_title=app.config["SITE_TITLE"],
        site_description=app.config["SITE_DESCRIPTION"],
        company_name=app.config["COMPANY_NAME"],
        site_logo=app.config["SITE_LOGO"]
    )

@app.context_processor
def inject_chat_config():
    """Inject chat configuration into templates"""
    chat_enabled = os.environ.get('CHAT_ENABLED', 'true').lower()
    return {
        'CHAT_ENABLED': chat_enabled in ['true', '1', 'yes', 'on'],
        'CHAT_URL': os.environ.get('CHAT_URL', 'https://chat.obedtv.com')
    }

# API Routes 
# Note: API routes are defined in routes.py

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)