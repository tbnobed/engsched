"""Group ownership, membership, and administration. Helpers never commit."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from markupsafe import escape
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import db
from models import TicketCategory, TicketGroup, TicketGroupMember, TicketGroupSettings, TicketHistory, User

ticket_groups = Blueprint('ticket_groups', __name__)


def _membership_graph():
    graph, users = {}, {}
    for member in TicketGroupMember.query.all():
        if member.member_user_id is not None:
            users.setdefault(member.group_id, set()).add(member.member_user_id)
        elif member.member_group_id is not None:
            graph.setdefault(member.group_id, set()).add(member.member_group_id)
    return graph, users


def _resolve(group_id, graph, users):
    found, visited, pending = set(), set(), [group_id]
    while pending:
        node = pending.pop()
        if node in visited:
            continue
        visited.add(node)
        found.update(users.get(node, ()))
        pending.extend(graph.get(node, ()))
    return found


def resolved_user_ids(group_id) -> set[int]:
    """Resolve nested groups, including disabled groups' retained memberships."""
    if group_id is None:
        return set()
    graph, users = _membership_graph()
    return _resolve(int(group_id), graph, users)


def user_group_ids(user_id) -> set[int]:
    graph, users = _membership_graph()
    return {group.id for group in TicketGroup.query.all()
            if int(user_id) in _resolve(group.id, graph, users)}


def assignment_options() -> list:
    """Includes disabled groups for existing-ticket display; pickers hide them."""
    graph, users = _membership_graph()
    return [{'id': group.id, 'name': group.name, 'enabled': group.enabled,
             'member_ids': sorted(_resolve(group.id, graph, users))}
            for group in TicketGroup.query.order_by(TicketGroup.name).all()]


def filter_assignees_enabled() -> bool:
    settings = db.session.get(TicketGroupSettings, 1)
    return settings.filter_assignees if settings else True


def _optional_id(value, label):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError(f'{label} must be a valid ID.')
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{label} must be a valid ID.') from None
    if number <= 0 or str(number) != str(value).strip():
        raise ValueError(f'{label} must be a valid ID.')
    return number


def apply_assignment(ticket, group_id, assignee_id, actor_id=None, notify=False, event='reassigned'):
    """Validate and stage assignment/history; caller owns commit and notifications.

    A nonmember assignee is cleared when filtering is enabled; the return value
    includes assignee_cleared so callers can display a notice.
    """
    if event not in ('new_ticket', 'reassigned', 'comment'):
        raise ValueError('Unknown group notification event.')
    group_id = _optional_id(group_id, 'Group')
    assignee_id = _optional_id(assignee_id, 'Assignee')
    old_group_id, old_assignee_id = ticket.group_id, ticket.assigned_to
    group = db.session.get(TicketGroup, group_id) if group_id else None
    assignee = db.session.get(User, assignee_id) if assignee_id else None
    if group_id and group is None:
        raise ValueError('Group does not exist.')
    if group and not group.enabled and group_id != old_group_id:
        raise ValueError('Disabled groups cannot receive new assignments.')
    if assignee_id and assignee is None:
        raise ValueError('Assignee does not exist.')
    cleared = bool(group_id and assignee_id and filter_assignees_enabled()
                   and assignee_id not in resolved_user_ids(group_id))
    # Retained assignments on disabled groups are not silently changed.
    if cleared and (group_id != old_group_id or assignee_id != old_assignee_id):
        assignee_id, assignee = None, None
    else:
        cleared = False
    changed_group, changed_assignee = old_group_id != group_id, old_assignee_id != assignee_id
    actor_id = _optional_id(actor_id, 'Actor') if actor_id is not None else ticket.created_by
    if (changed_group or changed_assignee) and (not actor_id or db.session.get(User, actor_id) is None):
        raise ValueError('A valid actor is required to record assignment history.')
    old_group = db.session.get(TicketGroup, old_group_id) if old_group_id else None
    ticket.group_id, ticket.group, ticket.assigned_to = group_id, group, assignee_id
    ticket.assigned_technician = assignee
    if changed_group:
        # Keep shared ownership out of technician assignment/handoff metrics.
        # Names are captured alongside IDs so disabled/renamed groups remain
        # identifiable in historical activity.
        old_label = f'{old_group.name} (id: {old_group_id})' if old_group else 'None (id: none)'
        new_label = f'{group.name} (id: {group_id})' if group else 'None (id: none)'
        db.session.add(TicketHistory(ticket=ticket, user_id=actor_id,
                                     action='group_changed',
                                     details=f'Group changed from {old_label} to {new_label}'))
    if changed_assignee:
        # Preserve the established parseable individual-assignment convention.
        # Relationship attachment also supports tickets not yet flushed.
        db.session.add(TicketHistory(
            ticket=ticket, user_id=actor_id,
            action='assigned' if assignee else 'unassigned',
            details=f'Assigned to {assignee.username}' if assignee else 'Ticket was unassigned'))
    if notify:
        group_notified = False
        if changed_group:
            notify_group(ticket, event)
            group_notified = bool(group and group.notifications_enabled and
                                  (event != 'comment' or not ticket.assigned_to) and
                                  getattr(group, {'new_ticket': 'notify_new_ticket',
                                                  'reassigned': 'notify_reassigned',
                                                  'comment': 'notify_comment'}[event])
                                  and assignee_id in resolved_user_ids(group.id))
        if changed_assignee and assignee_id and not group_notified:
            from email_utils import send_email
            send_email(to_emails=[assignee.email], subject=f'Ticket assigned: #{ticket.id} {ticket.title}',
                       html_content=f'<p>You were assigned ticket #{ticket.id}: {escape(ticket.title)}</p>')
    return {'group_changed': changed_group, 'assignee_changed': changed_assignee,
            'assignee_cleared': cleared}


def notify_group(ticket, event):
    """Send one email per resolved member. Explicitly opt in after persistence."""
    flags = {'new_ticket': 'notify_new_ticket', 'reassigned': 'notify_reassigned',
             'comment': 'notify_comment'}
    if event not in flags:
        raise ValueError('Unknown group notification event.')
    group = db.session.get(TicketGroup, ticket.group_id) if ticket.group_id else None
    if not group or not group.notifications_enabled or not getattr(group, flags[event]):
        return True
    if event == 'comment' and ticket.assigned_to:
        return True
    from email_utils import send_email
    recipients = User.query.filter(User.id.in_(resolved_user_ids(group.id))).all()
    domain = current_app.config.get('EMAIL_DOMAIN', 'localhost:5000')
    scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'http')
    link = f'{scheme}://{domain}/tickets/{ticket.id}'
    labels = {'new_ticket': 'New ticket assigned', 'reassigned': 'Ticket reassigned',
              'comment': 'New comment'}
    success = True
    for user in recipients:
        sent = send_email(
            to_emails=[user.email],
            subject=f'{labels[event]} to {group.name}: #{ticket.id} {ticket.title}',
            html_content=f'<p>{escape(labels[event])} — {escape(group.name)}</p>'
                         f'<p><a href="{escape(link)}">#{ticket.id}: {escape(ticket.title)}</a></p>')
        if not sent:
            current_app.logger.error('Group notification failed: ticket=%s group=%s user=%s event=%s',
                                     ticket.id, group.id, user.id, event)
            success = False
    return success


def apply_category_defaults(ticket, explicit_group=False, explicit_assignee=False):
    """Only fill unspecified assignments. This schema has no subcategories."""
    category = db.session.get(TicketCategory, ticket.category_id) if ticket.category_id else ticket.category
    if not category:
        return
    group_id, assignee_id = ticket.group_id, ticket.assigned_to
    if not explicit_group and group_id is None and category.default_group_id:
        group = db.session.get(TicketGroup, category.default_group_id)
        if group and group.enabled:
            group_id = group.id
    if not explicit_assignee and assignee_id is None:
        assignee_id = category.default_assignee_id
    # An explicit individual takes precedence over incompatible category defaults.
    if group_id and assignee_id and filter_assignees_enabled() and assignee_id not in resolved_user_ids(group_id):
        if explicit_assignee and not explicit_group:
            group_id = ticket.group_id
        elif not explicit_assignee:
            assignee_id = None
    ticket.group_id, ticket.assigned_to = group_id, assignee_id
    ticket.group = db.session.get(TicketGroup, group_id) if group_id else None
    ticket.assigned_technician = db.session.get(User, assignee_id) if assignee_id else None


def _lock_memberships(session):
    # Table-wide serialization covers A->B concurrent with B->A, not just
    # edits to the same parent. Held until the caller commits or rolls back.
    if session.get_bind().dialect.name == 'postgresql':
        session.execute(text('LOCK TABLE ticket_group_member IN SHARE ROW EXCLUSIVE MODE'))


@event.listens_for(Session, 'before_flush')
def _validate_membership_graph(session, flush_context, instances):
    changes = [row for row in session.new.union(session.dirty).union(session.deleted)
               if isinstance(row, TicketGroupMember)]
    if not changes:
        return
    _lock_memberships(session)
    with session.no_autoflush:
        rows = session.query(TicketGroupMember).all()
    rows = [row for row in rows if row not in session.deleted]
    rows += [row for row in session.new if isinstance(row, TicketGroupMember) and row not in rows]
    graph = {}
    for row in rows:
        parent = row.group_id or (row.group.id if row.group else None)
        child = row.member_group_id or (row.member_group.id if row.member_group else None)
        user = row.member_user_id or (row.member_user.id if row.member_user else None)
        if (child is None) == (user is None):
            raise ValueError('Each member must be exactly one user or group.')
        if child is not None:
            graph.setdefault(parent, set()).add(child)
    for parent in graph:
        pending, seen = list(graph[parent]), set()
        while pending:
            child = pending.pop()
            if child == parent:
                raise ValueError('Groups cannot contain themselves, directly or through nested groups.')
            if child not in seen:
                seen.add(child)
                pending.extend(graph.get(child, ()))


def can_manage_groups():
    return bool(current_user.is_authenticated and
                (current_user.is_admin or TicketGroup.query.filter_by(manager_user_id=current_user.id).first()))


def _managed_group(group_id):
    group = db.get_or_404(TicketGroup, group_id)
    if not current_user.is_admin and group.manager_user_id != current_user.id:
        abort(403)
    return group


def _admin():
    if not current_user.is_admin:
        abort(403)


@ticket_groups.get('/admin/groups')
@login_required
def index():
    if not can_manage_groups():
        abort(403)
    query = TicketGroup.query
    if not current_user.is_admin:
        query = query.filter_by(manager_user_id=current_user.id)
    search, enabled = request.args.get('q', '').strip(), request.args.get('enabled', 'enabled')
    if search:
        query = query.filter(db.or_(TicketGroup.name.ilike(f'%{search}%'), TicketGroup.description.ilike(f'%{search}%')))
    if enabled != 'all':
        query = query.filter_by(enabled=enabled != 'disabled')
    groups = query.order_by(TicketGroup.name).all()
    graph, users = _membership_graph()
    return render_template('admin/groups/index.html', groups=groups, search=search, enabled=enabled,
                           counts={g.id: len(_resolve(g.id, graph, users)) for g in groups},
                           filter_assignees=filter_assignees_enabled())


@ticket_groups.post('/admin/groups/settings')
@login_required
def settings():
    _admin()
    # Serialize the singleton's initial insert as well as updates.
    if db.engine.dialect.name == 'postgresql':
        db.session.execute(text('SELECT pg_advisory_xact_lock(72419033)'))
    row = db.session.get(TicketGroupSettings, 1)
    if row is None:
        row = TicketGroupSettings(id=1)
        db.session.add(row)
    row.filter_assignees = request.form.get('filter_assignees') == 'on'
    db.session.commit()
    flash('Group assignment settings saved.', 'success')
    return redirect(url_for('ticket_groups.index'))


@ticket_groups.route('/admin/groups/new', methods=['GET', 'POST'])
@ticket_groups.route('/admin/groups/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(group_id=None):
    _admin()
    group = db.get_or_404(TicketGroup, group_id) if group_id else TicketGroup()
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            if not name or len(name) > 100:
                raise ValueError('Group name is required and must be at most 100 characters.')
            manager_id = _optional_id(request.form.get('manager_user_id'), 'Manager')
            if manager_id and db.session.get(User, manager_id) is None:
                raise ValueError('Manager does not exist.')
            group.name, group.description = name, request.form.get('description', '').strip()
            group.manager_user_id = manager_id
            for field in ('notifications_enabled', 'enabled', 'notify_new_ticket', 'notify_reassigned', 'notify_comment'):
                setattr(group, field, request.form.get(field) == 'on')
            db.session.add(group)
            db.session.commit()
            flash('Group saved.', 'success')
            return redirect(url_for('ticket_groups.detail', group_id=group.id))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else 'A group with this name already exists.', 'danger')
    return render_template('admin/groups/edit.html', group=group, users=User.query.order_by(User.username).all())


@ticket_groups.get('/admin/groups/<int:group_id>')
@login_required
def detail(group_id):
    group = _managed_group(group_id)
    users = User.query.order_by(User.username).all()
    groups = TicketGroup.query.filter(TicketGroup.id != group.id).order_by(TicketGroup.name).all()
    resolved = resolved_user_ids(group.id)
    return render_template('admin/groups/detail.html', group=group, users=users, groups=groups,
                           resolved_users=[user for user in users if user.id in resolved])


@ticket_groups.post('/admin/groups/<int:group_id>/members')
@login_required
def add_members(group_id):
    group = _managed_group(group_id)
    try:
        _lock_memberships(db.session)
        choices = request.form.getlist('members')
        if not choices:
            raise ValueError('Select at least one user or group.')
        with db.session.no_autoflush:
            existing = {(m.member_user_id, m.member_group_id) for m in group.members}
            additions = []
            for choice in set(choices):
                kind, separator, value = choice.partition(':')
                if not separator or kind not in ('user', 'group'):
                    raise ValueError('Invalid membership selection.')
                member_id = _optional_id(value, 'Member')
                model = User if kind == 'user' else TicketGroup
                if member_id is None or db.session.get(model, member_id) is None:
                    raise ValueError('Selected member no longer exists.')
                key = (member_id, None) if kind == 'user' else (None, member_id)
                if key not in existing:
                    additions.append(TicketGroupMember(group_id=group.id, member_user_id=key[0], member_group_id=key[1]))
                    existing.add(key)
            db.session.add_all(additions)
        db.session.commit()
        flash('Members added.', 'success')
    except (ValueError, IntegrityError) as exc:
        db.session.rollback()
        flash(str(exc) if isinstance(exc, ValueError) else 'Membership could not be saved; refresh and try again.', 'danger')
    return redirect(url_for('ticket_groups.detail', group_id=group_id))


@ticket_groups.post('/admin/groups/<int:group_id>/members/<int:member_id>/remove')
@login_required
def remove_member(group_id, member_id):
    _managed_group(group_id)
    _lock_memberships(db.session)
    member = db.get_or_404(TicketGroupMember, member_id)
    if member.group_id != group_id:
        abort(404)
    db.session.delete(member)
    db.session.commit()
    flash('Member removed.', 'success')
    return redirect(url_for('ticket_groups.detail', group_id=group_id))
