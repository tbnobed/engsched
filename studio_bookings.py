"""Read-only aggregation of independently hosted BookStud.io calendars."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta, timezone
from urllib.parse import urlsplit

import requests


def calendar_sources():
    configured = os.environ.get('STUDIO_BOOKING_API_URLS')
    if configured is None:
        configured = os.environ.get('STUDIO_BOOKING_API_URL', 'https://plex.bookstud.io')
    urls = list(dict.fromkeys(url.strip().rstrip('/') for url in configured.split(',') if url.strip()))
    if not urls or len(urls) > 10:
        raise ValueError('Configure between one and ten studio calendars.')
    sources = []
    for url in urls:
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
                parsed.password or parsed.query or parsed.fragment):
            raise ValueError('Studio calendar addresses must be HTTPS base URLs.')
        sources.append({'url': url, 'name': parsed.hostname.split('.')[0].upper()})
    return sources


def parse_time(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Booking time must include a timezone.')
    return parsed.astimezone(timezone.utc)


def fetch_source(source, start, end, user_tz):
    try:
        response = requests.get(
            f"{source['url']}/api/public/bookings",
            params={'start': start.isoformat(), 'end': end.isoformat()},
            timeout=(3, 10))
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            raise ValueError('Expected a booking list.')
        bookings, seen, invalid = [], set(), 0
        for row in rows:
            try:
                if not isinstance(row, dict):
                    raise ValueError('Invalid booking.')
                begins, ends = parse_time(row['start']), parse_time(row['end'])
                if ends <= begins:
                    raise ValueError('Invalid booking interval.')
                if begins >= end or ends <= start:
                    continue
                identity = (str(row.get('id', '')), begins.isoformat(), ends.isoformat(), str(row.get('title', '')))
                if identity in seen:
                    continue
                seen.add(identity)
                bookings.append({
                    **row, 'source_name': source['name'], 'source_url': source['url'],
                    'source_booking_id': f"{source['url']}:{row.get('id', '')}",
                    'start': begins.isoformat(), 'end': ends.isoformat(),
                    'start_local': begins.astimezone(user_tz).strftime('%H:%M'),
                    'end_local': ends.astimezone(user_tz).strftime('%H:%M'),
                })
            except (ValueError, TypeError, KeyError, AttributeError):
                invalid += 1
        return bookings, {**source, 'success': True, 'count': len(bookings), 'invalid_count': invalid}
    except (requests.RequestException, ValueError, TypeError):
        return [], {**source, 'success': False, 'count': 0, 'error': 'Calendar unavailable'}


def get_studio_bookings(user_tz, now=None):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(user_tz).date()
    # Localize each boundary independently so DST transition days remain correct.
    start = user_tz.localize(datetime.combine(today, time.min)).astimezone(timezone.utc)
    end = user_tz.localize(datetime.combine(today + timedelta(days=1), time.min)).astimezone(timezone.utc)
    try:
        sources = calendar_sources()
    except ValueError as error:
        return {'success': False, 'bookings': [], 'sources': [], 'partial': False, 'error': str(error)}
    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        results = list(pool.map(lambda source: fetch_source(source, start, end, user_tz), sources))
    bookings = [booking for rows, _ in results for booking in rows]
    bookings.sort(key=lambda booking: (booking['start'], booking['source_name'], str(booking.get('id', ''))))
    statuses = [status for _, status in results]
    success = any(status['success'] for status in statuses)
    return {
        'success': success, 'bookings': bookings, 'sources': statuses, 'date': today.isoformat(),
        'partial': success and any(not status['success'] or status.get('invalid_count') for status in statuses),
        **({'error': 'All studio calendars are unavailable.'} if not success else {}),
    }
