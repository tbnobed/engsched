# Docker Deployment Troubleshooting Guide

## Quick Start

1. **Copy environment file**: `cp .env.example .env`
2. **Edit configuration**: `nano .env` (set passwords, API keys, etc.)
3. **Run deployment**: `./deploy.sh`
4. **Access application**: http://localhost:5000

## Common Issues and Solutions

### 1. Environment Configuration Issues

**Problem**: Missing or incorrect environment variables
**Solution**:
```bash
# Check your .env file has all required variables
cat .env.example  # See what's needed
nano .env         # Edit your configuration
```

**Required variables**:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `FLASK_SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL`
- `SENDGRID_API_KEY` (optional, for email notifications)

### 2. Port Already in Use

**Problem**: `Port 5000 is in use by another program`
**Solution**:
```bash
# Stop existing containers
docker-compose down

# Kill any process using port 5000
sudo lsof -t -i tcp:5000 | xargs kill -9

# Or change port in docker-compose.yml
# Change "5000:5000" to "5001:5000" in web service
```

### 3. Docker Build Permission Issues (FIXED)

**Problem**: `chmod: changing permissions of '/app/docker-entrypoint.sh': Operation not permitted`

**Solution**: This issue has been resolved in the latest Dockerfile version by using `COPY --chmod=755` to set permissions during the copy operation.

**What was changed**:
- Used `COPY --chmod=755` instead of separate `chmod` command
- Set executable permissions on the host before Docker build
- Proper entrypoint script preserved for database initialization
- Enhanced entrypoint script to handle gunicorn startup

The entrypoint script is essential for:
- Waiting for PostgreSQL to be ready before starting the application
- Proper database connection handling in containerized environments
- Graceful startup sequencing

### 4. Database Schema Issues (FIXED)

**Problem**: `ERROR: relation "location" does not exist` during database initialization

**Solution**: This issue has been resolved in the latest init.sql version. The database schema now includes all required tables in the correct order:

**Tables created**:
- `users` - User accounts and technician information
- `location` - Work locations (studios, control rooms, etc.)
- `schedule` - Individual schedule entries
- `recurring_schedule_template` - Recurring schedule patterns (THIS IS WHERE TEMPLATES ARE STORED)
- `ticket`, `ticket_category`, `ticket_comment`, `ticket_history` - Ticket system
- `quick_link` - Quick links in sidebar

**Recurring Schedule Templates** are stored in the `recurring_schedule_template` table and include:
- Weekly time patterns (start/end times for each day of the week)
- Auto-generation settings (how many weeks ahead to generate schedules)
- Location assignments for each template
- Active/inactive status for each template

### 6. Database Schema Mismatches (FIXED)

**Problem**: Multiple database column errors like:
- `column quick_link.created_at does not exist`
- `column ticket.archived does not exist` 
- Missing user profile and theme columns

**Solution**: Updated init.sql to include all required columns that match the SQLAlchemy models:

**Added to users table**:
- `theme_preference` - Light/dark theme setting
- `profile_picture` - Profile picture file path

**Added to ticket table**:
- `archived` - Boolean flag for archived tickets

**Added to quick_link table**:
- `created_at` - Timestamp when link was created
- `updated_at` - Timestamp when link was last modified

**To apply fixes**: Rebuild your Docker containers to get the updated schema:
```bash
docker-compose down
docker-compose up --build -d
```

### 8. Foreign Key Constraint Violations (FIXED)

**Problem**: `ForeignKeyViolation: insert or update on table "schedule" violates foreign key constraint "schedule_technician_id_fkey"`
**Details**: Recurring schedule templates reference technician IDs that don't exist in the current database

**Root Cause**: The recurring schedule system was trying to create schedules for users that may not exist in the current database instance.

**Solution**: Disabled problematic recurring schedule templates to prevent constraint violations:
```sql
UPDATE recurring_schedule_template SET active = FALSE WHERE technician_id NOT IN (SELECT id FROM "user");
```

**Prevention**: Always verify user IDs exist before creating recurring schedule templates.

### 9. Backup Restoration Table Name Mismatch (FIXED)

**Problem**: `ForeignKeyViolation: Key (technician_id)=(12) is not present in table "users"`
**Root Cause**: Table name inconsistency between init.sql and SQLAlchemy models

**Details**: 
- init.sql was creating tables named "users" (plural)
- SQLAlchemy models expect table named "user" (singular)
- This caused foreign key constraint failures during backup restoration

**Solution**: Updated init.sql to use consistent table naming:
- Changed `CREATE TABLE users` to `CREATE TABLE "user"`
- Updated all foreign key references from `REFERENCES users(id)` to `REFERENCES "user"(id)`
- Fixed table references in: schedule, ticket, ticket_comment, ticket_history, recurring_schedule_template

**Result**: Backup restoration now works correctly with proper table name consistency.

**To apply fix**: Rebuild containers to get updated schema:
```bash
docker-compose down
docker-compose up --build -d
```

### 10. Automatic Schedule Generation

**Feature**: The application includes automatic recurring schedule generation that runs every Sunday at 2:00 AM.

**How it works**:
- APScheduler runs in the background when the application starts
- Automatically generates schedules for active templates with "Auto-generate" enabled
- Respects the 7-day minimum interval to prevent over-generation
- Comprehensive logging for monitoring and debugging

**Checking scheduler status**:
```bash
# View application logs to see scheduler activity
docker-compose logs web | grep -i scheduler

# Look for these log messages:
# "Automatic recurring schedule generator started - runs every Sunday at 2:00 AM"
# "Next wakeup is due at YYYY-MM-DD 02:00:00"
# "Running automatic recurring schedule generation..."
```

**Manual trigger** (for testing):
```bash
# Access the auto-generate API endpoint manually (requires admin login)
# Use the "Auto-Generate" button in the recurring schedules interface
# Or call the API with proper CSRF token
```

**No additional configuration needed** - the scheduler starts automatically with the application.

### 7. Running create_admin.py Script

**Problem**: `ModuleNotFoundError: No module named 'flask'` when running the script directly

**Solution**: The create_admin.py script needs to run inside the Docker container where Flask dependencies are installed.

**Method 1 - Run inside Docker container**:
```bash
# If using docker-compose
docker-compose exec web python create_admin.py

# Or if container is named differently
docker exec -it <container_name> python create_admin.py
```

**Method 2 - Install dependencies locally** (if needed):
```bash
pip3 install flask flask-sqlalchemy flask-login flask-wtf
python3 create_admin.py
```

**Method 3 - Use Python virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # or manually install flask
python create_admin.py
```

**What the script creates**:
- Username: `admin`
- Email: `admin@obedtv.com`
- Password: `TBN@dmin!!`
- Full administrator privileges

### 5. Database Connection Issues

**Problem**: Application can't connect to database
**Solution**:
```bash
# Check database container status
docker-compose ps

# View database logs
docker-compose logs db

# Restart database service
docker-compose restart db

# Test database connection manually
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB
```

### 4. Permission Issues

**Problem**: File permission errors in containers
**Solution**:
```bash
# Fix upload directory permissions
sudo chown -R $USER:$USER static/uploads/
chmod -R 755 static/uploads/

# Rebuild containers with proper permissions
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 5. Profile Picture Upload Issues

**Problem**: Profile pictures not uploading or displaying
**Solution**:
```bash
# Ensure upload directory exists
mkdir -p static/uploads/profile_pictures

# Check container volume mapping
docker-compose exec web ls -la /app/static/uploads/

# Verify volume mount in docker-compose.yml
# Should have: uploads_data:/app/static/uploads
```

### 6. SendGrid Email Issues

**Problem**: Email notifications not working
**Solution**:
```bash
# Check if SENDGRID_API_KEY is set
echo $SENDGRID_API_KEY

# Test SendGrid connection
docker-compose exec web python -c "
from email_utils import send_email
print('Testing SendGrid...')
# This will show any connection issues
"
```

**Note**: Email notifications are optional. The app works without SendGrid.

### 7. Build Failures

**Problem**: Docker build fails with dependency issues
**Solution**:
```bash
# Clear Docker cache and rebuild
docker system prune -a
docker-compose build --no-cache

# If specific package fails, check pyproject.toml
# All dependencies should be in the Dockerfile
```

### 8. Application Won't Start

**Problem**: Web container exits immediately
**Solution**:
```bash
# Check web container logs
docker-compose logs web

# Common causes:
# - Missing environment variables
# - Database not ready
# - Python import errors

# Debug by running container interactively
docker-compose run web bash
```

### 9. Health Check Failures

**Problem**: Container health checks failing
**Solution**:
```bash
# Check health endpoint manually
curl -f http://localhost:5000/health

# View detailed health check logs
docker-compose logs web | grep health

# Disable health checks temporarily in docker-compose.yml
# Comment out healthcheck section
```

### 10. Volume/Data Persistence Issues

**Problem**: Data lost after container restart
**Solution**:
```bash
# Verify volumes exist
docker volume ls

# Check volume contents
docker volume inspect technician-scheduler_postgres_data

# Backup important data
docker-compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql
```

## Useful Commands

### Monitoring
```bash
# View all services status
docker-compose ps

# Follow logs for all services
docker-compose logs -f

# View specific service logs
docker-compose logs -f web
docker-compose logs -f db
```

### Database Management
```bash
# Access database shell
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB

# Create database backup
docker-compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database backup
docker-compose exec -T db psql -U $POSTGRES_USER -d $POSTGRES_DB < backup.sql
```

### Maintenance
```bash
# Update application
git pull
docker-compose build --no-cache
docker-compose up -d

# Clean up unused Docker resources
docker system prune -a

# Reset everything (⚠️ DESTROYS DATA)
docker-compose down -v
docker-compose up -d
```

## Getting Help

If you encounter issues not covered here:

1. **Check logs**: `docker-compose logs -f`
2. **Verify environment**: Ensure `.env` file is properly configured
3. **Test components**: Use the commands above to isolate issues
4. **Check Docker status**: Ensure Docker daemon is running

## Security Notes

- Never commit `.env` files to version control
- Use strong passwords for database credentials
- Keep SendGrid API keys secure
- Regularly update Docker images
- Monitor container logs for security issues