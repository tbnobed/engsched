# Production calendar sources

Both dashboards combine the public booking feeds configured in this comma-separated
environment variable:

```text
STUDIO_BOOKING_API_URLS=https://plex.bookstud.io,https://nash.bookstud.io,https://tust.bookstud.io
```

This setting takes precedence over the legacy `STUDIO_BOOKING_API_URL`, which
continues to work for a single source (or a comma-separated list). Configure the
new variable on separately hosted installations too; Replit environment settings
do not configure external hosting.

The application only reads `/api/public/bookings`. It does not create or modify
production bookings. Sources are fetched concurrently, labeled by hostname,
and combined chronologically in the viewer's timezone. Overlapping overnight
bookings are included. Identical booking IDs from different calendars remain
separate. Failed sources and malformed records produce visible incomplete-data
warnings rather than falsely reporting zero bookings.
