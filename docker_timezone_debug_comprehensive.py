#!/usr/bin/env python3
"""
Comprehensive Docker Timezone Debugging Script for OOO Date Shifting Issue
Run this inside your Docker container to diagnose timezone differences between environments
"""

import os
import sys
import pytz
from datetime import datetime, time, date
import json

def comprehensive_timezone_debug():
    """Comprehensive timezone debugging for Docker vs Replit differences"""
    
    print("=" * 60)
    print("COMPREHENSIVE DOCKER TIMEZONE DEBUG")
    print("=" * 60)
    
    # 1. Environment Detection
    print("\n1. ENVIRONMENT DETECTION:")
    print(f"   Python version: {sys.version}")
    print(f"   Current working directory: {os.getcwd()}")
    print(f"   Is Docker: {os.path.exists('/.dockerenv')}")
    print(f"   Is Replit: {bool(os.environ.get('REPL_ID'))}")
    
    # 2. System Timezone Configuration
    print("\n2. SYSTEM TIMEZONE CONFIGURATION:")
    print(f"   TZ environment variable: {os.environ.get('TZ', 'Not set')}")
    
    # Check system timezone files
    timezone_files = [
        '/etc/timezone',
        '/etc/localtime'
    ]
    
    for file_path in timezone_files:
        if os.path.exists(file_path):
            try:
                if file_path == '/etc/timezone':
                    with open(file_path, 'r') as f:
                        content = f.read().strip()
                    print(f"   {file_path}: {content}")
                else:
                    # For /etc/localtime, show what it links to
                    if os.path.islink(file_path):
                        link_target = os.readlink(file_path)
                        print(f"   {file_path} -> {link_target}")
                    else:
                        print(f"   {file_path}: exists (not a symlink)")
            except Exception as e:
                print(f"   {file_path}: Error reading - {e}")
        else:
            print(f"   {file_path}: Not found")
    
    # 3. Python Timezone Libraries
    print("\n3. PYTHON TIMEZONE LIBRARIES:")
    try:
        import pytz
        print(f"   pytz version: {pytz.__version__}")
        
        # Test Pacific timezone
        pacific_tz = pytz.timezone('America/Los_Angeles')
        print(f"   Pacific timezone object: {pacific_tz}")
        
        # Test current time in Pacific
        now_pacific = datetime.now(pacific_tz)
        print(f"   Current time in Pacific: {now_pacific}")
        print(f"   DST active: {now_pacific.dst() != datetime.min.replace(tzinfo=pacific_tz).dst()}")
        
    except ImportError as e:
        print(f"   pytz error: {e}")
    
    try:
        from zoneinfo import ZoneInfo
        print(f"   zoneinfo: Available")
        zi_pacific = ZoneInfo('America/Los_Angeles')
        now_zi = datetime.now(zi_pacific)
        print(f"   Current time with zoneinfo: {now_zi}")
    except ImportError:
        print(f"   zoneinfo: Not available (Python < 3.9)")
    except Exception as e:
        print(f"   zoneinfo error: {e}")
    
    # 4. Critical OOO Test Cases
    print("\n4. OOO ALL-DAY TIMEZONE CONVERSION TEST:")
    
    test_cases = [
        ("2025-07-19", "Summer (DST active)"),
        ("2025-01-19", "Winter (Standard time)"),
        ("2025-03-09", "DST transition day (Spring forward)"),
        ("2025-11-02", "DST transition day (Fall back)")
    ]
    
    pacific_tz = pytz.timezone('America/Los_Angeles')
    
    for date_str, description in test_cases:
        print(f"\n   Testing {date_str} ({description}):")
        test_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        try:
            # Old method (what was causing issues)
            old_start = pacific_tz.localize(datetime.combine(test_date, time(0, 0)))
            old_utc = old_start.astimezone(pytz.UTC)
            old_display = old_utc.astimezone(pacific_tz)
            
            print(f"     OLD METHOD:")
            print(f"       Pacific 00:00: {old_start}")
            print(f"       UTC storage: {old_utc}")
            print(f"       Display back: {old_display}")
            print(f"       Display date: {old_display.date()}")
            print(f"       Date match: {old_display.date() == test_date}")
            
            # New method (timezone-neutral)
            new_utc = pytz.UTC.localize(datetime.combine(test_date, time(0, 0)))
            new_display = new_utc.astimezone(pacific_tz)
            
            print(f"     NEW METHOD (timezone-neutral):")
            print(f"       UTC storage: {new_utc}")
            print(f"       Display back: {new_display}")
            print(f"       Display date: {new_display.date()}")
            print(f"       Date match: {new_display.date() == test_date}")
            
            # Check if there's a discrepancy
            if old_display.date() != test_date:
                print(f"       ❌ OLD METHOD ISSUE: Expected {test_date}, got {old_display.date()}")
            else:
                print(f"       ✅ Old method working correctly")
                
            if new_display.date() != test_date:
                print(f"       ❌ NEW METHOD ISSUE: Shows {new_display.date()} instead of {test_date}")
            else:
                print(f"       ✅ New method shows correct date")
                
        except Exception as e:
            print(f"       ❌ ERROR: {e}")
    
    # 5. Database Connection Test (if available)
    print("\n5. DATABASE CONNECTION TEST:")
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            print(f"   Database URL configured: {database_url[:50]}...")
            
            # Try to connect and check existing OOO entries
            try:
                import psycopg2
                from urllib.parse import urlparse
                
                result = urlparse(database_url)
                conn = psycopg2.connect(
                    database=result.path[1:],
                    user=result.username,
                    password=result.password,
                    host=result.hostname,
                    port=result.port
                )
                
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, start_time, end_time, all_day, time_off 
                    FROM schedule 
                    WHERE technician_id = 9 AND all_day = true AND time_off = true 
                    ORDER BY start_time DESC LIMIT 3
                """)
                
                rows = cursor.fetchall()
                print(f"   Found {len(rows)} all-day OOO entries:")
                
                for row in rows:
                    schedule_id, start_time, end_time, all_day, time_off = row
                    print(f"     Schedule {schedule_id}:")
                    print(f"       UTC times: {start_time} to {end_time}")
                    
                    # Test display in Pacific
                    if start_time.tzinfo is None:
                        start_utc = pytz.UTC.localize(start_time)
                    else:
                        start_utc = start_time.astimezone(pytz.UTC)
                        
                    display_pacific = start_utc.astimezone(pacific_tz)
                    print(f"       Pacific display: {display_pacific}")
                    print(f"       Display date: {display_pacific.date()}")
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                print(f"   Database query error: {e}")
                
        else:
            print("   No DATABASE_URL configured")
            
    except Exception as e:
        print(f"   Database test error: {e}")
    
    # 6. Environment Summary
    print("\n6. ENVIRONMENT SUMMARY:")
    summary = {
        "python_version": sys.version.split()[0],
        "pytz_version": getattr(pytz, '__version__', 'unknown'),
        "system_tz": os.environ.get('TZ', 'Not set'),
        "docker_container": os.path.exists('/.dockerenv'),
        "replit_environment": bool(os.environ.get('REPL_ID'))
    }
    
    print(json.dumps(summary, indent=2))
    
    print("\n" + "=" * 60)
    print("DEBUG COMPLETE - Compare output between Replit and your Docker server")
    print("=" * 60)

if __name__ == "__main__":
    comprehensive_timezone_debug()