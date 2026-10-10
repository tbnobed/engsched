"""Development-only regression checks; synthetic records are cleaned up."""
import unittest
from unittest.mock import patch
from test_email_threading import IncidentThreadTests
from app import app, db
from models import User, Ticket, TicketComment, TicketCommentMetadata, TicketWorkspace


class WorkspaceTests(IncidentThreadTests):
    def client(self, user_id=None):
        client = app.test_client()
        if user_id is None:
            with app.app_context():
                user_id = User.query.filter_by(is_admin=True).first().id
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True
        return client

    def test_intake_and_workspace(self):
        response = self.deliver("workspace")
        self.assertEqual(response.status_code, 200)
        ticket_id = response.json["ticket_id"]
        with app.app_context():
            ticket = db.session.get(Ticket, ticket_id)
            self.assertEqual(ticket.priority, -1)
            self.assertEqual(ticket.category.name, "Unsorted")
        client = self.client()
        result = client.get(f"/tickets/api/{ticket_id}/workspace")
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json["ticket"]["created_at"].endswith("Z"))
        self.assertEqual(client.get("/tickets/api/ux-summary").status_code, 200)
        self.assertEqual(client.get("/tickets/api/requesters?q=admin").status_code, 200)
        self.assertEqual(client.get("/api/team-schedule?start=2026-10-01&end=2026-10-08").status_code, 200)
        self.assertEqual(client.get("/api/team-schedule?start=bad&end=bad").status_code, 400)

    def test_internal_note_metadata(self):
        ticket_id = self.deliver("note").json["ticket_id"]
        client = self.client()
        with patch.dict(app.config, WTF_CSRF_ENABLED=False):
            response = client.post(f"/tickets/{ticket_id}/comment", data={"content": "Private test note", "visibility": "internal"})
        self.assertEqual(response.status_code, 302)
        with app.app_context():
            comment = TicketComment.query.filter_by(ticket_id=ticket_id).first()
            self.assertEqual(db.session.get(TicketCommentMetadata, comment.id).visibility, "internal")
            from email_utils import send_ticket_comment_notification
            with patch("email_utils.send_email") as sender:
                send_ticket_comment_notification(db.session.get(Ticket, ticket_id), comment, comment.user)
                sender.assert_not_called()

    def test_merge_preserves_content(self):
        target_id = self.deliver("merge-target").json["ticket_id"]
        # Different incident creates an independent test source.
        original_number = self.number
        self.number = original_number + "7"
        source_id = self.deliver("merge-source").json["ticket_id"]
        self.number = original_number
        client = self.client()
        try:
            with patch.dict(app.config, WTF_CSRF_ENABLED=False):
                result = client.post("/tickets/api/merge", json={"target_id": target_id, "source_ids": [source_id]})
                self.assertEqual(result.status_code, 200, result.json)
                repeat = client.post("/tickets/api/merge", json={"target_id": target_id, "source_ids": [source_id]})
                self.assertEqual(repeat.status_code, 409)
            with app.app_context():
                self.assertTrue(db.session.get(Ticket, source_id).archived)
                self.assertEqual(db.session.get(TicketWorkspace, source_id).merged_into, target_id)
                self.assertGreater(TicketComment.query.filter_by(ticket_id=target_id).count(), 0)
        finally:
            from models import ExternalIncidentThread
            with app.app_context():
                ExternalIncidentThread.query.filter_by(incident_number=original_number + "7").delete()
                db.session.commit()

    def test_permissions_and_filters(self):
        ticket_id = self.deliver("filter-permission").json["ticket_id"]
        with app.app_context():
            ticket = db.session.get(Ticket, ticket_id)
            ticket.status = "Open"  # Legacy/imported mixed-case values must remain searchable.
            user = User(username=f"restricted-{self.number}", email=f"restricted-{self.number}@example.invalid", password_hash="!", is_admin=False)
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            title = ticket.title
        try:
            admin = self.client()
            result = admin.get("/tickets/dashboard", query_string={"search": title, "status": "open"})
            self.assertEqual(result.status_code, 200)
            self.assertIn(title.encode(), result.data)
            overdue = admin.get("/tickets/dashboard", query_string={"search": title, "overdue": "1"})
            self.assertNotIn(f'data-ticket-id="{ticket_id}"'.encode(), overdue.data)
            restricted = self.client(user_id)
            with patch.dict(app.config, WTF_CSRF_ENABLED=False):
                self.assertEqual(restricted.post(f"/tickets/api/{ticket_id}/quick-update", json={"field": "status", "value": "closed"}).status_code, 403)
                self.assertEqual(restricted.post("/tickets/api/merge", json={"target_id": ticket_id, "source_ids": [ticket_id + 1]}).status_code, 403)
        finally:
            with app.app_context():
                db.session.delete(db.session.get(User, user_id))
                db.session.commit()


if __name__ == "__main__":
    unittest.main()
