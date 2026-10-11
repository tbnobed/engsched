"""Ticket reporting calculations. Calendar-hour metrics never infer missing events."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import math
import re

UTC = timezone.utc
DONE = {'resolved', 'closed'}
STATUS_NAMES = {'open': 'Open', 'in_progress': 'In progress', 'pending': 'Pending',
                'resolved': 'Resolved', 'closed': 'Closed'}
PRIORITIES = {0: 'Low', 1: 'Medium', 2: 'High', 3: 'Urgent'}
REPORT_NAMES = {
    'volume': 'Ticket volume and trends', 'aging': 'Backlog and ticket aging',
    'first_response': 'First-response time', 'resolution_time': 'Resolution time',
    'workload': 'Technician workload', 'categories': 'Category and issue trends',
    'stalled': 'Waiting and stalled tickets',
    'targets': 'Response and resolution targets',
    'requesters': 'Requester and department demand',
    'reopened': 'Reopened tickets',
    'handoffs': 'Assignment and handoff history',
    'satisfaction': 'Customer satisfaction',
    'ai_usage': 'AI assistance usage',
}
CATALOG = [
    ('my_open', 'My open tickets', 'Unresolved tickets currently assigned to you.'),
    ('unassigned', 'Unassigned tickets', 'Unresolved tickets without an owner.'),
    ('high_priority', 'High-priority tickets', 'Unresolved high and urgent tickets.'),
    ('overdue', 'Overdue tickets', 'Unresolved tickets past their due date.'),
    ('created', 'Tickets created', 'Tickets opened during the selected period.'),
    ('resolved', 'Tickets completed', 'Unique tickets with a recorded completion in the period.'),
    ('volume', 'Created vs completed', 'Daily demand and recorded completions.'),
    ('aging', 'Backlog by age', 'Current unresolved tickets grouped by age.'),
    ('workload', 'Technician workload', 'Current unresolved assignments.'),
    ('categories', 'Category demand', 'Tickets created in the period by category.'),
    ('status', 'Tickets by status', 'Current unarchived tickets by status.'),
    ('my_queue', 'My work queue', 'Your unresolved tickets, oldest first.'),
    ('stalled', 'Stalled tickets', 'Unresolved tickets with no recent human conversation.'),
    ('first_response', 'First response', 'Median calendar hours to the first qualifying human reply.'),
    ('resolution_time', 'Resolution time', 'Median calendar hours to recorded completion.'),
]


def utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def requester_key(ticket):
    if ticket.external_email:
        return 'email:' + ticket.external_email.strip().casefold()
    return f'user:{ticket.created_by}'


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def comment_text(content):
    parser = _Text()
    parser.feed(content or '')
    return ' '.join(parser.parts).strip()


def is_ai_comment(content, username=''):
    # Legacy n8n comments were sometimes attached to a real technician.
    text = comment_text(content).lstrip('🤖 📋\ufe0f\n\t ')
    return username.casefold() == 'ai assistant' or (
        text.startswith('AI Analysis') and 'Summary' in text and
        ('Possible Causes' in text or 'Confidence Level' in text))


def is_staff_reply(comment, ticket):
    if is_ai_comment(comment.content, comment.user.username if comment.user else ''):
        return False
    if not comment.user or comment.user.username.casefold() in {'system', 'ai assistant'}:
        return False
    text = comment_text(comment.content)
    if text.startswith('Email reply from:'):
        # External replies have an admin FK; inspect the actual sender, not that FK.
        match = re.search(r'Email reply from:.*?\(([^()\s]+@[^()\s]+)\)', text)
        if not match:
            return False
        sender = match.group(1).casefold()
        if sender != (comment.user.email or '').casefold():
            return False
        if sender == (ticket.external_email or '').casefold():
            return False
    return bool(ticket.external_email) or comment.user_id != ticket.created_by


def completion_events(histories, created, now):
    results = []
    for event in histories:
        when = utc(event.created_at)
        if not when or when < created or when > now or event.action != 'status_changed':
            continue
        match = re.search(
            r'Status changed from (open|in_progress|pending|resolved|closed) to '
            r'(open|in_progress|pending|resolved|closed)\b', event.details or '', re.I)
        if match and match[1].lower() not in DONE and match[2].lower() in DONE:
            results.append(when)
    return sorted(set(results))


def median(values):
    return percentile(values, 0.5)


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    return round(values[low] + (values[high] - values[low]) * (position - low), 2)


def default_layout(preset='team'):
    types = (['my_open', 'overdue', 'first_response', 'my_queue', 'stalled', 'volume']
             if preset == 'my' else
             ['unassigned', 'high_priority', 'created', 'resolved', 'volume', 'aging', 'workload', 'stalled'])
    return {'version': 1, 'preset': preset, 'widgets': [
        {'id': f'{kind}-{index}', 'type': kind,
         'size': 'small' if kind in {'my_open', 'overdue', 'first_response', 'unassigned',
                                    'high_priority', 'created', 'resolved'} else 'medium',
         'scope': 'me' if preset == 'my' else 'team', 'limit': 5}
        for index, kind in enumerate(types)]}


def validate_layout(layout):
    if not isinstance(layout, dict) or layout.get('version') != 1:
        raise ValueError('Unsupported dashboard layout.')
    if layout.get('preset') not in {'my', 'team'}:
        raise ValueError('Choose My Work or Team Overview.')
    widgets = layout.get('widgets')
    if not isinstance(widgets, list) or len(widgets) > 20:
        raise ValueError('A dashboard can contain up to 20 widgets.')
    ids, cleaned = set(), []
    for widget in widgets:
        if not isinstance(widget, dict):
            raise ValueError('Invalid widget.')
        identifier = widget.get('id')
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', identifier) or identifier in ids:
            raise ValueError('Widget IDs must be unique.')
        ids.add(identifier)
        if widget.get('type') not in {item[0] for item in CATALOG}:
            raise ValueError('Unknown widget type.')
        if widget.get('size') not in {'small', 'medium', 'large'} or widget.get('scope') not in {'me', 'team'}:
            raise ValueError('Invalid widget size or scope.')
        if type(widget.get('limit')) is not int or widget['limit'] not in {5, 10, 20}:
            raise ValueError('Widget lists can show 5, 10, or 20 tickets.')
        cleaned.append({key: widget[key] for key in ('id', 'type', 'size', 'scope', 'limit')})
    return {'version': 1, 'preset': layout['preset'], 'widgets': cleaned}


def build_insights(tickets, comments, histories, users, categories, email_ids, filters, user_id, tz, now=None):
    now = utc(now or datetime.now(UTC))
    start, end = filters['start'], filters['end']
    start_at = tz.localize(datetime.combine(start, datetime.min.time())).astimezone(UTC)
    end_at = tz.localize(datetime.combine(end + timedelta(days=1), datetime.min.time())).astimezone(UTC)
    comment_map, history_map = defaultdict(list), defaultdict(list)
    for comment in comments:
        comment_map[comment.ticket_id].append(comment)
    for history in histories:
        history_map[history.ticket_id].append(history)
    rows, excluded_ai, missing_history = [], 0, 0
    for ticket in tickets:
        source = 'email' if ticket.external_email or ticket.id in email_ids else 'web'
        if filters.get('source', 'all') != 'all' and source != filters['source']:
            continue
        created = utc(ticket.created_at)
        if not created or created > now:
            continue
        first_reply, human_updates = [], [created]
        for comment in comment_map[ticket.id]:
            when = utc(comment.created_at)
            if not when or when < created or when > now:
                continue
            if is_ai_comment(comment.content, comment.user.username if comment.user else ''):
                excluded_ai += 1
                continue
            human_updates.append(when)
            if is_staff_reply(comment, ticket):
                first_reply.append(when)
        events = completion_events(history_map[ticket.id], created, now)
        pending_entries = []
        for history in history_map[ticket.id]:
            when = utc(history.created_at)
            if history.action == 'internal_note' and when and created <= when <= now:
                human_updates.append(when)
            if (history.action == 'status_changed' and ticket.status == 'pending'
                    and when and created <= when <= now
                    and re.search(r'Status changed from (open|in_progress|resolved|closed) to pending\b',
                                  history.details or '', re.I)):
                pending_entries.append(when)
        completions_in_period = [when for when in events if start_at <= when < end_at]
        # Latest completion in the requested window; no invented updated_at fallback.
        completed = max(completions_in_period, default=None)
        response_at = min(first_reply, default=None)
        is_open = ticket.status not in DONE and not ticket.archived
        if ticket.status in DONE and not events:
            missing_history += 1
        last_human = max(human_updates)
        due = utc(ticket.due_date)
        assignee = users.get(ticket.assigned_to)
        row = {
            'id': ticket.id, 'title': ticket.title, 'url': f'/tickets/{ticket.id}',
            'status': ticket.status, 'priority': ticket.priority,
            'assignee_id': ticket.assigned_to, 'assignee': assignee.username if assignee else 'Unassigned',
            'category': categories.get(ticket.category_id, 'Uncategorized'), 'source': source,
            'created_at': created.isoformat(), 'created_display': created.astimezone(tz).strftime('%Y-%m-%d %H:%M'),
            'age_days': round((now - created).total_seconds() / 86400, 2),
            'idle_days': round((now - last_human).total_seconds() / 86400, 2),
            'last_human_at': last_human.isoformat(), 'due_at': due.isoformat() if due else None,
            'pending_days': round((now - max(pending_entries)).total_seconds() / 86400, 2) if pending_entries else None,
            'first_response_hours': round((response_at - created).total_seconds() / 3600, 2) if response_at else None,
            'first_response_at': response_at.isoformat() if response_at else None,
            'resolution_hours': round((completed - created).total_seconds() / 3600, 2) if completed else None,
            'completed_at': completed.isoformat() if completed else None,
            'is_open': is_open, 'is_overdue': bool(is_open and due and due < now),
            'in_created_period': start_at <= created < end_at,
            'in_resolved_period': bool(completed), 'has_response': bool(response_at),
            'archived': bool(ticket.archived),
        }
        rows.append(row)
    rows.sort(key=lambda row: row['created_at'])
    opened = [row for row in rows if row['is_open']]
    created_rows = [row for row in rows if row['in_created_period']]
    resolved_rows = [row for row in rows if row['in_resolved_period']]
    response_values = [row['first_response_hours'] for row in created_rows if row['has_response']]
    resolution_values = [row['resolution_hours'] for row in resolved_rows]
    stalled = [row for row in opened if row['idle_days'] >= filters['stalled_days']]
    volume = {}
    day = start
    while day <= end:
        volume[day.isoformat()] = {'label': day.isoformat(), 'created': 0, 'resolved': 0}
        day += timedelta(days=1)
    for row in created_rows:
        volume[row['created_display'][:10]]['created'] += 1
    for row in resolved_rows:
        local_day = datetime.fromisoformat(row['completed_at']).astimezone(tz).date().isoformat()
        volume[local_day]['resolved'] += 1

    def group(items, key):
        grouped = defaultdict(list)
        for row in items:
            grouped[key(row)].append(row['id'])
        return [{'label': label, 'count': len(ids), 'ids': ids}
                for label, ids in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))]

    age_labels = ['Under 1 day', '1–3 days', '3–7 days', '7–14 days', '14–30 days', '30+ days']
    age_groups = {label: [] for label in age_labels}
    for row in opened:
        bucket = sum(row['age_days'] >= threshold for threshold in (1, 3, 7, 14, 30))
        age_groups[age_labels[bucket]].append(row['id'])
    aging = [{'label': label, 'count': len(ids), 'ids': ids} for label, ids in age_groups.items()]

    def report(name, description, columns, report_rows, **extra):
        return {'title': REPORT_NAMES[name], 'description': description,
                'columns': [{'key': key, 'label': label} for key, label in columns],
                'rows': report_rows, **extra}

    def ticket_record(row):
        return {'ticket_id': row['id'], 'ticket_url': row['url'], 'title': row['title'],
                'status': STATUS_NAMES.get(row['status'], row['status']), 'assignee': row['assignee'],
                'category': row['category'], 'priority': PRIORITIES.get(row['priority'], 'Unknown')}

    workload_rows = []
    for name in sorted({row['assignee'] for row in rows}):
        owned = [row for row in rows if row['assignee'] == name]
        active = [row for row in owned if row['is_open']]
        workload_rows.append({'technician': name, 'open': len(active),
                              'high_priority': sum(row['priority'] >= 2 for row in active),
                              'overdue': sum(row['is_overdue'] for row in active),
                              'completed': sum(row['in_resolved_period'] for row in owned),
                              'ticket_ids': [row['id'] for row in active]})
    category_rows = []
    for category in sorted({row['category'] for row in rows}):
        matching = [row for row in rows if row['category'] == category]
        durations = [row['resolution_hours'] for row in matching if row['in_resolved_period']]
        category_rows.append({'category': category,
                              'created': sum(row['in_created_period'] for row in matching),
                              'open': sum(row['is_open'] for row in matching),
                              'completed': len(durations), 'median_hours': median(durations),
                              'ticket_ids': [row['id'] for row in matching if row['in_created_period']]})
    reports = {
        'volume': report('volume', 'Created and unique tickets completed per day in the selected timezone. Repeated completions use the latest event in this period; net change is created minus completed, not a historical backlog.',
                         [('date', 'Date'), ('created', 'Created'), ('resolved', 'Completed'), ('net', 'Net change')],
                         [dict(date=v['label'], created=v['created'], resolved=v['resolved'],
                               net=v['created'] - v['resolved']) for v in volume.values()]),
        'aging': report('aging', 'Current unresolved, unarchived tickets. Age is calendar time since creation. This snapshot ignores the date range.',
                        [('ticket_id', 'Ticket'), ('title', 'Title'), ('status', 'Status'), ('priority', 'Priority'),
                         ('assignee', 'Technician'), ('age_days', 'Age (days)'), ('overdue', 'Overdue')],
                        [dict(ticket_record(row), age_days=row['age_days'], overdue='Yes' if row['is_overdue'] else 'No') for row in opened]),
        'first_response': report('first_response', 'Creation-date cohort. First recorded public reply by a human other than the requester; excludes AI, internal notes, and external email proxy authors. Calendar hours, not business hours. Missing historical replies cannot be distinguished from unanswered tickets.',
                                 [('ticket_id', 'Ticket'), ('title', 'Title'), ('category', 'Category'),
                                  ('assignee', 'Current technician'), ('hours', 'Response (hours)'), ('tracking', 'Coverage')],
                                 [dict(ticket_record(row), hours=row['first_response_hours'],
                                       tracking='Recorded' if row['has_response'] else 'No qualifying reply recorded') for row in created_rows],
                                 median_hours=median(response_values), p90_hours=percentile(response_values, .9),
                                 measured=len(response_values), total=len(created_rows)),
        'resolution_time': report('resolution_time', 'Tickets with a recorded completion in the selected period. Calendar hours from creation to the latest completion in that period, including waiting time. A resolved/closed status without a transition timestamp is not used.',
                                  [('ticket_id', 'Ticket'), ('title', 'Title'), ('category', 'Category'),
                                   ('assignee', 'Current technician'), ('completed', 'Completed'), ('hours', 'Resolution (hours)')],
                                  [dict(ticket_record(row), hours=row['resolution_hours'],
                                        completed=datetime.fromisoformat(row['completed_at']).astimezone(tz).strftime('%Y-%m-%d %H:%M')) for row in resolved_rows],
                                  median_hours=median(resolution_values), p90_hours=percentile(resolution_values, .9),
                                  measured=len(resolution_values), missing_history=missing_history),
        'workload': report('workload', 'Current unresolved assignments, regardless of date range. Completed counts use the selected period and CURRENT assignee, not the person who resolved the ticket. Counts alone are not a performance ranking.',
                           [('technician', 'Technician'), ('open', 'Open'), ('high_priority', 'High / urgent'),
                            ('overdue', 'Overdue'), ('completed', 'Completed in period')], workload_rows),
        'categories': report('categories', 'Created and recorded completions use the selected period; open counts are the current backlog, regardless of creation date. Median resolution uses calendar hours.',
                             [('category', 'Category'), ('created', 'Created'), ('open', 'Current open'),
                              ('completed', 'Completed'), ('median_hours', 'Median resolution (hours)')], category_rows),
        'stalled': report('stalled', f'Current unresolved tickets without a human reply or internal note for {filters["stalled_days"]} days. Opening starts the clock. AI, passive views, and assignment/status changes do not reset it. Pending duration uses the latest recorded transition into pending; missing transitions are not tracked. The system does not identify who is being waited on. Date range does not apply.',
                          [('ticket_id', 'Ticket'), ('title', 'Title'), ('status', 'Status'), ('assignee', 'Technician'),
                           ('idle_days', 'Days without conversation'), ('pending_days', 'Current pending (days)'), ('last_update', 'Last human conversation')],
                          [dict(ticket_record(row), idle_days=row['idle_days'], pending_days=row['pending_days'],
                                last_update=datetime.fromisoformat(row['last_human_at']).astimezone(tz).strftime('%Y-%m-%d %H:%M')) for row in sorted(stalled, key=lambda r: -r['idle_days'])]),
    }
    return {
        'timezone': str(tz), 'start': start.isoformat(), 'end': end.isoformat(), 'generated_at': now.isoformat(),
        'methodology': [
            'Times are calendar hours in your profile timezone; no business-hour or SLA targets are configured.',
            'Aging, open workload, and stalled tickets are current snapshots and ignore the selected date range.',
            'Period reports include archived tickets; current backlog excludes them. Filters use current category, status, priority, source, and assignee, not historical ownership.',
            'First-response time excludes recognized legacy AI analyses, requester replies, and internal notes. Legacy sender identity is used when available.',
            'Missing completion history is not inferred from last-updated timestamps. Deleted/imported events may limit historical accuracy.',
        ],
        'coverage': {'missing_resolution_history': missing_history, 'excluded_ai_comments': excluded_ai},
        'metrics': {'my_open': sum(row['assignee_id'] == user_id for row in opened),
                    'unassigned': sum(row['assignee_id'] is None for row in opened),
                    'high_priority': sum(row['priority'] >= 2 for row in opened),
                    'overdue': sum(row['is_overdue'] for row in opened),
                    'created': len(created_rows), 'resolved': len(resolved_rows),
                    'first_response': median(response_values), 'resolution_time': median(resolution_values),
                    'stalled': len(stalled)},
        'tickets': rows,
        'charts': {'volume': list(volume.values()), 'aging': aging,
                   'workload': group(opened, lambda row: row['assignee']),
                   'categories': group(created_rows, lambda row: row['category']),
                   'status': group([row for row in rows if not row['archived']], lambda row: STATUS_NAMES.get(row['status'], row['status']))},
        'reports': reports,
    }
