#!/bin/bash
# Script to prepare a deployment package for the Plex Technician Scheduler
# This creates a zip file containing only the necessary files for deployment

set -e  # Exit immediately if a command exits with a non-zero status

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="plex_scheduler_deploy_${TIMESTAMP}.zip"

echo "=== Preparing deployment package for Plex Technician Scheduler ==="
echo "Creating package: $PACKAGE_NAME"

# Create a temporary directory for the deployment files
mkdir -p deploy_temp

# Copy key files to the deployment directory
echo "Copying application files..."
cp -r \
    app.py \
    auth.py \
    create_admin.py \
    deployment_steps.md \
    docker-compose.yml \
    Dockerfile \
    email_utils.py \
    fix_admin_password.py \
    forms.py \
    health.py \
    main.py \
    models.py \
    pyproject.toml \
    release_notes.md \
    routes.py \
    ticket_routes.py \
    update_database.sh \
    update_database.sql \
    update_schema.py \
    update_schema.sql \
    update_schema_instructions.md \
    update_steps.md \
    backup_checklist.md \
    add_archived_column.py \
    update_timezone_field.py \
    update_timezone_field.sql \
    update_timezone_field.sh \
    update_theme_preference.py \
    update_theme_preference.sql \
    add_schedule_created_at.sql \
    update_schedule_columns.sh \
    docker-entrypoint.sh \
    db_healthcheck.sh \
    .env.example \
    admin_guide.md \
    technician_quick_start.md \
    user_admin_guide.md \
    static \
    templates \
    deploy_temp/

# Create empty directories where needed
mkdir -p deploy_temp/static/uploads
mkdir -p deploy_temp/static/backups

# Remove any __pycache__ directories
find deploy_temp -type d -name __pycache__ -exec rm -rf {} +

# Create the distribution zip file
echo "Creating zip archive..."
cd deploy_temp
zip -r ../$PACKAGE_NAME *
cd ..

# Clean up
echo "Cleaning up temporary files..."
rm -rf deploy_temp

echo ""
echo "=== Deployment package created: $PACKAGE_NAME ==="
echo "This file contains all necessary files for deploying to your Ubuntu server."
echo "Transfer this file to your server and follow the update_steps.md instructions."
echo ""
echo "Quick deployment steps:"
echo "1. scp $PACKAGE_NAME user@your-server:/tmp/"
echo "2. ssh user@your-server"
echo "3. cd /opt/technician-scheduler"
echo "4. ./backup.sh"
echo "5. unzip /tmp/$PACKAGE_NAME -d /tmp/update"
echo "6. cp -r /tmp/update/* ."
echo "7. ./update_database.sh"
echo "8. docker-compose down"
echo "9. docker-compose up -d --build"
echo "10. docker-compose logs -f"