import pytz
from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from typing import List
from sqlalchemy.orm import validates

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    def __repr__(self):
        return f'<Location {self.name}>'

    def to_dict(self):
        """Serialize location data for backup"""
        return {
            'id': self.id,  # Include ID for reference
            'name': self.name,
            'description': self.description,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class QuickLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.String(500), nullable=True, default='')  # Optional description
    icon = db.Column(db.String(50), nullable=False, default='link')  # Feather icon name
    category = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    def __repr__(self):
        return f'<QuickLink {self.title}>'

    def to_dict(self):
        """Serialize quick link data for backup"""
        return {
            'title': self.title,
            'url': self.url,
            'description': self.description,
            'icon': self.icon,
            'category': self.category,
            'order': self.order
        }

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(7), default="#3498db")  # Default color for calendar
    timezone = db.Column(db.String(50), default='UTC')  # New timezone field
    theme_preference = db.Column(db.String(20), default='dark')  # Theme preference (dark/light)
    profile_picture = db.Column(db.String(255), nullable=True)  # Path to profile picture file
    
    # Override email property to ensure lowercase
    @property
    def email_normalized(self):
        return self.email.lower() if self.email else None
    
# NOTE: The SQLAlchemy validates decorator was causing issues,
# so we're using Python property functionality to handle email normalization
    schedules = db.relationship('Schedule', backref='technician', lazy='dynamic')
    assigned_tickets = db.relationship('Ticket', 
                                     foreign_keys='Ticket.assigned_to',
                                     backref='assigned_technician', 
                                     lazy='dynamic')
    created_tickets = db.relationship('Ticket',
                                    foreign_keys='Ticket.created_by',
                                    backref='creator',
                                    lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_timezone(self):
        """Get the user's timezone string"""
        return self.timezone if self.timezone else 'UTC'
    
    def get_timezone_obj(self):
        """Get the user's timezone object"""
        try:
            return pytz.timezone(self.get_timezone())
        except pytz.exceptions.UnknownTimeZoneError:
            return pytz.UTC

    def to_dict(self):
        """Serialize user data for backup"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'is_admin': self.is_admin,
            'color': self.color,
            'timezone': self.timezone,
            'theme_preference': self.theme_preference,
            'profile_picture': self.profile_picture,
            'created_schedules': [schedule.id for schedule in self.schedules]
        }

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    technician_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)
    description = db.Column(db.String(200))
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    location = db.relationship('Location', backref='schedules')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(current_app.config['TIMEZONE']))
    time_off = db.Column(db.Boolean, default=False)  # For time off entries
    all_day = db.Column(db.Boolean, default=False)  # For all-day events that should display on correct date regardless of timezone

    def get_user_timezone(self):
        """Get the technician's timezone for this schedule"""
        return self.technician.get_timezone_obj()

    def to_dict(self):
        """Serialize schedule data for backup with reference data"""
        return {
            'id': self.id,
            'technician_id': self.technician_id,
            'technician_username': self.technician.username,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'description': self.description,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else None,
            'time_off': self.time_off,
            'all_day': self.all_day,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TicketCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(200))
    icon = db.Column(db.String(50), default='help-circle')  # Feather icon name
    priority_level = db.Column(db.Integer, default=0)  # Higher number = higher priority
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    tickets = db.relationship('Ticket', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<TicketCategory {self.name}>'
        
    def to_dict(self):
        """Serialize ticket category data for backup"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'priority_level': self.priority_level,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TicketStatus:
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    PENDING = 'pending'
    RESOLVED = 'resolved'
    CLOSED = 'closed'

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('ticket_category.id'), nullable=False)
    status = db.Column(db.String(20), default=TicketStatus.OPEN)
    priority = db.Column(db.Integer, default=0)  # 0=Low, 1=Medium, 2=High, 3=Urgent
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))
    due_date = db.Column(db.DateTime(timezone=True))
    archived = db.Column(db.Boolean, default=False)  # Flag for archived tickets
    
    # External email communication fields
    external_email = db.Column(db.String(255), nullable=True)  # Email address of external user
    external_name = db.Column(db.String(100), nullable=True)   # Name of external user
    email_notifications = db.Column(db.Boolean, default=True)  # Whether to send email notifications
    email_thread_id = db.Column(db.String(50), nullable=True)  # Unique thread ID for email replies

    comments = db.relationship('TicketComment', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')
    history = db.relationship('TicketHistory', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')

    def add_comment(self, user: User, content: str) -> 'TicketComment':
        comment = TicketComment(
            ticket_id=self.id,
            user_id=user.id,
            content=content
        )
        db.session.add(comment)
        return comment

    def log_history(self, user: User, action: str, details: str = None) -> 'TicketHistory':
        """Log an action in the ticket's history"""
        if not self.id:
            raise ValueError("Cannot log history for ticket with no ID")

        history = TicketHistory(
            ticket_id=self.id,
            user_id=user.id,
            action=action,
            details=details
        )
        db.session.add(history)
        return history
    
    def is_external_user(self) -> bool:
        """Check if this ticket is from an external user"""
        return self.external_email is not None
    
    def get_notification_email(self) -> str:
        """Get the email address for notifications (external or internal user)"""
        if self.is_external_user():
            return self.external_email
        elif self.creator:
            return self.creator.email
        return None
    
    def get_display_name(self) -> str:
        """Get the display name for the ticket creator"""
        if self.is_external_user():
            return self.external_name or self.external_email
        elif self.creator:
            return self.creator.username
        return "Unknown"
    
    def has_unread_activity(self, user_id: int) -> bool:
        """Check if ticket has activity since user last viewed it"""
        # Get user's last view time for this ticket
        ticket_view = TicketView.query.filter_by(
            user_id=user_id, 
            ticket_id=self.id
        ).first()
        
        if not ticket_view:
            # User has never viewed this ticket, so it's "unread"
            return True
        
        # Check for comments after last view
        recent_comments = self.comments.filter(
            TicketComment.created_at > ticket_view.last_viewed_at
        ).count()
        
        # Check for history entries after last view
        recent_history = self.history.filter(
            TicketHistory.created_at > ticket_view.last_viewed_at
        ).count()
        
        # Check if ticket was updated after last view
        ticket_updated = self.updated_at > ticket_view.last_viewed_at
        
        return recent_comments > 0 or recent_history > 0 or ticket_updated
    
    def mark_as_viewed(self, user_id: int):
        """Mark ticket as viewed by user"""
        ticket_view = TicketView.query.filter_by(
            user_id=user_id,
            ticket_id=self.id
        ).first()
        
        if ticket_view:
            ticket_view.last_viewed_at = datetime.now(pytz.UTC)
        else:
            ticket_view = TicketView(
                user_id=user_id,
                ticket_id=self.id,
                last_viewed_at=datetime.now(pytz.UTC)
            )
            db.session.add(ticket_view)
        
        return ticket_view
        
    def to_dict(self):
        """Serialize ticket data for backup with reference data"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category_id': self.category_id,
            'status': self.status,
            'priority': self.priority,
            'assigned_to': self.assigned_to,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'archived': self.archived,
            # External user fields
            'external_email': self.external_email,
            'external_name': self.external_name,
            'email_notifications': self.email_notifications,
            'email_thread_id': self.email_thread_id,
            # Add references
            'category_name': self.category.name if self.category else None,
            'creator_username': self.creator.username if self.creator else None,
            'assigned_username': self.assigned_technician.username if self.assigned_technician else None,
            # Include associated data
            'comments': [comment.to_dict() for comment in self.comments],
            'history': [history.to_dict() for history in self.history]
        }

class TicketComment(db.Model):
    # Use autoincrement to ensure unique IDs
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    user = db.relationship('User', backref='ticket_comments')
    
    def to_dict(self):
        """Serialize comment data for backup"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user_id': self.user_id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'username': self.user.username if self.user else None
        }

class TicketHistory(db.Model):
    # Use db.sequence to generate unique IDs
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # e.g., "status_changed", "assigned", etc.
    details = db.Column(db.Text)  # Additional details about the action
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))

    user = db.relationship('User', backref='ticket_history_entries')
    
    def to_dict(self):
        """Serialize history entry data for backup"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'username': self.user.username if self.user else None
        }

class TicketView(db.Model):
    """Track when users last viewed tickets to show unread indicators"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    last_viewed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    
    # Unique constraint to ensure one view record per user per ticket
    __table_args__ = (db.UniqueConstraint('user_id', 'ticket_id'),)
    
    user = db.relationship('User', backref='ticket_views')
    ticket = db.relationship('Ticket', backref='ticket_views')

class EmailSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_email_group = db.Column(db.String(120), nullable=False, default='alerts@obedtv.com')
    notify_on_create = db.Column(db.Boolean, default=True)
    notify_on_update = db.Column(db.Boolean, default=True)
    notify_on_delete = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    def to_dict(self):
        """Serialize email settings data"""
        return {
            'admin_email_group': self.admin_email_group,
            'notify_on_create': self.notify_on_create,
            'notify_on_update': self.notify_on_update,
            'notify_on_delete': self.notify_on_delete
        }

class RecurringScheduleTemplate(db.Model):
    """Template for recurring schedules - defines weekly work patterns"""
    id = db.Column(db.Integer, primary_key=True)
    technician_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    template_name = db.Column(db.String(100), nullable=False)  # e.g., "Standard Work Week"
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    active = db.Column(db.Boolean, default=True)
    
    # Weekly schedule times (stored as time strings, e.g., "09:00" or null for off days)
    monday_start = db.Column(db.String(5))      # "09:00"
    monday_end = db.Column(db.String(5))        # "17:00"
    tuesday_start = db.Column(db.String(5))
    tuesday_end = db.Column(db.String(5))
    wednesday_start = db.Column(db.String(5))
    wednesday_end = db.Column(db.String(5))
    thursday_start = db.Column(db.String(5))
    thursday_end = db.Column(db.String(5))
    friday_start = db.Column(db.String(5))
    friday_end = db.Column(db.String(5))
    saturday_start = db.Column(db.String(5))
    saturday_end = db.Column(db.String(5))
    sunday_start = db.Column(db.String(5))
    sunday_end = db.Column(db.String(5))
    
    # Auto-generation settings
    auto_generate = db.Column(db.Boolean, default=True)
    weeks_ahead = db.Column(db.Integer, default=2)  # Generate 2 weeks ahead
    last_generated = db.Column(db.DateTime(timezone=True))
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))
    
    # Relationships
    technician = db.relationship('User', backref='recurring_templates')
    location = db.relationship('Location', backref='recurring_templates')
    
    def __repr__(self):
        return f'<RecurringScheduleTemplate {self.template_name} for {self.technician.username}>'
    
    def get_day_schedule(self, day_name):
        """Get start and end times for a specific day"""
        day_name = day_name.lower()
        start_attr = f"{day_name}_start"
        end_attr = f"{day_name}_end"
        
        start_time = getattr(self, start_attr, None)
        end_time = getattr(self, end_attr, None)
        
        if start_time and end_time:
            return start_time, end_time
        return None, None
    
    def get_weekly_schedule(self):
        """Get the complete weekly schedule as a dictionary"""
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        schedule = {}
        
        for day in days:
            start, end = self.get_day_schedule(day)
            schedule[day] = {
                'start': start,
                'end': end,
                'working': start is not None and end is not None
            }
        
        return schedule
    
    def update_existing_schedules(self):
        """Update existing auto-generated schedules when template is modified"""
        from datetime import datetime, timedelta
        import pytz
        from app import db
        
        if not self.active:
            return 0
        
        # Find existing auto-generated schedules for this template
        # Check for both old format with description and new format with empty description
        existing_schedules = Schedule.query.filter(
            Schedule.technician_id == self.technician_id,
            (Schedule.description.like(f"Auto-generated from {self.template_name}") | 
             (Schedule.description == "")),
            Schedule.start_time >= datetime.now(pytz.UTC)  # Only future schedules
        ).all()
        
        updated_count = 0
        technician_tz = pytz.timezone(self.technician.get_timezone())
        
        for schedule in existing_schedules:
            # Convert to technician's local time to get the day
            local_start = schedule.start_time.astimezone(technician_tz)
            day_name = local_start.strftime('%A').lower()
            
            # Get new times for this day from template
            start_time_str, end_time_str = self.get_day_schedule(day_name)
            
            if start_time_str and end_time_str:
                # Calculate new start and end times
                start_hour, start_minute = map(int, start_time_str.split(':'))
                end_hour, end_minute = map(int, end_time_str.split(':'))
                
                # Create new datetime objects in technician's timezone
                new_start = local_start.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                new_end = local_start.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
                
                # Convert to UTC for storage
                new_start_utc = new_start.astimezone(pytz.UTC)
                new_end_utc = new_end.astimezone(pytz.UTC)
                
                # Check if this would create a conflict with another schedule
                conflict = Schedule.query.filter(
                    Schedule.technician_id == self.technician_id,
                    Schedule.id != schedule.id,  # Exclude current schedule
                    Schedule.start_time < new_end_utc,
                    Schedule.end_time > new_start_utc
                ).first()
                
                if not conflict:
                    # Update the schedule
                    schedule.start_time = new_start_utc
                    schedule.end_time = new_end_utc
                    updated_count += 1
            else:
                # This day is no longer scheduled in the template, delete the schedule
                db.session.delete(schedule)
                updated_count += 1
        
        return updated_count

    def generate_schedules(self, start_date=None, weeks=None):
        """Generate actual Schedule entries from this template"""
        from datetime import datetime, timedelta
        import pytz
        
        if not self.active:
            return []
        
        if start_date is None:
            start_date = datetime.now(pytz.UTC).date()
        
        if weeks is None:
            weeks = self.weeks_ahead
        
        # Find the next Monday
        days_until_monday = (7 - start_date.weekday()) % 7
        if days_until_monday == 0 and start_date.weekday() == 0:
            monday = start_date
        else:
            monday = start_date + timedelta(days=days_until_monday)
        
        generated_schedules = []
        
        for week in range(weeks):
            week_start = monday + timedelta(weeks=week)
            
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            for day_idx, day_name in enumerate(days):
                start_time_str, end_time_str = self.get_day_schedule(day_name)
                
                if start_time_str and end_time_str:
                    # Calculate the actual date for this day
                    day_date = week_start + timedelta(days=day_idx)
                    
                    # Parse time strings and create datetime objects
                    start_hour, start_minute = map(int, start_time_str.split(':'))
                    end_hour, end_minute = map(int, end_time_str.split(':'))
                    
                    # Get technician's timezone
                    tech_tz = pytz.timezone(self.technician.get_timezone())
                    
                    # Create datetime objects in technician's timezone
                    start_datetime = tech_tz.localize(datetime.combine(day_date, datetime.min.time().replace(hour=start_hour, minute=start_minute)))
                    end_datetime = tech_tz.localize(datetime.combine(day_date, datetime.min.time().replace(hour=end_hour, minute=end_minute)))
                    
                    # Convert to UTC for database storage
                    start_datetime_utc = start_datetime.astimezone(pytz.UTC)
                    end_datetime_utc = end_datetime.astimezone(pytz.UTC)
                    
                    # Check if schedule already exists for this time slot
                    existing_schedule = Schedule.query.filter_by(
                        technician_id=self.technician_id,
                        start_time=start_datetime_utc,
                        end_time=end_datetime_utc
                    ).first()
                    
                    # Check for OOO conflicts: Don't create schedules on days with OOO entries
                    date_start = pytz.UTC.localize(datetime.combine(day_date, datetime.min.time()))
                    date_end = pytz.UTC.localize(datetime.combine(day_date, datetime.max.time()))
                    
                    ooo_conflict = Schedule.query.filter(
                        Schedule.technician_id == self.technician_id,
                        Schedule.time_off == True,
                        Schedule.all_day == True,
                        Schedule.start_time >= date_start,
                        Schedule.start_time <= date_end
                    ).first()
                    
                    if ooo_conflict:
                        # Skip this day due to OOO conflict
                        continue
                    
                    if not existing_schedule:
                        schedule = Schedule(
                            technician_id=self.technician_id,
                            start_time=start_datetime_utc,
                            end_time=end_datetime_utc,
                            description="",
                            location_id=self.location_id,
                            time_off=False
                        )
                        generated_schedules.append(schedule)
        
        return generated_schedules
    
    def to_dict(self):
        """Serialize recurring schedule template data"""
        return {
            'id': self.id,
            'technician_id': self.technician_id,
            'technician_name': self.technician.username if self.technician else None,
            'template_name': self.template_name,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else None,
            'active': self.active,
            'weekly_schedule': self.get_weekly_schedule(),
            'auto_generate': self.auto_generate,
            'weeks_ahead': self.weeks_ahead,
            'last_generated': self.last_generated.isoformat() if self.last_generated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }