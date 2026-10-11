"""Opt-in integration tests; create and remove only uniquely named test records.

RUN_API_INTEGRATION=1 python -m unittest tests.test_api_v1 -v
"""
import json
import os
import re
import secrets
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone


@unittest.skipUnless(os.environ.get('RUN_API_INTEGRATION') == '1', 'Opt-in database integration tests')
class APIV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from main import app
        cls.app = app

    def setUp(self):
        from app import db
        from models import User, TicketCategory
        from api_access import issue_key, SCOPES
        self.label = 'API-test-' + secrets.token_hex(6)
        self.tokens, self.key_ids = [], []
        with self.app.app_context():
            owner = User(username=self.label, email=self.label + '@example.invalid', is_admin=True, show_on_dashboard=False, timezone='UTC')
            tech = User(username=self.label + '-tech', email=self.label + '-tech@example.invalid', is_admin=False, show_on_dashboard=False, timezone='UTC')
            db.session.add_all([owner, tech])
            db.session.flush()
            self.owner, self.tech = owner.id, tech.id
            category = TicketCategory(name=self.label)
            db.session.add(category)
            db.session.flush()
            self.category = category.id
            key, token = issue_key(self.label, list(SCOPES), self.owner, datetime.now(timezone.utc) + timedelta(days=1))
            self.key_ids.append(key.id)
            self.tokens.append(token)
            db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        from app import db
        from models import (ApplicationAPIKey, ApplicationAPIAudit, ApplicationAPIReplay,
                            Ticket, TicketComment, TicketHistory, TicketView, Schedule, TicketCategory, User)
        with self.app.app_context():
            keys = db.session.query(ApplicationAPIKey.id).filter(ApplicationAPIKey.name == self.label)
            ApplicationAPIAudit.query.filter(ApplicationAPIAudit.key_id.in_(keys)).delete(synchronize_session=False)
            ApplicationAPIReplay.query.filter(ApplicationAPIReplay.key_id.in_(keys)).delete(synchronize_session=False)
            ApplicationAPIKey.query.filter(ApplicationAPIKey.name == self.label).delete(synchronize_session=False)
            tickets = db.session.query(Ticket.id).filter(Ticket.category_id == self.category)
            for model in (TicketComment, TicketHistory, TicketView):
                model.query.filter(model.ticket_id.in_(tickets)).delete(synchronize_session=False)
            Ticket.query.filter_by(category_id=self.category).delete(synchronize_session=False)
            Schedule.query.filter(Schedule.technician_id.in_([self.owner, self.tech])).delete(synchronize_session=False)
            TicketCategory.query.filter_by(id=self.category).delete(synchronize_session=False)
            User.query.filter(User.id.in_([self.owner, self.tech])).delete(synchronize_session=False)
            db.session.commit()

    def request(self, method, path, body=None, headers=None, client=None, token=None):
        actual_headers = {'Authorization': 'Bearer ' + (token or self.tokens[0]), **(headers or {})}
        return (client or self.client).open('/api/v1' + path, method=method, json=body, headers=actual_headers)

    def ticket_payload(self):
        return {'title': self.label, 'description': 'A synthetic test only.',
                'category_id': self.category, 'assigned_to': self.tech}

    def schedule_payload(self):
        return {'technician_id': self.tech, 'start_time': '2035-01-02T09:00:00Z',
                'end_time': '2035-01-02T10:00:00Z', 'description': self.label}

    def admin_client(self, user_id=None):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user_id or self.owner)
            session['_fresh'] = True
        html = client.get('/tickets/reports').get_data(as_text=True)
        csrf = re.search(r'<meta name="csrf-token" content="([^"]+)"', html).group(1)
        return client, {'X-CSRFToken': csrf}

    def new_key(self, scopes):
        from app import db
        from api_access import issue_key
        with self.app.app_context():
            key, token = issue_key(self.label, scopes, self.owner, datetime.now(timezone.utc) + timedelta(days=1))
            self.key_ids.append(key.id)
            self.tokens.append(token)
            db.session.commit()
            return token

    def test_auth_and_safe_directory(self):
        self.assertEqual(self.client.get('/api/v1/tickets').status_code, 401)
        self.assertEqual(self.client.get('/api/v1/tickets?api_key=not-a-credential').status_code, 400)
        admin, _ = self.admin_client()
        self.assertEqual(admin.get('/api/v1/tickets').status_code, 401)
        response = self.request('GET', '/technicians')
        self.assertEqual(response.status_code, 200)
        self.assertFalse('password_hash' in response.get_data(as_text=True))
        alternate = self.client.get('/api/v1/', headers={'X-API-Key': self.tokens[0]})
        self.assertEqual(alternate.status_code, 200)
        limited = self.new_key(['tickets:read'])
        self.assertEqual(self.request('GET', '/tickets', token=limited).status_code, 200)
        self.assertEqual(self.request('POST', '/tickets', self.ticket_payload(), token=limited).status_code, 403)
        self.assertEqual(self.request('GET', '/schedules', token=limited).status_code, 403)

    def test_key_management_rotation_revocation_and_csrf(self):
        admin, headers = self.admin_client()
        payload = {'name': self.label, 'scopes': ['tickets:read'], 'expires_days': 1}
        self.assertEqual(admin.post('/api/admin/api-keys', json=payload).status_code, 400)
        created = admin.post('/api/admin/api-keys', json=payload, headers=headers)
        self.assertEqual(created.status_code, 201)
        data = created.get_json()
        listed = admin.get('/api/admin/api-keys').get_data(as_text=True)
        self.assertFalse(data['token'] in listed)
        self.assertFalse('token_hash' in listed)
        rotated = admin.post(f"/api/admin/api-keys/{data['key']['id']}/rotate", json={}, headers=headers)
        self.assertEqual(rotated.status_code, 201)
        self.assertEqual(self.request('GET', '/tickets', token=data['token']).status_code, 401)
        replacement = rotated.get_json()
        self.assertEqual(self.request('GET', '/tickets', token=replacement['token']).status_code, 200)
        self.assertEqual(admin.delete(f"/api/admin/api-keys/{replacement['key']['id']}", headers=headers).status_code, 200)
        self.assertEqual(self.request('GET', '/tickets', token=replacement['token']).status_code, 401)
        tech, th = self.admin_client(self.tech)
        self.assertEqual(tech.get('/api/admin/api-keys').status_code, 403)
        self.assertEqual(tech.post('/api/admin/api-keys', json=payload, headers=th).status_code, 403)

    def test_refresh_expired_key_form_token(self):
        import time
        from unittest.mock import patch
        admin, _ = self.admin_client()
        endpoint = '/api/admin/api-keys/csrf'
        self.assertEqual(self.app.test_client().get(endpoint).status_code, 401)
        tech, _ = self.admin_client(self.tech)
        self.assertEqual(tech.get(endpoint).status_code, 403)
        def expired_token():
            from flask_wtf.csrf import generate_csrf
            with patch('itsdangerous.TimestampSigner.get_timestamp', return_value=int(time.time()) - 7200):
                return generate_csrf()
        with patch('api_access.generate_csrf', side_effect=expired_token):
            stale = admin.get(endpoint).get_json()['csrf_token']
        payload = {'name': self.label, 'expires_days': 90,
                   'scopes': ['tickets:read', 'tickets:write', 'schedules:read', 'directory:read']}
        rejected = admin.post('/api/admin/api-keys', json=payload, headers={'X-CSRFToken': stale})
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.get_json()['code'], 'csrf_failed')
        refreshed = admin.get(endpoint)
        self.assertIn('no-store', refreshed.headers['Cache-Control'])
        accepted = admin.post('/api/admin/api-keys', json=payload,
                              headers={'X-CSRFToken': refreshed.get_json()['csrf_token']})
        self.assertEqual(accepted.status_code, 201)

    def test_ticket_lifecycle_comments_notes_and_history(self):
        payload = dict(self.ticket_payload(), description='<script>alert(1)</script>\nPlain text')
        response = self.request('POST', '/tickets', payload)
        self.assertEqual(response.status_code, 201)
        ticket_id = response.get_json()['data']['id']
        self.assertFalse('<script>' in response.get_json()['data']['description_html'])
        self.assertFalse(response.get_json()['notifications_sent'])
        path = f'/tickets/{ticket_id}'
        self.assertEqual(self.request('PATCH', path, {'status': 'resolved', 'priority': 3}).status_code, 200)
        comment = self.request('POST', path + '/comments', {'content': 'Test comment'})
        self.assertEqual(comment.status_code, 201)
        self.assertEqual(self.request('POST', path + '/notes', {'content': 'Private note'}).status_code, 201)
        self.assertEqual(self.request('GET', path + '/comments').get_json()['meta']['total'], 1)
        history = self.request('GET', path + '/history').get_json()['data']
        self.assertTrue(any(row['action'] == 'status_changed' and row['details'] == 'Status changed from open to resolved' for row in history))
        self.assertTrue(any(row['action'] == 'internal_note' for row in history))
        self.assertEqual(self.request('DELETE', path).status_code, 200)
        self.assertTrue(self.request('GET', path).get_json()['data']['archived'])
        self.assertEqual(self.request('GET', f'/tickets?category_id={self.category}').get_json()['meta']['total'], 0)
        self.assertEqual(self.request('GET', f'/tickets?category_id={self.category}&archived=true').get_json()['meta']['total'], 1)
        self.assertEqual(self.request('PATCH', path, {'archived': False}).status_code, 200)

    def test_idempotency_is_atomic_and_detects_conflicts(self):
        payload = self.ticket_payload()
        header = {'Idempotency-Key': 'same-create'}
        first = self.request('POST', '/tickets', payload, header)
        second = self.request('POST', '/tickets', payload, header)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.get_json()['data']['id'], second.get_json()['data']['id'])
        self.assertEqual(second.headers.get('Idempotency-Replayed'), 'true')
        self.assertEqual(self.request('POST', '/tickets', dict(payload, title='Different'), header).status_code, 409)
        self.assertEqual(self.request('GET', f'/tickets?category_id={self.category}').get_json()['meta']['total'], 1)
        from app import db
        from models import ApplicationAPIAudit
        with self.app.app_context():
            self.assertEqual(ApplicationAPIAudit.query.filter_by(key_id=self.key_ids[0]).count(), 1)

    def test_concurrent_duplicate_posts(self):
        def create(_):
            response = self.request('POST', '/tickets', self.ticket_payload(), {'Idempotency-Key': 'parallel'},
                                    client=self.app.test_client())
            return response.status_code, response.get_json().get('data', {}).get('id')
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(create, range(2)))
        self.assertEqual([item[0] for item in results], [201, 201])
        self.assertEqual(results[0][1], results[1][1])

    def test_schedule_lifecycle_and_overlap(self):
        payload = self.schedule_payload()
        first = self.request('POST', '/schedules', payload)
        self.assertEqual(first.status_code, 201)
        schedule_id = first.get_json()['data']['id']
        self.assertEqual(self.request('POST', '/schedules', payload).status_code, 409)
        matching = self.request('GET', f'/schedules?technician_id={self.tech}&start=2035-01-02T09:30:00Z&end=2035-01-02T09:45:00Z')
        self.assertEqual(matching.get_json()['meta']['total'], 1)
        self.assertEqual(self.request('PATCH', f'/schedules/{schedule_id}', {'description': 'Changed'}).status_code, 200)
        adjacent = dict(payload, start_time='2035-01-02T10:00:00Z', end_time='2035-01-02T11:00:00Z')
        self.assertEqual(self.request('POST', '/schedules', adjacent).status_code, 201)
        self.assertEqual(self.request('DELETE', f'/schedules/{schedule_id}').status_code, 200)
        self.assertEqual(self.request('GET', f'/schedules/{schedule_id}').status_code, 404)

    def test_concurrent_schedule_conflicts_across_keys(self):
        second = self.new_key(['schedules:write'])
        def create(token):
            return self.request('POST', '/schedules', self.schedule_payload(), token=token,
                                client=self.app.test_client()).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(create, [self.tokens[0], second]))
        self.assertEqual(sorted(results), [201, 409])

    def test_validation_and_json_errors(self):
        for invalid in ({'priority': True}, {'status': []}, {'category_id': -1}, {'due_date': '2035-01-01'},
                        {'extra': 'unknown'}, {'assigned_to': '1'}):
            response = self.request('POST', '/tickets', dict(self.ticket_payload(), **invalid))
            self.assertEqual(response.status_code, 400)
        for invalid in ({'start_time': '2035-01-02T09:00:00'}, {'end_time': '2035-01-02T08:00:00Z'},
                        {'all_day': True}, {'time_off': 'false'}):
            self.assertEqual(self.request('POST', '/schedules', dict(self.schedule_payload(), **invalid)).status_code, 400)
        self.assertEqual(self.request('GET', '/tickets?page_size=101').status_code, 400)
        self.assertEqual(self.request('GET', '/tickets?archived=maybe').status_code, 400)
        for path, method, status in (('/missing', 'GET', 404), ('/technicians', 'POST', 405)):
            response = self.request(method, path)
            self.assertEqual(response.status_code, status)
            self.assertTrue(response.is_json)
        response = self.client.post('/api/v1/tickets', data='x' * 262145,
                                    headers={'Authorization': 'Bearer ' + self.tokens[0], 'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 413)

    def test_limits_expiry_and_disabled_owner(self):
        from app import db
        from models import ApplicationAPIKey, User
        with self.app.app_context():
            key = db.session.get(ApplicationAPIKey, self.key_ids[0])
            key.rate_count, key.rate_window = 120, datetime.now(timezone.utc)
            db.session.commit()
        response = self.request('GET', '/tickets')
        self.assertEqual(response.status_code, 429)
        self.assertTrue(int(response.headers['Retry-After']) > 0)
        with self.app.app_context():
            key = db.session.get(ApplicationAPIKey, self.key_ids[0])
            key.rate_count, key.expires_at = 0, datetime.now(timezone.utc) - timedelta(seconds=1)
            db.session.commit()
        self.assertEqual(self.request('GET', '/tickets').status_code, 401)
        with self.app.app_context():
            db.session.get(ApplicationAPIKey, self.key_ids[0]).expires_at = datetime.now(timezone.utc) + timedelta(days=1)
            db.session.get(User, self.owner).is_admin = False
            db.session.commit()
        self.assertEqual(self.request('GET', '/tickets').status_code, 401)

    def test_public_docs_and_openapi(self):
        self.assertEqual(self.client.get('/api/v1/docs').status_code, 200)
        schema = self.client.get('/api/v1/openapi.json').get_json()
        self.assertEqual(schema['openapi'], '3.1.0')
        self.assertTrue('/tickets/{ticket_id}/notes' in schema['paths'])
        self.assertTrue('/schedule-templates' in schema['paths'])
        self.assertEqual(self.request('GET', '/schedule-templates').status_code, 200)

    def test_secure_admin_csrf_requires_same_origin_referrer(self):
        admin = self.app.test_client()
        with admin.session_transaction(base_url='https://localhost') as session:
            session['_user_id'], session['_fresh'] = str(self.owner), True
        page = admin.get('/admin/api-access', base_url='https://localhost')
        self.assertEqual(page.headers['Referrer-Policy'], 'same-origin')
        token = re.search(r'<meta name="csrf-token" content="([^"]+)"', page.get_data(as_text=True)).group(1)
        headers = {'X-CSRFToken': token, 'Referer': 'https://localhost/admin/api-access'}
        payload = {'name': self.label, 'scopes': ['tickets:read'], 'expires_days': 1}
        response = admin.post('/api/admin/api-keys', base_url='https://localhost', json=payload, headers=headers)
        self.assertEqual(response.status_code, 201)


if __name__ == '__main__':
    unittest.main()
