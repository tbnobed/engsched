"""Versioned ticket and schedule resources; writes are committed by API middleware."""
from datetime import datetime, timezone
from html import escape
import re

from flask import abort, g, jsonify, request
from app import db
from models import Ticket, TicketCategory, TicketComment, TicketHistory, Schedule, Location, User, RecurringScheduleTemplate, TicketGroup
from ticket_groups import apply_assignment, apply_category_defaults, resolved_user_ids
from api_v1_core import (api_v1, require_scope, fields, integer, boolean, text, timestamp,
                         iso, paginated, query_int, query_bool)
from ticket_insights_service import comment_text, STATUS_NAMES


def reference(model, value, field, nullable=False):
    if nullable and value is None:
        return None
    integer(value, field)
    obj = db.session.get(model, value)
    if not obj:
        abort(400, description=f'{field} does not refer to an existing record.')
    return obj.id


def safe_html(value):
    return escape(value).replace('\n', '<br>')


def ticket_json(ticket):
    return {
        'id': ticket.id, 'title': ticket.title, 'description': comment_text(ticket.description),
        'description_html': ticket.description, 'category_id': ticket.category_id,
        'status': ticket.status, 'priority': ticket.priority, 'assigned_to': ticket.assigned_to,
        'group_id': ticket.group_id, 'group_name': ticket.group.name if ticket.group else None,
        'requester_id': ticket.created_by, 'external_email': ticket.external_email,
        'external_name': ticket.external_name, 'archived': bool(ticket.archived),
        'due_date': iso(ticket.due_date), 'created_at': iso(ticket.created_at), 'updated_at': iso(ticket.updated_at),
    }


def history_json(row):
    return {'id': row.id, 'ticket_id': row.ticket_id, 'author_id': row.user_id,
            'action': row.action, 'details': row.details, 'created_at': iso(row.created_at)}


def comment_json(row):
    return {'id': row.id, 'ticket_id': row.ticket_id, 'author_id': row.user_id,
            'content': comment_text(row.content), 'content_html': row.content, 'created_at': iso(row.created_at)}


def ticket_event(ticket, action, details):
    db.session.add(TicketHistory(ticket_id=ticket.id, user_id=g.api_key.owner_id,
                               action=action, details=details, created_at=datetime.now(timezone.utc)))


TICKET_FIELDS = {'title', 'description', 'category_id', 'priority', 'assigned_to', 'group_id', 'requester_id',
                 'external_email', 'external_name', 'due_date', 'status', 'archived'}


def apply_ticket(ticket, payload, creating=False):
    before_status = ticket.status
    desired_group, desired_owner = ticket.group_id, ticket.assigned_to
    for field, value in payload.items():
        if field == 'title':
            ticket.title = text(value, field, 200)
        elif field == 'description':
            ticket.description = safe_html(text(value, field, 50000))
        elif field == 'category_id':
            ticket.category_id = reference(TicketCategory, value, field)
        elif field == 'priority':
            ticket.priority = integer(value, field, 0, 3)
        elif field == 'assigned_to':
            desired_owner = reference(User, value, field, nullable=True)
        elif field == 'group_id':
            desired_group = reference(TicketGroup, value, field, nullable=True)
        elif field == 'requester_id':
            ticket.created_by = reference(User, value, field)
        elif field == 'external_name':
            ticket.external_name = None if value is None else text(value, field, 100, empty=True)
        elif field == 'external_email':
            if value is None:
                ticket.external_email = None
            else:
                value = text(value, field, 255).casefold()
                if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
                    abort(400, description='external_email must be a valid email address or null.')
                ticket.external_email = value
        elif field == 'due_date':
            ticket.due_date = None if value is None else timestamp(value, field)
        elif field == 'status':
            if not isinstance(value, str) or value not in STATUS_NAMES:
                abort(400, description='Invalid ticket status.')
            ticket.status = value
        elif field == 'archived':
            ticket.archived = boolean(value, field)
    try:
        if creating:
            ticket.group_id, ticket.assigned_to = desired_group, desired_owner
            apply_category_defaults(ticket, explicit_group='group_id' in payload,
                                    explicit_assignee='assigned_to' in payload)
            desired_group, desired_owner = ticket.group_id, ticket.assigned_to
            ticket.group_id, ticket.assigned_to = None, None
        # API writes intentionally do not trigger notification or AI side effects.
        apply_assignment(ticket, desired_group, desired_owner, actor_id=g.api_key.owner_id)
    except ValueError as exc:
        abort(400, description=str(exc))
    ticket.updated_at = datetime.now(timezone.utc)
    db.session.flush()
    if ticket.status != before_status:
        ticket_event(ticket, 'status_changed', f'Status changed from {before_status} to {ticket.status}')
    ticket_event(ticket, 'created' if creating else 'api_updated',
                 f'{"Created" if creating else "Updated"} via API key: {g.api_key.name}')


@api_v1.get('')
@api_v1.get('/')
def index():
    return jsonify(data={'version': 'v1', 'scopes': g.api_key.scopes, 'docs': '/api/v1/docs'})


@api_v1.route('/tickets', methods=['GET', 'POST'])
def tickets():
    if request.method == 'GET':
        return list_tickets()
    return create_ticket()


@require_scope('tickets:read')
def list_tickets():
    query = Ticket.query.filter(Ticket.archived == query_bool('archived', False))
    for field in ('category_id', 'priority', 'requester_id'):
        value = query_int(field, minimum=0 if field == 'priority' else 1, maximum=3 if field == 'priority' else 2147483647)
        if value is not None:
            query = query.filter(getattr(Ticket, 'created_by' if field == 'requester_id' else field) == value)
    if 'assigned_to' in request.args:
        value = request.args['assigned_to']
        query = query.filter(Ticket.assigned_to.is_(None)) if value == 'unassigned' else query.filter(Ticket.assigned_to == query_int('assigned_to'))
    if 'group_id' in request.args:
        query = (query.filter(Ticket.group_id.is_(None)) if request.args['group_id'] == 'none'
                 else query.filter(Ticket.group_id == query_int('group_id')))
    if 'status' in request.args:
        status = request.args['status']
        if status not in STATUS_NAMES:
            abort(400, description='Invalid ticket status.')
        query = query.filter(Ticket.status == status)
    if 'updated_since' in request.args:
        query = query.filter(Ticket.updated_at >= timestamp(request.args['updated_since'], 'updated_since'))
    if 'q' in request.args:
        term = text(request.args['q'], 'q', 200)
        query = query.filter(Ticket.title.ilike('%' + term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%', escape='\\'))
    return paginated(query.order_by(Ticket.id), ticket_json)


@require_scope('tickets:write')
def create_ticket():
    payload = fields(TICKET_FIELDS, ('title', 'description', 'category_id'))
    ticket = Ticket(title='', description='', category_id=1, status='open', priority=0,
                    created_by=g.api_key.owner_id, email_notifications=False, archived=False)
    db.session.add(ticket)
    # Avoid autoflush before required references and fields have been validated.
    with db.session.no_autoflush:
        apply_ticket(ticket, payload, creating=True)
    return jsonify(data=ticket_json(ticket), notifications_sent=False), 201


@api_v1.route('/tickets/<int:ticket_id>', methods=['GET', 'PATCH', 'DELETE'])
def ticket_detail(ticket_id):
    needed = 'tickets:read' if request.method == 'GET' else 'tickets:write'
    if needed not in g.api_key.scopes:
        abort(403, description=f'Required permission: {needed}.')
    query = Ticket.query.filter_by(id=ticket_id)
    ticket = query.first_or_404() if request.method == 'GET' else query.with_for_update().first_or_404()
    if request.method == 'PATCH':
        apply_ticket(ticket, fields(TICKET_FIELDS))
    elif request.method == 'DELETE':
        fields(())
        if not ticket.archived:
            ticket.archived = True
            ticket.updated_at = datetime.now(timezone.utc)
            ticket_event(ticket, 'archived', f'Archived via API key: {g.api_key.name}')
        return jsonify(data={'id': ticket.id, 'archived': True})
    return jsonify(data=ticket_json(ticket))


@api_v1.route('/tickets/<int:ticket_id>/comments', methods=['GET', 'POST'])
def comments(ticket_id):
    needed = 'tickets:read' if request.method == 'GET' else 'tickets:write'
    if needed not in g.api_key.scopes:
        abort(403, description=f'Required permission: {needed}.')
    ticket = Ticket.query.filter_by(id=ticket_id).first_or_404() if request.method == 'GET' else Ticket.query.filter_by(id=ticket_id).with_for_update().first_or_404()
    if request.method == 'GET':
        return paginated(TicketComment.query.filter_by(ticket_id=ticket_id).order_by(TicketComment.id), comment_json)
    payload = fields({'content'}, ('content',))
    row = TicketComment(ticket_id=ticket_id, user_id=g.api_key.owner_id,
                        content=safe_html(text(payload['content'], 'content', 20000)))
    db.session.add(row)
    ticket.updated_at = datetime.now(timezone.utc)
    ticket_event(ticket, 'comment_added', f'Comment recorded via API key: {g.api_key.name}; no email sent')
    db.session.flush()
    return jsonify(data=comment_json(row), notifications_sent=False), 201


@api_v1.get('/tickets/<int:ticket_id>/history')
@require_scope('tickets:read')
def history(ticket_id):
    db.get_or_404(Ticket, ticket_id)
    return paginated(TicketHistory.query.filter_by(ticket_id=ticket_id).order_by(TicketHistory.id), history_json)


@api_v1.post('/tickets/<int:ticket_id>/notes')
@require_scope('tickets:write')
def internal_note(ticket_id):
    ticket = Ticket.query.filter_by(id=ticket_id).with_for_update().first_or_404()
    payload = fields({'content'}, ('content',))
    row = TicketHistory(ticket_id=ticket_id, user_id=g.api_key.owner_id, action='internal_note',
                        details=safe_html(text(payload['content'], 'content', 20000)))
    ticket.updated_at = datetime.now(timezone.utc)
    db.session.add(row)
    db.session.flush()
    return jsonify(data=history_json(row), notifications_sent=False), 201


def schedule_json(row):
    return {
        'id': row.id, 'technician_id': row.technician_id,
        'technician_timezone': row.technician.get_timezone(),
        'start_time': iso(row.start_time), 'end_time': iso(row.end_time),
        'description': row.description, 'location_id': row.location_id,
        'time_off': bool(row.time_off), 'all_day': bool(row.all_day), 'created_at': iso(row.created_at),
    }


SCHEDULE_FIELDS = {'technician_id', 'start_time', 'end_time', 'description', 'location_id', 'time_off', 'all_day'}


def apply_schedule(row, payload):
    for field, value in payload.items():
        if field == 'technician_id':
            row.technician_id = reference(User, value, field)
        elif field == 'location_id':
            row.location_id = reference(Location, value, field, nullable=True)
        elif field in {'start_time', 'end_time'}:
            setattr(row, field, timestamp(value, field))
        elif field in {'time_off', 'all_day'}:
            setattr(row, field, boolean(value, field))
        elif field == 'description':
            row.description = text(value, field, 200, empty=True)
    start, end = row.start_time, row.end_time
    # Existing timezone-aware columns may be returned naive by SQLite test environments.
    from ticket_insights_service import utc
    start, end = utc(start), utc(end)
    if end <= start:
        abort(400, description='end_time must be after start_time. End boundaries are exclusive.')
    if (end - start).days > 366:
        abort(400, description='A schedule entry cannot exceed 366 days.')
    # This serializes competing API writes even when they use different API keys.
    tech = User.query.filter_by(id=row.technician_id).with_for_update().first()
    if row.all_day:
        zone = tech.get_timezone_obj()
        a, b = start.astimezone(zone), end.astimezone(zone)
        if not row.time_off or any((a.hour, a.minute, a.second, a.microsecond, b.hour, b.minute, b.second, b.microsecond)):
            abort(400, description='All-day time off must use midnight boundaries in the technician timezone, with an exclusive end.')
    overlap = Schedule.query.filter(Schedule.technician_id == row.technician_id,
                                    Schedule.start_time < end, Schedule.end_time > start)
    if row.id:
        overlap = overlap.filter(Schedule.id != row.id)
    if overlap.first():
        abort(409, description='This entry overlaps an existing schedule for this technician. Existing appointments were not changed.')
    db.session.flush()


@api_v1.route('/schedules', methods=['GET', 'POST'])
def schedules():
    needed = 'schedules:read' if request.method == 'GET' else 'schedules:write'
    if needed not in g.api_key.scopes:
        abort(403, description=f'Required permission: {needed}.')
    if request.method == 'GET':
        query = Schedule.query
        for field in ('technician_id', 'location_id'):
            value = query_int(field)
            if value is not None:
                query = query.filter(getattr(Schedule, field) == value)
        off = query_bool('time_off')
        if off is not None:
            query = query.filter(Schedule.time_off == off)
        start = timestamp(request.args['start'], 'start') if 'start' in request.args else None
        end = timestamp(request.args['end'], 'end') if 'end' in request.args else None
        if start and end and end <= start:
            abort(400, description='end must be after start.')
        if start:
            query = query.filter(Schedule.end_time > start)
        if end:
            query = query.filter(Schedule.start_time < end)
        return paginated(query.order_by(Schedule.id), schedule_json)
    payload = fields(SCHEDULE_FIELDS, ('technician_id', 'start_time', 'end_time'))
    row = Schedule(time_off=False, all_day=False, description='')
    db.session.add(row)
    with db.session.no_autoflush:
        apply_schedule(row, payload)
    return jsonify(data=schedule_json(row), notifications_sent=False), 201


@api_v1.route('/schedules/<int:schedule_id>', methods=['GET', 'PATCH', 'DELETE'])
def schedule_detail(schedule_id):
    needed = 'schedules:read' if request.method == 'GET' else 'schedules:write'
    if needed not in g.api_key.scopes:
        abort(403, description=f'Required permission: {needed}.')
    query = Schedule.query.filter_by(id=schedule_id)
    row = query.first_or_404() if request.method == 'GET' else query.with_for_update().first_or_404()
    if request.method == 'DELETE':
        fields(())
        db.session.delete(row)
        return jsonify(data={'id': schedule_id, 'deleted': True})
    if request.method == 'PATCH':
        with db.session.no_autoflush:
            apply_schedule(row, fields(SCHEDULE_FIELDS))
    return jsonify(data=schedule_json(row))


@api_v1.get('/technicians')
@require_scope('directory:read')
def technicians():
    return paginated(User.query.order_by(User.id), lambda user: {
        'id': user.id, 'username': user.username, 'email': user.email,
        'timezone': user.get_timezone(), 'show_on_dashboard': user.show_on_dashboard,
    })


@api_v1.get('/categories')
@require_scope('directory:read')
def categories():
    return paginated(TicketCategory.query.order_by(TicketCategory.id), lambda row: {
        'id': row.id, 'name': row.name, 'description': row.description,
        'default_group_id': row.default_group_id, 'default_assignee_id': row.default_assignee_id,
    })


@api_v1.get('/groups')
@require_scope('directory:read')
def groups():
    query = TicketGroup.query
    if 'enabled' in request.args:
        query = query.filter(TicketGroup.enabled == query_bool('enabled', True))
    return paginated(query.order_by(TicketGroup.id), lambda row: {
        'id': row.id, 'name': row.name, 'description': row.description,
        'manager_user_id': row.manager_user_id, 'enabled': row.enabled,
        'notifications_enabled': row.notifications_enabled,
        'member_ids': sorted(resolved_user_ids(row.id)),
    })


@api_v1.get('/locations')
@require_scope('directory:read')
def locations():
    return paginated(Location.query.order_by(Location.id), lambda row: {
        'id': row.id, 'name': row.name, 'description': row.description, 'active': bool(row.active),
    })


@api_v1.get('/schedule-templates')
@require_scope('schedules:read')
def schedule_templates():
    query = RecurringScheduleTemplate.query
    technician_id = query_int('technician_id')
    active = query_bool('active')
    if technician_id is not None:
        query = query.filter_by(technician_id=technician_id)
    if active is not None:
        query = query.filter_by(active=active)

    def serialize(row):
        return {
            'id': row.id, 'name': row.template_name, 'technician_id': row.technician_id,
            'location_id': row.location_id, 'active': bool(row.active),
            'timezone': row.technician.get_timezone(),
            'weekly_hours': {day: {'start': getattr(row, day + '_start'), 'end': getattr(row, day + '_end')}
                             for day in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')},
        }
    return paginated(query.order_by(RecurringScheduleTemplate.id), serialize)
