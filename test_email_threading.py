"""Integration checks against the development DB; all synthetic rows are removed."""
import logging
import unittest
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from email.message import EmailMessage

logging.disable(logging.CRITICAL)
from app import app, db
from models import Ticket, TicketComment, ProcessedEmail, ExternalIncidentThread
from email_threading import (
    incident_key, acquire_incident_lock, release_incident_lock, outbound_recipients,
)
from email_utils import send_email as real_send_email


class IncidentThreadTests(unittest.TestCase):
    def setUp(self):
        self.number = str(uuid.uuid4().int)[:24]
        self.prefix = "thread-test-" + uuid.uuid4().hex
        self.ids = set()
        self.patches = [
            patch("email_utils.send_email", return_value=True),
            patch("email_utils.send_new_ticket_notification", return_value=True),
            patch("email_utils.send_ticket_comment_notification", return_value=True),
            patch("ticket_ai.queue_initial_analysis"),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        with app.app_context():
            ExternalIncidentThread.query.filter_by(incident_number=self.number).delete()
            ProcessedEmail.query.filter(ProcessedEmail.message_id.like(self.prefix + "%")).delete(synchronize_session=False)
            for ticket_id in self.ids:
                ticket = db.session.get(Ticket, ticket_id)
                if ticket:
                    db.session.delete(ticket)
            db.session.commit()

    def deliver(self, suffix, subject=None, sender="ITSupport@tbnalert.tv"):
        message = EmailMessage()
        message["From"] = sender
        message["To"] = "support@example.test"
        message["Subject"] = subject or f"[tbn] (#1036) Incident #{self.number} Synthetic test"
        message["Message-ID"] = f"<{self.prefix}-{suffix}@example.test>"
        message.set_content("Synthetic threading verification, no actual incident.")
        with app.test_client() as client:
            response = client.post("/api/inbound-email", data={"email": message.as_string()})
        if response.json and response.json.get("ticket_id"):
            self.ids.add(response.json["ticket_id"])
        return response

    def test_distinct_updates_closed_ticket_and_retry(self):
        first = self.deliver("one")
        self.assertEqual(first.status_code, 200, first.json)
        ticket_id = first.json["ticket_id"]
        second = self.deliver("two", f"Re: Incident #{self.number} Changed wording",
                              "Synthetic Person <thread-test@tbn.tv>")
        self.assertEqual(second.status_code, 200, second.json)
        self.assertEqual(second.json["ticket_id"], ticket_id)
        with app.app_context():
            ticket = db.session.get(Ticket, ticket_id)
            ticket.status = "closed"
            ticket.archived = True
            db.session.commit()
        third = self.deliver("three")
        self.assertEqual(third.json["ticket_id"], ticket_id)
        retry = self.deliver("three")
        self.assertEqual(retry.json["reason"], "duplicate message-id")
        with app.app_context():
            ticket = db.session.get(Ticket, ticket_id)
            self.assertEqual(ticket.status, "closed")
            self.assertTrue(ticket.archived)
            self.assertEqual(TicketComment.query.filter_by(ticket_id=ticket_id).count(), 2)
            self.assertEqual(ExternalIncidentThread.query.filter_by(incident_number=self.number).count(), 1)

    def test_busy_incident_is_retryable_and_not_claimed(self):
        key = ("tbn-support", self.number)
        with app.app_context():
            lock = acquire_incident_lock(key)
        try:
            result = self.deliver("busy")
            self.assertEqual(result.status_code, 503)
            with app.app_context():
                self.assertEqual(ProcessedEmail.query.filter(
                    ProcessedEmail.message_id.like(self.prefix + "%")
                ).count(), 0)
        finally:
            release_incident_lock(lock)
        self.assertEqual(self.deliver("busy").status_code, 200)

    def test_existing_ticket_adopted_without_merging(self):
        first = self.deliver("one")
        self.assertEqual(first.status_code, 200, first.json)
        with app.app_context():
            ExternalIncidentThread.query.filter_by(incident_number=self.number).delete()
            db.session.commit()
        second = self.deliver("two")
        self.assertEqual(second.json["ticket_id"], first.json["ticket_id"])

    def test_source_boundaries(self):
        self.assertIsNone(incident_key("Incident #123", "other@example.com"))
        self.assertIsNone(incident_key("Incident #123 and Incident #124", "ITSupport@tbnalert.tv"))
        self.assertEqual(incident_key("Re: Incident #00123", "TECH@TBN.TV"), ("tbn-support", "123"))

    def test_concurrent_distinct_emails(self):
        def send_with_retry(index):
            for attempt in range(20):
                response = self.deliver(f"concurrent-{index}")
                if response.status_code != 503:
                    return response
                time.sleep(.05)
            return response
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(send_with_retry, range(4)))
        self.assertTrue(all(r.status_code == 200 for r in results))
        self.assertEqual(len({r.json["ticket_id"] for r in results}), 1)
        ticket_id = results[0].json["ticket_id"]
        with app.app_context():
            self.assertEqual(TicketComment.query.filter_by(ticket_id=ticket_id).count(), 3)

    def test_failed_transaction_releases_claim(self):
        with patch("email_threading.record_delivery", side_effect=RuntimeError("Synthetic failure")):
            failed = self.deliver("recover")
        self.assertEqual(failed.status_code, 500)
        with app.app_context():
            self.assertEqual(ProcessedEmail.query.filter(
                ProcessedEmail.message_id.like(self.prefix + "%")
            ).count(), 0)
            self.assertEqual(Ticket.query.filter(Ticket.title.contains(self.number)).count(), 0)
        self.assertEqual(self.deliver("recover").status_code, 200)

    def test_automated_recipients_suppressed_only(self):
        self.assertEqual(outbound_recipients([
            "IT Alerts <ITSUPPORT@TBNALERT.TV>", "technician@example.test"
        ]), ["technician@example.test"])
        with app.app_context(), patch("email_utils.SendGridAPIClient") as client:
            self.assertTrue(real_send_email(["ITSupport@tbnalert.tv"], "test", "test"))
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
