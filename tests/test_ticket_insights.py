"""Reporting regressions, using only synthetic fixtures (no database writes)."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

import pytz

from ticket_insights_service import (
    build_insights, completion_events, default_layout, is_ai_comment,
    is_staff_reply, percentile, validate_layout,
)

UTC = timezone.utc
NOW = datetime(2026, 10, 10, 19, tzinfo=UTC)


def ticket(**overrides):
    values = dict(id=1, title='Synthetic test ticket', created_at=NOW - timedelta(days=10),
                  status='open', priority=2, assigned_to=2, created_by=1, external_email=None,
                  archived=False, due_date=NOW - timedelta(days=1), category_id=1)
    values.update(overrides)
    return NS(**values)


def comment(content='Human reply', user_id=2, **overrides):
    values = dict(ticket_id=1, content=content, user_id=user_id,
                  user=NS(username='Technician', email='technician@example.invalid'),
                  created_at=NOW - timedelta(days=9))
    values.update(overrides)
    return NS(**values)


def event(old='open', new='resolved', **overrides):
    values = dict(ticket_id=1, action='status_changed', details=f'Status changed from {old} to {new}',
                  created_at=NOW - timedelta(days=2))
    values.update(overrides)
    return NS(**values)


class TicketInsightsTests(unittest.TestCase):
    def build(self, tickets=None, comments=None, histories=None, **overrides):
        filters = dict(start=NOW.date() - timedelta(days=29), end=NOW.date(), source='all', stalled_days=7)
        filters.update(overrides)
        return build_insights(tickets or [ticket()], comments or [], histories or [],
                              {2: NS(username='Technician')}, {1: 'Software'}, set(),
                              filters, 2, pytz.timezone('America/Los_Angeles'), NOW)

    def test_legacy_ai_attributed_to_human_is_not_a_response(self):
        ai = comment('<p><strong>🤖 AI Analysis:</strong></p><p>Summary: Test</p><p>Possible Causes: Test</p>')
        result = self.build(comments=[ai])
        self.assertIsNone(result['metrics']['first_response'])
        self.assertEqual(result['coverage']['excluded_ai_comments'], 1)
        self.assertEqual(result['metrics']['stalled'], 1)

    def test_ordinary_ai_discussion_is_not_filtered(self):
        self.assertFalse(is_ai_comment('I checked the AI Analysis and fixed the cable.'))
        result = self.build(comments=[comment()])
        self.assertEqual(result['metrics']['first_response'], 24)
        self.assertEqual(result['reports']['first_response']['p90_hours'], 24)

    def test_requester_reply_does_not_count(self):
        self.assertIsNone(self.build(comments=[comment(user_id=1)])['metrics']['first_response'])

    def test_external_proxy_author_is_not_technician(self):
        item = ticket(external_email='requester@example.invalid')
        inbound = comment('Email reply from: Requester (requester@example.invalid)\nThanks')
        self.assertFalse(is_staff_reply(inbound, item))
        self.assertTrue(is_staff_reply(comment(), item))
        technician_email = comment('Email reply from: Technician (technician@example.invalid)\nFixed')
        self.assertTrue(is_staff_reply(technician_email, item))

    def test_completion_requires_recorded_transition(self):
        result = self.build(tickets=[ticket(status='resolved')])
        self.assertEqual(result['coverage']['missing_resolution_history'], 1)
        self.assertEqual(result['metrics']['resolved'], 0)
        self.assertIsNone(result['metrics']['resolution_time'])

    def test_close_after_resolution_is_not_double_counted(self):
        result = self.build(histories=[event(), event('resolved', 'closed')])
        self.assertEqual(result['metrics']['resolved'], 1)
        self.assertEqual(result['metrics']['resolution_time'], 192)
        self.assertEqual(sum(day['resolved'] for day in result['charts']['volume']), 1)

    def test_reopen_uses_latest_completion_once(self):
        history = [event(created_at=NOW - timedelta(days=5)),
                   event('resolved', 'open', created_at=NOW - timedelta(days=4)),
                   event('open', 'resolved', created_at=NOW - timedelta(days=1))]
        result = self.build(histories=history)
        self.assertEqual(result['metrics']['resolution_time'], 216)
        self.assertEqual(result['metrics']['resolved'], 1)

    def test_snapshot_ignores_creation_range(self):
        result = self.build(start=NOW.date(), end=NOW.date())
        self.assertEqual(result['metrics']['created'], 0)
        self.assertEqual(result['metrics']['my_open'], 1)
        self.assertEqual(len(result['reports']['aging']['rows']), 1)

    def test_archived_tickets_are_not_backlog(self):
        result = self.build(tickets=[ticket(archived=True)])
        self.assertEqual(result['metrics']['my_open'], 0)
        self.assertEqual(result['metrics']['created'], 1)

    def test_internal_note_resets_stalled_not_response(self):
        result = self.build(histories=[event(action='internal_note', details='Investigating', created_at=NOW)])
        self.assertEqual(result['metrics']['stalled'], 0)
        self.assertIsNone(result['metrics']['first_response'])

    def test_views_dont_reset_stalled(self):
        result = self.build(histories=[event(action='viewed', details='Viewed', created_at=NOW)])
        self.assertEqual(result['metrics']['stalled'], 1)

    def test_pending_duration_requires_transition(self):
        result = self.build(tickets=[ticket(status='pending')], histories=[event(new='pending')])
        self.assertEqual(result['reports']['stalled']['rows'][0]['pending_days'], 2)
        missing = self.build(tickets=[ticket(status='pending')])
        self.assertIsNone(missing['reports']['stalled']['rows'][0]['pending_days'])

    def test_timezone_boundary(self):
        # UTC October 10 06:30 is October 9 in Los Angeles.
        item = ticket(created_at=datetime(2026, 10, 10, 6, 30, tzinfo=UTC))
        result = self.build(tickets=[item], start=NOW.date(), end=NOW.date())
        self.assertEqual(result['metrics']['created'], 0)
        self.assertEqual(result['tickets'][0]['created_display'], '2026-10-09 23:30')

    def test_source_filter(self):
        result = self.build(source='email')
        self.assertEqual(result['tickets'], [])
        self.assertIsNone(result['metrics']['resolution_time'])

    def test_layout_roundtrip_and_empty(self):
        self.assertEqual(validate_layout(default_layout()), default_layout())
        self.assertEqual(validate_layout({'version': 1, 'preset': 'my', 'widgets': []})['widgets'], [])

    def test_layout_remembers_filters(self):
        layout = default_layout('my')
        layout['filters'] = {'priority': '2', 'technician': '17', 'start': '2026-10-01'}
        self.assertEqual(validate_layout(layout), layout)
        layout['filters'] = {}
        self.assertEqual(validate_layout(layout)['filters'], {})
        for invalid in ([], {'unknown': 'x'}, {'priority': 2}, {'source': 'x' * 201}):
            layout['filters'] = invalid
            with self.assertRaises(ValueError):
                validate_layout(layout)

    def test_layout_rejects_malformed_ids_types_and_sizes(self):
        for field, value in [('id', '<script>'), ('type', 'unknown'), ('size', 'huge'), ('limit', True)]:
            layout = default_layout()
            layout['widgets'][0][field] = value
            with self.assertRaises(ValueError):
                validate_layout(layout)
        layout = default_layout()
        layout['widgets'].append(layout['widgets'][0])
        with self.assertRaises(ValueError):
            validate_layout(layout)

    def test_percentile(self):
        self.assertIsNone(percentile([], .9))
        self.assertEqual(percentile([0, 10, 20, 30, 40], .9), 36)


if __name__ == '__main__':
    unittest.main()
