import requests
import re
import time

# Base URL
base_url = "http://localhost:5000"

# Create a session to maintain cookies
session = requests.Session()

# 1. Visit login page to get CSRF token
login_page = session.get(f"{base_url}/login")
csrf_token = None

# Extract CSRF token
match = re.search(r'<input[^>]*name="csrf_token"[^>]*value="([^"]*)"', login_page.text)
if match:
    csrf_token = match.group(1)
    print(f"Got CSRF token: {csrf_token}")
else:
    print("Failed to get CSRF token")
    exit(1)

# 2. Login with admin credentials
login_data = {
    "email": "admin@techscheduler.com",
    "password": "admin",  # Updated password
    "csrf_token": csrf_token,
    "remember_me": "on"
}

login_response = session.post(f"{base_url}/login", data=login_data)
print(f"Login response status: {login_response.status_code}")

if login_response.status_code != 200 and login_response.status_code != 302:
    print("Login failed")
    exit(1)

# 3. Give the server a moment to process the login
time.sleep(1)

# 4. Access calendar page (should go to mobile version due to our override)
calendar_page = session.get(f"{base_url}/calendar")
print(f"Calendar page status: {calendar_page.status_code}")

# Check if mobile template is being served
if "mobile-calendar" in calendar_page.text:
    print("SUCCESS: Mobile calendar template is being served")
    
    # Check position in the template
    html_parts = calendar_page.text.split("mobile-calendar")
    if len(html_parts) > 1:
        # Look for content before the mobile-calendar div
        before_calendar = html_parts[0][-500:]  # Get the last 500 chars before mobile-calendar
        print(f"Content before mobile-calendar div: \n{before_calendar}")
else:
    print("FAILURE: Mobile calendar template is NOT being served")
    
# 5. Access personal schedule page
personal_page = session.get(f"{base_url}/personal_schedule")
print(f"Personal schedule page status: {personal_page.status_code}")

# Check if mobile template is being served
if "mobile-calendar" in personal_page.text:
    print("SUCCESS: Mobile personal schedule template is being served")
    
    # Check position in the template
    html_parts = personal_page.text.split("mobile-calendar")
    if len(html_parts) > 1:
        # Look for content before the mobile-calendar div
        before_calendar = html_parts[0][-500:]  # Get the last 500 chars before mobile-calendar
        print(f"Content before mobile-calendar div: \n{before_calendar}")
else:
    print("FAILURE: Mobile personal schedule template is NOT being served")