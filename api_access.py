"""Session/CSRF-protected administration, separate from bearer-authenticated API."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user, login_required
from app import db
from models import ApplicationAPIKey, ApplicationAPIAudit, User
from ticket_insights_service import utc

api_admin = Blueprint('api_admin', __name__)
SCOPES = {
    'tickets:read': 'Read tickets, comments and history',
    'tickets:write': 'Create and update tickets, add notes, archive tickets',
    'schedules:read': 'Read technician schedules',
    'schedules:write': 'Create, edit and delete schedule entries',
    'directory:read': 'Read technicians, ticket categories and locations',
}


def key_metadata(key):
    owner = db.session.get(User, key.owner_id) if key.owner_id else None
    return {'disabled': not owner or not owner.is_admin,
            **{field: getattr(key, field) for field in ('id', 'name', 'prefix', 'scopes')},
            **{field: utc(getattr(key, field)).isoformat() if getattr(key, field) else None
               for field in ('created_at', 'expires_at', 'revoked_at', 'last_used_at')}}


def issue_key(name, scopes, owner_id, expires_at):
    token = 'plex_' + secrets.token_urlsafe(32)
    key = ApplicationAPIKey(name=name, scopes=scopes, owner_id=owner_id, expires_at=expires_at,
                            token_hash=sha256(token.encode()).hexdigest(), prefix=token[:13])
    db.session.add(key)
    db.session.flush()
    return key, token


@api_admin.before_request
def admin_only():
    if not current_user.is_authenticated:
        if request.path.startswith('/api/'):
            return jsonify(error='Sign in as an administrator.'), 401
        return None  # Page's login_required handles the normal login redirect.
    if not current_user.is_admin:
        return jsonify(error='Administrator access required.'), 403


@api_admin.after_request
def private(response):
    response.headers['Cache-Control'] = 'private, no-store'
    # Flask-WTF's HTTPS CSRF validation requires a same-origin Referer.
    response.headers['Referrer-Policy'] = 'same-origin'
    return response


@api_admin.get('/admin/api-access')
@login_required
def page():
    return render_template('admin/api_access.html')


@api_admin.route('/api/admin/api-keys', methods=['GET', 'POST'])
@login_required
def keys():
    if request.method == 'GET':
        return jsonify(keys=[key_metadata(key) for key in ApplicationAPIKey.query.order_by(ApplicationAPIKey.id.desc()).all()],
                       scopes=[{'id': scope, 'label': label} for scope, label in SCOPES.items()],
                       base_path='/api/v1', docs_url='/api/v1/docs', rate_limit=120)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) - {'name', 'scopes', 'expires_days'}:
        return jsonify(error='Provide name, scopes and expires_days.'), 400
    name, scopes, days = payload.get('name'), payload.get('scopes'), payload.get('expires_days', 90)
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        return jsonify(error='Name must contain 1–80 characters.'), 400
    if not isinstance(scopes, list) or not scopes or any(not isinstance(scope, str) or scope not in SCOPES for scope in scopes):
        return jsonify(error='Select at least one valid scope.'), 400
    if type(days) is not int or not 1 <= days <= 365:
        return jsonify(error='Expiration must be 1–365 days.'), 400
    key, token = issue_key(name.strip(), sorted(set(scopes)), current_user.id, datetime.now(timezone.utc) + timedelta(days=days))
    db.session.commit()
    return jsonify(key=key_metadata(key), token=token), 201


@api_admin.delete('/api/admin/api-keys/<int:key_id>')
@login_required
def revoke(key_id):
    key = ApplicationAPIKey.query.filter_by(id=key_id).with_for_update().first_or_404()
    key.revoked_at = key.revoked_at or datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(revoked=True)


@api_admin.post('/api/admin/api-keys/<int:key_id>/rotate')
@login_required
def rotate(key_id):
    old = ApplicationAPIKey.query.filter_by(id=key_id).with_for_update().first_or_404()
    now = datetime.now(timezone.utc)
    if old.revoked_at or utc(old.expires_at) <= now:
        return jsonify(error='Only an active, unexpired key can be rotated.'), 409
    old.revoked_at = now
    new, token = issue_key(old.name, list(old.scopes), current_user.id, old.expires_at)
    db.session.commit()
    return jsonify(key=key_metadata(new), token=token), 201


@api_admin.get('/api/admin/api-audit')
@login_required
def audit():
    rows = ApplicationAPIAudit.query.order_by(ApplicationAPIAudit.id.desc()).limit(50).all()
    return jsonify(events=[{
        **{field: getattr(row, field) for field in ('id', 'key_name', 'method', 'path', 'status', 'request_id')},
        'created_at': utc(row.created_at).isoformat(),
    } for row in rows])
