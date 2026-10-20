"""ORM unit-of-work integration covers web, API, email and feedback writes."""
import copy
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from automation_engine import event_pass, snapshot, keyword_text
from automation_models import now
from models import Ticket, TicketComment, TicketFeedback, TicketHistory


@event.listens_for(Session, 'before_flush')
def collect_events(session, flush_context, instances):
    if session.info.get('automation_suppressed'):
        return
    collected = session.info.setdefault('automation_collecting', [])
    with session.no_autoflush:
        for row in list(session.new) + list(session.dirty):
            if row in session.deleted:
                continue
            if isinstance(row, Ticket):
                new = row in session.new
                changes = {attr.key: attr.history for attr in inspect(row).attrs
                           if attr.history.has_changes() and attr.key in row.__table__.columns}
                if not new and not changes:
                    continue
                instant = now()
                if new:
                    row.created_at = row.created_at or instant
                    row.updated_at = row.updated_at or instant
                else:
                    row.updated_at = instant
                if 'assigned_to' in changes and row.assigned_to:
                    row.assigned_at = instant
                if 'status' in changes:
                    if row.status == 'resolved':
                        row.resolved_at = instant
                    elif row.status == 'closed':
                        row.closed_at = instant
                    elif row.status == 'open' and any(v in ('resolved', 'closed') for v in changes['status'].deleted):
                        row.reopened_at = instant
                data = snapshot(row)
                previous = copy.deepcopy(data)
                for key, history in changes.items():
                    if history.deleted:
                        previous[key] = copy.deepcopy(history.deleted[0])
                    elif not new:
                        # An expired scalar assigned without loading has no old
                        # value in history; fetch its pre-flush persisted value.
                        previous[key] = session.connection().execute(
                            row.__table__.select().with_only_columns(row.__table__.c[key]).where(
                                row.__table__.c.id == row.id)).scalar()
                previous['keyword'] = keyword_text(previous)
                collected.append((row, 'created' if new else 'updated', data, previous, None))
            elif isinstance(row, TicketComment) and row in session.new:
                ticket = row.ticket or (session.get(Ticket, row.ticket_id) if row.ticket_id else None)
                if ticket:
                    # New comments advance the last-updated anchor as well.
                    ticket.updated_at = now()
                    row.created_at = row.created_at or now()
                    collected.append((ticket, 'comment_added', None, None, row))
            elif isinstance(row, TicketFeedback) and row.responded_at and (
                    row in session.new or inspect(row).attrs.responded_at.history.has_changes()):
                ticket = session.get(Ticket, row.ticket_id)
                if ticket:
                    collected.append((ticket, 'survey_submitted', None, None, None))
            elif isinstance(row, TicketHistory) and row in session.new and row.action == 'internal_note':
                ticket = row.ticket or (session.get(Ticket, row.ticket_id) if row.ticket_id else None)
                if ticket:
                    collected.append((ticket, 'comment_added', None, None, row))


@event.listens_for(Session, 'after_flush_postexec')
def finalize_events(session, flush_context):
    if session.info.get('automation_suppressed'):
        return
    events = session.info.pop('automation_collecting', [])
    queue = session.info.setdefault('automation_events', [])
    with session.no_autoflush:
        for ticket, trigger, data, previous, comment in events:
            if data is None or trigger == 'created':
                data = snapshot(ticket, comment)
            else:
                data['id'] = ticket.id
            queue.append((ticket.id, trigger, copy.deepcopy(data), previous))


@event.listens_for(Session, 'before_commit')
def execute_events(session):
    if session.info.get('automation_suppressed') or session.in_nested_transaction():
        return
    session.flush()
    queue = session.info.pop('automation_events', [])
    if not queue:
        return
    session.info['automation_suppressed'] = True
    try:
        for ticket_id, trigger, data, previous in queue:
            ticket = session.get(Ticket, ticket_id)
            if ticket and ticket not in session.deleted:
                event_pass(ticket, trigger, data, previous)
        session.flush()
    finally:
        session.info.pop('automation_suppressed', None)
        session.info.pop('automation_collecting', None)


@event.listens_for(Session, 'after_soft_rollback')
def clear_rollback_events(session, previous_transaction):
    if not previous_transaction.nested:
        session.info.pop('automation_collecting', None)
        session.info.pop('automation_events', None)
