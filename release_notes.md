# Release Notes - Technician Scheduler

## Version 1.2.2 (March 31, 2025)

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

## Version 1.2.1 (March 29, 2025)

### New Features and Improvements
- **Database schema update utilities**: Added tools to simplify database schema updates during PostgreSQL version upgrades.
- **Enhanced deployment documentation**: Added detailed guides for database schema migrations.

### Bug Fixes
- Fixed database compatibility issue with PostgreSQL 15 by adding schema update scripts.
- Added missing columns when upgrading from older database schema versions.

## Version 1.2.0 (March 28, 2025)

### New Features and Improvements
- **Case-insensitive login**: Users can now log in using their email address regardless of capitalization.
- **Health check endpoint**: Added a `/health` endpoint for container health checks and monitoring systems.
- **Improved deployment documentation**: Enhanced deployment guide with email configuration details.
- **Environment variable updates**: Added `EMAIL_DOMAIN` environment variable for proper email link handling.

### Bug Fixes
- Fixed case-insensitive login using proper SQL LOWER function implementation.
- Updated Dockerfile to properly handle health check endpoint.
- Updated environment templates with all required variables.

## Version 1.1.0 (February 15, 2025)

### New Features
- **Dark/Light theme toggle**: Users can now switch between dark and light themes with preferences saved per user.
- **Ticket archiving system**: Added functionality to archive old tickets to manage database growth.
- **Improved backup/restore**: Enhanced to preserve ticket IDs, comments, and history during restore.
- **Docker deployment**: Full Docker and Docker-Compose configuration for easy deployment.

### Bug Fixes
- Fixed text contrast issues in light mode.
- Fixed username/email visibility in profile settings in dark mode.
- Fixed issue with editing due dates on existing tickets.
- Fixed database schema by adding missing 'archived' column to ticket table.
- Fixed navigation bar disappearing in light theme mode.

## Version 1.0.0 (January 10, 2025)

### Initial Release
- Complete technician scheduling system with calendar view
- Email notifications for schedule changes via SendGrid
- Ticketing system with categories, priority levels, and assignments
- User management with admin and technician roles
- Mobile-responsive design for all screens
- Location management for technician assignments
- Quick links feature for commonly used resources