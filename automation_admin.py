"""Admin-only writes and manager-readable automation settings and audit views."""
import copy
import json
import re
from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from app import db
from models import Ticket, TicketGroup, User
from ticket_groups import can_manage_groups
from automation_models import (AutomationAction, AutomationCondition, AutomationCustomField,
                               AutomationRule, AutomationRun, AutomationScheduledJob,
                               AutomationSettings, now)
from automation_engine import (ANCHORS, SYSTEM_FIELDS, TRIGGERS, TYPES, WRITABLE, evaluate,
                               expression, field_catalog, regex_matches, render_config,
                               snapshot, validate_webhook)

automation = Blueprint('automation', __name__)
CONDITION_KEYS = ('number', 'kind', 'field_key', 'value_type', 'operator', 'value',
                  'amount', 'unit', 'direction', 'anchor_field', 'public_only')
ACTION_TYPES = ('update_record', 'add_tag', 'add_comment', 'send_notification', 'create_record', 'webhook')


def permission(write=False):
    if not current_user.is_admin and (write or not can_manage_groups()):
        abort(403)


def serialize(rule):
    return {
        'name': rule.name or '', 'description': rule.description or '', 'active': bool(rule.active),
        'position': rule.position or 0, 'trigger': rule.trigger or 'created',
        'custom_triggers': rule.custom_triggers or [], 'scope': rule.scope or 'ticket',
        'condition_logic': rule.condition_logic or 'all', 'custom_expression': rule.custom_expression or '',
        'conditions': [{key: getattr(row, key) for key in CONDITION_KEYS} for row in rule.conditions],
        'actions': [{'type': row.type, 'position': row.position, 'config': copy.deepcopy(row.config)} for row in rule.actions],
    }


def integer(value, name, minimum=0, maximum=1000000):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer between {minimum} and {maximum}.')
    return value


def validate_action(kind, config, catalog):
    if kind not in ACTION_TYPES or not isinstance(config, dict):
        raise ValueError('Select a supported action and provide an object configuration.')
    if kind in ('update_record', 'create_record'):
        fields = config.get('fields', {})
        if not isinstance(fields, dict) or (not fields and not config.get('cc')):
            raise ValueError('Update/create requires fields or CC operations.')
        for key in fields:
            if key not in WRITABLE and not (key.startswith('custom.') and key in catalog):
                raise ValueError(f'Field {key} is unsupported or read-only. No native site, subcategory or source/channel exists.')
        if kind == 'create_record' and any(key not in fields for key in ('title', 'description', 'category_id', 'created_by')):
            raise ValueError('Linked tickets require title, description, category_id and created_by.')
        for operation in config.get('cc', []):
            if not isinstance(operation, dict) or operation.get('kind') not in ('user', 'group') or operation.get('operation') not in ('add', 'remove'):
                raise ValueError('CC operations require kind user/group, id and operation add/remove.')
            integer(operation.get('id'), 'CC member ID', 1)
    elif kind == 'add_tag':
        if not isinstance(config.get('tag'), str) or not config['tag'].strip():
            raise ValueError('Tag text is required.')
    elif kind == 'add_comment':
        if not isinstance(config.get('body'), str) or not config['body'].strip():
            raise ValueError('Comment body is required.')
        if not isinstance(config.get('private', False), bool):
            raise ValueError('Comment private flag must be a boolean.')
    elif kind == 'send_notification':
        if config.get('template'):
            raise ValueError('There is no existing notification template catalog. Enter subject and body.')
        if not config.get('subject') or not config.get('body'):
            raise ValueError('Notification subject and body are required.')
        if not isinstance(config.get('recipients'), list) or not config['recipients']:
            raise ValueError('Select internal notification recipients.')
        for recipient in config['recipients']:
            if not isinstance(recipient, dict) or set(recipient) - {'kind', 'id'}:
                raise ValueError('Free-text addresses are prohibited.')
            if recipient.get('kind') not in ('user', 'group', 'requester', 'assignee', 'ticket_group', 'group_manager', 'cc'):
                raise ValueError('Only internal users or group selectors are allowed.')
            if recipient['kind'] in ('user', 'group'):
                integer(recipient.get('id'), 'Recipient ID', 1)
                model = User if recipient['kind'] == 'user' else TicketGroup
                if db.session.get(model, recipient['id']) is None:
                    raise ValueError('Notification recipient does not exist.')
    elif kind == 'webhook':
        if not isinstance(config.get('url'), str) or '{{' in config['url']:
            raise ValueError('Webhook requires a static HTTPS URL; variables are allowed in headers only.')
        if not isinstance(config.get('headers', {}), dict):
            raise ValueError('Webhook headers must be an object.')
        validate_webhook(config['url'], config.get('headers', {}))


def validate_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError('Rule must be a JSON object.')
    if not isinstance(payload.get('name'), str) or not 1 <= len(payload['name'].strip()) <= 200:
        raise ValueError('Name is required (maximum 200 characters).')
    if payload.get('trigger') not in TRIGGERS or payload.get('scope', 'ticket') != 'ticket':
        raise ValueError('Select a supported trigger and ticket scope.')
    if not isinstance(payload.get('active', False), bool):
        raise ValueError('Active must be a boolean.')
    integer(payload.get('position', 0), 'Position', 0)
    custom = payload.get('custom_triggers', [])
    if not isinstance(custom, list) or any(t not in ('created', 'updated', 'comment_added') for t in custom):
        raise ValueError('Custom triggers can only contain created, updated and comment_added.')
    if payload['trigger'] == 'custom' and not custom:
        raise ValueError('Select at least one custom trigger.')
    if payload.get('condition_logic') not in ('all', 'any', 'custom'):
        raise ValueError('Select all, any or custom condition logic.')
    conditions, actions = payload.get('conditions', []), payload.get('actions', [])
    if not isinstance(conditions, list) or not isinstance(actions, list) or len(conditions) > 100 or not 1 <= len(actions) <= 50:
        raise ValueError('Rules support up to 100 conditions and require 1–50 actions.')
    catalog, timed, change = field_catalog(), False, False
    numbers = []
    for condition in conditions:
        if not isinstance(condition, dict) or set(condition) - set(CONDITION_KEYS):
            raise ValueError('Invalid condition properties.')
        number = integer(condition.get('number'), 'Condition number', 1, 100)
        numbers.append(number)
        if condition.get('kind') == 'time_based':
            timed = True
            amount = integer(condition.get('amount'), 'Time amount', 0, 400 * 24 * 60)
            unit = condition.get('unit')
            if unit not in ('minutes', 'hours', 'days', 'business hours'):
                raise ValueError('Invalid time unit.')
            days = amount / {'minutes': 1440, 'hours': 24, 'days': 1, 'business hours': 24}[unit]
            if days > 400:
                raise ValueError('Time offsets cannot exceed 400 days.')
            if condition.get('direction') not in ('before', 'after') or condition.get('anchor_field') not in ANCHORS:
                raise ValueError('Select a valid direction and anchor.')
            if not isinstance(condition.get('public_only', True), bool):
                raise ValueError('Public-comments flag must be a boolean.')
        elif condition.get('kind') == 'regular':
            key, mode, op = condition.get('field_key'), condition.get('value_type'), condition.get('operator')
            if key not in catalog:
                raise ValueError(f'Unsupported field: {key}. Custom fields must be defined first; no native site, subcategory or source/channel exists.')
            if mode not in ('current_value', 'any_change', 'updated_from', 'updated_to'):
                raise ValueError('Invalid value type.')
            if mode != 'current_value':
                change = True
                if payload['trigger'] not in ('updated', 'custom'):
                    raise ValueError('Change/from/to conditions require an updated or custom trigger.')
            if op not in TYPES[catalog[key]['type']]:
                raise ValueError(f'Operator {op} is invalid for {key}.')
            if op == 'is one of' and not isinstance(condition.get('value'), list):
                raise ValueError('Is one of requires a JSON list of values.')
            if op == 'matches regex':
                regex_matches(condition.get('value'), '')
            if op in ('equals', 'greater than', 'less than') and mode != 'any_change':
                try:
                    float(condition.get('value'))
                except (TypeError, ValueError):
                    raise ValueError('Numeric conditions require a number.') from None
        else:
            raise ValueError('Condition kind must be regular or time_based.')
    if sorted(numbers) != list(range(1, len(numbers) + 1)):
        raise ValueError('Conditions must be numbered consecutively from 1.')
    if timed and change:
        raise ValueError('Time-based conditions cannot be mixed with any_change, updated_from or updated_to: scheduled runs have no original change event to compare.')
    if payload['condition_logic'] == 'custom':
        expression(payload.get('custom_expression', ''), dict.fromkeys(numbers, False))
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError('Invalid action.')
        validate_action(action.get('type'), action.get('config'), catalog)
    return payload


def assign(rule, payload):
    for key in ('name', 'description', 'active', 'position', 'trigger', 'custom_triggers',
                'scope', 'condition_logic', 'custom_expression'):
        if key in payload:
            setattr(rule, key, payload[key])
    rule.name = rule.name.strip()
    # Delete old numbered children before inserting replacements (unique constraint).
    rule.conditions.clear()
    rule.actions.clear()
    if rule.id:
        db.session.flush()
    rule.conditions = [AutomationCondition(**{key: value for key, value in item.items() if key in CONDITION_KEYS})
                       for item in payload['conditions']]
    rule.actions = [AutomationAction(type=item['type'], config=item['config'], position=index)
                    for index, item in enumerate(payload['actions'], 1)]
    if rule.id:
        AutomationScheduledJob.query.filter_by(rule_id=rule.id, status='pending').update({'status': 'cancelled'})


@automation.get('/admin/automation')
@login_required
def index():
    permission()
    query = AutomationRule.query
    q, active, trigger = request.args.get('q', '').strip(), request.args.get('active', 'all'), request.args.get('trigger', '')
    if q:
        query = query.filter(db.or_(AutomationRule.name.ilike(f'%{q}%'), AutomationRule.description.ilike(f'%{q}%')))
    if active in ('true', 'false'):
        query = query.filter_by(active=active == 'true')
    if trigger in TRIGGERS:
        query = query.filter_by(trigger=trigger)
    stats = {}
    for rule_id, last, count in db.session.query(
            AutomationRun.rule_id, func.max(AutomationRun.started_at),
            func.count(AutomationRun.id).filter(AutomationRun.started_at >= now() - timedelta(days=7))
    ).filter(AutomationRun.matched.is_(True)).group_by(AutomationRun.rule_id):
        stats[rule_id] = {'last': last, 'count': count}
    settings = db.session.get(AutomationSettings, 1)
    return render_template('admin/automation/index.html', rules=query.order_by(AutomationRule.position, AutomationRule.id).all(),
                           stats=stats, q=q, active=active, trigger=trigger, triggers=TRIGGERS,
                           settings=settings, custom_fields=AutomationCustomField.query.order_by(AutomationCustomField.key).all())


@automation.route('/admin/automation/new', methods=['GET', 'POST'])
@automation.route('/admin/automation/<int:rule_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(rule_id=None):
    permission(write=request.method == 'POST' or rule_id is None)
    rule = db.get_or_404(AutomationRule, rule_id) if rule_id else AutomationRule(
        active=True, position=0, name='', trigger='created', scope='ticket', condition_logic='all')
    payload = serialize(rule)
    clone = request.args.get('clone') == '1'
    if clone:
        permission(write=True)
        payload['name'], payload['active'] = 'Copy of ' + payload['name'], False
    if request.method == 'POST':
        try:
            if len(request.form.get('definition', '')) > 200000:
                raise ValueError('Rule definition is too large.')
            payload = json.loads(request.form.get('definition', '{}'))
            validate_payload(payload)
            if clone or not rule_id:
                rule = AutomationRule(created_by=current_user.id)
            assign(rule, payload)
            db.session.add(rule)
            db.session.commit()
            flash('Automation rule saved.', 'success')
            return redirect(url_for('automation.index'))
        except (ValueError, TypeError, KeyError) as exc:
            db.session.rollback()
            flash(str(exc), 'danger')
    return render_template('admin/automation/edit.html', rule=rule, definition=payload, clone=clone,
                           fields=field_catalog(), operators=TYPES, anchors=ANCHORS, triggers=TRIGGERS,
                           user_options=[{'id': row.id, 'name': row.username} for row in User.query.order_by(User.username)],
                           group_options=[{'id': row.id, 'name': row.name} for row in TicketGroup.query.order_by(TicketGroup.name)])


@automation.post('/admin/automation/<int:rule_id>/change')
@login_required
def change(rule_id):
    permission(write=True)
    rule = db.get_or_404(AutomationRule, rule_id)
    try:
        if request.form.get('operation') == 'delete':
            db.session.delete(rule)
        elif request.form.get('operation') == 'toggle':
            rule.active = not rule.active
            if not rule.active:
                AutomationScheduledJob.query.filter_by(rule_id=rule.id, status='pending').update({'status': 'cancelled'})
        elif request.form.get('operation') == 'position':
            rule.position = integer(int(request.form.get('position', '')), 'Position')
        else:
            raise ValueError('Unknown operation.')
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return redirect(url_for('automation.index'))


@automation.post('/admin/automation/validate-expression')
@login_required
def validate_expression():
    permission()
    payload = request.get_json() or {}
    try:
        expression(payload.get('expression', ''), {int(n): False for n in payload.get('numbers', [])})
        return jsonify(valid=True)
    except (ValueError, TypeError) as exc:
        return jsonify(valid=False, error=str(exc)), 400


@automation.post('/admin/automation/preview')
@login_required
def preview():
    permission()
    try:
        body = request.get_json() or {}
        payload = validate_payload(body.get('definition'))
        ticket_id = integer(body.get('ticket_id'), 'Ticket ID', 1)
        ticket = db.get_or_404(Ticket, ticket_id)
        # Transient ORM objects are never attached to the session.
        rule = AutomationRule(**{key: payload[key] for key in (
            'name', 'trigger', 'condition_logic')})
        rule.custom_expression = payload.get('custom_expression', '')
        rule.conditions = [AutomationCondition(**row) for row in payload['conditions']]
        data = snapshot(ticket)
        previous = body.get('previous')
        if previous is not None and not isinstance(previous, dict):
            raise ValueError('Previous snapshot must be an object.')
        result = evaluate(rule, data, previous or data)
        if any(row.get('value_type') in ('any_change', 'updated_from', 'updated_to') for row in payload['conditions']) and previous is None:
            result['errors'].append({'error': 'No previous event snapshot supplied: change conditions compare current data to itself.'})
        actions = []
        for action in payload['actions']:
            actions.append({'type': action['type'], 'config': render_config(action['config'], data, result['errors']),
                            'would_run': result['matched']})
        return jsonify(**result, actions=actions)
    except (ValueError, TypeError, KeyError) as exc:
        return jsonify(error=str(exc)), 400


@automation.get('/admin/automation/tickets')
@login_required
def ticket_choices():
    permission()
    search = request.args.get('q', '').strip()[:200]
    query = Ticket.query
    if search:
        filters = [Ticket.title.ilike(f'%{search}%')]
        if search.isdigit():
            filters.append(Ticket.id == int(search))
        query = query.filter(db.or_(*filters))
    return jsonify(tickets=[{'id': ticket.id, 'title': ticket.title}
                            for ticket in query.order_by(Ticket.id.desc()).limit(20)])


@automation.get('/admin/automation/runs')
@login_required
def runs():
    permission()
    query = AutomationRun.query
    rule_id, ticket_id = request.args.get('rule_id', type=int), request.args.get('ticket_id', type=int)
    if rule_id:
        query = query.filter_by(rule_id=rule_id)
    if ticket_id:
        query = query.filter_by(ticket_id=ticket_id)
    page = query.order_by(AutomationRun.id.desc()).paginate(page=max(1, request.args.get('page', 1, type=int)), per_page=50)
    return render_template('admin/automation/runs.html', page=page, rule_id=rule_id, ticket_id=ticket_id)


@automation.post('/admin/automation/settings')
@login_required
def settings():
    permission(write=True)
    try:
        timezone = request.form.get('timezone', '').strip()
        ZoneInfo(timezone)
        hours = json.loads(request.form.get('business_hours', '{}'))
        if not isinstance(hours, dict) or not hours:
            raise ValueError('Configure at least one working weekday.')
        for day, interval in hours.items():
            if day not in [str(i) for i in range(7)] or not isinstance(interval, list) or len(interval) != 2:
                raise ValueError('Calendar keys are weekdays 0–6 with [start, end] intervals.')
            if any(not isinstance(v, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', v) for v in interval) or interval[0] >= interval[1]:
                raise ValueError('Use increasing HH:MM intervals. Overnight intervals are not supported.')
        row = db.session.get(AutomationSettings, 1) or AutomationSettings(id=1)
        row.timezone, row.business_hours = timezone, hours
        db.session.add(row)
        db.session.commit()
        flash('Instance business calendar saved.', 'success')
    except (ValueError, TypeError, ZoneInfoNotFoundError) as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return redirect(url_for('automation.index'))


@automation.post('/admin/automation/custom-fields')
@login_required
def custom_fields():
    permission(write=True)
    try:
        key = request.form.get('key', '').strip()
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', key):
            raise ValueError('Custom field keys use lowercase letters, digits and underscores.')
        if db.session.get(AutomationCustomField, key):
            raise ValueError('That custom field already exists.')
        typ = request.form.get('data_type')
        if typ not in ('text', 'select', 'number', 'date'):
            raise ValueError('Invalid custom field type.')
        label = request.form.get('label', '').strip()
        if not label or len(label) > 150:
            raise ValueError('Custom field label is required (max 150 characters).')
        choices = [value.strip() for value in request.form.get('choices', '').splitlines() if value.strip()]
        if typ == 'select' and not choices:
            raise ValueError('Dropdown fields require choices, one per line.')
        db.session.add(AutomationCustomField(key=key, label=label, data_type=typ, choices=choices))
        db.session.commit()
        flash('Custom field defined; available in the rule builder and variables.', 'success')
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return redirect(url_for('automation.index'))
