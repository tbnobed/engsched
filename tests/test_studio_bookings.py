import os
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytz
import requests
from studio_bookings import calendar_sources, get_studio_bookings


URLS = 'https://plex.bookstud.io,https://nash.bookstud.io,https://tust.bookstud.io'
NOW = datetime(2026, 10, 11, 19, tzinfo=timezone.utc)
TZ = pytz.timezone('America/Los_Angeles')


def booking(identifier=1, start='2026-10-11T12:00:00Z', end='2026-10-11T14:00:00Z'):
    return dict(id=identifier, title='Synthetic booking', start=start, end=end)


class StudioBookingsTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'STUDIO_BOOKING_API_URLS': URLS})
        env.start()
        self.addCleanup(env.stop)

    def fetch(self, payloads, now=NOW):
        def response(url, **kwargs):
            value = payloads[url.split('/')[2].split('.')[0]]
            if isinstance(value, Exception):
                raise value
            return Mock(raise_for_status=Mock(), json=Mock(return_value=value))
        with patch('studio_bookings.requests.get', side_effect=response) as get:
            return get_studio_bookings(TZ, now), get

    def test_combines_sources_without_losing_colliding_ids(self):
        result, _ = self.fetch(dict(plex=[booking()], nash=[booking()], tust=[booking()]))
        self.assertEqual(len(result['bookings']), 3)
        self.assertEqual(len({row['source_booking_id'] for row in result['bookings']}), 3)
        self.assertFalse(result['partial'])

    def test_partial_and_total_failure(self):
        failure = requests.Timeout()
        result, _ = self.fetch(dict(plex=[booking()], nash=failure, tust=[]))
        self.assertTrue(result['success'])
        self.assertTrue(result['partial'])
        self.assertEqual(len(result['bookings']), 1)
        result, _ = self.fetch(dict(plex=failure, nash=failure, tust=failure))
        self.assertFalse(result['success'])

    def test_overnight_overlap_and_day_boundaries(self):
        spanning = booking(1, '2026-10-10T06:00:00Z', '2026-10-13T06:00:00Z')
        ends_at_midnight = booking(2, '2026-10-10T06:00:00Z', '2026-10-11T07:00:00Z')
        starts_next_day = booking(3, '2026-10-12T07:00:00Z', '2026-10-12T08:00:00Z')
        result, _ = self.fetch(dict(plex=[spanning, ends_at_midnight, starts_next_day], nash=[], tust=[]))
        self.assertEqual([row['id'] for row in result['bookings']], [1])

    def test_bad_records_and_duplicates(self):
        result, _ = self.fetch(dict(plex=[booking(), booking(), {'start': 'bad'}], nash=[], tust=[]))
        self.assertEqual(len(result['bookings']), 1)
        self.assertTrue(result['partial'])
        self.assertEqual(result['sources'][0]['invalid_count'], 1)

    def test_bad_response_and_empty_calendars(self):
        result, _ = self.fetch(dict(plex={'error': 'wrong shape'}, nash=[], tust=[]))
        self.assertTrue(result['partial'])
        result, _ = self.fetch(dict(plex=[], nash=[], tust=[]))
        self.assertTrue(result['success'])
        self.assertFalse(result['partial'])
        self.assertEqual(result['bookings'], [])

    def test_dst_boundaries(self):
        _, get = self.fetch(dict(plex=[], nash=[], tust=[]), datetime(2026, 11, 1, 20, tzinfo=timezone.utc))
        params = get.call_args.kwargs['params']
        span = datetime.fromisoformat(params['end']) - datetime.fromisoformat(params['start'])
        self.assertEqual(span.total_seconds() / 3600, 25)

    def test_configuration_and_legacy_compatibility(self):
        with patch.dict(os.environ, {'STUDIO_BOOKING_API_URLS': URLS + ',https://plex.bookstud.io/'}):
            self.assertEqual(len(calendar_sources()), 3)
        with patch.dict(os.environ, {'STUDIO_BOOKING_API_URL': 'https://nash.bookstud.io'}, clear=True):
            self.assertEqual(calendar_sources()[0]['name'], 'NASH')
        with patch.dict(os.environ, {'STUDIO_BOOKING_API_URLS': 'http://invalid.example'}):
            self.assertFalse(get_studio_bookings(TZ, NOW)['success'])


if __name__ == '__main__':
    unittest.main()
