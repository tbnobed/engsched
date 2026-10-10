"""External incident threading and automated-recipient loop protection."""
import hashlib
import os
import re
from email.utils import parseaddr

from sqlalchemy import text, or_, func
from app import db
from models import Ticket, User, ExternalIncidentThread, ProcessedEmail


def address(value):
    return parseaddr(value or "")[1].strip().lower()


def automated_addresses():
    return {
        address(item) for item in os.environ.get(
            "AUTOMATED_TICKET_SENDERS", "ITSupport@tbnalert.tv"
        ).split(",") if address(item)
    }


def outbound_recipients(recipients):
    blocked = automated_addresses()
    return [recipient for recipient in (recipients or []) if address(recipient) not in blocked]


def incident_number(subject):
    matches = set(re.findall(r"\bIncident\s*#\s*(\d+)\b", subject or "", re.I))
    return str(int(next(iter(matches)))) if len(matches) == 1 else None


def incident_key(subject, sender):
    number = incident_number(subject)
    sender = address(sender)
    # Explicitly scoped to this support system, not arbitrary Incident # subjects.
    if number and (sender == "itsupport@tbnalert.tv" or sender.endswith("@tbn.tv")):
        return ("tbn-support", number)
    return None


def acquire_incident_lock(key):
    """A separate connection keeps the lock across the handler's commits."""
    connection = db.engine.connect()
    lock_id = int.from_bytes(
        hashlib.sha256("\0".join(key).encode()).digest()[:8], "big", signed=True
    )
    try:
        if not connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_id}
        ).scalar():
            connection.close()
            return None
        connection.commit()
        return connection, lock_id
    except Exception:
        connection.invalidate()
        connection.close()
        raise


def release_incident_lock(lock):
    if lock:
        connection, lock_id = lock
        try:
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_id})
            connection.commit()
        except Exception:
            connection.invalidate()
        finally:
            connection.close()


def find_incident_ticket(key):
    source, number = key
    mapping = ExternalIncidentThread.query.filter_by(
        source=source, incident_number=number
    ).first()
    if mapping and mapping.ticket_id:
        ticket = db.session.get(Ticket, mapping.ticket_id)
        if ticket:
            return ticket
    # Lazily adopt existing tickets without merging or deleting any records.
    # No 14-day/50-ticket cutoff: an incident remains the same when closed.
    candidates = Ticket.query.outerjoin(User, Ticket.created_by == User.id).filter(
        Ticket.title.ilike("%Incident%"),
        or_(
            func.lower(Ticket.external_email) == "itsupport@tbnalert.tv",
            func.lower(Ticket.external_email).like("%@tbn.tv"),
            (Ticket.external_email.is_(None)) & or_(
                func.lower(User.email) == "itsupport@tbnalert.tv",
                func.lower(User.email).like("%@tbn.tv"),
            ),
        ),
    ).order_by(Ticket.created_at, Ticket.id).all()
    matching = [t for t in candidates if incident_number(t.title) == number]
    active = [t for t in matching if not t.archived and t.status in ("open", "in_progress", "pending")]
    return (active or matching or [None])[0]


def referenced_ticket(headers):
    ids = re.findall(r"<([^<>]+)>", headers or "")
    for message_id in reversed(ids):
        delivery = ProcessedEmail.query.filter_by(message_id=message_id).first()
        if delivery and delivery.ticket_id:
            ticket = db.session.get(Ticket, delivery.ticket_id)
            if ticket:
                return ticket
    return None


def record_delivery(key, message_id, ticket_id):
    """Persist threading and retry dedup in the same transaction as the content."""
    if key:
        mapping = ExternalIncidentThread.query.filter_by(
            source=key[0], incident_number=key[1]
        ).first()
        if mapping is None:
            mapping = ExternalIncidentThread(source=key[0], incident_number=key[1])
            db.session.add(mapping)
        mapping.ticket_id = ticket_id
    if message_id:
        claim = ProcessedEmail.query.filter_by(message_id=message_id).first()
        if claim:
            claim.ticket_id = ticket_id
