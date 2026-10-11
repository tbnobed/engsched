import unittest
from datetime import timedelta
from types import SimpleNamespace as NS

import pytz

from tests.test_ticket_insights import NOW, ticket, comment, event
from ticket_insights_service import build_insights, requester_key
from ticket_insights_extended import extend_insights


class RemainingReportTests(unittest.TestCase):
    def build(self, tickets=None, comments=None, histories=None, targets=None,
              profiles=None, surveys=None, messages=None, ratings=None):
        tickets = tickets or [ticket(external_name=None)]
        for item in tickets:
            if not hasattr(item, 'external_name'):
                item.external_name = None
        histories = histories or []
        for index, history in enumerate(histories):
            history.id = index + 1
        users = {1: NS(username='Requester', email='requester@example.invalid'),
                 2: NS(username='Technician', email='technician@example.invalid')}
        filters = dict(start=NOW.date() - timedelta(days=29), end=NOW.date(),
                       source='all', stalled_days=7)
        tz = pytz.timezone('America/Los_Angeles')
        base = build_insights(tickets, comments or [], histories, users, {1: 'Software'},
                              set(), filters, 2, tz, NOW)
        return extend_insights(base, tickets, histories, users, filters, tz, 2,
                               targets or [], profiles or {}, surveys or [],
                               messages or [], ratings or [], NOW)

    def test_all_thirteen_reports(self):
        self.assertEqual(len(self.build()['reports']), 13)

    def test_unconfigured_targets_are_not_successes(self):
        report = self.build()['reports']['targets']
        self.assertEqual(report['rows'][0]['response_state'], 'Not configured')
        self.assertEqual(report['summary'][0]['value'], 0)

    def test_calendar_targets_and_at_risk(self):
        targets = [{'priority': 2, 'response_hours': 48, 'resolution_hours': 300}]
        row = self.build(comments=[comment()], targets=targets)['reports']['targets']['rows'][0]
        self.assertEqual(row['response_state'], 'Met')
        self.assertEqual(row['resolution_state'], 'At risk')
        self.assertEqual(row['response_hours'], 24)

    def test_missing_completion_is_not_inferred(self):
        result = self.build(tickets=[ticket(status='closed')], targets=[
            {'priority': 2, 'response_hours': 24, 'resolution_hours': 48}])
        row = result['reports']['targets']['rows'][0]
        self.assertEqual(row['resolution_state'], 'Not tracked')
        self.assertIsNone(row['resolution_hours'])

    def test_profiles_use_exact_identity_not_domain(self):
        profile = NS(department='Broadcast', location='Studio')
        data = self.build(profiles={'user:1': profile})
        self.assertEqual(data['reports']['requesters']['rows'][0]['department'], 'Broadcast')
        self.assertEqual(data['tickets'][0]['requester_key'], 'user:1')
        self.assertEqual(requester_key(ticket(external_email=' PERSON@Example.Invalid ')), 'email:person@example.invalid')

    def test_reopens_and_cohort_rate(self):
        data = self.build(histories=[
            event(created_at=NOW - timedelta(days=5)),
            event('resolved', 'open', created_at=NOW - timedelta(days=4)),
            event('open', 'resolved', created_at=NOW - timedelta(days=3)),
            event('resolved', 'pending', created_at=NOW - timedelta(days=2)),
        ])
        report = data['reports']['reopened']
        self.assertEqual(report['rows'][0]['reopens'], 2)
        self.assertEqual(report['summary'][2]['value'], '100.0%')

    def test_missing_handoff_history_has_no_fabricated_duration(self):
        row = self.build()['reports']['handoffs']['rows'][0]
        self.assertIsNone(row['hours'])
        self.assertEqual(row['handoff'], 'Not tracked')

    def test_handoff_deduplicates_same_destination(self):
        histories = [
            event(action='assigned', details='Assigned to Alex', created_at=NOW - timedelta(days=9)),
            event(action='assigned', details='Assigned to Alex (bulk)', created_at=NOW - timedelta(days=8)),
            event(action='assigned', details='Assigned to Sam - Note: transfer', created_at=NOW - timedelta(days=7)),
            event(action='unassigned', details='Unassigned', created_at=NOW - timedelta(days=6)),
        ]
        report = self.build(histories=histories)['reports']['handoffs']
        self.assertEqual(len(report['rows']), 3)
        self.assertEqual(report['rows'][0]['hours'], 48)
        self.assertEqual(report['summary'][0]['value'], 1)
        self.assertEqual(report['summary'][1]['value'], 144)

    def test_feedback_cohort_and_expiration(self):
        survey = NS(ticket_id=1, invited_at=NOW - timedelta(days=2), responded_at=None,
                    expires_at=NOW - timedelta(days=1), score=None, comment='')
        report = self.build(surveys=[survey])['reports']['satisfaction']
        self.assertEqual(report['rows'][0]['state'], 'Expired')
        self.assertEqual(report['summary'][2]['value'], '0.0%')
        self.assertIsNone(report['summary'][3]['value'])
        survey.score, survey.responded_at = 5, NOW
        report = self.build(surveys=[survey])['reports']['satisfaction']
        self.assertEqual(report['summary'][3]['value'], 5)

    def test_ai_followups_failure_and_vote_ownership(self):
        messages = [
            NS(id=1, ticket_id=1, role='assistant', status='completed', user_id=None,
               created_at=NOW - timedelta(days=3), content='Initial answer'),
            NS(id=2, ticket_id=1, role='user', status='completed', user_id=2,
               created_at=NOW - timedelta(days=2), content='Question'),
            NS(id=3, ticket_id=1, role='assistant', status='failed', user_id=None,
               created_at=NOW - timedelta(days=2), content=''),
        ]
        ratings = [NS(message_id=1, user_id=2, helpful=True), NS(message_id=1, user_id=1, helpful=False)]
        report = self.build(messages=messages, ratings=ratings)['reports']['ai_usage']
        self.assertEqual(len(report['rows']), 2)
        self.assertEqual(report['rows'][0]['my_rating'], True)
        self.assertEqual(report['rows'][1]['kind'], 'Follow-up')
        self.assertEqual(report['summary'][-1]['value'], '50.0%')


if __name__ == '__main__':
    unittest.main()
