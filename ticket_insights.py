"""Authenticated ticket dashboard, per-user layouts, and report exports."""
import csv
import io
from datetime import date, datetime, timedelta, timezone

import pytz
from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app import db
from models import (ProcessedEmail, Ticket, TicketCategory, TicketComment,
                    TicketDashboardLayout, TicketHistory, User)
from ticket_insights_service import (CATALOG, PRIORITIES, REPORT_NAMES, STATUS_NAMES,
                                     build_insights, default_layout, utc, validate_layout)

insights = Blueprint('insights', __name__)


@insights.before_request
def protect_api():
    if request.path.startswith('/api/') and not current_user.is_authenticated:
        return jsonify(error='Please sign in to view ticket reports.'), 401


@insights.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def profile_timezone():
    try:
        return pytz.timezone(current_user.timezone or 'America/Los_Angeles')
    except pytz.UnknownTimeZoneError:
        return pytz.UTC


@insights.route('/tickets/overview')
@login_required
def overview():
    return render_template('tickets/overview.html', insights_page='overview')


@insights.route('/tickets/reports')
@login_required
def reports():
    return render_template('tickets/reports.html', insights_page='reports')


@insights.route('/api/ticket-insights/config')
@login_required
def config():
    saved = db.session.get(TicketDashboardLayout, current_user.id)
    return jsonify(
        user_id=current_user.id, timezone=str(profile_timezone()),
        options={
            'technicians': [{'id': user.id, 'name': user.username} for user in User.query.order_by(User.username)],
            'categories': [{'id': category.id, 'name': category.name} for category in TicketCategory.query.order_by(TicketCategory.name)],
            'statuses': [{'id': key, 'name': name} for key, name in STATUS_NAMES.items()],
            'priorities': [{'id': key, 'name': name} for key, name in PRIORITIES.items()],
            'sources': [{'id': 'email', 'name': 'Email'}, {'id': 'web', 'name': 'Web'}],
        },
        catalog=[dict(type=kind, title=title, description=description) for kind, title, description in CATALOG],
        layout=saved.layout if saved else default_layout(),
    )


@insights.route('/api/ticket-insights/layout', methods=['PUT'])
@login_required
def save_layout():
    if request.content_length and request.content_length > 20000:
        return jsonify(error='Dashboard layout is too large.'), 413
    try:
        layout = validate_layout(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    # Upsert keeps first saves from two browser tabs from violating the user key.
    if db.engine.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
        stmt = insert(TicketDashboardLayout).values(
            user_id=current_user.id, layout=layout, updated_at=datetime.now(timezone.utc))
        db.session.execute(stmt.on_conflict_do_update(
            index_elements=['user_id'], set_={'layout': layout, 'updated_at': datetime.now(timezone.utc)}))
    else:
        saved = db.session.get(TicketDashboardLayout, current_user.id)
        if saved:
            saved.layout = layout
            saved.updated_at = datetime.now(timezone.utc)
        else:
            db.session.add(TicketDashboardLayout(user_id=current_user.id, layout=layout))
    db.session.commit()
    return jsonify(layout=layout)


def read_filters():
    today = datetime.now(profile_timezone()).date()
    try:
        start = date.fromisoformat(request.args.get('start') or (today - timedelta(days=29)).isoformat())
        end = date.fromisoformat(request.args.get('end') or today.isoformat())
    except (TypeError, ValueError):
        raise ValueError('Dates must use YYYY-MM-DD.')
    if start > end or (end - start).days > 365:
        raise ValueError('Choose a date range from 1 to 366 days.')
    filters = {'start': start, 'end': end}
    allowed = {
        'technician': {'all', 'me', 'unassigned'}, 'category': {'all'},
        'priority': {'all', '0', '1', '2', '3'}, 'status': {'all', *STATUS_NAMES},
        'source': {'all', 'email', 'web'}, 'scope': {'team', 'me'},
        'stalled_days': {'3', '7', '14', '30'},
    }
    for key, choices in allowed.items():
        default = '7' if key == 'stalled_days' else 'team' if key == 'scope' else 'all'
        value = request.args.get(key, default)
        if value not in choices:
            if key not in {'technician', 'category'} or not value.isdecimal() or not (0 < int(value) <= 2147483647):
                raise ValueError(f'Invalid {key.replace("_", " ")} filter.')
        filters[key] = value
    filters['stalled_days'] = int(filters['stalled_days'])
    return filters


def load_data(filters):
    query = Ticket.query
    if filters['technician'] == 'me':
        query = query.filter(Ticket.assigned_to == current_user.id)
    elif filters['technician'] == 'unassigned':
        query = query.filter(Ticket.assigned_to.is_(None))
    elif filters['technician'] != 'all':
        query = query.filter(Ticket.assigned_to == int(filters['technician']))
    if filters['scope'] == 'me':
        query = query.filter(Ticket.assigned_to == current_user.id)
    if filters['category'] != 'all':
        query = query.filter(Ticket.category_id == int(filters['category']))
    if filters['priority'] != 'all':
        query = query.filter(Ticket.priority == int(filters['priority']))
    if filters['status'] != 'all':
        query = query.filter(Ticket.status == filters['status'])
    tickets = query.all()
    ids_query = query.with_entities(Ticket.id)
    comments = TicketComment.query.options(joinedload(TicketComment.user)).filter(TicketComment.ticket_id.in_(ids_query)).all()
    histories = TicketHistory.query.filter(TicketHistory.ticket_id.in_(ids_query)).all()
    # Email from an internal user does not populate external_email.
    ticket_by_id = {ticket.id: ticket for ticket in tickets}
    email_ids = set()
    for entry in db.session.query(ProcessedEmail.ticket_id, ProcessedEmail.processed_at).filter(
            ProcessedEmail.ticket_id.in_(ids_query)):
        ticket = ticket_by_id[entry.ticket_id]
        if ticket.created_at and entry.processed_at and abs(
                (utc(entry.processed_at) - utc(ticket.created_at)).total_seconds()) <= 120:
            email_ids.add(ticket.id)
    users = {user.id: user for user in User.query.all()}
    categories = {category.id: category.name for category in TicketCategory.query.all()}
    return build_insights(tickets, comments, histories, users, categories, email_ids,
                          filters, current_user.id, profile_timezone())


@insights.route('/api/ticket-insights/data')
@login_required
def data():
    try:
        filters = read_filters()
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(load_data(filters))


def csv_cell(value):
    if value is None:
        return 'Not tracked'
    # Spreadsheet exports must not execute formulas from ticket titles/usernames.
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + value
    return value


@insights.route('/api/ticket-insights/export/<report>.csv')
@login_required
def export(report):
    if report not in REPORT_NAMES:
        return jsonify(error='Unknown report.'), 404
    try:
        filters = read_filters()
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    payload = load_data(filters)
    result = payload['reports'][report]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([column['label'] for column in result['columns']])
    for row in result['rows']:
        writer.writerow([csv_cell(row.get(column['key'])) for column in result['columns']])
    return Response('\ufeff' + output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="tickets-{report}-{payload["start"]}-{payload["end"]}.csv"'})
