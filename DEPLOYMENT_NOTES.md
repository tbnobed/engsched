# Docker Deployment Notes - All-Day OOO Feature Update

## Overview
This deployment includes the complete all-day Out-of-Office (OOO) feature that allows technicians to easily create all-day time-off entries with proper timezone handling.

## Key Features Added
- **All-day OOO checkbox**: Automatically creates 00:00-23:59 time-off entries
- **Timezone-neutral storage**: All-day entries display correctly across all timezones
- **Enhanced visual styling**: Dashed borders and clear "OOO ALL DAY" text
- **Mobile support**: Full functionality on mobile devices
- **Dashboard integration**: All-day entries show properly in both calendar and dashboard views

## Database Schema Changes
The following schema updates are included:

### New Columns
- `schedule.all_day` (BOOLEAN) - Flags all-day time-off entries
- `email_settings` table - Stores email notification preferences
- `ticket.external_email` (VARCHAR) - External user email for Option 3 support
- `ticket.external_name` (VARCHAR) - External user name for Option 3 support
- `ticket.email_notifications` (BOOLEAN) - Enable/disable email notifications
- `ticket.email_thread_id` (VARCHAR) - Unique thread ID for email conversations

### New Indexes
- `idx_ticket_external_email` - Efficient lookups for external user emails
- `idx_ticket_email_thread_id` - Fast email thread tracking
- `idx_ticket_external_notifications` - Performance optimization for external notifications

### Migration Handling
- Automatic schema updates run during container startup
- Existing time-off entries are automatically migrated to use all_day flag
- External user columns added with proper defaults and indexes
- Safe migration with rollback protection

## Admin Credentials
- **Username**: admin
- **Email**: admin@obedtv.com  
- **Password**: TBN@dmin!!

## Environment Variables
Ensure these are set in your `.env` file:
```bash
# Database Configuration
POSTGRES_USER=technician_scheduler_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=technician_scheduler
DATABASE_URL=postgresql://technician_scheduler_user:your_secure_password@db:5432/technician_scheduler

# Flask Configuration
FLASK_SECRET_KEY=your_32_character_secret_key

# Email Configuration
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_FROM_EMAIL=alerts@yourdomain.com  # Must be verified in SendGrid
EMAIL_DOMAIN=your-domain.com

# Site Branding
SITE_NAME="Plex Engineering"
SITE_TITLE="Tech Scheduler"
COMPANY_NAME="Plex Engineering"

# Chat Configuration
CHAT_ENABLED=true
CHAT_URL=https://your-chat-url.com
```

## Deployment Steps

### Fresh Installation
1. Copy `.env.example` to `.env` and configure
2. Run `./deploy.sh` to build and start containers
3. Access application at `http://localhost:5000`

### Updating Existing Installation
1. Stop existing containers: `docker-compose down`
2. Pull latest changes with updated Docker files
3. Run `./deploy.sh` to rebuild and restart
4. Database schema will automatically update during startup

## Testing All-Day OOO Feature
1. Login as any technician
2. Create a new schedule entry
3. Check "OOO (Out of Office) - All Day Vacation" checkbox
4. Submit the form
5. Verify the entry appears as "OOO ALL DAY" in both calendar and dashboard

## Email-to-Ticket System (Option 3 - External Users)
The system now supports external customer communication via email:

### Key Features
- **Email-to-Ticket Conversion**: External customers can email any address at your configured domain to create tickets
- **External User Tracking**: System tracks external users without requiring accounts
- **Email Thread Management**: Unique thread IDs ensure proper conversation tracking
- **Automatic Notifications**: External users receive email notifications for all ticket updates

### Configuration Requirements
1. **SendGrid Inbound Parse**: Configure SendGrid to forward emails to `/api/inbound-email` webhook
2. **DNS Setup**: Point MX record to `mx.sendgrid.net` for your email domain
3. **SendGrid Sender Verification**: Verify the email address configured in `SENDGRID_FROM_EMAIL` in your SendGrid dashboard
4. **Environment Variables**: Ensure `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, and `EMAIL_DOMAIN` are configured

### Testing External User System
1. Send email to any address at your configured domain (e.g., support@yourdomain.com)
2. Verify ticket is created in admin dashboard
3. Check external user receives confirmation email with thread ID
4. Test reply functionality by responding to confirmation email
5. Verify ticket updates trigger notifications to external user

## Troubleshooting

### Schema Update Issues
If schema updates fail:
```bash
# Run schema update manually
docker-compose exec db psql -U technician_scheduler_user -d technician_scheduler -f /app/update_database_schema.sql
```

### Missing All-Day Entries
If all-day entries don't appear:
1. Check database for `all_day` column: `SELECT * FROM schedule WHERE time_off = true LIMIT 1;`
2. Verify timezone settings in user profile
3. Check browser console for JavaScript errors

### Container Health Issues
```bash
# Check container logs
docker-compose logs web
docker-compose logs db

# Restart specific service
docker-compose restart web
```

## Production Considerations
- Use strong passwords for all accounts
- Configure proper SendGrid settings for email notifications
- Set up regular database backups using the backup volume
- Monitor container health and resource usage
- Consider implementing SSL/TLS for production domains

## File Structure
```
.
├── init.sql                    # Complete database schema
├── update_database_schema.sql  # Migration script for existing databases
├── docker-compose.yml          # Container orchestration
├── Dockerfile                  # Application container build
├── docker-entrypoint.sh        # Container startup script
├── deploy.sh                   # Deployment automation
└── .env.example               # Environment variables template
```

## Support
For issues with the all-day OOO feature or deployment:
1. Check application logs: `docker-compose logs -f web`
2. Verify database connectivity: `docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB`
3. Test feature manually through the web interface
4. Check environment variables are properly set