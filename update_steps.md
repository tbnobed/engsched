# Update Guide for Plex Technician Scheduler

This document provides a step-by-step guide for updating your existing Plex Technician Scheduler installation on Ubuntu with the latest changes.

## Update Steps (Version 1.2.3)

1. **Backup your current installation and database**

```bash
# Navigate to your installation directory
cd /opt/technician-scheduler

# Run backup script
./backup.sh

# Verify the backup was created
ls -l /var/lib/technician-scheduler/backups
```

2. **Pull the latest code**

```bash
# If using Git
cd /opt/technician-scheduler
git pull

# OR, if you're transferring files manually
# First, on your local machine
cd /path/to/local/project
zip -r technician-scheduler.zip *

# Transfer the zip file to your server
scp technician-scheduler.zip user@your-server:/tmp

# Then, on your server
cd /opt/technician-scheduler
unzip /tmp/technician-scheduler.zip -d /tmp/update
cp -r /tmp/update/* .
rm -rf /tmp/update
rm /tmp/technician-scheduler.zip
```

3. **Update database schema (if needed)**

```bash
cd /opt/technician-scheduler
./update_database.sh
```

4. **Restart the application**

```bash
cd /opt/technician-scheduler
docker-compose down
docker-compose up -d --build
```

5. **Verify the application is running properly**

```bash
# Check container status
docker-compose ps

# Check logs for any errors
docker-compose logs -f

# Test the health endpoint
curl http://localhost:5000/health
```

## What's New in Version 1.2.3 (April 9, 2025)

### New Features and Improvements
- **Enhanced Database Connection Reliability**: Added retry mechanism for database connections to improve stability during startup.
- **Improved Container Orchestration**: Added wait-for-database script to ensure application starts only when database is ready.
- **Enhanced Database Health Check**: Added comprehensive database connectivity check to the health endpoint.
- **Enhanced Schema Update Tools**: New tools to facilitate database schema migrations.

### Bug Fixes
- Fixed issue with missing database columns in deployments.
- Fixed connection timing issues during initial setup.
- Fixed docker-compose dependencies to ensure proper startup sequence.

### Documentation
- Added detailed troubleshooting guide for database connection issues.
- Updated deployment documentation with more robust steps.

## What's New in Version 1.2.2 (March 31, 2025)

### New Features and Improvements
- **Added favicon and Apple touch icon support**: Implemented browser tab icon support for both desktop and mobile devices.
- **Improved browser compatibility**: Added support for iOS and mobile browser icon requests.
- **Comprehensive documentation updates**: Completely revised user guide with detailed mobile feature documentation.
- **Enhanced technician quick start guide**: Updated with mobile-specific instructions and screenshots.
- **Deployment preparation tool**: Added script to automate packaging files for server deployment.

### Bug Fixes
- Fixed 404 errors for favicon.ico and Apple touch icon requests.
- Fixed mobile browser tab icon display issues.

### Documentation
- Added detailed backup checklist for administrators.
- Created step-by-step update instructions for server deployments.
- Enhanced mobile section in user guide with detailed navigation instructions.

## Troubleshooting

### If you encounter database connection issues:

1. **Check if database columns are missing**
   
   If you see an error like `column schedule.created_at does not exist`, run:
   
   ```bash
   # Run the schedule column update script
   ./update_schedule_columns.sh
   
   # Restart the application
   docker-compose down
   docker-compose up -d
   ```

2. **Check database connection status**
   
   Use the database healthcheck script to verify the connection:
   
   ```bash
   # Make the script executable if needed
   chmod +x db_healthcheck.sh
   
   # Run the database healthcheck
   ./db_healthcheck.sh
   ```

3. **Verify application health**
   
   Check the enhanced health endpoint for more diagnostics:
   
   ```bash
   curl http://localhost:5000/health
   ```
   
   The response will show detailed status about database connectivity.

4. **Check container logs for connection problems**
   
   ```bash
   # Check logs for database connection issues
   docker-compose logs web | grep -i "database\|connection\|postgres"
   
   # Check if the database container is healthy
   docker-compose logs db
   ```

5. **Ensure docker-compose settings are correct**
   
   Make sure your docker-compose.yml has the proper dependency configuration:
   
   ```yaml
   depends_on:
     db:
       condition: service_healthy
   ```

### If the browser tab icon is not displaying correctly:

1. **Clear browser cache**
   - On Chrome: Press Ctrl+Shift+Delete, select "Cached images and files", and click "Clear data"
   - On Firefox: Press Ctrl+Shift+Delete, select "Cache", and click "Clear Now"
   - On Safari: Press Command+Option+E

2. **Verify the image file exists**
   ```bash
   docker-compose exec web ls -l /app/static/images/plex_logo_small.png
   ```

3. **Check logs for any 404 errors related to favicon or Apple touch icon**
   ```bash
   docker-compose logs web | grep -E "favicon|apple-touch-icon"
   ```

4. **Manual fix if icon routes are missing**
   
   If you see errors and the routes are missing, you can manually edit the app.py file:
   
   ```bash
   # Edit app.py file
   nano app.py
   ```
   
   Add these routes before the `with app.app_context():` line:
   
   ```python
   # Favicon and Apple Touch Icon routes
   @app.route('/favicon.ico')
   def favicon():
       return redirect(url_for('static', filename='images/plex_logo_small.png'))
   
   @app.route('/apple-touch-icon.png')
   @app.route('/apple-touch-icon-precomposed.png')
   @app.route('/apple-touch-icon-120x120.png')
   @app.route('/apple-touch-icon-120x120-precomposed.png')
   def apple_touch_icon():
       return redirect(url_for('static', filename='images/plex_logo_small.png'))
   ```
   
   Then restart the application:
   
   ```bash
   docker-compose restart web
   ```

For additional help with deployment or troubleshooting, refer to the full deployment guide in `deployment_steps.md`.