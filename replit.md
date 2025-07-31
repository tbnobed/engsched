# Plex Engineering Technician Scheduler

## Overview
This is a comprehensive web application designed for managing technician schedules and tickets, built with Flask and PostgreSQL. Its primary purpose is to provide a robust system for calendar-based scheduling, efficient ticket management, and flexible user administration. The application aims to streamline operations, enhance communication, and provide real-time insights into team availability and workload, serving as a critical tool for operational efficiency in an engineering or service technician environment.

## User Preferences
Preferred communication style: Simple, everyday language.
Chat Requirements: Auto-launch team chat and maintain stay-on-top functionality while preserving dropdown menu interactions.

## System Architecture

### Backend Architecture
- **Framework**: Flask 3.1.0+ with Python 3.11 for server-side logic.
- **Database**: PostgreSQL with SQLAlchemy ORM for data persistence and management.
- **Authentication**: Flask-Login handles user sessions and authentication.
- **Security**: Flask-WTF provides CSRF protection for forms.
- **Email**: SendGrid API integrated for transactional email notifications.

### Frontend Architecture
- **UI Framework**: Bootstrap 5.1.3 ensures a responsive and modern user interface.
- **Icons**: Feather Icons provide a consistent and scalable icon set.
- **Mobile Support**: Dedicated mobile templates and responsive design ensure optimal experience across devices.
- **Theme System**: User-configurable light and dark mode toggle.

### Core Features
- **Authentication System**: Case-insensitive email login, session management, remember-me functionality, and admin role-based access.
- **Calendar & Scheduling**: Weekly calendar view with user-specific timezone support, technician schedule management, location-based filtering, time-off tracking (including all-day OOO), and conflict prevention for scheduling. Supports 30-minute increments.
- **Ticket Management**: Full lifecycle management (open, in-progress, pending, resolved, closed), priority and category system, comment history, assignment, unread activity indicators, and email notifications. All users can modify tickets, only admins can delete.
- **User Management**: Profile management with timezone preferences, theme selection, and color-coded identification.
- **Email Notifications**: Comprehensive system for ticket assignments, status changes, comments, and schedule alterations, including external user support with email reply detection and consistent threading.
- **Mobile Support**: Dedicated mobile interface with bottom navigation, optimized templates, and daily calendar view.
- **Team Chat Integration**: Auto-launching chat with stay-on-top functionality and UI interaction preservation.
- **Quick Links Management**: Customizable quick links with icon selection and administrative editing capabilities.
- **Automated Scheduling**: Recurring schedule generation based on templates, with an automatic background scheduler.
- **Profile Pictures**: Upload and display of user profile pictures across various sections like sidebar, admin table, and OOO events.
- **Dashboard Enhancements**: Real-time team statistics (availability, active tickets, schedule coverage, time off), dynamic timeline, and studio bookings display with timezone awareness.
- **Backup & Restore**: System for exporting and importing complete application data, including users, schedules, tickets, and recurring templates.

## External Dependencies

- **PostgreSQL**: Primary database for all application data.
- **SendGrid**: Used for sending all email notifications (ticket updates, schedule changes).
- **Bootstrap 5.1.3**: Frontend UI framework.
- **Feather Icons**: Icon library for UI elements.
- **jQuery**: JavaScript library for DOM manipulation and AJAX requests.
- **pytz**: Python library for timezone calculations and conversions.
- **Flask-Login**: Flask extension for user session management.
- **Flask-WTF**: Flask extension for form handling and CSRF protection.
- **SQLAlchemy**: Python SQL toolkit and Object Relational Mapper.
- **APScheduler**: Python library for scheduling recurring tasks.
- **Werkzeug**: Comprehensive WSGI utility library, used for password hashing.
- **python-dotenv**: For loading environment variables from `.env` files.
- **gunicorn**: WSGI HTTP Server used for production deployment.
- **requests**: Python HTTP library for making API calls.
- **trafilatura**: For extracting content from web pages (used in email parsing).
- **Studio Booking API**: External service for integrating studio booking information (configurable via `STUDIO_BOOKING_API_URL`).