"""Configuration and new reporting signals. Public surveys expose no ticket content."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import math
import secrets

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from models import (Ticket, TicketAIMessage, TicketAIRating, TicketFeedback,
                    TicketReportingSettings, TicketRequesterProfile, User)
from ticket_insights_service import utc, requester_key

reporting_controls = Blueprint('reporting_controls', __name__)


def target_defaults():
    return [{'priority': priority, 'response_hours': None, 'resolution_hours': None} for priority in range(4)]


def validate_targets(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('targets'), list) or len(payload['targets']) != 4:
        raise ValueError('Provide targets for each of the four priorities.')
    targets, priorities = [], set()
    for item in payload['targets']:
        if not isinstance(item, dict) or type(item.get('priority')) is not int or item['priority'] not in range(4) or item['priority'] in priorities:
            raise ValueError('Each priority must appear exactly once.')
        priorities.add(item['priority'])
        clean = {'priority': item['priority']}
        for field in ('response_hours', 'resolution_hours'):
            value = item.get(field)
            if value is not None and (type(value) not in (float, int) or not math.isfinite(value) or not .01 <= value <= 8760):
                raise ValueError('Targets must be blank or between 0.01 and 8760 calendar hours.')
            clean[field] = value
        targets.append(clean)
    return sorted(targets, key=lambda item: item['priority'])


@reporting_controls.before_request
def protect_controls():
    if request.path.startswith('/api/') and not current_user.is_authenticated:
        return jsonify(error='Please sign in.'), 401


@reporting_controls.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'private, no-store'
    if request.path.startswith('/feedback/'):
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
        response.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'self' 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    return response


def require_admin():
    if not current_user.is_admin:
        abort(403)


def settings_payload():
    row = db.session.get(TicketReportingSettings, 1)
    return {'targets': row.targets if row else target_defaults(),
            'updated_at': utc(row.updated_at).isoformat() if row else None}


@reporting_controls.get('/tickets/report-settings')
@login_required
def settings_page():
    require_admin()
    return render_template('tickets/report_settings.html')


@reporting_controls.route('/api/ticket-insights/settings', methods=['GET', 'PUT'])
@login_required
def settings():
    require_admin()
    if request.method == 'PUT':
        try:
            targets = validate_targets(request.get_json(silent=True))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        from sqlalchemy.dialects.postgresql import insert
        if db.engine.dialect.name == 'postgresql':
            statement = insert(TicketReportingSettings).values(id=1, targets=targets, updated_at=datetime.now(timezone.utc))
            db.session.execute(statement.on_conflict_do_update(
                index_elements=['id'], set_={'targets': targets, 'updated_at': datetime.now(timezone.utc)}))
        else:
            row = db.session.get(TicketReportingSettings, 1)
            if row:
                row.targets, row.updated_at = targets, datetime.now(timezone.utc)
            else:
                db.session.add(TicketReportingSettings(id=1, targets=targets))
        db.session.commit()
    return jsonify(settings_payload())


def requester_directory():
    users = {user.id: user for user in User.query.all()}
    profiles = {row.key: row for row in TicketRequesterProfile.query.all()}
    found = {}
    for ticket in Ticket.query.all():
        key = requester_key(ticket)
        user = users.get(ticket.created_by)
        profile = profiles.get(key)
        found.setdefault(key, {
            'key': key, 'name': ticket.external_name or ticket.external_email if ticket.external_email else user.username if user else 'Unknown requester',
            'email': ticket.external_email or (user.email if user else ''),
            'department': profile.department if profile else '',
            'location': profile.location if profile else '',
        })
    return sorted(found.values(), key=lambda item: (item['name'] or '').casefold())


@reporting_controls.route('/api/ticket-insights/requesters', methods=['GET', 'PUT'])
@login_required
def requesters():
    require_admin()
    directory = requester_directory()
    if request.method == 'GET':
        return jsonify(requesters=directory)
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get('key'), str):
        return jsonify(error='Select a requester.'), 400
    selected = next((entry for entry in directory if entry['key'] == body['key']), None)
    if not selected:
        return jsonify(error='Requester not found.'), 404
    for field in ('department', 'location'):
        if not isinstance(body.get(field), str) or len(body[field].strip()) > 100:
            return jsonify(error='Department and location must be text of at most 100 characters.'), 400
    department, location = body['department'].strip(), body['location'].strip()
    # Atomic upsert handles concurrent edits without duplicate requester keys.
    if db.engine.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
        if department or location:
            statement = insert(TicketRequesterProfile).values(key=selected['key'], department=department, location=location)
            db.session.execute(statement.on_conflict_do_update(
                index_elements=['key'], set_={'department': department, 'location': location}))
        else:
            TicketRequesterProfile.query.filter_by(key=selected['key']).delete()
    else:
        profile = db.session.get(TicketRequesterProfile, selected['key'])
        if department or location:
            if not profile:
                profile = TicketRequesterProfile(key=selected['key'])
                db.session.add(profile)
            profile.department, profile.location = department, location
        elif profile:
            db.session.delete(profile)
    db.session.commit()
    return jsonify(requester=dict(selected, department=department, location=location))


@reporting_controls.post('/api/ticket-insights/feedback-links')
@login_required
def feedback_link():
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or type(body.get('ticket_id')) is not int:
        return jsonify(error='Select a resolved or closed ticket.'), 400
    ticket = Ticket.query.filter_by(id=body['ticket_id']).with_for_update().first_or_404()
    if ticket.status not in {'resolved', 'closed'}:
        return jsonify(error='Feedback links are available after a ticket is resolved or closed.'), 409
    existing = db.session.get(TicketFeedback, ticket.id)
    if existing and existing.responded_at:
        return jsonify(error='This ticket already has feedback. Submitted feedback cannot be replaced.'), 409
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    row = existing or TicketFeedback(ticket_id=ticket.id)
    row.token_hash = sha256(token.encode()).hexdigest()
    row.invited_by, row.invited_at, row.expires_at = current_user.id, now, now + timedelta(days=30)
    db.session.add(row)
    db.session.commit()
    return jsonify(path=url_for('reporting_controls.feedback', token=token), expires_at=utc(row.expires_at).isoformat())


@reporting_controls.route('/feedback/<token>', methods=['GET', 'POST'])
def feedback(token):
    if len(token) > 100:
        abort(404)
    digest = sha256(token.encode()).hexdigest()
    query = TicketFeedback.query.filter_by(token_hash=digest)
    row = query.with_for_update().first() if request.method == 'POST' else query.first()
    now = datetime.now(timezone.utc)
    if not row or (not row.responded_at and utc(row.expires_at) <= now):
        return render_template('tickets/feedback.html', state='expired', ticket_number=None, form_error=None), 410 if row else 404
    if row.responded_at:
        return render_template('tickets/feedback.html', state='submitted', ticket_number=None, form_error=None)
    error = None
    if request.method == 'POST':
        score_text, comment = request.form.get('score', ''), request.form.get('comment', '').strip()
        if score_text not in {'1', '2', '3', '4', '5'}:
            error = 'Please choose a rating from 1 to 5.'
        elif len(comment) > 2000:
            error = 'Please keep feedback under 2,000 characters.'
        else:
            row.score, row.comment, row.responded_at = int(score_text), comment, now
            db.session.commit()
            return redirect(url_for('reporting_controls.feedback', token=token), code=303)
    return render_template('tickets/feedback.html', state='open', ticket_number=row.ticket_id, form_error=error), 400 if error else 200


@reporting_controls.put('/api/ticket-insights/ai/<int:message_id>/rating')
@login_required
def ai_rating(message_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or 'helpful' not in body or (body['helpful'] is not None and type(body['helpful']) is not bool):
        return jsonify(error='Choose helpful, not helpful, or clear your rating.'), 400
    message = TicketAIMessage.query.filter_by(id=message_id).with_for_update().first_or_404()
    if message.role != 'assistant' or message.status != 'completed':
        return jsonify(error='Only completed AI responses can be rated.'), 409
    rating = db.session.get(TicketAIRating, (message_id, current_user.id))
    if body['helpful'] is None:
        if rating:
            db.session.delete(rating)
    elif rating:
        rating.helpful, rating.updated_at = body['helpful'], datetime.now(timezone.utc)
    else:
        db.session.add(TicketAIRating(message_id=message_id, user_id=current_user.id, helpful=body['helpful']))
    db.session.commit()
    ratings = TicketAIRating.query.filter_by(message_id=message_id).all()
    return jsonify(helpful_votes=sum(r.helpful for r in ratings),
                   not_helpful_votes=sum(not r.helpful for r in ratings), my_rating=body['helpful'])
