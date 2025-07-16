# Plex Engineering Technician Scheduler

## Overview

This is a comprehensive web application for managing technician schedules and tickets, built with Flask and PostgreSQL. The system provides calendar-based scheduling, ticket management, and user administration with both desktop and mobile-responsive interfaces.

## User Preferences

Preferred communication style: Simple, everyday language.
Chat Requirements: Auto-launch team chat and maintain stay-on-top functionality while preserving dropdown menu interactions.

Recent Updates (July 16, 2025):
- ✅ COMPLETED: Unread Activity Indicator System for Tickets
- Implemented comprehensive ticket viewing tracking with TicketView database model
- Added visual "NEW" badges with pulsing animation for tickets with unread activity since last view
- Enhanced dashboard with row highlighting and unread indicators in both desktop and mobile templates
- Updated sidebar Active Tickets section to show unread status with conditional styling
- Automatic read marking when users view tickets - seamless UX without manual actions
- Created database migration scripts and updated Docker files for production deployment
- System tracks last viewed timestamp per user/ticket and detects new comments, status changes, and updates
- Database includes proper indexing (user_id, ticket_id, last_viewed_at) for optimal performance
- All templates updated with responsive styling for light/dark theme compatibility
- ✅ COMPLETED: CRITICAL Email Threading Fix - Perfect Conversation Continuity
- Fixed critical threading issue where status update and assignment emails broke conversation threads
- ALL email notifications now use identical subject line format: "[Ticket #ID] - {ticket.title}"
- Removed dynamic suffixes that were breaking threading:
  * OLD: "[Ticket #14] - Hello, who can help me (Assigned)" ❌ 
  * OLD: "[Ticket #14] - Hello, who can help me (New Comment)" ❌
  * OLD: "[Ticket #14] - Hello, who can help me (Status: In Progress)" ❌
  * NEW: "[Ticket #14] - Hello, who can help me" ✅ (ALL notification types)
- Email replies to ANY ticket notification now stay in same conversation thread
- External users can reply to assignment, comment, or status update emails without creating new tickets
- Perfect bidirectional email communication for seamless external user experience

Recent Updates (July 15, 2025):
- ✅ COMPLETED: Email Reply Detection and Comment Threading System with Consistent Subject Lines
- Implemented intelligent reply detection using "[Ticket #ID]" pattern in email subject lines
- Enhanced EMAIL_TO_TICKET_SETUP.md documentation with complete reply handling workflow
- ✅ COMPLETED: External User Ticket Attribution Display Fix
- Fixed ticket view and dashboard to display external user email addresses instead of "admin" 
- Updated view_ticket() and tickets_dashboard() functions to use proper Ticket model methods (get_display_name(), is_external_user())
- External user tickets now correctly show originator email (e.g., "unknown@email.com") in both detail view and dashboard listing
- Preserves external email information while maintaining internal admin assignment for review and routing
- ✅ COMPLETED: Complete External User Email Notification System Verification  
- Confirmed all ticket notification types include external users: assignment, comments, status changes
- External users receive professional HTML emails with ticket details, links, and proper threading
- Tested comprehensive notification workflow: ticket creation → assignment → comment → status change
- All notifications successfully delivered with HTTP 202 responses from SendGrid API
- External users stay fully informed throughout entire ticket lifecycle without requiring system access
- ✅ COMPLETED: Configurable SendGrid Sender Email via Environment Variable
- Added SENDGRID_FROM_EMAIL environment variable for configurable "from" address in all email notifications
- Updated .env.example, .env, and docker-compose.yml with new SENDGRID_FROM_EMAIL configuration
- Modified send_email function to use environment-configured sender address instead of hardcoded value
- Enhanced deployment documentation to include SendGrid sender verification requirements
- Maintains backward compatibility with default alerts@obedtv.com if environment variable not set
- All email notifications (ticket assignments, status changes, comments, confirmations) now use configured sender
- ✅ COMPLETED: Email-Only Communication System (Option 3) for External Users
- Successfully implemented comprehensive external user support for email-to-ticket system
- Added external user tracking fields to Ticket model: external_email, external_name, email_notifications, email_thread_id
- Created database migration script (add_external_email_columns.py) with proper indexing for email lookups
- Enhanced ticket creation workflow to distinguish between internal and external users
- Automatic assignment: Internal users as ticket creators, external users assigned to primary admin for review
- Unique email thread ID generation for proper email reply tracking and conversation threading
- Updated all email notification functions to include external users in communications
- External users receive detailed confirmation emails with reply instructions and thread tracking
- Internal users receive simplified confirmation emails with standard ticket details
- Enhanced Ticket model with external user identification methods: is_external_user(), get_notification_email(), get_display_name()
- Updated email notification system to automatically include external users in assignment, status, and comment notifications
- Comprehensive testing confirms all external user functionality working correctly
- Email webhook endpoint properly creates tickets with external user data and sends confirmation emails
- ✅ COMPLETED: Email-to-Ticket System implemented using SendGrid Inbound Parse
- Created `/api/inbound-email` webhook endpoint to receive emails sent to mail1.opscal.io
- Automatic ticket creation from email content with subject as title and body as description
- User recognition system - assigns tickets to known users based on sender email
- Confirmation emails sent to known users with ticket number and details
- Admin test endpoint `/api/test-email-webhook` for system verification
- Comprehensive setup documentation in EMAIL_TO_TICKET_SETUP.md
- DNS configuration: MX record points mail1.opscal.io to mx.sendgrid.net
- Supports any email address ending in @mail1.opscal.io (tickets@, support@, help@, etc.)
- ✅ COMPLETED: Enhanced email parsing for forwarded emails and empty content
- Improved handling of Fw:/Fwd: emails with pattern detection for original content
- Metadata capture from headers, envelope, and attachment data when email body is empty
- Fixed database constraint issue for unknown email senders (assigns to admin user)
- Enhanced debugging and logging for troubleshooting email processing issues
- Production testing confirmed: webhook working on https://dev.opscal.io
- ✅ COMPLETED: Raw MIME email parsing implementation
- Added full support for SendGrid's "POST the raw, full MIME message" format
- Intelligent parsing handles multipart emails, content-type detection, and UTF-8 encoding
- Fallback support maintains compatibility with both raw MIME and form-based email data
- Comprehensive testing confirms proper email body extraction from raw MIME format
- ✅ COMPLETED: Database session handling modernization
- Eliminated all deprecated `create_scoped_session()` calls from ticket_routes.py
- Replaced with proper Flask-SQLAlchemy session handling using `Ticket.query.get()`
- Fixed critical database session compatibility issues preventing proper ticket operations
- All ticket status updates, assignments, and comment creation now working without session errors
- Email notifications for ticket operations fully restored and functional
- ✅ COMPLETED: All email functions verified and working perfectly
- Ticket assignment notifications: Working with SendGrid API (HTTP 202 responses)
- Ticket status change notifications: Working with proper email formatting
- Ticket comment notifications: Working with full context and links
- Schedule creation/update/deletion notifications: Working with technician and admin alerts
- Email-to-ticket webhook: Working with raw MIME parsing and ticket creation
- Fixed email_utils.py session handling issue in get_email_settings() function
- Comprehensive testing confirms all email systems operational with no session errors
- ✅ COMPLETED: Email-to-ticket attribution system fixed and verified
- Fixed sender attribution logic to properly assign tickets to known users based on email address
- Enhanced logging to track email processing and user recognition for debugging
- Unknown email senders correctly assigned to primary admin (admin@obedtv.com) for review and manual assignment
- Known users receive automatic confirmation emails with ticket details and are assigned as ticket creators
- System properly recognizes users like lhaley@tbn.tv and mgralish@tbn.tv and assigns tickets accordingly
- Resolved confusion where unknown senders were assigned to lhaley (who has admin privileges) instead of primary admin
- System now specifically targets primary admin account for unknown sender ticket assignment
- ✅ COMPLETED: Studio Booking API URL made configurable via STUDIO_BOOKING_API_URL environment variable
- Updated .env.example, .env, and docker-compose.yml with new configuration option
- Maintains backward compatibility with default https://plex.bookstud.io URL
- ✅ COMPLETED: All-day OOO timezone display issue completely resolved across ALL views
- Applied smart timezone detection logic to calendar, dashboard, mobile templates, and sidebar time-off views
- Fixed dashboard duplication issue where OOO entries appeared multiple times when switching between timezones
- Implemented proper date filtering to ensure OOO entries only display on their intended calendar dates
- Enhanced mobile personal schedule and mobile calendar with same timezone logic as desktop views
- Updated upcoming time-off sidebar API to properly handle Chicago-created vs Pacific-created entries
- Root cause: Existing OOO entries were created when user timezone was Chicago, causing boundary issues in Pacific timezone
- System now uses smart detection to reverse-engineer intended calendar dates for legacy entries
- Dashboard query now properly filters schedules after timezone conversion to prevent duplication
- All views (calendar, dashboard, mobile, sidebar) now display consistently regardless of user timezone setting

Recent Updates (July 14, 2025):
- ✅ COMPLETED: OOO Conflict Prevention System implemented
- Regular schedules automatically marked as "CANCELLED - OOO" when all-day OOO entries are created
- Recurring schedule generation now skips days with existing OOO entries to prevent conflicts
- Enhanced automatic generation logging to report OOO conflicts and their impact
- Manual recurring generation provides feedback about OOO conflicts preventing schedule creation
- Docker timezone troubleshooting tools and comprehensive fix documentation created
- Updated Dockerfile with proper timezone configuration (tzdata package, system timezone setting)
- Enhanced all-day time-off visual styling with dashed dark orange borders, gradient backgrounds, and vacation emoji
- Applied "OOO ALL DAY" text styling for maximum visibility across all supported views
- Dark theme support with appropriate color adjustments for accessibility
- ✅ COMPLETED: Mobile template vacation system fully implemented
- Updated both mobile calendar and mobile personal schedule templates with "OOO (Out of Office)" checkbox
- Fixed JavaScript click handlers to properly set both "Time Off" and "OOO" checkboxes when editing existing vacation entries
- Mobile templates now correctly clear both checkboxes when creating new schedule entries
- All mobile vacation functionality matches desktop experience with proper timezone handling
- ✅ COMPLETED: All-day time-off display feature implemented
- Updated JavaScript positioning logic to detect 00:00-00:00 time-off events across all calendar views
- All-day time-off events now display as compact "OOO all day" entries in 00:00 time slot only
- Enhanced mobile templates (mobile_calendar.html, mobile_personal_schedule.html) to show "OOO all day" text
- Updated dashboard positioning to handle all-day time-off events with proper compact display
- Maintains backward compatibility for existing partial-day time-off schedules
- ✅ COMPLETED: Calendar and dashboard OOO display bug fixed
- Applied overlap logic to calendar and dashboard queries to include midnight-starting OOO entries
- Fixed timezone conversion issue preventing all-day events from showing correctly
- Both calendar and dashboard now use consistent query logic for proper OOO entry display
- ✅ COMPLETED: Docker infrastructure fully updated for all-day OOO feature
- Updated init.sql with all_day column in schedule table and complete email_settings table
- Added automatic database schema migration script (update_database_schema.sql)
- Enhanced docker-entrypoint.sh to run schema updates during container startup
- Updated admin credentials to admin@obedtv.com for production consistency
- Created comprehensive deployment documentation (DEPLOYMENT_NOTES.md)
- All Docker files now support complete all-day OOO functionality with proper database schema
- ✅ COMPLETED: Auto-generated schedule descriptions cleaned up
- Removed automatic "Auto-generated from template" text from schedule descriptions
- Auto-generated schedules now have empty descriptions for cleaner calendar display
- Fixed dashboard to properly display time-off entries with gray color and "- Time Off" label
- ✅ COMPLETED: Fixed admin privileges issue in user editing
- Corrected checkbox handling for admin status in user edit form
- Admin privileges now properly maintained when updating user accounts
- Fixed issue where admins would lose admin privileges when updating their own accounts
- ✅ COMPLETED: TRUE AUTOMATIC SCHEDULING SYSTEM IMPLEMENTED
- Added APScheduler background scheduler for automatic recurring schedule generation
- System now automatically runs every Sunday at 2:00 AM to generate schedules from active templates
- Comprehensive logging for automatic generation events and debugging
- Updated documentation to reflect true "hands-off scheduling" capability
- No manual intervention required - schedules generate automatically weekly
- Auto-generation respects the 7-day minimum interval to prevent over-generation
- Fixed misleading "hands-off scheduling" documentation - now actually hands-off
- ✅ COMPLETED: Production backup restoration issue completely resolved
- Fixed table naming inconsistency between database schema and SQLAlchemy models
- Updated init.sql to use "user" table name consistently throughout all references
- Fixed sequence reset commands to reference correct table and sequence names
- Production database now matches development environment for seamless backup restoration
- All foreign key constraints now work correctly with consistent table naming
- Updated troubleshooting documentation with complete solution for production environments
- ✅ COMPLETED: Configurable chat system implemented
- Added CHAT_ENABLED environment variable to enable/disable chat functionality
- Added CHAT_URL environment variable for customizable chat service URL
- Updated all templates (base.html, mobile templates) to conditionally show chat features
- Chat functionality can now be completely disabled by setting CHAT_ENABLED=false
- Chat URL can be customized via CHAT_URL environment variable
- Updated .env.example and docker-compose.yml with new chat configuration options
- ✅ COMPLETED: Chat environment variable loading fixed
- Added python-dotenv import to app.py for proper .env file processing
- Environment variables (CHAT_ENABLED, CHAT_URL) now correctly loaded and applied to templates
- ✅ COMPLETED: Recurring schedule auto-generation CSRF token issue resolved
- Fixed auto-generate button to include proper CSRF token in JavaScript fetch request
- Auto-generation API now properly protected and functional for batch schedule creation
- ✅ COMPLETED: Edit recurring schedule form pre-population issue fixed
- Added explicit time field pre-population for Monday through Sunday start/end times
- Edit forms now correctly display existing template data instead of empty dropdowns
- Template editing functionality fully restored for comprehensive schedule management

Recent Updates (July 13, 2025):
- ✅ COMPLETED: Database schema issues resolved in init.sql
- Fixed missing location table that was referenced by schedule table
- Added complete recurring_schedule_template table for storing schedule templates
- Added proper indexes for performance optimization
- Added sample location data (Main Studio, Studio B, Control Room, Remote, Maintenance Bay)
- Updated troubleshooting documentation with schema fix details
- ✅ COMPLETED: Docker permission issue resolved in Dockerfile
- Fixed "chmod: changing permissions of '/app/docker-entrypoint.sh': Operation not permitted" error
- Used COPY --chmod=755 for proper permission handling during Docker build
- Preserved entrypoint script for essential database initialization and startup sequencing
- Enhanced entrypoint script to properly handle gunicorn startup commands
- Updated DOCKER_TROUBLESHOOTING.md with correct fix documentation
- ✅ COMPLETED: Configurable site branding system implemented
- Added comprehensive environment variable support for customizable branding
- Environment variables: SITE_NAME, SITE_TITLE, SITE_DESCRIPTION, COMPANY_NAME, SITE_LOGO
- Updated all templates (base.html, login.html, mobile templates) to use dynamic branding
- Modified app.py to inject branding variables into template context
- Updated .env.example and docker-compose.yml with branding configuration
- Maintains backward compatibility with default "Plex Engineering" branding
- ✅ COMPLETED: Quick Links editing functionality fully restored
- Fixed modal positioning by moving edit modals outside table structure for proper display
- Corrected modal IDs and Bootstrap attributes for full functionality
- Enhanced CSS z-index layering and backdrop opacity for better modal appearance
- ✅ COMPLETED: Icon selector enhancement for Quick Links management
- Replaced manual icon name entry with comprehensive dropdown selector
- Added visual icon representations (emojis) with descriptive labels
- Included 120+ Feather icons organized by category (links, communication, files, etc.)
- Applied consistent icon selector to both add and edit quick link modals
- Eliminated need for users to remember exact icon names
- ✅ COMPLETED: Quick Links 2-column grid layout implementation
- Updated sidebar Quick Links section to use CSS grid system for better space utilization
- Added hover effects, card-style containers, and proper theme support
- Implemented text overflow handling for longer link titles
- ✅ COMPLETED: Chat positioning system enhanced for application window relative positioning
- Updated chat window positioning to be relative to browser window instead of screen
- Uses window.screenX/screenY and window.outerWidth/outerHeight for precise positioning
- Chat now consistently appears in bottom-left corner of application window (100px from bottom)
- Added boundary checks to prevent chat from going off-screen
- Enhanced positioning logic works regardless of app window size or screen position
- Improved stay-on-top verification to bring chat to front of window stack without changing position
- Added moveToFront() method calls to ensure proper window stacking order
- ✅ COMPLETED: Studio Bookings auto-refresh system implemented
- Added automatic API calls every 3 minutes (180,000ms) to refresh studio booking data
- Implemented subtle loading indicator with spinning refresh icon during API calls
- Added console logging for auto-refresh events for debugging and monitoring
- System automatically updates booking information without requiring page refresh
- Enhanced user experience with real-time studio booking updates
- ✅ COMPLETED: Profile picture upload system for technicians
- Added profile_picture field to User model with database migration
- Implemented file upload handling in admin edit user interface with comprehensive debugging
- Created secure file storage in static/uploads/profile_pictures/ directory
- Updated sidebar to display actual profile photos when available, fallback to initials
- Enhanced 2-column grid layout for active technicians display
- Profile pictures support JPG, PNG, WEBP formats with timestamp-based naming
- Automatic cleanup of old profile pictures when new ones are uploaded
- Updated API endpoints to include profile picture data for frontend display
- ✅ COMPLETED: Sidebar scaling - increased all elements by 10% for better readability
- Enhanced Current Time Display, section headers, technician cards, time off cards, Quick Links
- Proportionally scaled fonts, padding, spacing, and icons across all sidebar components
- Maintained design consistency in both light and dark modes
- ✅ COMPLETED: Admin dashboard technicians table enhanced with profile pictures
- Added "Profile" column displaying 40px circular profile images when available
- Implemented fallback to colored initial badges for users without profile pictures
- Applied consistent styling matching sidebar Active Technicians design pattern
- ✅ COMPLETED: Dark mode styling for Active Technicians sidebar matching user design
- Added dynamic dark mode detection in JavaScript for real-time theme switching
- Implemented dark card backgrounds (#2d2d2d), borders (#3a3a3a), and proper text colors
- Applied consistent dark mode styling to both Active Technicians and Upcoming Time Off sections
- Enhanced sidebar appearance to match user's requested dark theme design
- ✅ COMPLETELY FIXED: Dashboard calendar positioning and CSS conflicts resolved
- Fixed CSS `background: transparent !important` that was overriding JavaScript color assignments
- Updated positioning algorithm to use `setProperty()` with `!important` for proper control
- All 4 overlapping schedules now display correctly side-by-side with proper colors and spacing
- Dashboard calendar now matches main calendar view functionality exactly
- ✅ FIXED: Timezone display clarity for overnight shifts
- Added "(+1)" indicator for overnight shifts that cross midnight to clarify end time is next day
- Improved time display logic to distinguish between same-day and overnight shifts
- ✅ CRITICAL FIX: Data integrity and CSS styling conflicts resolved
- Removed fake auto-generated overnight shifts that were creating unrealistic 23-hour schedules
- Disabled problematic recurring templates ("Obed morning" and "Obed Afternoon")
- Restored legitimate Sunday work schedules for current operations (kmoore, dmorter)
- Fixed CSS conflicts where dashboard styles were breaking main calendar styling
- Scoped dashboard-specific CSS to only apply within `.dashboard` context
- Restored proper calendar styling with `background: transparent !important` for normal events
- ✅ COMPLETED: Dashboard timezone awareness implementation
- Dashboard schedule times now display in user's selected timezone instead of UTC
- Updated template to use `current_user.get_timezone_obj()` for proper timezone conversion
- Added timezone-aware data attributes for JavaScript positioning accuracy
- Maintained "(+1)" indicator for overnight shifts that cross midnight
- Fixed CSS scoping to ensure dashboard events show proper user colors while preserving calendar styling
- ✅ COMPLETED: Dashboard schedule styling matches main calendar perfectly
- Applied exact same CSS approach as main calendar to dashboard schedule events
- Uses `background: transparent !important` with `::before` pseudo-element for semi-transparent body
- Schedule headers show full technician colors, body areas show 20% opacity color overlay
- Removed conflicting CSS rules that were preventing proper styling
- Dashboard now displays schedule blocks identically to main calendar view
- ✅ COMPLETED: Upcoming Time Off section enhanced with profile pictures and 10% scaling
- Replaced calendar icons with user profile pictures (22px circular images when available)
- Added fallback to colored initial badges for users without profile pictures
- Updated API endpoint to include profile picture data for time off entries
- Applied 10% size increase to all elements: fonts, padding, spacing, and profile images
- All sidebar section headers now use consistent 1.21rem font size for uniformity
- Maintained consistent styling with other scaled sidebar sections in both light and dark modes
- ✅ COMPLETED: Dashboard section headers enhanced with dark background colors for proper white text contrast
- Active Tickets header: dark blue (#1e40af) for excellent white text visibility
- Studio Bookings header: dark green (#047857) for strong contrast and readability
- Today's Schedule header: dark teal (#0e7490) for clear white text display
- Sidebar headers remain unchanged to maintain design differentiation
- ✅ COMPLETED: Recurring Schedules interface enhanced with full 24-hour time support
- Added JavaScript function to generate complete 24-hour time options (00:00 to 23:30)
- All dropdown menus now provide full day coverage with 30-minute increments
- Efficient dynamic population of all time selectors on page load
- Preserves selected values when dropdowns are updated
- ✅ COMPLETED: Docker deployment infrastructure fully updated
- Updated Dockerfile with all current dependencies including gunicorn, requests, trafilatura
- Added support for profile picture uploads with proper directory structure
- Enhanced docker-compose.yml with volume mapping for uploads and SESSION_SECRET environment variable
- Updated .env.example with all necessary configuration variables
- Created comprehensive deploy.sh script with health checks and deployment automation
- Added TicketView table creation to init.sql and update_database_schema.sql for unread indicators
- Docker entrypoint script automatically applies database schema updates during container startup
- All Docker files now support the complete application feature set including unread activity tracking

Previous Updates (July 12, 2025):
- Updated all logos with new TBN logo while maintaining "PLEX ENGINEERING" text branding
- Fixed logo aspect ratio to prevent squishing (height: 36px, width: auto)
- Team chat moved to main navigation with proper functionality
- Fixed chat auto-launch to only trigger for authenticated users (not on login page)
- Added "PLEX ENGINEERING" text under TBN logo on login page
- ✅ COMPLETED: Comprehensive automated recurring schedule system fully functional
- ✅ Fixed timezone handling bugs with separate get_timezone() and get_timezone_obj() methods
- ✅ Resolved CSRF token issues across all recurring schedule forms
- ✅ Fixed technician dropdown pre-population when editing templates
- ✅ Verified system correctly prevents duplicate schedule creation and generates new schedules for future periods
- ✅ System automatically converts timezone-aware schedules (Pacific Time to UTC storage) correctly

## System Architecture

### Backend Architecture
- **Framework**: Flask 3.1.0+ with Python 3.11
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login for session management
- **Security**: Flask-WTF for CSRF protection
- **Email**: SendGrid API for notifications

### Frontend Architecture
- **UI Framework**: Bootstrap 5.1.3 for responsive design
- **Icons**: Feather Icons for consistent iconography
- **Mobile Support**: Responsive design with dedicated mobile templates
- **Theme System**: Light/dark theme toggle with user preferences

### Data Storage
- **Primary Database**: PostgreSQL with connection pooling
- **Models**: User, Schedule, Ticket, Location, QuickLink, and related entities
- **Backup System**: Automated database backups with JSON exports

## Key Components

### Authentication System
- Case-insensitive email login
- Session management with remember-me functionality
- Admin role-based access control
- Password hashing with Werkzeug security

### Calendar & Scheduling
- Weekly calendar view with timezone support
- Technician schedule management
- Location-based filtering
- Time-off tracking
- Overlap detection and validation

### Ticket Management
- Complete ticket lifecycle (open, in-progress, pending, resolved, closed)
- Priority system (low, medium, high, urgent)
- Category-based organization
- Comment system with history tracking
- Assignment and notification system
- Archive functionality for old tickets

### User Management
- Profile management with timezone preferences
- Theme selection (light/dark)
- Color-coded user identification
- Admin user management interface

### Email Notifications
- Ticket assignment notifications
- Status change alerts
- Comment notifications
- Schedule change notifications

### Mobile Support
- Responsive design for all screen sizes
- Mobile-optimized templates
- Touch-friendly navigation
- Day-by-day calendar view on mobile

### Team Chat Integration
- Auto-launch chat system for new and returning users
- Smart stay-on-top functionality with dropdown protection
- Intelligent detection of user interactions to prevent UI interference
- Manual chat access via user dropdown menu

## Data Flow

1. **User Authentication**: Login → Session Creation → Role-based Access
2. **Schedule Management**: Form Input → Validation → Database Storage → Email Notifications
3. **Ticket Workflow**: Creation → Assignment → Status Updates → History Tracking → Notifications
4. **Real-time Updates**: AJAX endpoints for active users and system status

## External Dependencies

### Email Service
- **SendGrid**: For all email notifications
- **Configuration**: API key required in environment variables
- **Domain**: Configurable email domain for link generation

### Frontend Libraries
- **Bootstrap**: UI framework and responsive grid
- **Feather Icons**: Scalable icon system
- **jQuery**: DOM manipulation and AJAX requests

### Development Tools
- **Flask-WTF**: Form handling and CSRF protection
- **SQLAlchemy**: Database ORM with migration support
- **pytz**: Timezone handling and conversion

## Deployment Strategy

### Container-based Deployment
- **Docker**: Multi-stage build with Python 3.11-slim base
- **Docker Compose**: PostgreSQL + Flask application stack
- **Health Checks**: Built-in health endpoint for monitoring
- **Volumes**: Persistent storage for database and backups

### Production Configuration
- **Environment Variables**: All sensitive configuration externalized
- **Database**: PostgreSQL with connection pooling
- **Static Files**: Served through Flask with CDN-ready setup
- **Backup Strategy**: Automated database dumps and application data exports

### Database Management
- **Schema Updates**: Automated migration scripts
- **Backup/Restore**: Complete system backup with JSON exports
- **Data Integrity**: Foreign key constraints and validation

### Security Considerations
- **CSRF Protection**: All forms protected with tokens
- **Session Security**: Secure session management
- **Input Validation**: Server-side validation for all inputs
- **SQL Injection Prevention**: Parameterized queries throughout

The application follows a modular architecture with clear separation of concerns, making it maintainable and scalable for team scheduling needs.