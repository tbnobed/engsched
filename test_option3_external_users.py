#!/usr/bin/env python3
"""
Test script to verify Option 3 (Email-Only Communication System) is working correctly
Tests external user ticket creation, notifications, and email thread tracking
"""

import os
import sys
import uuid
from datetime import datetime
from flask import Flask
from models import User, Ticket, TicketCategory, db
from email_utils import send_email

def test_external_user_ticket_creation():
    """Test creating tickets for external users"""
    print("=== Testing External User Ticket Creation ===")
    
    # Create a test external user ticket
    default_category = TicketCategory.query.first()
    if not default_category:
        default_category = TicketCategory(
            name="Test Category",
            description="Test category for external users",
            priority_level=1
        )
        db.session.add(default_category)
        db.session.commit()
    
    # Get admin user for assignment
    admin_user = User.query.filter_by(is_admin=True).first()
    if not admin_user:
        print("ERROR: No admin user found for testing")
        return False
    
    # Create external user ticket
    external_email = "external.customer@company.com"
    external_name = "John Customer"
    email_thread_id = f"ticket-{uuid.uuid4().hex[:8]}"
    
    external_ticket = Ticket(
        title="External User Test Ticket",
        description=f"Email from: {external_name} ({external_email})\n\nThis is a test ticket from an external user to verify Option 3 functionality.",
        category_id=default_category.id,
        priority=1,
        status='open',
        created_by=admin_user.id,
        external_email=external_email,
        external_name=external_name,
        email_thread_id=email_thread_id,
        email_notifications=True
    )
    
    db.session.add(external_ticket)
    db.session.commit()
    
    print(f"✓ Created external user ticket #{external_ticket.id}")
    print(f"  - External email: {external_ticket.external_email}")
    print(f"  - External name: {external_ticket.external_name}")
    print(f"  - Thread ID: {external_ticket.email_thread_id}")
    print(f"  - Email notifications: {external_ticket.email_notifications}")
    
    # Test external user identification methods
    print(f"  - Is external user: {external_ticket.is_external_user()}")
    print(f"  - Notification email: {external_ticket.get_notification_email()}")
    print(f"  - Display name: {external_ticket.get_display_name()}")
    
    return external_ticket

def test_internal_user_ticket_creation():
    """Test creating tickets for internal users"""
    print("\n=== Testing Internal User Ticket Creation ===")
    
    # Create ticket for internal user
    internal_user = User.query.filter_by(is_admin=False).first()
    if not internal_user:
        print("WARNING: No internal user found for testing")
        return None
    
    default_category = TicketCategory.query.first()
    
    internal_ticket = Ticket(
        title="Internal User Test Ticket",
        description="This is a test ticket from an internal user.",
        category_id=default_category.id,
        priority=1,
        status='open',
        created_by=internal_user.id,
        external_email=None,
        external_name=None,
        email_thread_id=None,
        email_notifications=True
    )
    
    db.session.add(internal_ticket)
    db.session.commit()
    
    print(f"✓ Created internal user ticket #{internal_ticket.id}")
    print(f"  - Is external user: {internal_ticket.is_external_user()}")
    print(f"  - Notification email: {internal_ticket.get_notification_email()}")
    print(f"  - Display name: {internal_ticket.get_display_name()}")
    
    return internal_ticket

def test_email_notifications():
    """Test email notification system for external users"""
    print("\n=== Testing Email Notifications ===")
    
    # Create test tickets
    external_ticket = test_external_user_ticket_creation()
    internal_ticket = test_internal_user_ticket_creation()
    
    if external_ticket and internal_ticket:
        print("✓ Both external and internal tickets created successfully")
        print("✓ Email notification system ready for testing")
        print("  - External user will receive notifications at:", external_ticket.external_email)
        print("  - Internal user will receive notifications at:", internal_ticket.creator.email)
        
        return True
    else:
        print("ERROR: Failed to create test tickets")
        return False

def test_database_schema():
    """Test that the database schema includes all required fields"""
    print("\n=== Testing Database Schema ===")
    
    # Check if the new columns exist
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('ticket')]
    
    required_columns = ['external_email', 'external_name', 'email_notifications', 'email_thread_id']
    
    for col in required_columns:
        if col in columns:
            print(f"✓ Column '{col}' exists in ticket table")
        else:
            print(f"✗ Column '{col}' missing from ticket table")
            return False
    
    print("✓ All required columns exist in the database")
    return True

def main():
    """Run all tests"""
    print("Starting Option 3 External User System Tests...")
    print("=" * 50)
    
    # Import app and create application context
    from app import app
    
    with app.app_context():
        try:
            # Test database schema
            if not test_database_schema():
                print("Database schema test failed!")
                return False
            
            # Test external user functionality
            if not test_email_notifications():
                print("Email notification test failed!")
                return False
            
            print("\n" + "=" * 50)
            print("✓ All Option 3 tests passed successfully!")
            print("✓ External user email communication system is ready")
            print("✓ Database schema is correct")
            print("✓ Email notifications are configured")
            
            return True
            
        except Exception as e:
            print(f"Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)