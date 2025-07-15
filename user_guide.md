# Plex Engineering Technician Scheduler User Guide

**Version 1.2.2 - March 2025**

![Plex Engineering Logo](static/images/plex_logo_small.png)

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
   - [Logging In](#logging-in)
   - [Interface Overview](#interface-overview)
   - [Mobile vs. Desktop Experience](#mobile-vs-desktop-experience)
   - [Theme Preferences](#theme-preferences)
3. [Calendar and Scheduling](#calendar-and-scheduling)
   - [Viewing the Calendar](#viewing-the-calendar)
   - [Creating a Schedule](#creating-a-schedule)
   - [Editing and Deleting Schedules](#editing-and-deleting-schedules)
   - [Time Off Management](#time-off-management)
   - [Mobile Calendar Navigation](#mobile-calendar-navigation)
4. [Ticket System](#ticket-system)
   - [Viewing Tickets](#viewing-tickets)
   - [Creating Tickets](#creating-tickets)
   - [Updating Ticket Status](#updating-ticket-status)
   - [Adding Comments](#adding-comments)
   - [Assigning Tickets](#assigning-tickets)
   - [Mobile Ticket Management](#mobile-ticket-management)
   - [Searching and Filtering](#searching-and-filtering)
   - [Archiving Tickets](#archiving-tickets)
5. [User Profile and Settings](#user-profile-and-settings)
   - [Changing Password](#changing-password)
   - [Updating Timezone](#updating-timezone)
   - [Setting Theme Preference](#setting-theme-preference)
   - [Mobile Profile Access](#mobile-profile-access)
6. [Admin Features](#admin-features)
   - [User Management](#user-management)
   - [Location Management](#location-management)
   - [Ticket Categories](#ticket-categories)
   - [Quick Links](#quick-links)
   - [Email Settings](#email-settings)
   - [Database Backup and Restore](#database-backup-and-restore)
7. [Mobile-Specific Features](#mobile-specific-features)
   - [Responsive Navigation](#responsive-navigation)
   - [Day-by-Day Calendar View](#day-by-day-calendar-view)
   - [Simplified Ticket Interface](#simplified-ticket-interface)
   - [Mobile-Optimized Forms](#mobile-optimized-forms)
8. [Troubleshooting](#troubleshooting)
   - [Common Issues](#common-issues)
   - [Browser Compatibility](#browser-compatibility)
   - [Contact Support](#contact-support)

## Introduction

The Plex Engineering Technician Scheduler is a comprehensive web-based application designed to optimize workforce management through intelligent scheduling and advanced communication tools. The system provides a central hub for managing technician schedules, locations, and service tickets.

This guide will walk you through all aspects of the system, including the mobile-responsive features that allow users to access and use the application effectively from any device.

## Getting Started

### Logging In

1. **Access the application** by navigating to your organization's URL in any modern web browser.
2. **Enter your credentials** on the login page:
   - Username or Email (case-insensitive for easier mobile entry)
   - Password (case-sensitive)
3. **Optional: Select "Remember Me"** to stay logged in on trusted devices.

*Note: If you don't have an account, contact your system administrator. Self-registration has been disabled for security purposes.*

### Interface Overview

The interface is divided into several key areas:

- **Navigation Sidebar** (Desktop): Access all system features from the left sidebar including calendar, tickets, profile, and admin functions.
- **Top Navigation Bar** (Mobile): Provides access to the main menu via hamburger icon, theme toggle, and displays your username.
- **Calendar View**: The main scheduling interface displaying technician assignments.
- **Active Users & Time Off**: Shows currently active technicians and upcoming time off (desktop only).
- **Ticket Dashboard**: Lists and manages service tickets.

### Mobile vs. Desktop Experience

The application automatically detects your device type and serves the appropriate interface:

- **Desktop Experience**: Full-featured interface with sidebar navigation, detailed views, and comprehensive data presentation.
- **Mobile Experience**: Streamlined interface with touch-friendly navigation, simplified views, and optimized forms for smaller screens.

*Note: All core functionality is available in both interfaces, but the mobile version prioritizes essential features and simplifies interactions.*

### Theme Preferences

The application supports both dark and light themes that can be toggled using:

- **Desktop**: Theme toggle button in the sidebar
- **Mobile**: Theme toggle button next to the hamburger menu

Your theme preference is saved to your user profile and will persist across sessions and devices.

## Calendar and Scheduling

### Viewing the Calendar

#### Desktop Calendar

The desktop calendar provides a comprehensive week view:

1. **Navigate** using the Previous/Next Week buttons or jump to Today.
2. **View technician schedules** color-coded by technician.
3. **See time off** marked with distinctive styling.
4. **Filter** to view all schedules or just your personal schedule.
5. **Time information** is displayed according to your selected timezone.

#### Mobile Calendar

The mobile calendar provides a focused day-by-day view:

1. **Navigate** using the Previous/Next Day buttons or jump to Today.
2. **View technician schedules** for the selected day only.
3. **Time off** is clearly marked with a dark red badge.
4. **Add new schedules** using the dedicated button on each day view.

### Creating a Schedule

#### Desktop Schedule Creation

1. Click the **Add Schedule** button or click directly on the calendar grid.
2. Complete the **schedule form**:
   - Select a technician
   - Set start and end times
   - Add a description
   - Select a location (optional)
   - Mark as time off if applicable
3. Click **Save** to create the schedule.

#### Mobile Schedule Creation

1. Navigate to the desired date.
2. Tap the **Add Schedule** button.
3. Complete the mobile-optimized form:
   - Select a technician
   - Set date and time (simplified entry for mobile)
   - Add description
   - Select location or time off options
4. Tap **Save** to create the schedule.

### Editing and Deleting Schedules

#### Desktop Editing

1. **Click on a schedule** in the calendar to open the detailed view.
2. Select **Edit** to modify the schedule details.
3. Select **Delete** to remove the schedule (confirmation required).

#### Mobile Editing

1. **Tap on a schedule** in the day view to open the details.
2. Tap **Edit** to access the simplified edit form.
3. Tap **Delete** to remove the schedule (confirmation required).

### Time Off Management

Time off is displayed distinctively in both desktop and mobile views:

- **Desktop**: Time off appears with a different background color and "Time Off" label.
- **Mobile**: Time off entries have a dark red badge for clear identification.

Creating time off follows the same process as regular schedules but with the "Time Off" option checked.

### Mobile Calendar Navigation

The mobile calendar interface provides unique navigation designed for touch and smaller screens:

1. **Day Selection**: Navigating by single days instead of weekly view.
2. **Date Display**: Clearly shows the current date at the top of the screen.
3. **Today Button**: Quickly jump to the current day.
4. **Schedule List**: Vertically scrollable list of schedules for the selected day.
5. **Empty Day Indicator**: Shows "No schedules for this day" when applicable.

## Ticket System

### Viewing Tickets

#### Desktop Ticket Dashboard

The desktop ticket dashboard provides a comprehensive view:

1. **Filter options** by status, category, priority, and assignment.
2. **Search functionality** to find tickets by keywords or assigned technician.
3. **Ticket metrics** showing counts by status.
4. **Detailed table view** with sortable columns.

#### Mobile Ticket Dashboard

The mobile ticket dashboard offers:

1. **Simplified filters** with toggle buttons for "Assigned to Me" and "Created by Me".
2. **Search box** for keyword and technician searches.
3. **Status counts** for quick reference.
4. **Compact list view** optimized for scrolling on mobile devices.

### Creating Tickets

#### Desktop Ticket Creation

1. Click **New Ticket** in the sidebar or ticket dashboard.
2. Complete the **ticket form**:
   - Title
   - Description
   - Category
   - Priority
   - Assigned Technician (optional)
   - Due Date (optional)
3. Click **Create Ticket**.

#### Mobile Ticket Creation

1. Tap **New Ticket** in the mobile dashboard.
2. Complete the mobile-optimized form with simplified fields.
3. Tap **Create Ticket** to submit.

### Updating Ticket Status

#### Desktop Status Updates

1. Open the ticket details view.
2. Click the **Update Status** button.
3. Select the new status from:
   - Open
   - In Progress
   - Pending
   - Resolved
   - Closed
4. Add a comment explaining the status change (optional).
5. Click **Update**.

#### Mobile Status Updates

1. Open the ticket in mobile view.
2. Tap the **Update Status** button.
3. Select the new status.
4. Add an optional comment.
5. Tap **Update** to save changes.

*Note: All authenticated users can update ticket status regardless of assignment, enabling team collaboration.*

### Adding Comments

#### Desktop Comment Addition

1. Scroll to the comment section on the ticket detail page.
2. Enter your comment in the text box.
3. Click **Add Comment**.

#### Mobile Comment Addition

1. Open the ticket in mobile view.
2. Scroll to the comment section.
3. Enter your comment in the mobile-optimized input area.
4. Tap **Add Comment**.

### Assigning Tickets

#### Desktop Assignment

1. Open the ticket details.
2. Click **Assign** button.
3. Select a technician from the dropdown.
4. Click **Assign Ticket**.

#### Mobile Assignment

1. Open the ticket in mobile view.
2. Tap **Assign** button.
3. Select a technician from the simplified dropdown.
4. Tap **Assign Ticket**.

*Note: All authenticated users can assign tickets, facilitating better team coordination.*

### Mobile Ticket Management

The mobile ticket interface includes several optimizations:

1. **Simplified Layout**: Critical information first, with details accessible via taps.
2. **Action Buttons**: Prominent buttons for common actions like status updates and assignment.
3. **Responsive Forms**: Input fields sized appropriately for mobile entry.
4. **Streamlined Navigation**: Easy access to ticket lists and details.
5. **Quick Filters**: Simplified filtering options optimized for touch.

### Searching and Filtering

#### Desktop Search and Filter

1. Use the **Filter** section on the ticket dashboard.
2. Select status, category, and priority filters as needed.
3. Use the **Search** box for keyword searches in title and description.
4. Search for tickets by assigned technician name.

#### Mobile Search and Filter

1. Use the **Search** box at the top of the mobile ticket dashboard.
2. Tap filter buttons to quickly view tickets relevant to you.
3. Search results update dynamically as you type.

### Archiving Tickets

Archived tickets are removed from the standard views but preserved in the database:

1. **Desktop**: Open the ticket and click the **Archive** button (admin only).
2. **Mobile**: Open the ticket and tap the **Archive** button (admin only).

Archived tickets can be viewed by admins by toggling the **Show Archived** filter.

## User Profile and Settings

### Changing Password

#### Desktop Password Change

1. Click your username in the sidebar.
2. Select **Change Password**.
3. Enter your current password and new password twice.
4. Click **Update Password**.

#### Mobile Password Change

1. Tap the hamburger menu.
2. Tap your username at the top.
3. Tap **Change Password**.
4. Complete the mobile-optimized password form.
5. Tap **Update Password**.

### Updating Timezone

#### Desktop Timezone Change

1. Click your username in the sidebar.
2. Select **Profile**.
3. Select your timezone from the dropdown.
4. Click **Update Profile**.

#### Mobile Timezone Change

1. Tap the hamburger menu.
2. Tap your username.
3. Tap **Change Timezone**.
4. Select your timezone from the optimized dropdown.
5. Tap **Update Timezone**.

*Note: Your timezone setting affects how dates and times are displayed throughout the application.*

### Setting Theme Preference

#### Desktop Theme Toggle

1. Click the **Light/Dark** toggle button in the sidebar.
2. Your preference is automatically saved to your profile.

#### Mobile Theme Toggle

1. Tap the theme toggle icon next to the hamburger menu.
2. Your preference is saved and will persist across sessions.

### Mobile Profile Access

The mobile profile screen provides access to:

1. **Username and Email**: View your account details.
2. **Timezone Settings**: Change your timezone preference.
3. **Password Management**: Update your security credentials.
4. **Theme Preference**: Toggle between light and dark themes.

## Admin Features

*Note: These features are only available to users with administrator privileges.*

### User Management

#### Desktop User Management

1. Navigate to **Admin > Users** in the sidebar.
2. View all users in the system.
3. **Create New Users** with the Add User button.
4. **Edit Users** to update details, reset passwords, or toggle admin status.
5. Assign custom colors to users for calendar display.

#### Mobile User Management

Admin features in mobile use the same responsive design patterns:

1. Tap the hamburger menu.
2. Tap **Admin**.
3. Tap **Users**.
4. View, add, and edit users with mobile-optimized forms.

### Location Management

#### Desktop Location Management

1. Navigate to **Admin > Locations** in the sidebar.
2. View, add, edit, and deactivate locations.
3. See location usage in schedules.

#### Mobile Location Management

1. Access through the Admin section in the mobile menu.
2. Add and edit locations with simplified forms.

### Ticket Categories

#### Desktop Category Management

1. Navigate to **Admin > Ticket Categories**.
2. Create, edit, and manage ticket categories.
3. Set default priority levels for each category.

#### Mobile Category Management

1. Access through the Admin section in the mobile menu.
2. Manage categories with mobile-optimized interface.

### Quick Links

Quick Links provide fast access to external resources:

1. Navigate to **Admin > Quick Links**.
2. Create links with title, URL, icon, and category.
3. Links appear in the sidebar (desktop) or admin section (mobile).

### Email Settings

Configure email notification settings:

1. Navigate to **Admin > Email Settings**.
2. Set admin email group for notifications.
3. Enable/disable notifications for different events.

### Database Backup and Restore

Administrators can backup and restore system data:

1. Navigate to **Admin > Backup & Restore**.
2. **Download Backup** creates a JSON file with all system data.
3. **Restore** from previously downloaded backup file.

## Mobile-Specific Features

### Responsive Navigation

The mobile interface uses a streamlined navigation system:

1. **Hamburger Menu**: Tap to access all main sections.
2. **Theme Toggle**: Quick access next to the menu button.
3. **Section Headers**: Clear indicators of your current location.
4. **Back Buttons**: Easily navigate to previous screens.
5. **Username Display**: Shows your login status at all times.

### Day-by-Day Calendar View

Unlike the desktop's week view, the mobile calendar provides:

1. **Single Day Focus**: View one day at a time for clarity on small screens.
2. **Easy Navigation**: Previous/Next day buttons and Today shortcut.
3. **Schedule List**: Vertically scrollable list of events.
4. **Add Button**: Prominently placed for easy schedule creation.
5. **Time Off Badges**: Clear visual indicators for time off entries.

### Simplified Ticket Interface

The mobile ticket system provides focused interfaces:

1. **Ticket List**: Compact, scrollable list with essential details.
2. **Ticket Detail**: Expandable sections for information, comments, and history.
3. **Quick Actions**: Prominent buttons for common tasks.
4. **Simplified Filters**: Easy touch targets for filtering by assignment.
5. **Search**: Accessible search with keyboard optimization.

### Mobile-Optimized Forms

All forms have been specially designed for mobile use:

1. **Larger Touch Targets**: Buttons and inputs sized for fingers.
2. **Simplified Fields**: Only essential fields shown by default.
3. **Mobile Date/Time Inputs**: Using native mobile date and time pickers.
4. **Responsive Layouts**: Forms adjust to screen orientation and size.
5. **Error Handling**: Clear validation messages optimized for mobile view.

## Troubleshooting

### Common Issues

#### Calendar Not Showing Latest Schedules

1. Refresh the page to update data.
2. Check your timezone settings.
3. Verify that you're not viewing filtered results.

#### Email Notifications Not Received

1. Check your email spam/junk folder.
2. Verify your email address is correct in your profile.
3. Ask an administrator to check email settings.

#### Mobile Display Problems

1. Ensure your device has an updated browser.
2. Try rotating your device to landscape for more screen space.
3. Clear browser cache and reload the application.

### Browser Compatibility

The application works best with:

- Chrome (version 88+)
- Firefox (version 85+)
- Safari (version 14+)
- Edge (version 88+)
- Chrome for Android (version 88+)
- Safari for iOS (version 14+)

### Contact Support

For additional help or to report issues:

1. Submit a ticket within the system.
2. Contact your system administrator.
3. Email support at support@plexengineering.com.

---

© 2025 Plex Engineering. All rights reserved.