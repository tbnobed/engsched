# Backup Checklist for Plex Technician Scheduler

Before deploying updates to your production server, make sure you have backups of the following critical files and data:

## 1. Database Backup

The most important data to back up is your PostgreSQL database. Run the backup script to create a complete database dump:

```bash
cd /opt/technician-scheduler
./backup.sh
```

Verify that both SQL dump and application JSON backup files were created:
```bash
ls -la /var/lib/technician-scheduler/backups
```

## 2. Custom Configuration Files

Make sure you have backups of these key configuration files:

- `.env` file with environment variables and secrets
- `docker-compose.yml` if you made any customizations
- Any custom Nginx or reverse proxy configurations

## 3. Custom Static Files

If you have any custom static files like logos or custom CSS, ensure they are backed up:

- `/opt/technician-scheduler/static/images/` directory
- `/opt/technician-scheduler/static/css/` directory
- `/opt/technician-scheduler/static/js/` directory

## 4. Backup Script Verification

Test that your backups can be restored successfully:

```bash
# Create a test database
docker-compose exec db psql -U postgres -c "CREATE DATABASE backup_test;"

# Test restore to the test database
zcat /var/lib/technician-scheduler/backups/backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose exec -T db psql -U postgres -d backup_test

# Check if restore was successful
docker-compose exec db psql -U postgres -d backup_test -c "SELECT COUNT(*) FROM users;"

# Clean up test database
docker-compose exec db psql -U postgres -c "DROP DATABASE backup_test;"
```

## 5. Offsite Backup

For additional safety, copy your backup files to an external location:

```bash
# Copy latest backup to a secure offsite location
latest_backup=$(ls -t /var/lib/technician-scheduler/backups/backup_*.sql.gz | head -1)
latest_app_backup=$(ls -t /var/lib/technician-scheduler/backups/app_backup_*.json.gz | head -1)

# Using rsync to copy to another server
rsync -avz "$latest_backup" "$latest_app_backup" user@backup-server:/path/to/backup/

# OR using AWS S3
aws s3 cp "$latest_backup" s3://your-backup-bucket/technician-scheduler/
aws s3 cp "$latest_app_backup" s3://your-backup-bucket/technician-scheduler/
```

## 6. Document Installation-Specific Customizations

Before deploying, document any customizations specific to your installation:

- Custom cron jobs in `/etc/cron.d/` or user crontab
- Custom system service configurations in `/etc/systemd/system/`
- Any firewall rules or security settings specific to this application
- Custom domain and SSL certificate configurations
- Email notification settings and SendGrid configurations

This checklist should be completed before any major update to ensure you can roll back if needed.