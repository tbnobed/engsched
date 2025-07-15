# Docker Timezone Troubleshooting Guide

## Issue Summary

All-day OOO (Out of Office) entries were displaying on incorrect calendar dates when viewed across different timezones. The root cause was identified as user timezone setting differences between when entries were created vs when they were viewed.

## Root Cause Analysis

### The Problem
- User account was set to `America/Chicago` timezone when OOO entries were originally created
- OOO entries were stored as Chicago→UTC conversions in the database
- When user timezone was later changed to `America/Los_Angeles`, the same UTC times displayed on different calendar dates
- This created the appearance of a "Docker vs Replit" environment issue, but was actually a user timezone configuration issue

### Technical Details
- **Chicago Time Creation**: `2025-07-26 00:00 CST` → `2025-07-26 06:00 UTC` (stored in database)
- **Pacific Time Display**: `2025-07-26 06:00 UTC` → `2025-07-25 23:00 PST` (displays on July 25th calendar)
- **Expected**: OOO entry should appear on July 26th regardless of viewing timezone

## Solution Implemented

### 1. Smart Timezone Detection
Added logic to detect whether existing OOO entries were created in Chicago timezone vs current user timezone:

```python
# Check if UTC time matches Chicago midnight conversion pattern
chicago_midnight = chicago_tz.localize(datetime.combine(chicago_display.date(), time(0, 0)))
if utc_time == chicago_midnight.astimezone(pytz.UTC):
    intended_date = chicago_display.date()  # Use Chicago date
else:
    intended_date = utc_time.astimezone(user_tz).date()  # Use current timezone date
```

### 2. Preserved Correct Storage Logic
- All-day OOO entries continue to be stored as user's local timezone converted to UTC
- This ensures new entries created with Pacific timezone display correctly
- Maintains backward compatibility with existing Chicago-created entries

### 3. Enhanced Display Logic
- Calendar, dashboard, and personal schedule views now use smart detection
- Existing Chicago-created entries display on correct calendar dates
- New Pacific-created entries display correctly without date shifting

## Environment Analysis Tools

### Comprehensive Debug Script
Created `docker_timezone_debug_comprehensive.py` to help diagnose timezone issues:

```bash
python3 docker_timezone_debug_comprehensive.py
```

This script tests:
- Environment detection (Docker vs Replit)
- System timezone configuration
- Python timezone library versions
- OOO conversion test cases
- Database entry analysis
- DST transition handling

### Key Test Results
- **OLD METHOD (current system)**: ✅ Works correctly
  - Pacific 00:00 → UTC: `2025-07-19 07:00:00+00:00`
  - Display back: `2025-07-19 00:00:00-07:00` (correct date)

- **NEW METHOD (timezone-neutral)**: ❌ Breaks display
  - UTC storage: `2025-07-19 00:00:00+00:00`
  - Display back: `2025-07-18 17:00:00-07:00` (wrong date)

## Docker Configuration

### Current Working Configuration
The Docker setup includes proper timezone configuration:

```dockerfile
# Install timezone data
RUN apt-get update && apt-get install -y tzdata

# Set system timezone
ENV DEBIAN_FRONTEND=noninteractive
RUN echo "America/Los_Angeles" > /etc/timezone && \
    ln -sf /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Set environment variable
ENV TZ=America/Los_Angeles
```

```yaml
# docker-compose.yml
environment:
  - TZ=America/Los_Angeles
```

## Resolution Verification

### Before Fix
- Existing OOO entries displayed on wrong calendar dates (July 25th instead of July 26th)
- User reported working correctly in Replit but not in Docker server

### After Fix
- User confirmed: "Ok, that fixed it!!"
- All-day OOO entries now display on correct calendar dates
- Smart detection handles mixed timezone scenarios automatically
- No environment-specific differences between Replit and Docker servers

## Key Learnings

1. **User timezone settings matter**: The timezone stored in user accounts affects how OOO entries are created and stored
2. **Environment differences were misleading**: The real issue was user configuration, not Docker vs Replit differences
3. **Backward compatibility is crucial**: Solutions must handle existing data created under different timezone settings
4. **Comprehensive testing reveals root causes**: The debug script showed that timezone conversion logic was working correctly - the issue was in the data creation context

## Prevention

- Document user timezone changes that may affect existing OOO entries
- Consider migration scripts when users change timezones significantly
- Use comprehensive debug tools to isolate real issues from environmental confusion
- Test timezone-sensitive features across different user timezone configurations

## Files Modified

- `routes.py`: Enhanced display logic with smart timezone detection
- `docker_timezone_debug_comprehensive.py`: Created comprehensive debugging tool
- `DOCKER_TIMEZONE_TROUBLESHOOTING.md`: This documentation
- `replit.md`: Updated with resolution details

## Status: ✅ RESOLVED
All-day OOO timezone display issue completely resolved. System now correctly handles mixed timezone scenarios while maintaining proper calendar date display across all views.