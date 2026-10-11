"""Bearer authentication, shared validation and atomic API write transactions."""
from datetime import datetime, timedelta, timezone
from functools import wraps
from hashlib import sha256
import json
import re
from uuid import uuid4

from flask import Blueprint, abort, g, jsonify, request, current_app
from werkzeug.exceptions import HTTPException
from app import db
from models import ApplicationAPIKey, ApplicationAPIAudit, ApplicationAPIReplay, User
from ticket_insights_service import utc

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')
PUBLIC_ENDPOINTS = {'api_v1.docs', 'api_v1.openapi'}
WRITE_METHODS = {'POST', 'PATCH', 'DELETE'}


def error_response(status, message):
    response = jsonify(error={'code': status, 'message': message},
                       request_id=getattr(g, 'api_request_id', None))
    response.status_code = status
    if status == 401:
        response.headers['WWW-Authenticate'] = 'Bearer realm="Plex API"'
    return response


def iso(value):
    return utc(value).isoformat() if value else None


def timestamp(value, field):
    if not isinstance(value, str):
        abort(400, description=f'{field} must be an ISO 8601 timestamp with an offset.')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        abort(400, description=f'{field} must be an ISO 8601 timestamp with an offset.')


def integer(value, field, minimum=1, maximum=2147483647):
    if type(value) is not int or not minimum <= value <= maximum:
        abort(400, description=f'{field} must be an integer from {minimum} to {maximum}.')
    return value


def text(value, field, maximum, empty=False):
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value.strip()):
        abort(400, description=f'{field} must be text of {1 if not empty else 0}–{maximum} characters.')
    return value.strip()


def boolean(value, field):
    if type(value) is not bool:
        abort(400, description=f'{field} must be true or false.')
    return value


def query_int(name, default=None, minimum=1, maximum=2147483647):
    value = request.args.get(name)
    if value is None:
        return default
    if not re.fullmatch(r'\d+', value) or len(value) > 10:
        abort(400, description=f'{name} must be an integer.')
    return integer(int(value), name, minimum, maximum)


def query_bool(name, default=None):
    value = request.args.get(name)
    if value is None:
        return default
    if value not in {'true', 'false'}:
        abort(400, description=f'{name} must be true or false.')
    return value == 'true'


def fields(allowed, required=()):
    payload = g.api_body
    unknown = set(payload) - set(allowed)
    missing = set(required) - set(payload)
    if unknown or missing:
        abort(400, description='Invalid fields. ' + ('Unknown: ' + ', '.join(sorted(unknown)) + '. ' if unknown else '') +
              ('Required: ' + ', '.join(sorted(missing)) + '.' if missing else ''))
    if request.method == 'PATCH' and not payload:
        abort(400, description='Provide at least one field to update.')
    return payload


def require_scope(scope):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if scope not in g.api_key.scopes:
                abort(403, description=f'Required permission: {scope}.')
            return fn(*args, **kwargs)
        return wrapped
    return decorate


def paginated(query, serialize):
    page = query_int('page', 1, maximum=1000000)
    size = query_int('page_size', 50, maximum=100)
    total = query.count()
    return jsonify(data=[serialize(item) for item in query.limit(size).offset((page - 1) * size).all()],
                   meta={'page': page, 'page_size': size, 'total': total, 'pages': (total + size - 1) // size})


@api_v1.before_request
def authenticate():
    g.api_request_id = str(uuid4())
    if request.endpoint in PUBLIC_ENDPOINTS:
        return
    if 'api_key' in request.args or 'token' in request.args:
        abort(400, description='Send credentials in a request header, never a URL.')
    authorization = request.headers.get('Authorization', '')
    alternate = request.headers.get('X-API-Key', '')
    parts = authorization.split(None, 1)
    token = parts[1].strip() if len(parts) == 2 and parts[0].casefold() == 'bearer' else alternate.strip() if not authorization else ''
    if not token or len(token) > 256 or (authorization and alternate and token != alternate):
        abort(401, description='A valid Bearer token or X-API-Key header is required.')
    key = ApplicationAPIKey.query.filter_by(token_hash=sha256(token.encode()).hexdigest()).with_for_update().first()
    now = datetime.now(timezone.utc)
    owner = db.session.get(User, key.owner_id) if key and key.owner_id else None
    if not key or key.revoked_at or utc(key.expires_at) <= now or not owner or not owner.is_admin:
        abort(401, description='API key is invalid, expired or revoked.')
    if not key.rate_window or now >= utc(key.rate_window) + timedelta(minutes=1):
        key.rate_window, key.rate_count = now, 0
    if key.rate_count >= 120:
        response = error_response(429, 'Rate limit exceeded: 120 requests per minute per key.')
        response.headers['Retry-After'] = str(max(1, int((utc(key.rate_window) + timedelta(minutes=1) - now).total_seconds()) + 1))
        db.session.rollback()
        return response
    key.rate_count += 1
    key.last_used_at = now
    g.api_remaining = 120 - key.rate_count
    key_id = key.id
    db.session.commit()
    g.api_key = key
    if request.method in WRITE_METHODS:
        # Serialize writes for a key, including idempotency lookup + resource commit.
        key = ApplicationAPIKey.query.filter_by(id=key_id).populate_existing().with_for_update().first()
        if key.revoked_at or utc(key.expires_at) <= datetime.now(timezone.utc):
            abort(401, description='API key is expired or revoked.')
        g.api_key = key
        raw = request.stream.read(262145)
        if len(raw) > 262144:
            abort(413, description='JSON request body exceeds 256 KiB.')
        if raw and not request.is_json:
            abort(415, description='Use Content-Type: application/json.')
        try:
            payload = json.loads(raw) if raw else {}
        except (ValueError, UnicodeDecodeError):
            abort(400, description='Malformed JSON body.')
        if not isinstance(payload, dict):
            abort(400, description='JSON body must be an object.')
        g.api_body = payload
        if request.headers.get('Idempotency-Key'):
            if request.method != 'POST':
                abort(400, description='Idempotency-Key is supported only for POST requests.')
            identity = request.headers['Idempotency-Key']
            if not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', identity):
                abort(400, description='Idempotency-Key must be 1–128 letters, numbers, dots, underscores, colons or hyphens.')
            fingerprint = sha256((request.method + request.path + json.dumps(payload, sort_keys=True)).encode()).hexdigest()
            existing = db.session.get(ApplicationAPIReplay, (key_id, identity))
            if existing and utc(existing.created_at) + timedelta(hours=24) <= now:
                db.session.delete(existing)
                db.session.flush()
                existing = None
            if existing:
                if existing.fingerprint != fingerprint:
                    abort(409, description='This Idempotency-Key was used for a different request.')
                g.api_replay = True
                response = jsonify(existing.response)
                response.status_code = existing.status
                response.headers['Idempotency-Replayed'] = 'true'
                return response
            g.api_idempotency = (identity, fingerprint)


@api_v1.after_request
def finalize(response):
    if request.method in WRITE_METHODS and hasattr(g, 'api_key') and response.status_code < 300 and not getattr(g, 'api_replay', False):
        try:
            db.session.add(ApplicationAPIAudit(key_id=g.api_key.id, key_name=g.api_key.name,
                           method=request.method, path=request.path, status=response.status_code,
                           request_id=g.api_request_id))
            if hasattr(g, 'api_idempotency'):
                identity, fingerprint = g.api_idempotency
                # Expired replay entries are opportunistically pruned on successful keyed POSTs.
                ApplicationAPIReplay.query.filter(ApplicationAPIReplay.key_id == g.api_key.id,
                    ApplicationAPIReplay.created_at < datetime.now(timezone.utc) - timedelta(hours=24)).delete(synchronize_session=False)
                db.session.add(ApplicationAPIReplay(key_id=g.api_key.id, idempotency_key=identity,
                               fingerprint=fingerprint, response=response.get_json(), status=response.status_code))
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.error('API write transaction failed; request ID %s', g.api_request_id)
            response = error_response(500, 'The change could not be saved.')
    else:
        db.session.rollback()
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Request-ID'] = getattr(g, 'api_request_id', '')
    response.headers['X-Content-Type-Options'] = 'nosniff'
    if hasattr(g, 'api_remaining'):
        response.headers['X-RateLimit-Limit'] = '120'
        response.headers['X-RateLimit-Remaining'] = str(g.api_remaining)
    return response


@api_v1.errorhandler(Exception)
def handle_error(exc):
    db.session.rollback()
    if isinstance(exc, HTTPException):
        return error_response(exc.code, exc.description)
    current_app.logger.error('API request failed; request ID %s', getattr(g, 'api_request_id', 'unknown'))
    return error_response(500, 'An internal API error occurred.')
