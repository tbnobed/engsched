"""Snapshot-based ticket automation. No helper commits; callers own transactions."""
import bleach
import copy
import http.client
import ipaddress
import json
import re
import socket
import ssl
import subprocess
import sys
from datetime import datetime, time, timedelta, timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from flask import current_app
from sqlalchemy import text
from app import db
from models import (Ticket, TicketCategory, TicketComment, TicketFeedback, TicketGroup,
                    TicketHistory, TicketRequesterProfile, ProcessedEmail, User)
from automation_models import (AutomationAction, AutomationCondition, AutomationCustomField,
                               AutomationRule, AutomationRun, AutomationScheduledJob,
                               AutomationSettings, AutomationTicketLink, now)

TRIGGERS = ('created', 'comment_added', 'updated', 'survey_submitted', 'custom')
ANCHORS = ('created_at', 'updated_at', 'assigned_at', 'resolved_at', 'closed_at',
           'reopened_at', 'due_date', 'last_requester_comment', 'last_agent_comment')
TYPES = {
    'text': ('is', 'is not', 'contains', 'does not contain', 'matches regex', 'is empty', 'is not empty'),
    'select': ('is', 'is not', 'is one of', 'is empty'),
    'user': ('is', 'is not', 'is one of', 'is empty'),
    'number': ('equals', 'greater than', 'less than'),
    'date': ('before', 'after', 'within', 'during business hours', 'outside business hours', 'is empty'),
}
SYSTEM_FIELDS = {
    'id': 'number', 'title': 'text', 'description': 'text', 'status': 'select',
    'priority': 'number', 'category_id': 'select', 'group_id': 'select',
    'assigned_to': 'user', 'created_by': 'user', 'requester_department': 'text',
    'requester_location': 'text', 'due_date': 'date', 'created_at': 'date',
    'updated_at': 'date', 'assigned_at': 'date', 'resolved_at': 'date',
    'closed_at': 'date', 'reopened_at': 'date', 'keyword': 'text',
    'comment_author': 'select', 'survey_score': 'number', 'archived': 'select',
    'source': 'select', 'external_name': 'text', 'external_email': 'text',
    'email_notifications': 'select', 'attachment': 'text',
}
WRITABLE = {'title', 'description', 'status', 'priority', 'category_id', 'group_id',
            'assigned_to', 'created_by', 'due_date', 'archived', 'email_notifications',
            'requester_department', 'requester_location'}
ALIASES = {'group': 'group_id', 'assignee': 'assigned_to', 'requester': 'created_by',
           'category': 'category_id'}


def aware(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def field_catalog():
    fields = {key: {'label': key.replace('_', ' ').title(), 'type': typ, 'origin': 'system'}
              for key, typ in SYSTEM_FIELDS.items()}
    for field in AutomationCustomField.query.all():
        fields['custom.' + field.key] = {'label': field.label, 'type': field.data_type, 'origin': 'custom'}
    return fields


def expression(source, values):
    """A bounded recursive-descent boolean grammar; never evaluates Python."""
    if len(source) > 2000:
        raise ValueError('Expression is too long.')
    tokens = re.findall(r'\d+|and\b|or\b|not\b|[()]|\S+', source.lower())
    if len(tokens) > 200:
        raise ValueError('Expression has too many tokens.')
    index = 0

    def atom(depth=0):
        nonlocal index
        if depth > 40 or index >= len(tokens):
            raise ValueError('Incomplete or excessively nested expression.')
        token = tokens[index]
        index += 1
        if token == 'not':
            return not atom(depth + 1)
        if token == '(':
            result = disjunction(depth + 1)
            if index >= len(tokens) or tokens[index] != ')':
                raise ValueError('Missing closing parenthesis.')
            index += 1
            return result
        if not token.isdigit() or int(token) not in values:
            raise ValueError(f'Unknown condition number or token: {token}')
        return bool(values[int(token)])

    def conjunction(depth):
        nonlocal index
        result = atom(depth)
        while index < len(tokens) and tokens[index] == 'and':
            index += 1
            other = atom(depth)
            result = result and other
        return result

    def disjunction(depth):
        nonlocal index
        result = conjunction(depth)
        while index < len(tokens) and tokens[index] == 'or':
            index += 1
            other = conjunction(depth)
            result = result or other
        return result

    result = disjunction(0)
    if index != len(tokens):
        raise ValueError('Expected and/or between conditions.')
    return result


def regex_matches(pattern, value):
    """Run untrusted regex in an isolated child with a hard wall-clock deadline."""
    if not isinstance(pattern, str) or len(pattern) > 500:
        raise ValueError('Regex must be at most 500 characters.')
    if len(str(value)) > 100000:
        raise ValueError('Regex input exceeds the 100,000-character safety limit.')
    script = ('import sys,json,re,resource;'
              'resource.setrlimit(resource.RLIMIT_CPU,(1,1));'
              'resource.setrlimit(resource.RLIMIT_AS,(134217728,134217728));'
              'p,s=json.load(sys.stdin);print(int(bool(re.search(p,s,re.I))))')
    try:
        result = subprocess.run([sys.executable, '-I', '-c', script],
                                input=json.dumps([pattern, str(value)]),
                                capture_output=True, text=True, timeout=1.5, check=False)
    except subprocess.TimeoutExpired:
        raise ValueError('Regex exceeded its execution time limit.') from None
    if result.returncode != 0:
        raise ValueError('Regex is invalid or exceeded its resource limit.')
    return result.stdout.strip() == '1'


def snapshot(ticket, comment=None):
    data = {key: copy.deepcopy(getattr(ticket, key, None)) for key in SYSTEM_FIELDS
            if hasattr(Ticket, key)}
    data['custom_values'] = copy.deepcopy(ticket.custom_values or {})
    data['tags'] = list(ticket.tags or [])
    data['cc_user_ids'], data['cc_group_ids'] = list(ticket.cc_user_ids or []), list(ticket.cc_group_ids or [])
    requester = db.session.get(User, ticket.created_by)
    profile_key = ('email:' + ticket.external_email.strip().casefold()) if ticket.external_email else ('user:' + str(ticket.created_by))
    profile = db.session.get(TicketRequesterProfile, profile_key)
    data.update(requester_name=ticket.external_name or (requester.username if requester else ''),
                requester_department=profile.department if profile else '',
                requester_location=profile.location if profile else '')
    group = db.session.get(TicketGroup, ticket.group_id) if ticket.group_id else None
    assignee = db.session.get(User, ticket.assigned_to) if ticket.assigned_to else None
    category = db.session.get(TicketCategory, ticket.category_id) if ticket.category_id else None
    data.update(group=group.name if group else None, assignee=assignee.username if assignee else None,
                category=category.name if category else None)
    domain = current_app.config.get('EMAIL_DOMAIN', 'localhost:5000')
    data['ticket_url'] = f"{current_app.config.get('PREFERRED_URL_SCHEME', 'http')}://{domain}/tickets/{ticket.id}"
    data['comment_body'] = getattr(comment, 'content', getattr(comment, 'details', '')) if comment else ''
    def requester_comment(row):
        content = getattr(row, 'content', getattr(row, 'details', '')) or ''
        if isinstance(row, TicketHistory):
            return False
        if ticket.external_email and content.startswith('Email reply from:'):
            match = re.search(r'Email reply from:.*?\(([^()\s]+@[^()\s]+)\)', content)
            return bool(match and match[1].strip().casefold() == ticket.external_email.strip().casefold())
        return not ticket.external_email and row.user_id == ticket.created_by
    data['comment_author'] = ('requester' if requester_comment(comment) else 'agent') if comment else None
    data['source'] = 'email' if ticket.external_email or (ticket.id and ProcessedEmail.query.filter_by(ticket_id=ticket.id).first()) else 'web'
    feedback = db.session.get(TicketFeedback, ticket.id) if ticket.id else None
    data['survey_score'] = feedback.score if feedback else None
    for role in ('requester', 'agent'):
        for public in (False, True):
            query = TicketComment.query.filter_by(ticket_id=ticket.id)
            if public:
                query = query.filter_by(is_private=False)
            row = next((row for row in query.order_by(TicketComment.created_at.desc(), TicketComment.id.desc())
                        if requester_comment(row) == (role == 'requester')), None)
            anchor = row.created_at if row else ticket.created_at
            if role == 'agent' and not public:
                note = TicketHistory.query.filter_by(ticket_id=ticket.id, action='internal_note').order_by(
                    TicketHistory.created_at.desc(), TicketHistory.id.desc()).first()
                if note and (anchor is None or aware(note.created_at) > aware(anchor)):
                    anchor = note.created_at
            data[f'last_{role}_comment_{"public" if public else "all"}'] = anchor
    data['keyword'] = keyword_text(data)
    return data


def keyword_text(data):
    text_values = [data.get('title') or '', data.get('description') or '', data.get('comment_body') or '']
    for field in AutomationCustomField.query.filter(AutomationCustomField.data_type.in_(('text', 'select'))):
        value = (data.get('custom_values') or {}).get(field.key)
        text_values.append(str(value) if value is not None else '')
    return '\n'.join(text_values)


def value_for(data, key):
    if key.startswith('custom.'):
        return data.get('custom_values', {}).get(key[7:])
    return data.get(ALIASES.get(key, key))


def business_config():
    # No pre-existing SLA/business calendar exists in this application. Do not
    # silently invent office hours; require the explicit instance calendar.
    row = db.session.get(AutomationSettings, 1)
    if not row or not row.business_hours:
        raise ValueError('Business hours are not configured. Configure the instance calendar in Automation Rules.')
    return ZoneInfo(row.timezone), row.business_hours


def in_business(moment):
    tz, hours = business_config()
    local = aware(moment).astimezone(tz)
    interval = hours.get(str(local.weekday()))
    if not interval:
        return False
    return interval[0] <= local.strftime('%H:%M') < interval[1]


def business_offset(moment, amount, sign):
    """Consume exact elapsed seconds inside local calendar working intervals."""
    tz, hours = business_config()
    anchor = aware(moment).astimezone(timezone.utc)
    remaining = amount * 3600
    if not remaining:
        return anchor
    date = anchor.astimezone(tz).date()
    for offset in range(401):
        day = date + timedelta(days=sign * offset)
        interval = hours.get(str(day.weekday()))
        if not interval:
            continue
        start = datetime.combine(day, time.fromisoformat(interval[0]), tzinfo=tz).astimezone(timezone.utc)
        end = datetime.combine(day, time.fromisoformat(interval[1]), tzinfo=tz).astimezone(timezone.utc)
        lower = max(start, anchor) if sign > 0 else start
        upper = end if sign > 0 else min(end, anchor)
        available = max(0, (upper - lower).total_seconds())
        if remaining <= available:
            result = lower + timedelta(seconds=remaining) if sign > 0 else upper - timedelta(seconds=remaining)
            if abs((result - anchor).total_seconds()) > 400 * 86400:
                break
            return result
        remaining -= available
    raise ValueError('Business-hours offset exceeds 400 calendar days.')


def scheduled_moment(condition, data):
    key = condition.anchor_field
    if key in ('last_requester_comment', 'last_agent_comment'):
        key += '_public' if condition.public_only else '_all'
    anchor = aware(data.get(key))
    if not anchor:
        return None
    sign = 1 if condition.direction == 'after' else -1
    if condition.unit == 'business hours':
        return business_offset(anchor, condition.amount, sign) if condition.amount else anchor
    return anchor + sign * timedelta(**{condition.unit: condition.amount})


def date_range(label, moment):
    tz = business_config()[0] if label in ('during business hours', 'outside business hours') else ZoneInfo(
        (db.session.get(AutomationSettings, 1).timezone if db.session.get(AutomationSettings, 1) else 'UTC'))
    local = moment.astimezone(tz)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    rolling = re.fullmatch(r'last (day|7 days|14 days|30 days|60 days|90 days)', str(label))
    if rolling:
        return local - timedelta(days=1 if rolling[1] == 'day' else int(rolling[1].split()[0])), local
    match = re.fullmatch(r'(this|last|end of) (week|month|quarter|year)', str(label))
    if not match:
        raise ValueError('Unsupported relative date value.')
    mode, unit = match.groups()
    if unit == 'week':
        start -= timedelta(days=start.weekday())
        end = start + timedelta(days=7)
        if mode == 'last':
            start, end = start - timedelta(days=7), start
    else:
        month = 1 if unit == 'year' else ((start.month - 1) // 3 * 3 + 1 if unit == 'quarter' else start.month)
        start = start.replace(month=month, day=1)
        count = {'month': 1, 'quarter': 3, 'year': 12}[unit]
        absolute = start.year * 12 + start.month - 1
        def at(number):
            return start.replace(year=number // 12, month=number % 12 + 1)
        end = at(absolute + count)
        if mode == 'last':
            start, end = at(absolute - count), start
    if mode == 'end of':
        start = end - timedelta(days=1)
    return start, end


def regular_match(condition, data, previous, moment):
    key, mode, op = condition.field_key, condition.value_type, condition.operator
    value, old = value_for(data, key), value_for(previous or {}, key)
    if mode == 'any_change':
        return old != value
    if mode in ('updated_from', 'updated_to') and old == value:
        return False
    if mode == 'updated_from':
        value = old
    target = condition.value
    if op == 'is empty':
        return value is None or value == '' or value == []
    if op == 'is not empty':
        return value is not None and value != '' and value != []
    typ = field_catalog()[key]['type']
    if typ == 'date':
        if value is None:
            return False
        date = aware(value)
        if op in ('during business hours', 'outside business hours') or target in ('during business hours', 'outside business hours'):
            inside = in_business(date)
            label = op if op in ('during business hours', 'outside business hours') else target
            return inside if label == 'during business hours' else not inside
        if isinstance(target, str) and (target.startswith(('last ', 'this ', 'end of '))):
            start, end = date_range(target, moment)
            if op == 'before':
                return date < start
            if op == 'after':
                return date >= end
            return start <= date < end
        if op == 'within':
            if not isinstance(target, list) or len(target) != 2:
                raise ValueError('Within requires a relative period or [start, end].')
            return aware(target[0]) <= date <= aware(target[1])
        return date < aware(target) if op == 'before' else date > aware(target)
    if op in ('equals', 'greater than', 'less than'):
        if value is None:
            return False
        left, right = float(value), float(target)
        return left == right if op == 'equals' else (left > right if op == 'greater than' else left < right)
    if op == 'is one of':
        return str(value).casefold() in [str(v).casefold() for v in target]
    left, right = str(value if value is not None else '').casefold(), str(target if target is not None else '').casefold()
    if op == 'matches regex':
        return regex_matches(str(target), value or '')
    if op in ('is', 'is not'):
        return (left == right) if op == 'is' else (left != right)
    return (right in left) if op == 'contains' else (right not in left)


def evaluate(rule, data, previous=None, moment=None):
    moment = moment or now()
    results, future, errors = {}, [], []
    for condition in rule.conditions:
        try:
            if condition.kind == 'time_based':
                run_at = scheduled_moment(condition, data)
                result = bool(run_at and run_at <= moment)
                if run_at and run_at > moment:
                    future.append(run_at)
            else:
                result = regular_match(condition, data, previous, moment)
            results[condition.number] = result
        except Exception as exc:
            errors.append({'condition': condition.number, 'error': str(exc)})
            results[condition.number] = False
    if rule.condition_logic == 'custom':
        matched = expression(rule.custom_expression, results)
    elif rule.condition_logic == 'any':
        matched = any(results.values())
    else:
        matched = all(results.values())
    return {'matched': matched and not errors, 'conditions': results, 'future': sorted(set(future)), 'errors': errors}


def render(value, data, errors):
    if not isinstance(value, str):
        return value
    def replacement(match):
        key = match[1].strip()
        custom_key = key if key.startswith('custom.') else 'custom.' + key
        known_custom = custom_key in field_catalog()
        known = key in data or known_custom
        if not known:
            errors.append({'error': 'undefined variable', 'variable': key})
            return ''
        result = value_for(data, custom_key if key not in data and known_custom else key)
        if result is None or result == '':
            errors.append({'error': 'null value', 'variable': key})
            return ''
        return result.isoformat() if isinstance(result, datetime) else str(result)
    return re.sub(r'{{\s*([^{}]+?)\s*}}', replacement, value)


def render_config(value, data, errors):
    if isinstance(value, dict):
        return {k: render_config(v, data, errors) for k, v in value.items()}
    if isinstance(value, list):
        return [render_config(v, data, errors) for v in value]
    return render(value, data, errors)


def validate_webhook(url, headers=None):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.fragment:
        raise ValueError('Webhook requires HTTPS without credentials or fragments.')
    if parts.port not in (None, 443):
        raise ValueError('Webhook must use port 443.')
    if len(url) > 2048:
        raise ValueError('Webhook URL is too long.')
    for key, value in (headers or {}).items():
        if not isinstance(key, str) or not isinstance(value, str) or len(key) > 200 or len(value) > 8000:
            raise ValueError('Webhook header names and values must be bounded strings.')
        if not re.fullmatch(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", key):
            raise ValueError('Invalid webhook header name.')
        if key.lower() in ('host', 'content-length', 'transfer-encoding', 'connection') or '\r' in key + value or '\n' in key + value:
            raise ValueError('Unsafe webhook header.')
    return parts


def webhook_post(url, headers, payload):
    parts = validate_webhook(url, headers)
    addresses = {row[4][0] for row in socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(address).is_global or address == '168.63.129.16' for address in addresses):
        raise ValueError('Webhook destination resolves to a private, metadata, or non-public address.')
    # Connect only to the address validated above, not a second DNS lookup.
    address = sorted(addresses)[0]
    connection = http.client.HTTPSConnection(parts.hostname, 443, timeout=8)
    sock = socket.create_connection((address, 443), timeout=8)
    try:
        connection.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=parts.hostname)
        body = json.dumps(payload, default=str).encode()
        if len(body) > 1024 * 1024:
            raise ValueError('Webhook payload exceeds 1 MiB.')
        connection.request('POST', parts.path + ('?' + parts.query if parts.query else ''),
                           body=body, headers={**headers, 'Content-Type': 'application/json'})
        response = connection.getresponse()
        response.read(4096)
        # http.client never follows redirects.
        if not 200 <= response.status < 300:
            raise ValueError(f'Webhook returned HTTP {response.status}; redirects are disabled.')
    finally:
        connection.close()
        sock.close()


def set_field(ticket, key, value, actor):
    from ticket_groups import apply_assignment
    key = ALIASES.get(key, key)
    if key in ('requester_department', 'requester_location'):
        if not isinstance(value, str) or len(value) > 100:
            raise ValueError('Requester department/location must be at most 100 characters.')
        profile_key = 'email:' + ticket.external_email.strip().casefold() if ticket.external_email else f'user:{ticket.created_by}'
        profile = db.session.get(TicketRequesterProfile, profile_key)
        if not profile:
            profile = TicketRequesterProfile(key=profile_key, department='', location='')
            db.session.add(profile)
        setattr(profile, 'department' if key == 'requester_department' else 'location', value)
        return
    if key.startswith('custom.'):
        field = db.session.get(AutomationCustomField, key[7:])
        if not field:
            raise ValueError('Unknown custom field.')
        if field.data_type == 'number' and value is not None:
            value = float(value)
        elif field.data_type == 'date' and value:
            value = aware(value).isoformat()
        elif field.data_type == 'select' and value not in (None, '') and value not in field.choices:
            raise ValueError('Invalid custom field choice.')
        elif field.data_type in ('text', 'select') and value is not None:
            value = str(value)
        ticket.custom_values = {**(ticket.custom_values or {}), field.key: value}
        return
    if key not in WRITABLE:
        raise ValueError(f'Unsupported or read-only system field: {key}. Subcategory, site and channel are not native fields.')
    if key in ('group_id', 'assigned_to'):
        previous_assignee = ticket.assigned_to
        if key == 'group_id' and isinstance(value, dict) and set(value) == {'group_name'}:
            group = TicketGroup.query.filter_by(name=value['group_name'], enabled=True).first()
            if not group:
                raise ValueError(f"Configured group '{value['group_name']}' does not exist or is disabled.")
            value = group.id
        apply_assignment(ticket, value if key == 'group_id' else ticket.group_id,
                         value if key == 'assigned_to' else ticket.assigned_to, actor_id=actor)
        if ticket.assigned_to and previous_assignee != ticket.assigned_to:
            ticket.assigned_at = now()
        return
    if key == 'status' and value not in ('open', 'in_progress', 'pending', 'resolved', 'closed'):
        raise ValueError('Invalid status. New maps to open; Awaiting Input maps to pending.')
    if key == 'priority':
        value = min(3, (ticket.priority or 0) + 1) if value == 'raise_one' else int(value)
        if value not in range(4):
            raise ValueError('Priority must be 0–3; Critical maps to Urgent (3).')
    if key in ('category_id', 'created_by'):
        model = TicketCategory if key == 'category_id' else User
        value = int(value)
        if not db.session.get(model, value):
            raise ValueError(f'{key} does not exist.')
    if key == 'due_date':
        value = aware(value) if value else None
    if key in ('title', 'description'):
        if not isinstance(value, str) or not value.strip() or (key == 'title' and len(value) > 200):
            raise ValueError(f'{key} is required (title max 200 characters).')
        if key == 'description':
            value = bleach.clean(value, strip=True)
    if key in ('archived', 'email_notifications') and not isinstance(value, bool):
        raise ValueError(f'{key} must be a boolean.')
    if key == 'status' and value != ticket.status:
        db.session.add(TicketHistory(ticket=ticket, user_id=actor, action='status_changed',
                                     details=f'Status changed from {ticket.status} to {value}'))
        anchor = {'resolved': 'resolved_at', 'closed': 'closed_at'}.get(value)
        if value == 'open' and ticket.status in ('closed', 'resolved'):
            anchor = 'reopened_at'
        if anchor:
            setattr(ticket, anchor, now())
    setattr(ticket, key, value)


def recipients(config, ticket):
    from ticket_groups import resolved_user_ids
    found = set()
    for selection in config:
        kind = selection.get('kind')
        if kind == 'user':
            found.add(int(selection['id']))
        elif kind == 'group':
            found.update(resolved_user_ids(int(selection['id'])))
        elif kind == 'requester':
            # External tickets use an internal proxy creator, not an internal requester.
            if not ticket.external_email:
                found.add(ticket.created_by)
        elif kind == 'assignee' and ticket.assigned_to:
            found.add(ticket.assigned_to)
        elif kind == 'ticket_group':
            found.update(resolved_user_ids(ticket.group_id))
        elif kind == 'group_manager':
            group = db.session.get(TicketGroup, ticket.group_id) if ticket.group_id else None
            if group and group.manager_user_id:
                found.add(group.manager_user_id)
        elif kind == 'cc':
            found.update(ticket.cc_user_ids or [])
            for group_id in ticket.cc_group_ids or []:
                found.update(resolved_user_ids(group_id))
        elif kind not in ('assignee', 'group_manager'):
            raise ValueError('Notification recipients must be internal users or supported group selectors.')
    return User.query.filter(User.id.in_(found)).all() if found else []


def execute_action(action, ticket, rule, data, errors):
    config = render_config(action.config, data, errors)
    actor = rule.created_by or ticket.created_by
    if action.type == 'update_record':
        for key, value in config.get('fields', {}).items():
            set_field(ticket, key, value, actor)
        for operation in config.get('cc', []):
            kind, member_id = operation['kind'], int(operation['id'])
            model = User if kind == 'user' else TicketGroup
            if not db.session.get(model, member_id):
                raise ValueError('CC member does not exist.')
            attr = 'cc_user_ids' if kind == 'user' else 'cc_group_ids'
            members = set(getattr(ticket, attr) or [])
            members.add(member_id) if operation['operation'] == 'add' else members.discard(member_id)
            setattr(ticket, attr, sorted(members))
    elif action.type == 'add_tag':
        tag = str(config.get('tag', '')).strip()
        if not tag or len(tag) > 100:
            raise ValueError('Tag must contain 1–100 characters.')
        ticket.tags = sorted(set(ticket.tags or []) | {tag})
    elif action.type == 'add_comment':
        body = config.get('body', '').strip()
        if not body:
            raise ValueError('Comment body is required.')
        db.session.add(TicketComment(ticket_id=ticket.id, user_id=actor,
                                     content=bleach.clean(body, strip=True), is_private=config.get('private', False)))
    elif action.type == 'send_notification':
        from email_utils import send_email
        from markupsafe import escape
        users = recipients(config.get('recipients', []), ticket)
        if not users:
            raise ValueError('Notification resolved to no internal recipients.')
        if config.get('template'):
            raise ValueError('This application has no reusable notification-template catalog. Provide subject and body.')
        if not config.get('subject') or not config.get('body'):
            raise ValueError('Notification requires subject and body.')
        for user in users:
            if not send_email(to_emails=[user.email], subject=config['subject'],
                              html_content='<p>' + str(escape(config['body'])).replace('\n', '<br>') + '</p>'):
                raise ValueError(f'Notification delivery failed for internal user {user.id}.')
    elif action.type == 'create_record':
        fields = config.get('fields', {})
        required = ('title', 'description', 'category_id', 'created_by')
        if any(fields.get(key) in (None, '') for key in required):
            raise ValueError('Linked ticket requires title, description, category_id and created_by.')
        linked = Ticket(status='open', priority=0)
        for key, value in fields.items():
            set_field(linked, key, value, actor)
        db.session.add(linked)
        db.session.flush()
        db.session.add(AutomationTicketLink(ticket_id=ticket.id, linked_ticket_id=linked.id))
        config['created_ticket_id'] = linked.id
    elif action.type == 'webhook':
        webhook_post(config['url'], config.get('headers', {}),
                     {'ticket': data, 'rule': {'id': rule.id, 'name': rule.name}})
    else:
        raise ValueError('Unsupported action type.')
    db.session.add(TicketHistory(ticket_id=ticket.id, user_id=actor, action='automation',
                                 details=f"Automation '{rule.name}' executed {action.type}: " +
                                 json.dumps({k: v for k, v in config.items() if k not in ('headers', 'body')}, default=str)[:3000]))
    return {'action_id': action.id, 'type': action.type, 'result': 'executed'}


def lock_jobs():
    if db.session.get_bind().dialect.name == 'postgresql':
        db.session.execute(text('SELECT pg_advisory_xact_lock(72419034)'))


def schedule(rule, ticket_id, future, errors):
    lock_jobs()
    current = AutomationScheduledJob.query.filter_by(rule_id=rule.id, ticket_id=ticket_id, status='pending').first()
    target = min(future) if future else None
    if current and aware(current.run_at) == target:
        return
    if current:
        current.status = 'cancelled'
        db.session.flush()
    if not target:
        return
    if AutomationScheduledJob.query.filter_by(status='pending').count() >= 5000:
        errors.append({'error': 'pending job cap reached', 'limit': 5000})
        current_app.logger.error('Automation pending job overflow rule=%s ticket=%s', rule.id, ticket_id)
        settings = db.session.get(AutomationSettings, 1)
        if settings is None:
            settings = AutomationSettings(id=1)
            db.session.add(settings)
        if not settings.overflow_alert_at or aware(settings.overflow_alert_at) < now() - timedelta(hours=1):
            from email_utils import send_email
            admins = User.query.filter_by(is_admin=True).all()
            if admins:
                sent = send_email(to_emails=[user.email for user in admins], subject='Automation pending job limit reached',
                                  html_content='<p>The 5,000 pending automation jobs limit was reached. Review Automation Rules run logs.</p>')
                if not sent:
                    errors.append({'error': 'admin overflow alert delivery failed'})
            settings.overflow_alert_at = now()
        return
    db.session.add(AutomationScheduledJob(rule_id=rule.id, ticket_id=ticket_id, run_at=target))


def run_rule(rule, ticket, event_name, data, previous=None, reschedule=True):
    result = evaluate(rule, data, previous)
    run = AutomationRun(rule_id=rule.id, rule_name=rule.name, ticket_id=ticket.id,
                        trigger_event=event_name, matched=result['matched'], errors=result['errors'],
                        actions_executed=[])
    db.session.add(run)
    errors, executed = list(result['errors']), []
    if reschedule:
        schedule(rule, ticket.id, result['future'], errors)
    if result['matched']:
        for action in rule.actions:
            try:
                # Each failed action rolls back only its own database work.
                with db.session.begin_nested():
                    outcome = execute_action(action, ticket, rule, data, errors)
                    db.session.flush()
                executed.append(outcome)
            except Exception as exc:
                errors.append({'action_id': action.id, 'type': action.type, 'error': str(exc)})
    run.actions_executed, run.errors, run.finished_at = executed, errors, now()
    return run


def anchor_moments(rule, data):
    moments, errors = [], []
    for condition in rule.conditions:
        if condition.kind == 'time_based':
            try:
                moment = scheduled_moment(condition, data)
                if moment:
                    moments.append(moment)
            except Exception as exc:
                errors.append({'condition': condition.number, 'error': str(exc)})
    return moments, errors


def event_pass(ticket, event_name, data, previous=None):
    rules = AutomationRule.query.filter_by(active=True).order_by(AutomationRule.position, AutomationRule.id).all()
    for rule in rules:
        matches = rule.trigger == event_name or (rule.trigger == 'custom' and event_name in rule.custom_triggers)
        # Scheduled rules keep their anchors fresh on every ticket mutation,
        # regardless of which event originally created their timer.
        pending = AutomationScheduledJob.query.filter_by(rule_id=rule.id, ticket_id=ticket.id, status='pending').first()
        if matches:
            run_rule(rule, ticket, event_name, data, previous)
        elif pending:
            moments, errors = anchor_moments(rule, data)
            future = [moment for moment in moments if moment > now()]
            # A different event maintains timers, not the rule's ordinary
            # trigger. Only run now if its timer actually became due/past.
            if not future and moments and not errors:
                run_rule(rule, ticket, 'anchor_changed', data, previous)
            else:
                schedule(rule, ticket.id, future, errors)
                if errors:
                    db.session.add(AutomationRun(rule_id=rule.id, rule_name=rule.name, ticket_id=ticket.id,
                                                trigger_event='rescheduled', matched=False, errors=errors,
                                                actions_executed=[], finished_at=now()))
    maintain_action_anchors(ticket, data, rules)


def maintain_action_anchors(ticket, data, rules=None):
    """Anchor housekeeping only: never execute a second rule from an action."""
    db.session.flush()
    current = snapshot(ticket)
    anchor_keys = [key for key in ANCHORS if not key.startswith('last_')] + [
        f'last_{role}_comment_{visibility}' for role in ('requester', 'agent') for visibility in ('public', 'all')]
    if any(current.get(key) != data.get(key) for key in anchor_keys):
        if rules is None:
            rules = AutomationRule.query.filter_by(active=True).all()
        for rule in rules:
            if AutomationScheduledJob.query.filter_by(rule_id=rule.id, ticket_id=ticket.id, status='pending').first():
                moments, errors = anchor_moments(rule, current)
                future = [moment for moment in moments if moment > now()]
                schedule(rule, ticket.id, future, errors)
                if errors:
                    db.session.add(AutomationRun(rule_id=rule.id, rule_name=rule.name, ticket_id=ticket.id,
                                                trigger_event='rescheduled', matched=False, errors=errors,
                                                actions_executed=[], finished_at=now()))


def process_scheduled_jobs():
    from app import app
    with app.app_context():
        db.session.info['automation_suppressed'] = True
        try:
            lock_jobs()
            jobs = AutomationScheduledJob.query.filter_by(status='pending').filter(
                AutomationScheduledJob.run_at <= now()).order_by(AutomationScheduledJob.run_at).with_for_update(skip_locked=True).limit(100).all()
            for job in jobs:
                rule, ticket = db.session.get(AutomationRule, job.rule_id), db.session.get(Ticket, job.ticket_id)
                job.status = 'done' if rule and rule.active and ticket else 'cancelled'
                db.session.flush()
                if job.status == 'done':
                    data = snapshot(ticket)
                    run_rule(rule, ticket, 'scheduled', data)
                    maintain_action_anchors(ticket, data)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Automation worker failed')
        finally:
            db.session.info.pop('automation_suppressed', None)
            db.session.remove()
