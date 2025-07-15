# Deployment Guide for Technician Scheduler

## Prerequisites

### 1. Install Docker and Docker Compose on Ubuntu

```bash
# Update package index
sudo apt-get update

# Install required packages
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up stable repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add your user to docker group (requires logout/login to take effect)
sudo usermod -aG docker $USER

# Verify installations
docker --version
docker-compose --version

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. Configure SendGrid

1. Verify Domain in SendGrid:
   - Log in to SendGrid dashboard
   - Go to Settings > Sender Authentication
   - Click on "Authenticate Your Domain"
   - Follow the DNS configuration steps for your domain
   - Add DNS records for DKIM authentication
   - Wait for verification (can take up to 48 hours)

2. Verify Sender Email:
   - Ensure alerts@obedtv.com is verified in SendGrid
   - Follow SendGrid's sender verification process
   - Test email sending functionality


### 3. Database Management

#### Database Schema Updates:
When upgrading PostgreSQL or after application updates, you may need to update the database schema to match the latest application code. The following steps will help you perform this update:

```bash
# Create the update_schema.sql file
cat <<EOF > /opt/technician-scheduler/update_schema.sql
-- Schema update script for Plex Technician Scheduler application
-- This script adds any missing columns required by the application

-- Add theme_preference column to user table if it doesn't exist
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS theme_preference VARCHAR(20) DEFAULT 'dark';

-- Add archived column to ticket table if it doesn't exist
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT false;

-- Run VACUUM to optimize the database after schema changes
VACUUM ANALYZE;
EOF

# Create update script
cat <<EOF > /opt/technician-scheduler/update_database.sh
#!/bin/bash
# Database schema update script for Plex Technician Scheduler

set -e  # Exit immediately if a command exits with a non-zero status

echo "=== Plex Technician Scheduler Database Update ==="
echo "This script will update your database schema to match the current application version."
echo

# Check if the containers are running
if ! docker-compose ps | grep -q "db.*Up"; then
    echo "Starting database container..."
    docker-compose up -d db
    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    sleep 10
fi

echo "Applying schema updates..."
# Run the SQL update script
cat update_schema.sql | docker-compose exec -T db psql -U technician_scheduler_user -d technician_scheduler

echo
echo "Schema update completed."
echo "You can now restart your application with:"
echo "  docker-compose down && docker-compose up -d"
EOF

# Make the script executable
chmod +x /opt/technician-scheduler/update_database.sh
```

To use the update script:
```bash
cd /opt/technician-scheduler
./update_database.sh
```

This script should be run whenever:
1. You upgrade PostgreSQL to a newer version
2. You update the application code with schema changes
3. You encounter database-related errors after an update

#### Regular Backups:
```bash
# Create backup directory
sudo mkdir -p /var/lib/technician-scheduler/backups
sudo chown -R $USER:$USER /var/lib/technician-scheduler/backups

# Create backup script (save as backup.sh)
cat <<'EOF' > /opt/technician-scheduler/backup.sh
#!/bin/bash
BACKUP_DIR="/var/lib/technician-scheduler/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"

# Load environment variables for database credentials
cd /opt/technician-scheduler
source .env

# Create database backup
docker-compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE"

# Create application backup using the built-in backup feature
BACKUP_APP_FILE="$BACKUP_DIR/app_backup_$TIMESTAMP.json"
curl -s -X GET "http://localhost:5000/admin/download-backup" -o "$BACKUP_APP_FILE"

# Compress backups
gzip "$BACKUP_FILE"
gzip "$BACKUP_APP_FILE"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "app_backup_*.json.gz" -mtime +30 -delete

# Log the backup completion
echo "Backup completed successfully at $(date)" >> "$BACKUP_DIR/backup.log"
EOF

# Make backup script executable
chmod +x /opt/technician-scheduler/backup.sh

# Create a separate script for database restoration
cat <<'EOF' > /opt/technician-scheduler/restore_db.sh
#!/bin/bash
# Usage: ./restore_db.sh /path/to/backup.sql.gz

if [ $# -ne 1 ]; then
    echo "Usage: $0 /path/to/backup.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Load environment variables for database credentials
cd /opt/technician-scheduler
source .env

echo "Stopping web service..."
docker-compose stop web

echo "Restoring database from $BACKUP_FILE..."
zcat "$BACKUP_FILE" | docker-compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "Starting web service..."
docker-compose start web

echo "Database restore completed at $(date)"
EOF

chmod +x /opt/technician-scheduler/restore_db.sh

# Setup automated backups:
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/technician-scheduler/backup.sh") | crontab -
```

### 4. Production Deployment Steps

1. Clone repository or copy files to your Ubuntu server:
```bash
# Create deployment directory
mkdir -p /opt/technician-scheduler
cd /opt/technician-scheduler

# If using Git
git clone https://your-repository-url.git .

# OR transfer files using rsync or scp
# rsync -avzP /path/to/local/project/ user@server:/opt/technician-scheduler/

# Create directories for persistent data
sudo mkdir -p /var/lib/technician-scheduler/{postgres,backups}
sudo chown -R $USER:$USER /var/lib/technician-scheduler
```

2. Set up environment variables:
```bash
# Create .env file from example
cp .env.example .env

# Generate secure secret key
echo "FLASK_SECRET_KEY=$(openssl rand -hex 32)" >> .env

# Edit the .env file with appropriate values
# Especially update the PostgreSQL password and SendGrid API key
nano .env
```

3. Configure the environment variables in .env file:
```
# Database Configuration
POSTGRES_USER=technician_scheduler_user
POSTGRES_PASSWORD=your_secure_password_here  # CHANGE THIS!
POSTGRES_DB=technician_scheduler
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Flask Configuration
FLASK_SECRET_KEY=your_generated_secret_key
FLASK_ENV=production

# Database URL
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# Email Configuration
SENDGRID_API_KEY=your_sendgrid_api_key_here  # ADD YOUR KEY HERE
EMAIL_DOMAIN=scheduler.yourdomain.com  # CHANGE TO YOUR DOMAIN
```

4. Update docker-compose.yml for production (Optional, if more customization needed):
```bash
# Create a production version of docker-compose.yml
cp docker-compose.yml docker-compose.prod.yml

# Edit docker-compose.prod.yml for production settings
nano docker-compose.prod.yml
```

5. Start the application stack:
```bash
# Build and start containers 
docker-compose up -d --build

# OR if using production-specific file
# docker-compose -f docker-compose.prod.yml up -d --build

# Verify services are running
docker-compose ps

# Check logs
docker-compose logs -f
```

6. Create admin user:
```bash
# Execute the admin creation script 
docker-compose exec web python create_admin.py
```

7. Set up a health check script to monitor the application:
```bash
cat <<EOF > /opt/technician-scheduler/health_check.sh
#!/bin/bash

# Check if containers are running
if ! docker-compose ps | grep -q "Up"; then
  echo "Containers not running. Restarting services..."
  docker-compose restart
  # Send notification to admin
  echo "Technician Scheduler services were restarted at $(date)" | mail -s "Service Restart Alert" admin@example.com
fi

# Check if web application is responding
if ! curl -s http://localhost:5000/health > /dev/null; then
  echo "Web application not responding. Restarting web service..."
  docker-compose restart web
  echo "Web service was restarted at $(date)" | mail -s "Web Service Restart Alert" admin@example.com
fi
EOF

chmod +x /opt/technician-scheduler/health_check.sh

# Add to crontab (check every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/technician-scheduler/health_check.sh") | crontab -
```

### 5. Setting Up HTTPS with Nginx (Recommended for Production)

1. Install Nginx and certbot:
```bash
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

2. Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/technician-scheduler.conf
```

3. Add the following Nginx configuration:
```nginx
server {
    listen 80;
    server_name scheduler.yourdomain.com;  # Replace with your domain name

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Additional settings for WebSocket support if needed
    location /socket.io {
        proxy_pass http://localhost:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

4. Enable the site and obtain SSL certificate:
```bash
sudo ln -s /etc/nginx/sites-available/technician-scheduler.conf /etc/nginx/sites-enabled/
sudo nginx -t  # Test the configuration
sudo systemctl reload nginx

# Obtain SSL certificate
sudo certbot --nginx -d scheduler.yourdomain.com
```

5. Update docker-compose.yml to only expose port 5000 locally:
```bash
# Edit docker-compose.yml and change the ports mapping for web service
nano docker-compose.yml
```

Change:
```yaml
ports:
  - "5000:5000"
```

To:
```yaml
ports:
  - "127.0.0.1:5000:5000"  # Only expose to localhost
```

6. Restart the Docker containers:
```bash
docker-compose down
docker-compose up -d
```

### 6. Security Best Practices

1. Network Security:
   - Use UFW or similar firewall to restrict access:
     ```bash
     sudo ufw allow 22/tcp          # SSH
     sudo ufw allow 80/tcp          # HTTP
     sudo ufw allow 443/tcp         # HTTPS
     sudo ufw enable                # Enable firewall
     ```
   - Only expose necessary ports (5000 for web app internally, 80/443 for Nginx)
   - Use fail2ban to prevent brute force attacks:
     ```bash
     sudo apt-get install -y fail2ban
     sudo systemctl enable fail2ban
     sudo systemctl start fail2ban
     ```

2. Database Security:
   - Use strong passwords with special characters, numbers, and mixed case
   - Regular security updates: `sudo apt-get update && sudo apt-get upgrade`
   - Schedule database backup verification:
     ```bash
     # Create a script to verify backups (verifybackup.sh)
     cat <<EOF > /opt/technician-scheduler/verifybackup.sh
     #!/bin/bash
     LATEST_BACKUP=\$(ls -t /var/lib/technician-scheduler/backups/backup_*.sql.gz | head -1)
     
     if [ -z "\$LATEST_BACKUP" ]; then
       echo "No backups found!"
       exit 1
     fi
     
     # Test restore to verify backup integrity
     zcat "\$LATEST_BACKUP" | docker-compose exec -T db pg_restore --dbname=postgres --schema=public --no-owner --no-privileges --clean --if-exists > /dev/null
     
     if [ \$? -eq 0 ]; then
       echo "Backup verification successful: \$LATEST_BACKUP"
     else
       echo "Backup verification failed: \$LATEST_BACKUP"
       # Send notification to admin
       echo "Backup verification failed for \$LATEST_BACKUP" | mail -s "Backup Verification Failed" admin@example.com
     fi
     EOF
     
     chmod +x /opt/technician-scheduler/verifybackup.sh
     
     # Add to crontab (run weekly)
     (crontab -l 2>/dev/null; echo "0 3 * * 0 /opt/technician-scheduler/verifybackup.sh") | crontab -
     ```

3. Application Security:
   - Keep dependencies updated:
     ```bash
     # Create a script to check for updates
     cat <<EOF > /opt/technician-scheduler/check_updates.sh
     #!/bin/bash
     cd /opt/technician-scheduler
     
     # Pull latest changes if using git
     git pull
     
     # Rebuild and restart containers
     docker-compose up -d --build
     EOF
     
     chmod +x /opt/technician-scheduler/check_updates.sh
     ```
   - Monitor application logs with logrotate:
     ```bash
     sudo nano /etc/logrotate.d/technician-scheduler
     ```
     
     Add:
     ```
     /var/log/technician-scheduler/*.log {
         daily
         missingok
         rotate 14
         compress
         delaycompress
         notifempty
         create 0640 www-data adm
     }
     ```
   - Configure sysctl for additional security:
     ```bash
     sudo nano /etc/sysctl.conf
     ```
     
     Add:
     ```
     # IP Spoofing protection
     net.ipv4.conf.all.rp_filter = 1
     net.ipv4.conf.default.rp_filter = 1
     
     # Ignore ICMP broadcast requests
     net.ipv4.icmp_echo_ignore_broadcasts = 1
     
     # Disable source packet routing
     net.ipv4.conf.all.accept_source_route = 0
     net.ipv4.conf.default.accept_source_route = 0
     
     # Ignore send redirects
     net.ipv4.conf.all.send_redirects = 0
     net.ipv4.conf.default.send_redirects = 0
     
     # Block SYN attacks
     net.ipv4.tcp_syncookies = 1
     net.ipv4.tcp_max_syn_backlog = 2048
     net.ipv4.tcp_synack_retries = 2
     net.ipv4.tcp_syn_retries = 5
     ```
     
     Apply settings:
     ```bash
     sudo sysctl -p
     ```

### 7. Troubleshooting

1. Email Issues:
```bash
# Check SendGrid logs
docker-compose logs web | grep "SendGrid"

# Verify SendGrid API key
docker-compose exec web python -c "import os; print(bool(os.environ.get('SENDGRID_API_KEY')))"

# Test email sending directly
docker-compose exec web python -c "from email_utils import send_email; print(send_email(['admin@example.com'], 'Test Email', '<p>This is a test email from the Technician Scheduler</p>'))"
```

2. Database Issues:
```bash
# Check database logs
docker-compose logs db

# Verify database connectivity
docker-compose exec web python -c "from app import db; print(db.engine.connect())"

# Check PostgreSQL processes
docker-compose exec db psql -U "$POSTGRES_USER" -c "SELECT * FROM pg_stat_activity;"

# Check database size and health
docker-compose exec db psql -U "$POSTGRES_USER" -c "SELECT pg_size_pretty(pg_database_size('$POSTGRES_DB'));"

# For schema-related errors like "column X does not exist", run the schema update script:
cd /opt/technician-scheduler
./update_database.sh

# To manually check if a specific column exists:
docker-compose exec db psql -U "$POSTGRES_USER" -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'user' AND column_name = 'theme_preference';"
```

3. Application Performance Issues:
```bash
# Check memory usage
docker stats

# Check disk space
df -h

# Check CPU usage
top

# Check for slow queries
docker-compose exec db psql -U "$POSTGRES_USER" -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

4. Security Monitoring:
```bash
# Check failed login attempts
docker-compose logs web | grep "login failed"

# Check for suspicious activity
cat /var/log/auth.log | grep "Failed password"

# Check fail2ban status
sudo fail2ban-client status
```

5. Common Problems and Solutions:

- If emails aren't sending:
  - Verify SendGrid API key is set correctly
  - Check domain verification status in SendGrid dashboard
  - Review email sending logs in SendGrid
  - Make sure the sender email is verified in SendGrid
  - Check that the application can reach the SendGrid API

- If database connections fail:
  - Check PostgreSQL logs: `docker-compose logs db`
  - Verify database credentials in .env file
  - Make sure the web service can reach the database container
  - Check if the database is at capacity (memory/disk)
  - Restart the database container: `docker-compose restart db`
  
- If you encounter database schema errors (e.g., "column X does not exist"):
  - Run the update_database.sh script to add missing columns
  - This is especially important after PostgreSQL version upgrades
  - If the error persists, check if the column exists in models.py but not in the database
  - For a full schema reset (last resort), use the backup/restore process

- If the application crashes:
  - Review application logs: `docker-compose logs web`
  - Check memory usage and increase if needed
  - Verify all environment variables are set correctly
  - Look for Python error tracebacks in the logs

- For performance issues:
  - Consider adding indexes to frequently queried database columns
  - Optimize slow queries identified by pg_stat_statements
  - Increase container resources if available
  - Consider implementing caching for frequently accessed data

### 8. Maintenance Procedures

1. Updating the Application:
```bash
# Assuming you're using Git for updates
cd /opt/technician-scheduler
git pull
docker-compose down
docker-compose up -d --build
```

2. Migrating to a New Server:
```bash
# On the old server
# Create a full database backup
cd /opt/technician-scheduler
docker-compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > full_db_backup.sql

# Backup the application data
docker-compose exec -T web python -c "import json; from models import *; from flask import json; print(json.dumps({
    'users': [u.to_dict() for u in User.query.all()],
    'locations': [l.to_dict() for l in Location.query.all()],
    'schedules': [s.to_dict() for s in Schedule.query.all()],
    'quick_links': [q.to_dict() for q in QuickLink.query.all()],
    'ticket_categories': [c.to_dict() for c in TicketCategory.query.all()],
    'tickets': [t.to_dict() for t in Ticket.query.all()],
    'email_settings': [EmailSettings.query.first().to_dict() if EmailSettings.query.first() else {}]
}))" > app_data_backup.json

# Compress backups
tar -czf technician_scheduler_backup.tar.gz full_db_backup.sql app_data_backup.json .env docker-compose.yml

# On the new server, follow the deployment steps and then restore from backup
```

3. Database Optimization:
```bash
# Run VACUUM ANALYZE to optimize PostgreSQL performance
docker-compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "VACUUM ANALYZE;"

# Create necessary indexes based on application usage patterns
docker-compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE INDEX IF NOT EXISTS idx_ticket_due_date ON ticket(due_date);"
```

4. Upgrade PostgreSQL Version (Major Version Upgrade):
```bash
# Create a full database backup first
cd /opt/technician-scheduler
./backup.sh

# Update PostgreSQL version in docker-compose.yml
# Change the image line from "image: postgres:15" to "image: postgres:16" or newer

# Restart with the new PostgreSQL version
docker-compose down
docker-compose up -d

# Run the schema update script to ensure compatibility with the application
./update_database.sh

# Restart the application with the updated schema
docker-compose down
docker-compose up -d

# Verify data integrity after upgrade
docker-compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM user;"
docker-compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM ticket;"
```