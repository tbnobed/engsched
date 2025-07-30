from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, DateTimeField, DateField, TextAreaField, ColorField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, URL, Optional
import pytz

class LocationForm(FlaskForm):
    name = StringField('Location Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Length(max=200)])
    active = BooleanField('Active', default=True)

class ScheduleForm(FlaskForm):
    technician = SelectField('Technician', coerce=int)
    start_time = DateTimeField('Start Time', validators=[DataRequired()],
                            format='%Y-%m-%d %H:%M')
    end_time = DateTimeField('End Time', validators=[DataRequired()],
                           format='%Y-%m-%d %H:%M')
    description = TextAreaField('Description', validators=[Length(max=200)])
    location_id = SelectField('Location', coerce=int, validators=[Optional()])
    time_off = BooleanField('Time Off')
    all_day = BooleanField('OOO (Out of Office) - All Day Vacation')
    repeat_days = StringField('Repeat Days', validators=[Optional()])

class LoginForm(FlaskForm):
    email = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
        validators=[DataRequired(), EqualTo('password')])
    timezone = SelectField('Timezone', choices=[(tz, tz) for tz in pytz.common_timezones])

class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    color = ColorField('Color', default='#6E7E85')
    is_admin = BooleanField('Is Admin')
    timezone = SelectField('Timezone', 
                         choices=[(tz, tz) for tz in pytz.common_timezones],
                         default='America/Los_Angeles')
    profile_picture = FileField('Profile Picture', 
                              validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 
                                                    'Only image files are allowed (JPG, PNG, WEBP)')])

class QuickLinkForm(FlaskForm):
    title = StringField('Link Title', validators=[DataRequired(), Length(max=100)])
    url = StringField('URL', validators=[DataRequired(), URL(), Length(max=500)])
    icon = StringField('Feather Icon Name', validators=[DataRequired(), Length(max=50)], default='link')
    category = StringField('Category', validators=[DataRequired(), Length(max=100)])
    order = IntegerField('Display Order', default=0)

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Confirm New Password', 
        validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])

class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    color = ColorField('Color')
    is_admin = BooleanField('Is Admin')
    timezone = SelectField('Timezone', 
                         choices=[(tz, tz) for tz in pytz.common_timezones],
                         default='America/Los_Angeles')
    password = PasswordField('New Password', validators=[Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
        validators=[EqualTo('password')])
    profile_picture = FileField('Profile Picture', 
                              validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 
                                                    'Only image files are allowed (JPG, PNG, WEBP)')])

class TimezoneForm(FlaskForm):
    timezone = SelectField('Timezone', choices=[(tz, tz) for tz in pytz.common_timezones])

class EmailSettingsForm(FlaskForm):
    admin_email_group = StringField('Admin Email Group', 
                                  validators=[DataRequired(), Email(), Length(max=120)],
                                  default='alerts@obedtv.com')
    notify_on_create = BooleanField('Send notifications for new schedules', default=True)
    notify_on_update = BooleanField('Send notifications for schedule updates', default=True)
    notify_on_delete = BooleanField('Send notifications for schedule deletions', default=True)

class TicketForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        (0, 'Low'),
        (1, 'Medium'),
        (2, 'High'),
        (3, 'Urgent')
    ], coerce=int)
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])

class TicketCommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])

class TicketCategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Length(max=200)])
    priority_level = SelectField('Default Priority', choices=[
        (0, 'Low'),
        (1, 'Medium'),
        (2, 'High'),
        (3, 'Urgent')
    ], coerce=int, default=0)

class RecurringScheduleForm(FlaskForm):
    """Form for creating/editing recurring schedule templates"""
    technician = SelectField('Technician', coerce=int, validators=[DataRequired()])
    template_name = StringField('Template Name', validators=[DataRequired(), Length(max=100)])
    location_id = SelectField('Location', coerce=int, validators=[Optional()])
    active = BooleanField('Active', default=True)
    
    # Monday
    monday_start = StringField('Monday Start', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 09:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    monday_end = StringField('Monday End', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 17:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    
    # Tuesday
    tuesday_start = StringField('Tuesday Start', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 09:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    tuesday_end = StringField('Tuesday End', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 17:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    
    # Wednesday
    wednesday_start = StringField('Wednesday Start', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 09:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    wednesday_end = StringField('Wednesday End', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 17:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    
    # Thursday
    thursday_start = StringField('Thursday Start', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 09:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    thursday_end = StringField('Thursday End', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 17:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    
    # Friday
    friday_start = StringField('Friday Start', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 09:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    friday_end = StringField('Friday End', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 17:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    
    # Saturday
    saturday_start = StringField('Saturday Start', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 09:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    saturday_end = StringField('Saturday End', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 17:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    
    # Sunday
    sunday_start = StringField('Sunday Start', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 09:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    sunday_end = StringField('Sunday End', validators=[Optional()], render_kw={'placeholder': 'HH:MM (e.g., 17:00)', 'pattern': '[0-9]{2}:[0-9]{2}'})
    
    # Auto-generation settings
    auto_generate = BooleanField('Auto-generate schedules', default=True)
    weeks_ahead = SelectField('Weeks to generate ahead', choices=[
        (1, '1 week'),
        (2, '2 weeks'),
        (3, '3 weeks'),
        (4, '4 weeks'),
        (8, '8 weeks')
    ], coerce=int, default=2)
    
    def validate_time_pairs(self):
        """Validate that start times come before end times"""
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        errors = []
        
        for day in days:
            start_field = getattr(self, f'{day}_start')
            end_field = getattr(self, f'{day}_end')
            
            start_time = start_field.data
            end_time = end_field.data
            
            # If one is provided, both must be provided
            if (start_time and not end_time) or (not start_time and end_time):
                errors.append(f"{day.capitalize()}: Both start and end times must be provided")
            
            # Validate time format and logic
            if start_time and end_time:
                try:
                    # Parse times
                    start_parts = start_time.split(':')
                    end_parts = end_time.split(':')
                    
                    if len(start_parts) != 2 or len(end_parts) != 2:
                        errors.append(f"{day.capitalize()}: Invalid time format")
                        continue
                    
                    start_hour, start_min = int(start_parts[0]), int(start_parts[1])
                    end_hour, end_min = int(end_parts[0]), int(end_parts[1])
                    
                    # Validate hour/minute ranges
                    if not (0 <= start_hour <= 23 and 0 <= start_min <= 59):
                        errors.append(f"{day.capitalize()}: Invalid start time")
                        continue
                    
                    if not (0 <= end_hour <= 23 and 0 <= end_min <= 59):
                        errors.append(f"{day.capitalize()}: Invalid end time")
                        continue
                    
                    # Check that start time is before end time
                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min
                    
                    if start_minutes >= end_minutes:
                        errors.append(f"{day.capitalize()}: Start time must be before end time")
                
                except ValueError:
                    errors.append(f"{day.capitalize()}: Invalid time format")
        
        return errors