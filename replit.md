# Plex Engineering Technician Scheduler

## Overview

This is a comprehensive web application for managing technician schedules and tickets, built with Flask and PostgreSQL. The system provides calendar-based scheduling, ticket management, and user administration with both desktop and mobile-responsive interfaces.

## User Preferences

Preferred communication style: Simple, everyday language.
Chat Requirements: Auto-launch team chat and maintain stay-on-top functionality while preserving dropdown menu interactions.

Recent Updates (July 29, 2025):
- ✅ COMPLETED: CRITICAL Docker Schema Fix - Quick Links Database Column Missing
- Fixed critical production database issue where quick_link table was missing the description column
- Updated init.sql to include description VARCHAR(500) DEFAULT '' column in quick_link table definition
- Created add_quick_link_description_column.sql migration script for existing deployments
- Enhanced docker-entrypoint.sh to automatically run database schema migrations on container startup
- Updated update_database_schema.sql to include quick_link description column fix alongside ticket_view table
- Created comprehensive documentation (QUICK_LINK_SCHEMA_FIX.md) for deployment and troubleshooting
- Resolved mobile quick links page 500 error: "column quick_link.description does not exist"
- Docker deployments now automatically sync database schema with model definitions
- ✅ COMPLETED: Mobile Calendar Interface Enhancements - Compact Design and Professional Styling
- Made schedule cards more compact with reduced padding (0.75rem/1rem) and smaller border-radius (1rem)
- Reduced margins between schedule items from 1.5rem to 1rem for better space utilization
- Decreased user avatar size from 48px to 36px with thinner borders for mobile optimization
- Enhanced time labels on timeline from 0.85rem to 1.1rem with font-weight 700 for better visibility
- Improved text contrast by forcing white color with !important declarations for gradient header
- Applied bold font-weight to all header text elements for consistent visual hierarchy
- Mobile calendar now displays more schedule information per screen while maintaining touch-friendly interactions
- ✅ COMPLETED: Mobile Calendar Header Gradient Implementation - Purple-Blue Gradient Display
- Fixed CSS specificity issues preventing gradient from displaying in mobile calendar header
- Added !important declarations to override conflicting Bootstrap and theme CSS
- Implemented theme-specific selectors for consistent gradient display across light/dark modes
- Mobile calendar header now displays beautiful purple-to-blue gradient (135deg, #667eea to #764ba2)
- Enhanced visual hierarchy with white text contrast and glassmorphism effects
- ✅ COMPLETED: Mobile Personal Schedule Week Navigation Fix - Consistent Monday-to-Sunday Display
- Fixed mobile personal schedule to always display weeks in Monday-to-Sunday order regardless of navigation direction
- Enhanced week calculation logic to normalize any provided date to its Monday week start for consistent display
- Updated form redirects to preserve week context after adding/editing schedules with proper error handling
- JavaScript navigation now correctly calculates Monday-based week boundaries for forward and backward navigation
- Backend route applies additional normalization to ensure any date parameter results in Monday week start
- Mobile personal schedule now maintains consistent week view structure when navigating between weeks
- All form submissions (add schedule, validation errors) redirect back to the correct week view
- ✅ COMPLETED: Critical Mobile Navigation Bug Fixes - Complete Mobile Route Consistency
- Fixed mobile users being incorrectly redirected to desktop views after performing ticket actions (status updates, comments, etc.)
- Implemented mobile-aware redirect helper functions in ticket_routes.py to maintain mobile navigation flow
- Updated all ticket operations (status changes, comments, form submissions) to route mobile users back to mobile interfaces
- Fixed mobile ticket template "Back" button to properly route to mobile tickets page instead of desktop dashboard
- Enhanced mobile device detection in redirect logic to ensure consistent mobile experience across all ticket operations
- Mobile users now stay within mobile interface throughout entire ticket management workflow
- ✅ COMPLETED: Mobile Ticket Creation Form Navigation Fix - Complete Form Submission Flow
- Fixed mobile ticket creation Cancel button to redirect to mobile tickets page instead of desktop dashboard
- Enhanced mobile_aware_redirect function to properly detect mobile devices using is_mobile_device() function
- Added hidden mobile parameter to mobile create ticket form for proper routing context detection
- Mobile ticket creation now maintains mobile interface throughout entire create/cancel workflow
- Form submissions from mobile devices correctly route back to mobile views after successful ticket creation
- All mobile ticket operations (New, View, Edit, Cancel, Create) now preserve mobile navigation consistency
- ✅ COMPLETED: Mobile Status Update Bug Fix - Quick Action Buttons Working
- Fixed critical mobile status update validation error that was preventing "Mark Resolved" buttons from working
- Replaced problematic `vars(TicketStatus).values()` validation with explicit valid status list
- Mobile quick action buttons (Start Work, Set Pending, Resolve, Close) now function correctly
- Status updates properly execute with automatic comment generation and email notifications
- Mobile users can now successfully update ticket status using both quick buttons and modal forms
- All mobile ticket status operations maintain mobile interface navigation throughout workflow
- ✅ COMPLETED: Mobile User Interface Enhancements - Complete User Menu System
- Added comprehensive user profile menu to mobile header with user icon dropdown
- Integrated logout functionality directly accessible from mobile interface header
- Created timezone change modal with simplified selection (CST, PST, EST, MST, UTC options)
- Added theme toggle functionality within mobile user menu for light/dark mode switching
- Removed dropdown arrows from timezone selector for cleaner mobile appearance
- Enhanced mobile device detection with 25+ device patterns for better real device recognition
- User menu includes: username display, theme toggle, timezone settings, profile link, and logout
- All mobile templates now support full user account management without desktop interface
- Dark/light theme support maintained across all new mobile user interface elements

Recent Updates (July 28, 2025):
- ✅ COMPLETED: Comprehensive Mobile App Redesign with Complete Navigation System
- Created complete mobile interface with modern bottom navigation for Dashboard, Schedule, Tickets, and Quick Links
- Built dedicated mobile templates: mobile/dashboard.html, mobile/tickets.html, mobile/calendar.html, mobile/personal_schedule.html, mobile/quick_links.html
- Added comprehensive mobile routes: /mobile/dashboard, /mobile/tickets, /mobile/calendar, /mobile/personal_schedule, /mobile/quick_links
- Enhanced mobile base template (mobile_base_enhanced.html) with proper navigation and responsive design
- Mobile dashboard includes active tickets, studio bookings, today's schedule, currently active technicians, and upcoming time off sections
- Mobile tickets view features filtering, quick status updates, and touch-friendly interface
- Mobile calendar provides daily schedule view with add/edit functionality and timezone awareness
- Mobile personal schedule shows weekly view with hours calculation and comprehensive schedule management
- Mobile quick links displays grid layout with admin editing capabilities and proper icon management
- All mobile templates include dark/light theme support and touch-optimized interactions
- Bottom navigation properly routes to mobile-specific pages for optimal mobile experience
- API endpoints support mobile functionality with real-time updates and badge counters
- ✅ COMPLETED: Mobile Navigation Bug Fixes and Route Corrections
- Fixed all route naming errors in mobile templates (admin_create_quick_link, admin_edit_quick_link, admin_delete_quick_link)
- Corrected CSRF token handling for proper form security across all mobile pages
- Fixed Location model queries to work with existing database schema (removed .active filter)
- Resolved date import errors in mobile routes for proper functionality
- ✅ COMPLETED: Enhanced Mobile Dashboard with Complete Sidebar Features
- Added "Currently Active" section showing real-time active technicians with profile pictures and status
- Added "Upcoming Time Off" section displaying scheduled time off with user profiles and dates
- Implemented auto-refresh functionality for real-time data updates every 60 seconds
- Mobile dashboard now matches desktop functionality with all essential information sections
- ✅ COMPLETED: Mobile Dashboard 2-Column Grid Layout with Optimized Readability
- Converted all mobile dashboard sections (Currently Active, Upcoming Time Off, Today's Schedule, Studio Bookings) to 2-column grid layouts
- Implemented smaller, compact cards with 8px gaps for efficient space utilization
- Enhanced readability with optimized font sizes: usernames 0.9rem, details 0.75rem, improved line height 1.2
- Fixed profile picture display issues - now shows actual user photos with proper /static/ paths
- All sections use consistent 28px profile pictures, center-aligned content, and 80px minimum card height
- Maintained real profile picture support and proper dark/light theme compatibility

Recent Updates (July 22, 2025):
- ✅ COMPLETED: Enhanced "Open" Status Filter - Active Ticket Grouping
- Updated "Open" status filter to include open, in_progress, and pending tickets for better workflow visibility
- Modified ticket dashboard query logic to group active statuses under the "Open" filter option
- Provides comprehensive view of all tickets requiring attention in a single filter selection
- Improves ticket management efficiency by showing all actionable tickets together
- ✅ COMPLETED: Universal Ticket Management Permissions - All Users Can Modify Tickets
- Removed admin-only restrictions from ticket assign, edit, update, and archive operations
- Updated templates (view.html, mobile_view_ticket.html) to show ticket action buttons for all authenticated users
- Modified ticket routes (assign_ticket, edit_ticket, archive_ticket, unarchive_ticket) to allow all users access
- Only delete operations remain admin-only for data protection while enabling collaborative ticket management
- All users can now: assign tickets, update status, edit ticket details, add comments, and archive/unarchive tickets
- Enhanced team collaboration by removing permission barriers while preserving critical delete safeguards
- ✅ COMPLETED: CRITICAL Password Restoration Bug Fixed - Complete Backup/Restore System Repair
- Fixed critical backup restoration issue where existing users' passwords weren't being updated during restore
- Enhanced restore_backup() function to update existing users instead of skipping them completely
- Updated User.to_dict() method to include profile_picture field in backup exports for complete data preservation
- All user fields now properly restored: password_hash, email, color, admin status, timezone, and profile pictures
- Backup system now handles both new user creation AND existing user data updates during restoration
- Resolved skip logic that was preventing password restoration from backup files
- Complete backup/restore functionality verified for all user account data and authentication credentials
- ✅ COMPLETED: 30-Minute Increment System Fully Implemented and Fixed
- Fixed critical JavaScript form submission issues where ":00" was being duplicated to time values
- Updated all edit window JavaScript to properly populate HH:MM format including minutes instead of just hours
- Fixed mobile template time display to use consistent 24-hour format (23:30) instead of 12-hour format (01:30 AM)
- Updated calendar.js, mobile_calendar.html, and mobile_personal_schedule.html for consistent time handling
- All schedule creation, editing, and display now supports precise 30-minute increments across desktop and mobile
- Form submission properly handles HH:MM format without adding extra ":00" suffixes
- Edit windows now correctly populate with existing schedule times including minutes

Recent Updates (July 18, 2025):
- ✅ COMPLETED: Dashboard Section Headers Enhanced with Conditional Dark Mode Gradient Colors
- Applied 50% opacity gradient backgrounds to all three dashboard section headers with theme-aware styling
- Light Mode: Dark color gradients (blue, green, teal) at 50% opacity for stronger visual distinction
- Dark Mode: Bright color gradients (cyan/purple, emerald, sky blue) at 50% opacity for enhanced visibility
- Fixed CSS specificity conflicts by creating dashboard-specific gradient classes with !important declarations
- Active Tickets: Blue/purple gradient with conditional theme-based color variants
- Studio Bookings: Green/emerald gradient adapting to light/dark theme preferences  
- Today's Schedule: Teal/cyan gradient providing optimal contrast in both themes
- Creates elegant visual distinction while maintaining readability across all theme preferences
- ✅ COMPLETED: Dark Mode Table Hover Fix - Text Visibility Restored
- Fixed dark gray hover backgrounds that were making text disappear in dark mode
- Applied light gray hover effect (rgba(255, 255, 255, 0.1)) for better contrast in dark theme
- Updated table-hover, tbody hover, and sortable-row hover styles for consistent behavior
- Dark mode table interactions now maintain text visibility while providing visual feedback
- ✅ COMPLETED: Template Import Issue Fixed - Multiple Technician Lookup Methods
- Fixed critical template import bug where backup files used different data format than import function expected
- Enhanced import logic to handle multiple technician identification methods:
  * Method 1: Direct username match (technician_username)
  * Method 2: Database ID lookup (technician_id) 
  * Method 3: Smart name matching (technician_name like "Blake G" → username starting with "blake")
- Fixed weekly schedule parsing to handle nested structure from backup files
- Updated import function to properly extract working days and time ranges from weekly_schedule object
- Template imports now work seamlessly with existing backup files
- ✅ COMPLETED: TBN Logo Replacement for Dark Mode Navigation and Auth Page
- Updated all navigation templates (base.html, mobile_base.html, mobile_base_simplified.html) to show new TBN logo in dark mode only
- Original site logo still displays in light mode for consistent branding
- Updated login/auth page (login.html) to use new TBN logo with 30% larger size (156px vs 120px)
- New logo file stored as static/tbn_logo_dark.png for reliable access
- ✅ COMPLETED: Export Page Freezing Issue Resolved - Streaming JSON Implementation
- Limited backup schedules to 2000 most recent entries to prevent data overload
- Implemented streaming JSON response with chunked processing (50-item batches)
- Added periodic yield points to prevent browser freezing during large exports
- Enhanced backup system with memory-efficient processing and progress logging

Recent Updates (July 17, 2025):
- ✅ COMPLETED: Export/Import Template Window Sizing Fixed - Ultra-Compact Design
- Fixed oversized export/import template cards that were taking excessive vertical space
- Applied strict height limits (120px max), reduced padding (py-1, px-2), and smaller fonts
- Created horizontal layout with file input and button side-by-side for import
- Reduced icon sizes, button padding, and margins for efficient space utilization
- Export/import section now takes minimal screen real estate while maintaining full functionality
- ✅ COMPLETED: Backup Export System Optimization and Error Fixes
- Fixed critical schedule export variable scope bug that was causing "user_tz not defined" errors
- Added loading indicators with automatic timeout and focus detection for better UX
- Optimized JSON serialization with compact formatting to prevent browser freezing
- Limited backup tickets to 1000 most recent to prevent memory overload during exports
- Enhanced error handling and logging for better troubleshooting of export issues
- ✅ COMPLETED: Recurring Schedule Templates Added to Backup and Restore System
- Enhanced backup functionality to include recurring schedule templates in all backup files
- Updated restore process to properly recreate recurring templates with technician and location references
- Backup now includes all critical data: users, schedules, recurring templates, locations, quick links, tickets, and email settings
- Restore process handles template conflicts by skipping duplicates and provides detailed feedback on restored/skipped items
- Updated backup interface to clearly show all included data types for transparency
- Added dedicated export/import section to recurring schedules admin page for template-specific backup management
- ✅ COMPLETED: Timezone-Aware Export System for Admin Schedule Exports
- Updated export_schedules function to respect individual user timezone settings instead of hardcoded Chicago time
- Each user's schedule export now displays times in their personal timezone (CST, PST, etc.)
- Added timezone information header to each Excel worksheet showing user's timezone setting
- Export now uses admin user's timezone for date range selection and each technician's timezone for their schedule data
- Enhanced export headers with clear timezone identification: "Timezone: America/Chicago (America/Chicago)"
- All exported times (Clock In, Clock Out) now show in user's local timezone for accurate timesheet reporting

Recent Updates (July 16, 2025):
- ✅ COMPLETED: Side-by-Side Checkbox Layout for Schedule Forms
- Updated all schedule forms to display "Time Off" and "OOO (Out of Office)" checkboxes side by side using Bootstrap columns
- Applied consistent layout across all templates: calendar.html, personal_schedule.html, mobile_calendar.html, mobile_personal_schedule.html
- Replaced stacked vertical layout with clean 2-column Bootstrap grid (col-6) for better space utilization
- Enhanced user experience with more compact form layout while maintaining proper form-check styling
- Checkboxes now display horizontally for cleaner visual appearance and better use of available space
- ✅ COMPLETED: Dashboard as Main Homepage with Logo Navigation Update
- Set dashboard as the primary homepage for authenticated users (already configured in routes.py)
- Updated logo navigation in all templates (base.html, mobile_base.html, mobile_base_simplified.html) to point to dashboard
- Logo now serves as home button leading to comprehensive dashboard view with tickets, studio bookings, and schedules
- Maintains mobile device detection that redirects to mobile calendar when appropriate
- ✅ COMPLETED: Studio Bookings Display Enhancement - Comprehensive Information Display
- Enhanced dashboard studio bookings to show all available API data instead of just title and time
- Added description, production type, status badges (confirmed=green, cancelled=red, pending=yellow), and severity indicators
- Removed studio ID and PCR room information per user preference for cleaner display
- Improved visual design with color-coded status badges and organized grid layout with proper icons
- Studio bookings now display: title, time, description, type, status, and severity (when applicable)
- Added dark mode support with proper background colors (#2d2d2d), borders (#3a3a3a), and text colors for better theme integration
- ✅ COMPLETED: CRITICAL MOBILE NAVIGATION CRISIS RESOLVED - Auth Blueprint Registration and Template Syntax Fix
- Fixed missing auth blueprint registration in app.py that was causing all auth.logout routes to be undefined
- Resolved critical Jinja template syntax error in mobile_base_simplified.html (orphaned {% endfor %} tag without matching {% for %})
- Removed duplicate logout route from routes.py to prevent route conflicts between auth.py and routes.py
- Updated all templates (base.html, mobile_base.html, mobile_base_simplified.html) to use correct auth.logout route
- All mobile navigation now functions properly without Internal Server Errors across all routes
- Enhanced mobile OOO styling with improved contrast, spacing, and proper dark/light theme support
- ✅ COMPLETED: Mobile Active Tickets Sidebar Fix - Now Shows Real Active Tickets
- Fixed hardcoded "No active tickets" text in both mobile_base.html and mobile_base_simplified.html templates
- Mobile Active Tickets sidebar now uses get_user_tickets() function to display actual active tickets from database
- Added proper priority badges, ticket IDs, status display, and click-through links to individual tickets
- Mobile sidebar now shows up to 5 active tickets with same functionality as desktop version
- ✅ COMPLETED: Mobile Calendar Template 500 Error Fix and Chrome DevTools Testing Solution
- Fixed missing user_timezone template variable in mobile_calendar.html that was causing 500 Internal Server Error
- Resolved Jinja template syntax error in mobile_base.html (missing {% for %} tag with orphaned {% endfor %})
- Enhanced mobile detection with comprehensive User-Agent analysis and Chrome DevTools compatibility
- Added force mobile parameter (?mobile=true) for testing mobile interface without actual mobile device
- Discovered Chrome DevTools mobile emulation limitation: sends desktop User-Agent even when mobile device selected
- Mobile force parameter enables reliable mobile testing: /dashboard?mobile=true redirects to mobile calendar interface
- Mobile templates now render correctly with proper viewport configuration and mobile-optimized navigation
- Real mobile devices will automatically detect and redirect to mobile interface using authentic mobile User-Agent headers
- ✅ COMPLETED: Mobile Dashboard Routing Fix for Optimal Mobile Experience
- Fixed dashboard route to detect mobile devices and automatically redirect to mobile-optimized calendar view
- Mobile users accessing /dashboard now seamlessly redirect to /calendar with mobile-friendly templates
- Enhanced mobile detection using User-Agent patterns: android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini|mobile
- Mobile interface displays compact sidebar with current time, active technicians, upcoming time off, and quick links
- Mobile navigation includes hamburger menu for easy access to all scheduling features
- Mobile templates provide touch-optimized daily calendar view instead of desktop weekly view
- System automatically serves mobile_calendar.html template for mobile devices while preserving desktop experience for desktop users
- ✅ COMPLETED: Calendar Logo Favicon and Mobile App Icons Implementation
- Created custom calendar-style SVG icons at multiple resolutions (32px, 192px, 512px) using site's brand colors
- Replaced TBN logo with calendar logo for favicon, mobile app icons, and navigation loading spinner
- Added comprehensive web app manifest for PWA support with proper theme colors and icon configurations
- Updated all templates (base.html, mobile_base.html, mobile_base_simplified.html) to use new iconography
- Navigation page transitions now use calendar logo instead of TBN logo for better brand consistency
- Enhanced mobile device support with proper apple-touch-icon and manifest.json configuration
- Maintained TBN logo as client branding in navigation while using calendar logo for technical/app purposes
- ✅ COMPLETED: Real-Time Sidebar Auto-Refresh System for Active Tickets
- Fixed API endpoint routing pattern to match Flask blueprint structure (/tickets/api/refresh-sidebar)
- Implemented automatic sidebar ticket updates every 60 seconds with authentication protection
- Added visual feedback for sidebar refresh operations with smooth animations and proper error handling
- Enhanced auto-refresh to pause when browser tab is hidden and resume when visible for performance
- Console logging shows successful sidebar refresh operations: "Sidebar tickets refreshed - 5 active tickets"
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