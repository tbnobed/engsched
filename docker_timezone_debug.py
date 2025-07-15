#!/usr/bin/env python3
"""
Docker Timezone Debugging Script
Run this inside your Docker container to diagnose timezone issues
"""

import os
import sys
import datetime
import pytz
from zoneinfo import ZoneInfo
import time

def debug_timezone_environment():
    """Debug timezone configuration in Docker environment"""
    print("=" * 60)
    print("DOCKER TIMEZONE DEBUGGING REPORT")
    print("=" * 60)
    
    # 1. Environment Variables
    print("\n1. ENVIRONMENT VARIABLES:")
    print(f"   TZ: {os.environ.get('TZ', 'NOT SET')}")
    print(f"   PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")
    
    # 2. System Time
    print("\n2. SYSTEM TIME:")
    print(f"   Current UTC time: {datetime.datetime.now(datetime.timezone.utc)}")
    print(f"   Current local time: {datetime.datetime.now()}")
    print(f"   System timezone: {time.tzname}")
    
    # 3. Python datetime
    print("\n3. PYTHON DATETIME:")
    print(f"   datetime.now(): {datetime.datetime.now()}")
    print(f"   datetime.now(tz=UTC): {datetime.datetime.now(datetime.timezone.utc)}")
    
    # 4. pytz timezone
    print("\n4. PYTZ TIMEZONE:")
    try:
        la_tz = pytz.timezone('America/Los_Angeles')
        print(f"   LA timezone: {la_tz}")
        print(f"   Current time in LA: {datetime.datetime.now(la_tz)}")
        
        # Test date conversion (the problematic case)
        test_date = datetime.date(2025, 7, 19)  # July 19, 2025
        test_start = datetime.datetime.combine(test_date, datetime.time(0, 0))
        test_end = datetime.datetime.combine(test_date, datetime.time(23, 0))
        
        print(f"\n   TEST CASE - July 19, 2025 OOO:")
        print(f"   Local start time: {test_start}")
        print(f"   Local end time: {test_end}")
        
        # Localize to LA timezone
        la_start = la_tz.localize(test_start)
        la_end = la_tz.localize(test_end)
        print(f"   LA start time: {la_start}")
        print(f"   LA end time: {la_end}")
        
        # Convert to UTC
        utc_start = la_start.astimezone(pytz.UTC)
        utc_end = la_end.astimezone(pytz.UTC)
        print(f"   UTC start time: {utc_start}")
        print(f"   UTC end time: {utc_end}")
        
        # Convert back to display
        display_start = utc_start.astimezone(la_tz)
        display_end = utc_end.astimezone(la_tz)
        print(f"   Display start: {display_start}")
        print(f"   Display end: {display_end}")
        print(f"   Display date: {display_start.date()}")
        
        if display_start.date() != test_date:
            print(f"   ❌ ISSUE DETECTED: Expected {test_date}, got {display_start.date()}")
        else:
            print(f"   ✅ Timezone conversion working correctly")
            
    except Exception as e:
        print(f"   Error with pytz: {e}")
    
    # 5. zoneinfo (Python 3.9+)
    print("\n5. ZONEINFO:")
    try:
        if sys.version_info >= (3, 9):
            from zoneinfo import ZoneInfo
            la_zi = ZoneInfo('America/Los_Angeles')
            print(f"   ZoneInfo LA: {la_zi}")
            print(f"   Current time with ZoneInfo: {datetime.datetime.now(la_zi)}")
        else:
            print("   zoneinfo not available (Python < 3.9)")
    except Exception as e:
        print(f"   Error with zoneinfo: {e}")
    
    # 6. File system checks
    print("\n6. TIMEZONE FILES:")
    tz_files = ['/etc/timezone', '/etc/localtime', '/usr/share/zoneinfo/America/Los_Angeles']
    for file_path in tz_files:
        if os.path.exists(file_path):
            try:
                if file_path == '/etc/timezone':
                    with open(file_path, 'r') as f:
                        content = f.read().strip()
                    print(f"   {file_path}: {content}")
                elif file_path == '/etc/localtime':
                    # Check if it's a symlink
                    if os.path.islink(file_path):
                        target = os.readlink(file_path)
                        print(f"   {file_path} -> {target}")
                    else:
                        print(f"   {file_path}: exists (not a symlink)")
                else:
                    print(f"   {file_path}: exists")
            except Exception as e:
                print(f"   {file_path}: error reading - {e}")
        else:
            print(f"   {file_path}: does not exist")
    
    print("\n" + "=" * 60)
    print("END TIMEZONE DEBUG REPORT")
    print("=" * 60)

if __name__ == "__main__":
    debug_timezone_environment()