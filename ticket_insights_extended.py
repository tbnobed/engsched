"""Additional reports built from recorded events, never synthetic history."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import re

from ticket_insights_service import (
    DONE, PRIORITIES, REPORT_NAMES, STATUS_NAMES, completion_events, median, utc, requester_key,
)


def extend_insights(data, tickets, histories, users, filters, tz, user_id,
                    targets, profiles, surveys, messages, ratings, now=None):
    now = utc(now or datetime.now(timezone.utc))
    start = tz.localize(datetime.combine(filters['start'], datetime.min.time())).astimezone(timezone.utc)
    end = tz.localize(datetime.combine(filters['end'] + timedelta(days=1), datetime.min.time())).astimezone(timezone.utc)
    by_id = {ticket.id: ticket for ticket in tickets}
    base = {row['id']: row for row in data['tickets']}
    history_map = defaultdict(list)
    for entry in histories:
        if entry.ticket_id in base and utc(entry.created_at) and utc(entry.created_at) <= now:
            history_map[entry.ticket_id].append(entry)
    for entries in history_map.values():
        entries.sort(key=lambda entry: (utc(entry.created_at), entry.id or 0))

    def within(value):
        return bool(value and start <= utc(value) < end and utc(value) <= now)

    def local(value):
        return utc(value).astimezone(tz).strftime('%Y-%m-%d %H:%M') if value else None

    def ticket_fields(row):
        return {'ticket_id': row['id'], 'ticket_url': row['url'], 'title': row['title'],
                'category': row['category'], 'status': STATUS_NAMES.get(row['status'], row['status']),
                'priority': PRIORITIES.get(row['priority'], 'Unknown'), 'assignee': row['assignee']}

    def report(key, description, columns, rows, summary=None):
        if key == 'requesters' and filters.get('group_by') == 'group':
            columns = [('group', 'Current group'), *columns]
        data['reports'][key] = {
            'title': REPORT_NAMES[key], 'description': description,
            'columns': [{'key': key, 'label': label} for key, label in columns],
            'rows': rows, 'summary': [{'label': label, 'value': value} for label, value in (summary or [])],
        }

    # Apply requester attributes to the same ticket records used by count drill-downs.
    for row in base.values():
        ticket = by_id[row['id']]
        key = requester_key(ticket)
        profile, user = profiles.get(key), users.get(ticket.created_by)
        row.update(requester_key=key,
                   requester=(ticket.external_name or ticket.external_email) if ticket.external_email else user.username if user else 'Unknown requester',
                   requester_email=ticket.external_email or (user.email if user else ''),
                   department=profile.department if profile else '',
                   location=profile.location if profile else '')

    policies = {item['priority']: item for item in targets}
    target_rows = []
    for row in base.values():
        if not (row['is_open'] or row['in_created_period']):
            continue
        created = utc(by_id[row['id']].created_at)
        completions = completion_events(history_map[row['id']], created, now)
        final_completion = max(completions, default=None) if row['status'] in DONE else None
        policy = policies.get(row['priority'], {})

        def evaluate(target, measured, active):
            if target is None:
                return 'Not configured', None, None
            deadline = created + timedelta(hours=target)
            if measured is None and not active:
                return 'Not tracked', None, local(deadline)
            elapsed = measured if measured is not None else (now - created).total_seconds() / 3600
            if elapsed > target:
                state = 'Breached'
            elif measured is not None:
                state = 'Met'
            elif elapsed >= target * .8:
                state = 'At risk'
            else:
                state = 'Within target'
            return state, round(elapsed, 2), local(deadline)

        response_hours = (utc(datetime.fromisoformat(row['first_response_at'])) - created).total_seconds() / 3600 if row.get('first_response_at') else None
        response = evaluate(policy.get('response_hours'), response_hours, row['is_open'])
        resolved_hours = (final_completion - created).total_seconds() / 3600 if final_completion else None
        resolution = evaluate(policy.get('resolution_hours'), resolved_hours, row['is_open'])
        target_rows.append(dict(ticket_fields(row),
                                response_target=policy.get('response_hours'), response_state=response[0],
                                response_hours=response[1], response_deadline=response[2],
                                resolution_target=policy.get('resolution_hours'), resolution_state=resolution[0],
                                resolution_hours=resolution[1], resolution_deadline=resolution[2]))
    report('targets',
           'Current unarchived open tickets plus tickets created in the period. Evaluated against CURRENT configured calendar-hour targets, with no waiting pauses or business-hour exclusions; this is not proof of a historical SLA. At risk means 80–100% of a target elapsed. Open tickets without a recorded reply continue aging; completed tickets with missing evidence are Not tracked. Configure actual targets in Report settings.',
           [('ticket_id', 'Ticket'), ('title', 'Title'), ('priority', 'Priority'), ('assignee', 'Current technician'),
            ('response_target', 'Response target (hours)'), ('response_state', 'Response target status'),
            ('response_hours', 'Response elapsed (hours)'), ('response_deadline', 'Response deadline'),
            ('resolution_target', 'Resolution target (hours)'), ('resolution_state', 'Resolution target status'),
            ('resolution_hours', 'Resolution elapsed (hours)'), ('resolution_deadline', 'Resolution deadline')],
           target_rows,
           [('Tickets with a breached target', sum('Breached' in (row['response_state'], row['resolution_state']) for row in target_rows)),
            ('Tickets at risk', sum('At risk' in (row['response_state'], row['resolution_state']) for row in target_rows)),
            ('Priorities with configured targets', sum(item.get('response_hours') is not None or item.get('resolution_hours') is not None for item in policies.values()))])

    requester_groups = defaultdict(list)
    for row in base.values():
        requester_groups[(row['requester_key'], row['group_id'] if filters.get('group_by') == 'group' else None)].append(row)
    requester_rows = []
    for (key, _group_id), group in requester_groups.items():
        sample = group[0]
        requester_rows.append({
            'requester_key': key, 'requester': sample['requester'], 'email': sample['requester_email'],
            'group_id': sample['group_id'], 'group': sample['group'],
            'department': sample['department'] or 'Not assigned', 'location': sample['location'] or 'Not assigned',
            'created': sum(row['in_created_period'] for row in group),
            'open': sum(row['is_open'] for row in group),
            'completed': sum(row['in_resolved_period'] for row in group),
            'median_hours': median([row['resolution_hours'] for row in group if row['in_resolved_period']]),
        })
    requester_rows.sort(key=lambda row: (-row['created'], -row['open'], row['requester']))
    report('requesters',
           'Demand grouped by requester identity. Created/completed counts use the selected period; open counts are the current backlog. Department and location are administrator-maintained current mappings, never inferred from an email domain or retroactively treated as historical organizational data. Filter department/location to compare groups.',
           [('requester', 'Requester'), ('email', 'Email'), ('department', 'Department'), ('location', 'Location'),
            ('created', 'Created'), ('open', 'Current open'), ('completed', 'Completed'), ('median_hours', 'Median resolution (hours)')],
           requester_rows,
           [('Requesters with new tickets', len({row['requester_key'] for row in requester_rows if row['created'] > 0})),
            ('Current open tickets', sum(row['open'] for row in requester_rows))])

    reopened_rows, completion_cohort, later_reopened = [], 0, 0
    for row in base.values():
        ticket = by_id[row['id']]
        reopen_times = []
        for entry in history_map[row['id']]:
            if entry.action == 'status_changed' and utc(entry.created_at) >= utc(ticket.created_at) and re.search(
                    r'Status changed from (resolved|closed) to (open|in_progress|pending)\b', entry.details or '', re.I):
                reopen_times.append(utc(entry.created_at))
        period_reopens = [when for when in reopen_times if within(when)]
        completions = [when for when in completion_events(history_map[row['id']], utc(ticket.created_at), now) if within(when)]
        if completions:
            completion_cohort += 1
            later_reopened += any(when > min(completions) for when in reopen_times)
        if period_reopens:
            reopened_rows.append(dict(ticket_fields(row), reopens=len(period_reopens),
                                      total_reopens=len(reopen_times), last_reopened=max(period_reopens).isoformat()))
    report('reopened',
           'Rows are tickets with a recorded resolved/closed → open/in-progress/pending transition during the period. The completion-cohort reopen rate is the share of tickets completed in the period with a later recorded reopen by now, even if that reopen is outside the period. Missing history cannot be reconstructed.',
           [('ticket_id', 'Ticket'), ('title', 'Title'), ('category', 'Category'), ('status', 'Current status'),
            ('reopens', 'Reopens in period'), ('total_reopens', 'All recorded reopens'), ('last_reopened', 'Last reopen in period')],
           reopened_rows,
           [('Tickets reopened in period', len(reopened_rows)),
            ('Recorded reopens in period', sum(row['reopens'] for row in reopened_rows)),
            ('Completion-cohort reopen rate', f'{100 * later_reopened / completion_cohort:.1f}%' if completion_cohort else None),
            ('Completion cohort size', completion_cohort)])

    assignment_rows, unknown_tickets, handoffs = [], 0, 0
    for row in base.values():
        ticket = by_id[row['id']]
        entries = []
        for entry in history_map[row['id']]:
            if utc(entry.created_at) < utc(ticket.created_at):
                continue
            if entry.action == 'unassigned':
                destination = 'Unassigned'
            elif entry.action == 'assigned':
                match = re.match(r'Assigned to (.+?)(?: - Note:|\s+\(bulk\)|$)', entry.details or '')
                if not match:
                    continue
                destination = match[1].strip()
            else:
                continue
            # Bulk/no-op assignments should not reset the ownership clock.
            if entries and entries[-1][1] == destination:
                continue
            entries.append((utc(entry.created_at), destination))
        if not entries:
            unknown_tickets += 1
            if row['is_open'] or row['in_created_period']:
                assignment_rows.append(dict(ticket_fields(row), technician=row['assignee'],
                                            from_technician=None, interval_start=None, interval_end=None,
                                            hours=None, handoff='Not tracked', coverage='No parseable assignment history; current owner only'))
            continue
        recorded_end = now
        if row['status'] in DONE:
            completions = completion_events(history_map[row['id']], utc(ticket.created_at), now)
            if completions:
                recorded_end = min(now, max(completions))
        for index, (assigned_at, destination) in enumerate(entries):
            next_at = entries[index + 1][0] if index + 1 < len(entries) else recorded_end
            clipped_start, clipped_end = max(assigned_at, start), min(next_at, end, now)
            if clipped_end < clipped_start or (clipped_end == clipped_start and not within(assigned_at)):
                continue
            previous = entries[index - 1][1] if index else None
            actual_handoff = bool(previous and previous != 'Unassigned' and destination != 'Unassigned' and previous != destination)
            if actual_handoff and within(assigned_at):
                handoffs += 1
            assignment_rows.append(dict(ticket_fields(row), technician=destination,
                                        from_technician=previous, interval_start=clipped_start.isoformat(), interval_end=clipped_end.isoformat(),
                                        hours=round(max(0, (clipped_end - clipped_start).total_seconds() / 3600), 2),
                                        handoff='Handoff' if actual_handoff else 'Unassignment' if destination == 'Unassigned' else 'First recorded assignment' if index == 0 else 'Assignment',
                                        coverage='Elapsed ownership, not active work; pre-first-assignment ownership unknown'))
    report('handoffs',
           'Recorded assignment intervals clipped to the selected period. Time is elapsed ownership, including waiting, not technician labor. Identical consecutive destinations are collapsed. Known unassigned intervals are shown; ownership before the first recorded assignment is unknown. Current-assignee filters select tickets, not historical owners. Completed tickets stop at their latest recorded completion when available.',
           [('ticket_id', 'Ticket'), ('title', 'Title'), ('from_technician', 'Previous recorded owner'),
            ('technician', 'Recorded owner'), ('interval_start', 'Interval start'), ('interval_end', 'Interval end'),
            ('hours', 'Calendar hours in period'), ('handoff', 'Assignment type'), ('coverage', 'Coverage')],
           assignment_rows,
           [('Recorded handoffs in period', handoffs),
            ('Known unassigned hours', round(sum(row['hours'] or 0 for row in assignment_rows if row['technician'] == 'Unassigned'), 2)),
            ('Tickets without assignment history', unknown_tickets)])

    feedback_rows = []
    for survey in surveys:
        if survey.ticket_id not in base or not within(survey.invited_at):
            continue
        feedback_rows.append(dict(ticket_fields(base[survey.ticket_id]),
                                  invited_at=utc(survey.invited_at).isoformat(),
                                  responded_at=utc(survey.responded_at).isoformat() if survey.responded_at else None,
                                  score=survey.score, comment=survey.comment or '',
                                  state='Responded' if survey.responded_at else 'Expired' if utc(survey.expires_at) <= now else 'Awaiting response'))
    scores = [row['score'] for row in feedback_rows if row['score'] is not None]
    report('satisfaction',
           'Invitation-date cohort: one survey per ticket, rated 1–5. Response rate includes responses received by now to invitations issued in the selected period. Expired unanswered invitations remain in the denominator. Reissuing an unanswered link replaces its invitation date and invalidates the old link. No historical satisfaction scores are invented.',
           [('ticket_id', 'Ticket'), ('title', 'Title'), ('invited_at', 'Invited'), ('responded_at', 'Responded'),
            ('state', 'Survey status'), ('score', 'Rating (1–5)'), ('comment', 'Requester feedback')],
           feedback_rows,
           [('Invited tickets', len(feedback_rows)), ('Responses', len(scores)),
            ('Response rate', f'{100 * len(scores) / len(feedback_rows):.1f}%' if feedback_rows else None),
            ('Average rating / 5', round(sum(scores) / len(scores), 2) if scores else None),
            ('Satisfied (4 or 5)', f'{100 * sum(score >= 4 for score in scores) / len(scores):.1f}%' if scores else None)])
    data['feedback_eligible'] = [{'id': row['id'], 'title': row['title']} for row in base.values() if row['status'] in DONE]

    rating_map = defaultdict(list)
    for rating in ratings:
        rating_map[rating.message_id].append(rating)
    ai_rows, prior_by_ticket = [], {}
    for message in sorted(messages, key=lambda entry: (utc(entry.created_at), entry.id)):
        if message.ticket_id not in base:
            continue
        prior = prior_by_ticket.get(message.ticket_id)
        prior_by_ticket[message.ticket_id] = message
        if message.role != 'assistant' or not within(message.created_at):
            continue
        followup = bool(prior and prior.role == 'user')
        requester = users.get(prior.user_id) if followup else None
        votes = rating_map[message.id]
        own = next((vote.helpful for vote in votes if vote.user_id == user_id), None)
        ai_rows.append(dict(ticket_fields(base[message.ticket_id]), status=message.status,
                            message_id=message.id, kind='Follow-up' if followup else 'Initial analysis',
                            requested_at=utc(message.created_at).isoformat(),
                            requested_by=requester.username if requester else 'Automatic / not tracked',
                            helpful_votes=sum(vote.helpful for vote in votes),
                            not_helpful_votes=sum(not vote.helpful for vote in votes), my_rating=own,
                            response_content=message.content if message.status == 'completed' else ''))
    helpful = sum(row['helpful_votes'] for row in ai_rows)
    negative = sum(row['not_helpful_votes'] for row in ai_rows)
    report('ai_usage',
           'Direct OpenAI assistant requests created in the period, with their current status and current technician votes. Follow-ups are identified by the preceding user question. Retries update the same request, so attempt counts and historical failures are not reconstructable. Legacy n8n comments are excluded. Usage and helpful votes do not prove a ticket was resolved, and response time/cost/token data is not tracked.',
           [('ticket_id', 'Ticket'), ('title', 'Title'), ('kind', 'Request type'), ('requested_at', 'Requested'),
            ('requested_by', 'Requested by'), ('status', 'Current state'),
            ('helpful_votes', 'Helpful votes'), ('not_helpful_votes', 'Not helpful votes')],
           ai_rows,
           [('Assistant requests', len(ai_rows)), ('Follow-ups', sum(row['kind'] == 'Follow-up' for row in ai_rows)),
            ('Currently failed', sum(row['status'] == 'failed' for row in ai_rows)),
            ('Rated responses', sum(row['helpful_votes'] + row['not_helpful_votes'] > 0 for row in ai_rows)),
            ('Helpful vote share', f'{100 * helpful / (helpful + negative):.1f}%' if helpful + negative else None)])
    data['methodology'].extend([
        'Service targets and requester department/location mappings use current administrator settings, not historical policies.',
        'Customer feedback is collected prospectively through single-use requester links. AI usefulness votes are per technician and can be changed or cleared.',
    ])
    return data
