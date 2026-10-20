from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, after_this_request
from flask_login import login_required, current_user
from forms import TicketForm, TicketCommentForm, TicketCategoryForm
from models import db, Ticket, TicketCategory, TicketComment, TicketHistory, User, TicketStatus, TicketView, ProcessedEmail
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text, or_, func
from app import app, is_mobile_device  # Import app for logging and mobile detection
from email_utils import send_ticket_assigned_notification, send_ticket_comment_notification, send_ticket_status_notification, send_new_ticket_notification
import bleach
from ticket_groups import (assignment_options, filter_assignees_enabled,
                           apply_assignment, apply_category_defaults,
                           notify_group, user_group_ids, resolved_user_ids)


@app.context_processor
def ticket_group_context():
    if not current_user.is_authenticated:
        return {}
    return {
        'ticket_group_options': assignment_options(),
        'ticket_group_filter_assignees': filter_assignees_enabled(),
        'ticket_group_users': User.query.order_by(User.username).all(),
    }


def _assignment_id(value):
    return None if value in (None, '', '0', '__default__') else int(value)


def _notify_ticket_assignment(ticket, old_group=None, old_assignee=None, event='reassigned'):
    """Deliver once per recipient when shared and individual ownership overlap."""
    group_covers_assignee = False
    if ticket.group_id and (event == 'new_ticket' or old_group != ticket.group_id):
        if notify_group(ticket, event) is False:
            raise RuntimeError('Group notification delivery failed.')
        group = ticket.group
        flag = 'notify_new_ticket' if event == 'new_ticket' else 'notify_reassigned'
        group_covers_assignee = (group.notifications_enabled and getattr(group, flag)
                                  and ticket.assigned_to in resolved_user_ids(group.id))
    if ticket.assigned_to and not group_covers_assignee and (event == 'new_ticket' or old_assignee != ticket.assigned_to):
        if send_ticket_assigned_notification(ticket=ticket, assigned_by=current_user) is False:
            raise RuntimeError('Assignee notification delivery failed.')


def _notify_ticket_comment(ticket, comment):
    if ticket.group_id and not ticket.assigned_to:
        if notify_group(ticket, 'comment') is False:
            raise RuntimeError('Group comment notification delivery failed.')
    else:
        send_ticket_comment_notification(ticket=ticket, comment=comment, commented_by=current_user)


def _group_filtered_query(query):
    group = request.args.get('group', 'all')
    view = request.args.get('group_view', '')
    if group == 'none':
        query = query.filter(Ticket.group_id.is_(None))
    elif group != 'all':
        try:
            query = query.filter(Ticket.group_id == int(group))
        except ValueError:
            query = query.filter(False)
    if view in ('my_groups', 'unassigned_groups'):
        query = query.filter(Ticket.group_id.in_(user_group_ids(current_user.id)),
                             Ticket.status.notin_(['closed', 'resolved']))
        if view == 'unassigned_groups':
            query = query.filter(Ticket.assigned_to.is_(None))
    return query


def _category_assignment_defaults(category):
    group_id = _assignment_id(request.form.get('default_group_id'))
    assignee_id = _assignment_id(request.form.get('default_assignee_id'))
    if group_id:
        option = next((g for g in assignment_options() if g['id'] == group_id), None)
        if not option or (not option['enabled'] and group_id != category.default_group_id):
            raise ValueError('Choose an enabled default group.')
        if (assignee_id and filter_assignees_enabled()
                and assignee_id not in option['member_ids']):
            raise ValueError('The default assignee must belong to the default group.')
    if assignee_id and not db.session.get(User, assignee_id):
        raise ValueError('The default assignee does not exist.')
    category.default_group_id = group_id
    category.default_assignee_id = assignee_id

def sanitize_html(html_content):
    """Sanitize HTML content to prevent XSS while allowing safe formatting and images"""
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'b', 'i', 'u', 'ul', 'ol', 'li', 
        'blockquote', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'span', 'div'
    ]
    allowed_attrs = {
        'a': ['href', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
        '*': ['class']
    }
    allowed_protocols = ['http', 'https', 'data']  # Allow data URIs for inline images
    
    cleaned = bleach.clean(
        html_content,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols=allowed_protocols,
        strip=True
    )
    
    return cleaned

def mobile_aware_redirect(endpoint, **kwargs):
    """Helper function to redirect based on mobile context"""
    # Check if we're in mobile context by examining referrer
    is_mobile_context = False
    if request.referrer:
        is_mobile_context = '/mobile/' in request.referrer
    
    # Also check current path
    current_path = request.path
    if '/mobile/' in current_path:
        is_mobile_context = True
    
    # Or if explicit mobile parameter is passed
    if request.args.get('mobile') == '1' or request.form.get('mobile') == '1':
        is_mobile_context = True
    
    # Also check if user is on a mobile device
    if is_mobile_device():
        is_mobile_context = True
    
    app.logger.debug(f"Mobile context check - referrer: {request.referrer}, path: {current_path}, mobile param: {request.args.get('mobile')}, is_mobile_device: {is_mobile_device()}, final decision: {is_mobile_context}")
    
    if is_mobile_context:
        # For mobile context, redirect to mobile-specific routes or views
        if endpoint == 'tickets.view_ticket':
            # Force mobile view with mobile parameter
            return redirect(url_for('tickets.view_ticket', mobile=1, **kwargs))
        elif endpoint == 'tickets.tickets_dashboard':
            return redirect(url_for('mobile_tickets'))  # mobile tickets dashboard
        else:
            # For other endpoints, use the original endpoint
            return redirect(url_for(endpoint, **kwargs))
    else:
        # For desktop, use original endpoints
        return redirect(url_for(endpoint, **kwargs))

# Update Blueprint to use the correct template directory
tickets = Blueprint('tickets', __name__)



@tickets.route('/tickets/standalone_dashboard')
@login_required
def standalone_dashboard():
    """A clean standalone version of the dashboard for testing filtering"""
    app.logger.debug(f"STANDALONE DASHBOARD - Raw request URL: {request.url}")
    app.logger.debug(f"STANDALONE DASHBOARD - Raw query args: {request.args}")
    
    # Get filter params from the request
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    category_filter = request.args.get('category', 'all')
    
    app.logger.debug(f"STANDALONE DASHBOARD - Filters: status={status_filter}, priority={priority_filter}, category={category_filter}")
    
    # Start with all tickets
    query = Ticket.query
    
    # Apply filters based on request parameters
    if status_filter != 'all':
        query = query.filter(Ticket.status == status_filter)
    
    if priority_filter != 'all':
        try:
            priority_value = int(priority_filter)
            query = query.filter(Ticket.priority == priority_value)
        except (ValueError, TypeError):
            app.logger.error(f"Invalid priority value: {priority_filter}")
    
    if category_filter != 'all':
        try:
            category_id = int(category_filter)
            query = query.filter(Ticket.category_id == category_id)
        except (ValueError, TypeError):
            app.logger.error(f"Invalid category value: {category_filter}")
            
    # Get tickets based on filters
    query = _group_filtered_query(query)
    if request.args.get('group_by') == 'group':
        tickets = query.outerjoin(Ticket.group).order_by(Ticket.group_id, Ticket.created_at.desc()).all()
    else:
        tickets = query.order_by(Ticket.created_at.desc()).all()
    app.logger.debug(f"STANDALONE DASHBOARD - Found {len(tickets)} tickets")
    
    # Convert to dictionaries for the template
    ticket_dicts = []
    for ticket in tickets:
        t = {
            'id': ticket.id,
            'title': ticket.title,
            'status': ticket.status,
            'priority': ticket.priority,
            'assigned_to': ticket.assigned_to,
            'group_id': ticket.group_id,
            'group': ticket.group,
            'created_by': ticket.created_by,
            'created_at': ticket.created_at,
            'updated_at': ticket.updated_at,
            'category': {
                'id': ticket.category.id,
                'name': ticket.category.name
            }
        }
        
        # Add assigned technician info if available
        if ticket.assigned_technician:
            t['assigned_technician'] = {
                'username': ticket.assigned_technician.username
            }
        else:
            t['assigned_technician'] = None
            
        ticket_dicts.append(t)
    
    # Get data for dropdowns
    categories = [
        {
            'id': category.id,
            'name': category.name
        }
        for category in TicketCategory.query.all()
    ]
    
    ticket_statuses = [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.PENDING,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED
    ]
    
    # Create filter_info for the template
    filter_info = {
        'status': status_filter,
        'priority': priority_filter,
        'category': category_filter,
        'timestamp': int(datetime.now().timestamp() * 1000)
    }
    
    # Disable caching for this request
    @after_this_request
    def add_no_cache(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    # Use the standalone template
    return render_template('tickets/standalone_dashboard.html',
                           tickets=ticket_dicts,
                           categories=categories,
                           ticket_statuses=ticket_statuses,
                           ticket_count=len(ticket_dicts),
                           filter_info=filter_info,
                           timestamp=filter_info['timestamp'])

@tickets.route('/tickets/dashboard')
@login_required
def tickets_dashboard():
    """Display all tickets with filtering options"""
    # Import the TicketStatus class from models (even though it's imported at the top)
    from models import TicketStatus, Ticket
    
    app.logger.debug(f"Raw request URL: {request.url}")
    app.logger.debug(f"Raw query args: {request.args}")
    
    # Get filters from request args with appropriate defaults
    # Check if no URL parameters or only cache-busting parameters
    cache_params = ['timestamp', 'rand', '_t']
    has_only_cache_params = all(k in cache_params for k in request.args.keys()) if request.args else True
    
    # Extract raw filter values from the request (for debugging)
    raw_status_filter = request.args.get('status')
    raw_category_filter = request.args.get('category')
    raw_priority_filter = request.args.get('priority')
    raw_technician_filter = request.args.get('technician')
    raw_assigned_to = request.args.get('assigned_to')
    raw_created_by = request.args.get('created_by')
    raw_search_query = request.args.get('search')
    
    app.logger.debug(f"Raw filter values from request - status: {raw_status_filter}, category: {raw_category_filter}, priority: {raw_priority_filter}, technician: {raw_technician_filter}, assigned_to: {raw_assigned_to}, created_by: {raw_created_by}, search: {raw_search_query}")
    
    # Determine final filter values
    if not request.args or has_only_cache_params:
        app.logger.debug("No filters specified or only cache parameters, defaulting to open tickets")
        status_filter = 'open'
        category_filter = 'all'
        priority_filter = 'all'
        technician_filter = 'all'
        assigned_to_filter = 'all'
        created_by_filter = 'all'
        search_query = ''
    else:
        # Use 'all' as default if not provided
        status_filter = raw_status_filter if raw_status_filter not in (None, '') else 'all'
        category_filter = raw_category_filter if raw_category_filter not in (None, '') else 'all'
        priority_filter = raw_priority_filter if raw_priority_filter not in (None, '') else 'all'
        technician_filter = raw_technician_filter if raw_technician_filter not in (None, '') else 'all'
        assigned_to_filter = raw_assigned_to if raw_assigned_to not in (None, '') else 'all'
        created_by_filter = raw_created_by if raw_created_by not in (None, '') else 'all'
        search_query = raw_search_query if raw_search_query not in (None, '') else ''
        
        # Log explicit parameter requests for debugging
        app.logger.debug(f"Explicit filter request - status:{status_filter}, category:{category_filter}, priority:{priority_filter}, technician:{technician_filter}")
        
        # Force-convert these to appropriate types for comparison
        status_filter = status_filter.strip().lower()
        app.logger.debug(f"Status filter from request (normalized): {status_filter}")
        app.logger.debug(f"Category filter from request: {category_filter}")
        app.logger.debug(f"Priority filter from request: {priority_filter}")
        app.logger.debug(f"Technician filter from request: {technician_filter}")
    
    # Verify that status filter is valid
    valid_statuses = vars(TicketStatus).values()
    if status_filter != 'all' and status_filter not in valid_statuses:
        app.logger.warning(f"Invalid status filter '{status_filter}', defaulting to 'open'")
        status_filter = 'open'
    
    # If status is explicitly set to 'all', make sure it's respected
    if status_filter == 'all':
        app.logger.debug("Status filter is 'all', showing all tickets")
    
    # Add debug logging to see what filters are being applied
    app.logger.debug(f"Ticket dashboard filters - status: {status_filter}, category: {category_filter}, priority: {priority_filter}, technician: {technician_filter}")

    # Add some diagnostic queries to check database status values
    # Count status distribution in database
    status_counts = db.session.execute(
        text("""
        SELECT status, COUNT(*) as count
        FROM ticket
        GROUP BY status
        ORDER BY status
        """)
    ).fetchall()
    app.logger.debug("Status counts in database:")
    for status, count in status_counts:
        app.logger.debug(f"  {status}: {count} tickets")

    # Get archived filter from the request
    show_archived = request.args.get('archived', 'false').lower() == 'true'
    
    # Base query
    query = Ticket.query
    
    # Apply filters
    app.logger.debug(f"Before filtering, query: {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
    
    # By default, don't show archived tickets unless explicitly requested
    if not show_archived:
        query = query.filter(Ticket.archived == False)
        app.logger.debug(f"Filtered to non-archived tickets only")
    
    # For explicit status checking, keep track of raw query string
    raw_status_filter = status_filter
    
    if status_filter != 'all':
        if status_filter == 'open':
            # Include open, in_progress, and pending tickets for the "open" filter
            query = query.filter(Ticket.status.in_(['open', 'in_progress', 'pending']))
            app.logger.debug(f"After 'open' status filter (includes open/in_progress/pending): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
        else:
            # For other specific statuses, filter exactly
            query = query.filter(Ticket.status == status_filter)
            app.logger.debug(f"After status filter ({status_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
    if category_filter != 'all':
        try:
            category_id = int(category_filter)
            query = query.filter(Ticket.category_id == category_id)
            app.logger.debug(f"After category filter ({category_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
        except (ValueError, TypeError):
            app.logger.error(f"Invalid category filter value: {category_filter}")

    if priority_filter != 'all':
        try:
            priority_value = int(priority_filter)
            query = query.filter(Ticket.priority == priority_value)
            app.logger.debug(f"After priority filter ({priority_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
        except (ValueError, TypeError):
            app.logger.error(f"Invalid priority filter value: {priority_filter}")
            
    if technician_filter != 'all':
        if technician_filter == 'unassigned':
            query = query.filter(Ticket.assigned_to.is_(None))
            app.logger.debug("Filtered to unassigned tickets")
        elif technician_filter == 'me':
            query = query.filter(Ticket.assigned_to == current_user.id)
            app.logger.debug(f"Filtered to current user ({current_user.id}) tickets")
        else:
            try:
                technician_id = int(technician_filter)
                query = query.filter(Ticket.assigned_to == technician_id)
                app.logger.debug(f"After technician filter ({technician_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
            except (ValueError, TypeError):
                app.logger.error(f"Invalid technician filter value: {technician_filter}")
            
    # Handle assigned_to filter separately from technician_filter
    if assigned_to_filter != 'all':
        try:
            assigned_id = int(assigned_to_filter)
            query = query.filter(Ticket.assigned_to == assigned_id)
            app.logger.debug(f"After assigned_to filter ({assigned_to_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
        except (ValueError, TypeError):
            app.logger.error(f"Invalid assigned_to filter value: {assigned_to_filter}")
            
    # Handle created_by filter
    if created_by_filter != 'all':
        try:
            creator_id = int(created_by_filter)
            query = query.filter(Ticket.created_by == creator_id)
            app.logger.debug(f"After created_by filter ({created_by_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
        except (ValueError, TypeError):
            app.logger.error(f"Invalid created_by filter value: {created_by_filter}")
            
    # Handle search query for keywords in title and description
    requester_email = request.args.get('requester_email', '').strip()
    if requester_email:
        query = query.filter(func.lower(Ticket.external_email) == requester_email.lower())

    if search_query:
        app.logger.debug(f"Applying search query: {search_query}")
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Ticket.title.ilike(search_term),
                Ticket.description.ilike(search_term)
            )
        )
        app.logger.debug(f"After search query filter: {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")

    # Shared ownership views retain all existing status/category/search filters.
    query = _group_filtered_query(query)
    if request.args.get('group_by') == 'group':
        tickets = query.order_by(Ticket.group_id, Ticket.created_at.desc()).all()
    else:
        tickets = query.order_by(Ticket.created_at.desc()).all()
    
    # Add special debug logs for status filter
    app.logger.debug(f"Status filter applied: '{raw_status_filter}'")
    app.logger.debug(f"Found {len(tickets)} tickets matching filters: status={status_filter}, category={category_filter}, priority={priority_filter}, technician={technician_filter}")
    
    # Add debug information about each ticket found
    for ticket in tickets:
        app.logger.debug(f"Ticket #{ticket.id}: {ticket.title} - Status: {ticket.status}, Category: {ticket.category_id}, Priority: {ticket.priority}")
        
    # FORCE FILTER - Apply filter directly to the data
    # No need for the force filtering here as the SQL query should handle it correctly
    # We'll keep a debug log of found tickets
    app.logger.debug(f"Found tickets after SQL filtering: {len(tickets)}")
    
    for ticket in tickets:
        app.logger.debug(f"Found ticket: ID={ticket.id}, Title={ticket.title}, Status={ticket.status}, Priority={ticket.priority}")
    
    # Disable caching for this request to make sure we're getting fresh data
    @after_this_request
    def add_no_cache(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    # Add a temporary filter to show exactly what's going to the template
    app.logger.debug(f"FINAL TICKETS TO TEMPLATE:")
    for ticket in tickets:
        app.logger.debug(f"FINAL Ticket #{ticket.id}: {ticket.title} - Status: {ticket.status} - Priority: {ticket.priority}")
        
    # Double-check all tickets have data in correct format (debug step)
    app.logger.debug(f"Double-checking all tickets in the database:")
    all_tickets = Ticket.query.all()
    for ticket in all_tickets:
        app.logger.debug(f"DB Ticket #{ticket.id}: {ticket.title} - Status: '{ticket.status}' - Priority: {ticket.priority}")
    
    # Get categories and convert to dictionaries
    categories_objects = TicketCategory.query.all()
    categories = [
        {
            'id': category.id,
            'name': category.name,
            'description': category.description
        }
        for category in categories_objects
    ]
    # Get all valid ticket statuses
    ticket_statuses = [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.PENDING,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED
    ]

    # For robust filtering, convert SQLAlchemy objects to simple dictionaries
    # This will eliminate any potential SQLAlchemy caching issues
    filtered_tickets = []
    for ticket in tickets:
        # Create a simple dict with only the data we need
        # Check NEW badge status with debug logging
        new_badge_status = ticket.has_unread_activity
        app.logger.debug(f"🔍 TICKET #{ticket.id} NEW BADGE CHECK: {new_badge_status}")
        
        ticket_dict = {
            'id': ticket.id,
            'title': ticket.title,
            'status': ticket.status,
            'priority': ticket.priority,
            'assigned_to': ticket.assigned_to,
            'group_id': ticket.group_id,
            'group': ticket.group,
            'created_by': ticket.created_by,
            'created_at': ticket.created_at,
            'updated_at': ticket.updated_at,
            'due_date': ticket.due_date,
            'has_unread_activity': new_badge_status,
            'category': {
                'id': ticket.category.id,
                'name': ticket.category.name
            }
        }
        
        # Add assigned technician info if available
        if ticket.assigned_technician:
            ticket_dict['assigned_technician'] = {
                'username': ticket.assigned_technician.username
            }
        else:
            ticket_dict['assigned_technician'] = None
        
        # Add creator info - handle external users properly
        if ticket.is_external_user():
            ticket_dict['creator'] = {
                'id': None,  # External users don't have internal IDs
                'username': ticket.get_display_name(),
                'is_external': True,
                'external_email': ticket.external_email
            }
        else:
            ticket_dict['creator'] = {
                'id': ticket.creator.id,
                'username': ticket.creator.username,
                'is_external': False
            }
            
        filtered_tickets.append(ticket_dict)
    
    # Final logging to verify what's being sent
    app.logger.debug(f"RENDERING TEMPLATE WITH {len(filtered_tickets)} TICKETS:")
    for idx, ticket in enumerate(filtered_tickets):
        app.logger.debug(f"RENDER TICKET #{idx+1}: ID={ticket['id']}, Title={ticket['title']}, Status={ticket['status']}, Priority={ticket['priority']}")
    
    # Add timestamp to prevent any caching
    timestamp = int(datetime.now().timestamp() * 1000)
    
    # Pass very explicit filtering info to the template
    filter_info = {
        'status': status_filter,
        'category': category_filter,
        'priority': priority_filter,
        'technician': technician_filter,
        'search': search_query,
        'timestamp': timestamp
    }
    
    # Get all technicians for the technician filter dropdown
    technicians = User.query.all()
    
    # Check if user is on a mobile device
    from app import is_mobile_device
    if is_mobile_device():
        # Convert string filters to integers for the template
        assigned_to_int = None
        if assigned_to_filter != 'all':
            try:
                assigned_to_int = int(assigned_to_filter)
            except (ValueError, TypeError):
                pass
                
        created_by_int = None
        if created_by_filter != 'all':
            try:
                created_by_int = int(created_by_filter)
            except (ValueError, TypeError):
                pass
        
        return render_template('tickets/mobile_dashboard.html', 
                             tickets=filtered_tickets,
                             categories=categories,
                             ticket_statuses=ticket_statuses,
                             technicians=technicians,
                             ticket_count=len(filtered_tickets),
                             filter_info=filter_info,
                             timestamp=timestamp,
                             filter_status=status_filter,
                             filter_assigned_to=assigned_to_int,
                             filter_created_by=created_by_int)
    else:
        # Compute Command-Center metrics across ALL non-archived tickets (not the filtered subset)
        from datetime import timedelta
        metrics_base = Ticket.query.filter(Ticket.archived == False)
        m_open = metrics_base.filter(Ticket.status == 'open').count()
        m_in_progress = metrics_base.filter(Ticket.status == 'in_progress').count()
        m_pending = metrics_base.filter(Ticket.status == 'pending').count()
        m_active = m_open + m_in_progress + m_pending
        m_high = metrics_base.filter(Ticket.status.in_(['open','in_progress','pending']),
                                     Ticket.priority >= 2).count()
        m_urgent = metrics_base.filter(Ticket.status.in_(['open','in_progress','pending']),
                                       Ticket.priority == 3).count()
        m_unassigned = metrics_base.filter(Ticket.status.in_(['open','in_progress','pending']),
                                           Ticket.assigned_to.is_(None)).count()
        m_mine = metrics_base.filter(Ticket.status.in_(['open','in_progress','pending']),
                                     Ticket.assigned_to == current_user.id).count()
        week_ago = datetime.now() - timedelta(days=7)
        m_resolved_week = metrics_base.filter(Ticket.status.in_(['resolved','closed']),
                                              Ticket.updated_at >= week_ago).count()
        m_new_today = metrics_base.filter(Ticket.created_at >= datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)).count()

        ticket_metrics = {
            'active': m_active, 'open': m_open, 'in_progress': m_in_progress,
            'pending': m_pending, 'high': m_high, 'urgent': m_urgent,
            'unassigned': m_unassigned, 'mine': m_mine,
            'resolved_week': m_resolved_week, 'new_today': m_new_today,
        }
        return render_template('tickets/dashboard.html', 
                             tickets=filtered_tickets,
                             categories=categories,
                             ticket_statuses=ticket_statuses,
                             technicians=technicians,
                             ticket_count=len(filtered_tickets),
                             filter_info=filter_info,
                             timestamp=timestamp,
                             ticket_metrics=ticket_metrics)

@tickets.route('/tickets/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    """Create a new ticket"""
    form = TicketForm()

    # Populate category choices
    form.category_id.choices = [(c.id, c.name) for c in TicketCategory.query.all()]

    # Populate technician choices for all users
    form.assigned_to.choices = [(u.id, u.username) for u in User.query.all()]
    form.assigned_to.choices.insert(0, (0, 'Unassigned'))
    form.assigned_to.choices.insert(0, (-1, 'Use category default'))

    if form.validate_on_submit():
        try:
            # Start a transaction
            app.logger.debug("Starting ticket creation transaction")

            # Create the ticket first
            # Handle due date - ensure it has proper timezone if provided
            due_date = None
            if form.due_date.data:
                app.logger.debug(f"Processing due date from form: {form.due_date.data}")
                # Make sure we create a proper datetime object at midnight in UTC
                date_obj = form.due_date.data
                due_date = datetime(
                    year=date_obj.year,
                    month=date_obj.month,
                    day=date_obj.day,
                    tzinfo=pytz.UTC
                )
                app.logger.debug(f"Processed due date: {due_date}")
            
            ticket = Ticket(
                title=form.title.data,
                description=sanitize_html(form.description.data),
                category_id=form.category_id.data,
                priority=form.priority.data,
                created_by=current_user.id,
                assigned_to=None,
                due_date=due_date
            )

            # Add ticket to session
            db.session.add(ticket)
            db.session.flush()  # This assigns the ID but doesn't commit
            explicit_group = request.form.get('group_id', '__default__') != '__default__'
            explicit_assignee = ('assigned_to' in request.form
                                 and request.form.get('assigned_to') != '-1')
            with db.session.no_autoflush:
                ticket.group_id = _assignment_id(request.form.get('group_id')) if explicit_group else None
                ticket.assigned_to = _assignment_id(request.form.get('assigned_to')) if explicit_assignee else None
                apply_category_defaults(ticket, explicit_group=explicit_group,
                                        explicit_assignee=explicit_assignee)
                new_group, new_assignee = ticket.group_id, ticket.assigned_to
                ticket.group_id, ticket.group = None, None
                ticket.assigned_to, ticket.assigned_technician = None, None
                assignment = apply_assignment(
                    ticket, new_group, new_assignee,
                    actor_id=current_user.id, notify=False, event='new_ticket')
                if assignment['assignee_cleared']:
                    flash('The assignee was cleared because they are not a member of the selected group.', 'warning')
            
            # Handle file upload if present
            if form.attachment.data:
                file = form.attachment.data
                if file and file.filename:
                    # Secure the filename and add timestamp
                    from werkzeug.utils import secure_filename
                    import os
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_ticket{ticket.id}_{filename}"
                    
                    # Save the file
                    upload_dir = os.path.join('static', 'uploads', 'ticket_attachments')
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, unique_filename)
                    file.save(file_path)
                    
                    # Store the filename in the database
                    ticket.attachment = unique_filename
                    app.logger.info(f"Saved ticket attachment: {unique_filename}")

            app.logger.debug(f"Created ticket with ID: {ticket.id}")

            if not ticket.id:
                raise ValueError("Failed to generate ticket ID")

            # Create history entry
            history = TicketHistory(
                ticket_id=ticket.id,
                user_id=current_user.id,
                action="created",
                details="Ticket created",
                created_at=datetime.now(pytz.UTC)
            )

            # Add history to session
            db.session.add(history)

            # Verify both objects are valid before committing
            if not history.ticket_id or not history.user_id:
                raise ValueError("Invalid history entry data")

            # Commit both changes
            db.session.commit()
            app.logger.info(f"Successfully created ticket {ticket.id} with history entry")
            
            from ticket_ai import queue_initial_analysis
            queue_initial_analysis(ticket.id)
            
            # Send new ticket notification to all users
            try:
                app.logger.info(f"Sending new ticket notification to all users for ticket #{ticket.id}")
                notification_result = True if ticket.group_id or ticket.assigned_to else send_new_ticket_notification(
                    ticket=ticket,
                    created_by=current_user
                )
                
                if notification_result:
                    app.logger.info("New ticket notification sent successfully to all users!")
                else:
                    app.logger.warning("Failed to send new ticket notification to all users")
            except Exception as e:
                app.logger.error(f"Exception sending new ticket notification: {str(e)}")
                import traceback
                app.logger.error(f"Exception traceback: {traceback.format_exc()}")
            
            # Send email notification if the ticket is assigned to someone
            if ticket.group_id or ticket.assigned_to:
                try:
                    app.logger.info(f"Sending initial assignment notification for ticket #{ticket.id}")
                    
                    # Now send the notification
                    from email_utils import send_ticket_assigned_notification
                    _notify_ticket_assignment(ticket, event='new_ticket')
                    result = True
                    
                    app.logger.info(f"Initial assignment notification result: {result}")
                    if not result:
                        app.logger.error("Initial ticket assignment notification failed!")
                    else:
                        app.logger.info("Initial ticket assignment notification sent successfully!")
                except Exception as e:
                    app.logger.error(f"Failed to send initial assignment notification: {str(e)}")
                    flash('Ticket saved, but assignment notification delivery failed.', 'warning')
                    # Print full exception traceback for debugging
                    import traceback
                    app.logger.error(f"Exception traceback: {traceback.format_exc()}")
            
            flash('Ticket created successfully', 'success')
            _is_ajax = request.args.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if _is_ajax:
                return jsonify({
                    'ok': True,
                    'ticket_id': ticket.id,
                    'redirect': url_for('tickets.view_ticket', ticket_id=ticket.id),
                })
            return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket.id)

        except ValueError as ve:
            db.session.rollback()
            app.logger.error(f"Validation error in ticket creation: {str(ve)}")
            flash(str(ve), 'error')
            
            # Choose template based on device type
            if is_mobile_device():
                return render_template('tickets/mobile_create.html', form=form)
            else:
                return render_template('tickets/create.html', form=form, )

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating ticket: {str(e)}")
            flash('Error creating ticket. Please try again.', 'error')
            
            # Choose template based on device type
            if is_mobile_device():
                return render_template('tickets/mobile_create.html', form=form)
            else:
                return render_template('tickets/create.html', form=form, )

    # Choose template based on device type
    if is_mobile_device():
        app.logger.debug("Using mobile template for ticket creation")
        return render_template('tickets/mobile_create.html', form=form)
    else:
        app.logger.debug("Using desktop template for ticket creation")
        return render_template('tickets/create.html', form=form, )

@tickets.route('/tickets/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    """View a specific ticket"""
    ticket_obj = Ticket.query.get_or_404(ticket_id)

    # All users can view all tickets

    # Mark ticket as viewed by current user and log the FIRST view in history
    try:
        ticket_obj.mark_as_viewed(current_user.id)
        
        # Only add history entry if this is the first time this user viewed this ticket
        existing_view_history = TicketHistory.query.filter_by(
            ticket_id=ticket_obj.id,
            user_id=current_user.id,
            action="viewed"
        ).first()
        
        if not existing_view_history:
            view_history = TicketHistory(
                ticket_id=ticket_obj.id,
                user_id=current_user.id,
                action="viewed",
                details=f"Ticket first viewed by {current_user.username}",
                created_at=datetime.now(pytz.UTC)
            )
            db.session.add(view_history)
            app.logger.debug(f"Ticket #{ticket_id} FIRST VIEW by user {current_user.username}")
        else:
            app.logger.debug(f"Ticket #{ticket_id} already viewed by user {current_user.username}, no new history entry")
        
        db.session.commit()
    except Exception as e:
        app.logger.warning(f"Failed to mark ticket #{ticket_id} as viewed: {str(e)}")
        db.session.rollback()
        # Don't let this affect the main functionality

    # Create forms for comments and editing
    comment_form = TicketCommentForm()
    form = TicketForm()
    
    # Get categories and technicians for the modal forms
    categories_objects = TicketCategory.query.all()
    # Convert categories to dictionaries
    categories = [
        {
            'id': category.id,
            'name': category.name,
            'description': category.description
        }
        for category in categories_objects
    ]
    technicians = User.query.all()

    # Convert ticket to dictionary to avoid SQLAlchemy caching issues
    ticket = {
        'id': ticket_obj.id,
        'title': ticket_obj.title,
        'description': ticket_obj.description,
        'category_id': ticket_obj.category_id,
        'status': ticket_obj.status,
        'priority': ticket_obj.priority,
        'assigned_to': ticket_obj.assigned_to,
        'group_id': ticket_obj.group_id,
        'group': ticket_obj.group,
        'created_by': ticket_obj.created_by,
        'created_at': ticket_obj.created_at,
        'updated_at': ticket_obj.updated_at,
        'due_date': ticket_obj.due_date,
        'custom_values': ticket_obj.custom_values or {},
        'tags': ticket_obj.tags or [],
        'cc_user_ids': ticket_obj.cc_user_ids or [],
        'cc_group_ids': ticket_obj.cc_group_ids or [],
        'attachment': ticket_obj.attachment,
        'category': {
            'id': ticket_obj.category.id,
            'name': ticket_obj.category.name
        },
        'comments': [{
            'id': comment.id,
            'content': comment.content,
            'is_private': comment.is_private,
            'created_at': comment.created_at,
            'attachment': comment.attachment,
            'user': {
                'id': comment.user.id,
                'username': comment.user.username,
                'color': comment.user.color
            }
        } for comment in ticket_obj.comments],
        'history': [{
            'id': history.id,
            'action': history.action,
            'details': history.details,
            'created_at': history.created_at,
            'user': {
                'id': history.user.id,
                'username': history.user.username
            }
        } for history in ticket_obj.history]
    }
    
    # Add creator info - handle external users properly
    if ticket_obj.is_external_user():
        ticket['creator'] = {
            'id': None,  # External users don't have internal IDs
            'username': ticket_obj.get_display_name(),
            'is_external': True,
            'email': ticket_obj.external_email,
            'external_email': ticket_obj.external_email
        }
    else:
        ticket['creator'] = {
            'id': ticket_obj.creator.id,
            'username': ticket_obj.creator.username,
            'email': ticket_obj.creator.email,
            'is_external': False
        }
    
    if ticket_obj.assigned_technician:
        ticket['assigned_technician'] = {
            'id': ticket_obj.assigned_technician.id,
            'username': ticket_obj.assigned_technician.username
        }
    else:
        ticket['assigned_technician'] = None

    # Populate form with current ticket data
    if request.method == 'GET':
        form.title.data = ticket_obj.title
        form.description.data = ticket_obj.description
        form.category_id.data = ticket_obj.category_id
        form.priority.data = ticket_obj.priority
        form.due_date.data = ticket_obj.due_date

        # Populate category choices
        form.category_id.choices = [(c['id'], c['name']) for c in categories]

        # Populate technician choices for admin users and ticket creators
        if current_user.is_admin or current_user.id == ticket_obj.created_by:
            form.assigned_to.choices = [(u.id, u.username) for u in technicians]

    timezone = pytz.timezone(current_user.timezone or 'America/Los_Angeles')

    def local_time(value):
        if value.tzinfo is None:
            value = pytz.UTC.localize(value)
        return value.astimezone(timezone)

    def display_time(value):
        return local_time(value).strftime('%b %-d, %-I:%M %p')

    initial_email = ProcessedEmail.query.filter(
        ProcessedEmail.ticket_id == ticket_obj.id,
        ProcessedEmail.processed_at <= local_time(ticket_obj.created_at) + timedelta(minutes=2)
    ).first()
    ticket['source'] = 'Email' if ticket_obj.is_external_user() or initial_email else 'Web'
    activity = [
        {'kind': 'comment', 'data': item, 'created_at': item['created_at']}
        for item in ticket['comments']
    ]
    activity.extend(
        {'kind': 'note' if item['action'] == 'internal_note' else 'history',
         'data': item, 'created_at': item['created_at']}
        for item in ticket['history'] if item['action'] not in ('created', 'commented')
    )
    activity.append({'kind': 'opening', 'data': ticket, 'created_at': ticket['created_at']})
    activity.sort(key=lambda entry: local_time(entry['created_at']), reverse=True)
    for entry in activity:
        entry['display_time'] = display_time(entry['created_at'])
    last_reply = max((local_time(item['created_at']) for item in ticket['comments']
                      if item['user']['username'] != 'AI Assistant'), default=None)
    display_last_reply = None
    if last_reply:
        seconds = max(0, (datetime.now(pytz.UTC) - last_reply).total_seconds())
        for unit, duration in (('month', 2592000), ('day', 86400), ('hour', 3600), ('minute', 60)):
            count = int(seconds // duration)
            if count:
                display_last_reply = f"{count} {unit}{'s' if count != 1 else ''} ago"
                break
        else:
            display_last_reply = 'just now'
    previous_ticket = Ticket.query.filter(Ticket.id < ticket_obj.id, Ticket.archived == False).order_by(Ticket.id.desc()).first()
    next_ticket = Ticket.query.filter(Ticket.id > ticket_obj.id, Ticket.archived == False).order_by(Ticket.id).first()
    from automation_models import AutomationTicketLink
    automation_links = AutomationTicketLink.query.filter(
        db.or_(AutomationTicketLink.ticket_id == ticket_obj.id,
               AutomationTicketLink.linked_ticket_id == ticket_obj.id)).all()
    automation_linked_ids = sorted({link.linked_ticket_id if link.ticket_id == ticket_obj.id else link.ticket_id
                                   for link in automation_links})
    return render_template(
        'tickets/view.html', ticket=ticket, comment_form=comment_form, form=form,
        categories=categories, technicians=technicians, TicketStatus=TicketStatus,
        creator=ticket['creator'], activity=activity,
        display_created=display_time(ticket['created_at']),
        display_updated=display_time(ticket['updated_at']),
        display_last_reply=display_last_reply,
        automation_linked_ids=automation_linked_ids,
        display_timezone=f"All times {local_time(ticket['created_at']).tzname()} ({timezone.zone})",
        previous_ticket_id=previous_ticket.id if previous_ticket else None,
        next_ticket_id=next_ticket.id if next_ticket else None,
        sidebar_mobile=is_mobile_device() or request.args.get('mobile') == '1')

@tickets.route('/tickets/<int:ticket_id>/comment', methods=['POST'])
@login_required
def add_comment(ticket_id):
    """Add a comment to a ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    form = TicketCommentForm()
    mode = request.form.get('mode', 'reply')
    after_status = request.form.get('after_status', '')
    if mode not in ('reply', 'internal_note') or after_status not in ('', 'open', 'in_progress', 'pending', 'resolved', 'closed'):
        flash('Invalid reply settings. Nothing was saved.', 'error')
        return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
    
    if form.validate_on_submit():
        content = sanitize_html(form.content.data)
        if not bleach.clean(content, tags=[], strip=True).strip() and '<img ' not in content:
            flash('Enter a reply or note before sending.', 'error')
            return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
        if mode == 'internal_note':
            if form.attachment.data and form.attachment.data.filename:
                flash('Attachments are supported on replies, not internal notes.', 'error')
                return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
            try:
                db.session.add(TicketHistory(ticket_id=ticket.id, user_id=current_user.id,
                                             action='internal_note', details=content,
                                             created_at=datetime.now(pytz.UTC)))
                ticket.updated_at = datetime.now(pytz.UTC)
                db.session.commit()
                flash('Internal note saved. No email was sent.', 'success')
            except Exception:
                db.session.rollback()
                app.logger.exception('Failed to save internal ticket note')
                flash('Could not save the internal note.', 'error')
            return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
        try:
            # Create a new comment directly with explicit autoincrement
            comment = TicketComment(
                ticket_id=ticket.id,
                user_id=current_user.id,
                content=content,
                created_at=datetime.now(pytz.UTC),
                updated_at=datetime.now(pytz.UTC)
            )
            db.session.add(comment)
            db.session.flush()  # Get the comment ID
            
            # Handle file upload if present
            if form.attachment.data:
                file = form.attachment.data
                if file and file.filename:
                    # Secure the filename and add timestamp
                    from werkzeug.utils import secure_filename
                    import os
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_comment{comment.id}_{filename}"
                    
                    # Save the file
                    upload_dir = os.path.join('static', 'uploads', 'ticket_attachments')
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, unique_filename)
                    file.save(file_path)
                    
                    # Store the filename in the database
                    comment.attachment = unique_filename
                    app.logger.info(f"Saved comment attachment: {unique_filename}")
            
            ticket.updated_at = datetime.now(pytz.UTC)
            if after_status and after_status != ticket.status:
                old_status = ticket.status
                ticket.status = after_status
                db.session.add(TicketHistory(
                    ticket_id=ticket.id, user_id=current_user.id, action='status_changed',
                    details=f'Status changed from {old_status} to {after_status}',
                    created_at=datetime.now(pytz.UTC)))
            db.session.commit()
            app.logger.debug(f"Added comment to ticket #{ticket.id}")
            
            # Create history entry directly
            try:
                history = TicketHistory(
                    ticket_id=ticket.id,
                    user_id=current_user.id,
                    action="commented",
                    details=f"Comment added by {current_user.username}",
                    created_at=datetime.now(pytz.UTC)
                )
                db.session.add(history)
                db.session.commit()
                app.logger.debug("Added comment history entry")
            except Exception as e:
                app.logger.error(f"Error creating comment history entry: {str(e)}")
                # Continue anyway since comment was added successfully
                pass
            
            # Send notification email to all relevant parties
            try:
                app.logger.debug(f"Sending comment notification for ticket #{ticket.id}")
                
                # The email function will create an app context if needed
                _notify_ticket_comment(ticket, comment)
            except Exception as e:
                app.logger.error(f"Failed to send comment notification: {str(e)}")
                flash('Comment saved, but notification delivery failed.', 'warning')
                import traceback
                app.logger.error(f"Exception traceback: {traceback.format_exc()}")
                # Continue anyway - the comment was saved
            
            flash('Comment added successfully', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding comment: {str(e)}")
            import traceback
            app.logger.error(f"Comment exception traceback: {traceback.format_exc()}")
            
            # Check if this is a sequence error and auto-fix it
            if "duplicate key value violates unique constraint" in str(e) and "ticket_comment_pkey" in str(e):
                try:
                    app.logger.info("Detected comment sequence issue, attempting to fix...")
                    # Reset the sequence to the correct value
                    db.session.execute(text("SELECT setval('ticket_comment_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM ticket_comment), false);"))
                    db.session.commit()
                    app.logger.info("Comment sequence fixed successfully")
                    
                    # Retry the comment insertion
                    saved_attachment = comment.attachment
                    comment = TicketComment(
                        ticket_id=ticket.id,
                        user_id=current_user.id,
                        content=content,
                        attachment=saved_attachment,
                        created_at=datetime.now(pytz.UTC),
                        updated_at=datetime.now(pytz.UTC)
                    )
                    db.session.add(comment)
                    ticket.updated_at = datetime.now(pytz.UTC)
                    if after_status and after_status != ticket.status:
                        old_status = ticket.status
                        ticket.status = after_status
                        db.session.add(TicketHistory(
                            ticket_id=ticket.id, user_id=current_user.id, action='status_changed',
                            details=f'Status changed from {old_status} to {after_status}',
                            created_at=datetime.now(pytz.UTC)))
                    db.session.commit()
                    _notify_ticket_comment(ticket, comment)
                    app.logger.info(f"Comment successfully added after sequence fix for ticket #{ticket.id}")
                    flash('Comment added successfully', 'success')
                    return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
                except Exception as retry_error:
                    app.logger.error(f"Failed to auto-fix sequence error: {str(retry_error)}")
                    db.session.rollback()
            
            flash('Error adding comment', 'error')
    
    if form.errors:
        flash('Your reply was not saved. Check the text and try again.', 'error')
    return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)

@tickets.route('/tickets/<int:ticket_id>/status', methods=['POST'])
@login_required
def update_status(ticket_id):
    """Update ticket status from the responsive detail page."""
    ticket = Ticket.query.get_or_404(ticket_id)
    new_status = request.form.get('status')
    comment = request.form.get('comment', '')
    
    app.logger.debug(f"Updating ticket #{ticket_id} status from '{ticket.status}' to '{new_status}'")
    app.logger.debug(f"Requested by user: {current_user.id} (admin: {current_user.is_admin})")
    
    # Allow any authenticated user to update status regardless of ownership
    
    valid_statuses = ['open', 'in_progress', 'pending', 'resolved', 'closed']
    if new_status not in valid_statuses:
        flash('Invalid ticket status', 'error')
        return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
    
    # Store old status for history and flag for tracking success
    old_status = ticket.status
    status_updated = False
    
    try:
        # Critical operation: Update the status
        ticket.status = new_status
        app.logger.debug(f"Changed status to: {ticket.status}")
        
        # Add status change to history
        details = f"Status changed from {old_status} to {new_status}"
        if comment:
            details += f" - Comment: {comment}"
            
        # Save the status change first
        db.session.commit()
        app.logger.debug("Committed status change")
        
        # Create history entry directly instead of using log_history method
        try:
            history = TicketHistory(
                ticket_id=ticket.id,
                user_id=current_user.id,
                action="status_changed",
                details=details,
                created_at=datetime.now(pytz.UTC)
            )
            db.session.add(history)
            db.session.commit()
            app.logger.debug("Added history entry")
        except Exception as e:
            app.logger.error(f"Error creating history entry: {str(e)}")
            # Continue anyway since status was updated successfully
            pass
        
        # Mark as successfully updated
        status_updated = True
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating ticket status: {str(e)}")
        import traceback
        app.logger.error(f"Exception traceback: {traceback.format_exc()}")
        flash('Error updating ticket status', 'error')
        return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
    
    # If we get here, the ticket status was updated successfully
    # Now handle non-critical operations
    
    # If a comment was provided, add it as a separate comment
    if comment and comment.strip():
        try:
            # Reload the ticket to ensure we have a fresh instance
            fresh_ticket = Ticket.query.get(ticket_id)
            if fresh_ticket:
                # Create a new comment with explicit autoincrement
                new_comment = TicketComment(
                    ticket_id=fresh_ticket.id,
                    user_id=current_user.id,
                    content=comment,
                    created_at=datetime.now(pytz.UTC),
                    updated_at=datetime.now(pytz.UTC)
                )
                db.session.add(new_comment)
                db.session.commit()
                app.logger.debug("Added comment successfully")
            else:
                app.logger.error(f"Could not find ticket #{ticket_id} when trying to add comment")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding comment: {str(e)}")
            import traceback
            app.logger.error(f"Comment exception traceback: {traceback.format_exc()}")
            # Don't show error for comment failure - status was still updated
    
    # Send notification email - but first get a fresh instance of the ticket
    # since the previous session may have been closed
    try:
        # Create a fresh session for the email notification to avoid detached instance errors
        # Fresh session creation removed
        fresh_ticket = Ticket.query.get(ticket_id)

        # Call the notification unconditionally when the ticket exists; the
        # email function now handles excluding the updater and includes the
        # external reporter even when the ticket is unassigned or the assignee
        # is the one making the change.
        if fresh_ticket:
            app.logger.info(f"Sending status update notification for ticket #{fresh_ticket.id}")
            
            # The email function will create an app context if needed
            result = send_ticket_status_notification(
                ticket=fresh_ticket,
                old_status=old_status,
                new_status=new_status,
                updated_by=current_user,
                comment=comment if comment else None
            )
            
            app.logger.info(f"Status notification result: {result}")
    except Exception as e:
        app.logger.error(f"Failed to send status update notification: {str(e)}")
        import traceback
        app.logger.error(f"Exception traceback: {traceback.format_exc()}")
        # Don't let email issues affect the user experience
    
    # Show success message since we successfully updated the status
    app.logger.debug(f"Successfully updated ticket #{ticket_id} status to '{new_status}'")
    flash('Ticket status updated successfully', 'success')
        
    return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)

@tickets.route('/tickets/<int:ticket_id>/mobile_status', methods=['POST'])
@login_required
def mobile_update_status(ticket_id):
    """Update ticket status (mobile version)"""
    app.logger.debug(f"Mobile status update for ticket #{ticket_id}")
    
    ticket = Ticket.query.get_or_404(ticket_id)
    new_status = request.form.get('status')
    comment = request.form.get('comment', '')
    
    app.logger.debug(f"Mobile updating ticket #{ticket_id} status from '{ticket.status}' to '{new_status}'")
    app.logger.debug(f"Mobile requested by user: {current_user.id} (admin: {current_user.is_admin})")
    app.logger.debug(f"Form data: {request.form}")
    
    # Validate new status
    valid_statuses = ['open', 'in_progress', 'pending', 'resolved', 'closed']
    if new_status not in valid_statuses:
        flash('Invalid ticket status', 'error')
        return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
    
    # Store old status for history
    old_status = ticket.status
    status_updated = False
    
    try:
        # Critical operation: Update the status
        ticket.status = new_status
        app.logger.debug(f"Changed status to: {ticket.status}")
        
        # Commit the status change
        db.session.add(ticket)
        db.session.commit()
        app.logger.debug("Committed status change")
        
        # Critical operation: Add the history entry
        details = f"Status changed from {old_status} to {new_status}"
        if comment:
            details += f" - Comment: {comment}"
        
        try:
            # Directly create history entry instead of using log_history
            history = TicketHistory(
                ticket_id=ticket.id,
                user_id=current_user.id,
                action="status_changed",
                details=details,
                created_at=datetime.now(pytz.UTC)
            )
            db.session.add(history)
            db.session.commit()
            app.logger.debug("Added history entry")
        except Exception as e:
            app.logger.error(f"Error creating history entry: {str(e)}")
            # Continue anyway since status was updated successfully
            pass
        
        # Mark as successfully updated - this is the key to showing the success message
        status_updated = True
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating ticket status in mobile view: {str(e)}")
        import traceback
        app.logger.error(f"Exception traceback: {traceback.format_exc()}")
        flash('Error updating ticket status', 'error')
        return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
    
    # If we get here, the status was updated successfully
    # Now handle non-critical operations separately
    
    # Add comment if provided
    if comment and comment.strip():
        try:
            # Create a new comment using the existing session
            new_comment = TicketComment(
                ticket_id=ticket_id,
                user_id=current_user.id,
                content=comment,
                created_at=datetime.now(pytz.UTC),
                updated_at=datetime.now(pytz.UTC)
            )
            db.session.add(new_comment)
            db.session.commit()
            app.logger.debug("Added comment successfully")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding comment: {str(e)}")
            import traceback
            app.logger.error(f"Comment exception traceback: {traceback.format_exc()}")
            # Don't show error for comment failure - status was still updated
    
    # Send notification email using the current ticket instance
    try:
        # Call unconditionally; the email function excludes the updater and
        # still notifies the external reporter when present.
        app.logger.info(f"Sending status update notification for ticket #{ticket.id}")
        result = send_ticket_status_notification(
            ticket=ticket,
            old_status=old_status,
            new_status=new_status,
            updated_by=current_user,
            comment=comment if comment else None
        )
        app.logger.info(f"Status notification result: {result}")
    except Exception as e:
        app.logger.error(f"Failed to send status update notification: {str(e)}")
        import traceback
        app.logger.error(f"Exception traceback: {traceback.format_exc()}")
        # Don't let email issues affect the user experience
    
    # Show success message since we successfully updated the status
    flash('Ticket status updated successfully', 'success')
    app.logger.info(f"Mobile status update successful for ticket #{ticket_id}")
    
    # Check if this is an AJAX request expecting JSON response
    if request.headers.get('Content-Type') == 'application/json' or request.is_json or 'application/json' in request.headers.get('Accept', ''):
        return jsonify({'success': True, 'message': 'Ticket status updated successfully'})
    
    return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)

@tickets.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
@login_required
def assign_ticket(ticket_id):
    """Assign shared ownership and/or an individual in a single transaction."""
    ticket = Ticket.query.get_or_404(ticket_id)
    old_group, old_assignee = ticket.group_id, ticket.assigned_to
    try:
        assignment = apply_assignment(ticket,
                         _assignment_id(request.form.get('group_id', ticket.group_id)),
                         _assignment_id(request.form.get('assigned_to')),
                         actor_id=current_user.id, notify=False)
        if assignment['assignee_cleared']:
            flash('The assignee was cleared because they are not a member of the selected group.', 'warning')
        note = request.form.get('note', '').strip()
        if note:
            db.session.add(TicketHistory(ticket_id=ticket.id, user_id=current_user.id,
                                         action='assignment_note', details=note,
                                         created_at=datetime.now(pytz.UTC)))
        ticket.mark_as_viewed(current_user.id)
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        flash(str(exc), 'error')
        return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
    try:
        _notify_ticket_assignment(ticket, old_group, old_assignee)
    except Exception:
        app.logger.exception('Ticket saved but assignment notification failed')
        flash('Assignment saved, but notification delivery failed.', 'warning')
    flash('Ticket assignment saved', 'success')
    return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)


@tickets.route('/tickets/<int:ticket_id>/take', methods=['POST'])
@login_required
def take_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.group_id not in user_group_ids(current_user.id):
        flash('You must be a member of this ticket group to take this ticket.', 'error')
        return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
    old_assignee = ticket.assigned_to
    try:
        apply_assignment(ticket, ticket.group_id, current_user.id,
                         actor_id=current_user.id, notify=False)
        db.session.commit()
        flash('Ticket assigned to you.', 'success')
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), 'error')
        return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
    try:
        _notify_ticket_assignment(ticket, ticket.group_id, old_assignee)
    except Exception:
        app.logger.exception('Ticket taken but assignment notification failed')
        flash('Assignment saved, but notification delivery failed.', 'warning')
    return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)


@tickets.route('/tickets/<int:ticket_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ticket(ticket_id):
    """Edit an existing ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    app.logger.debug(f"Editing ticket #{ticket_id}")

    # Allow all authenticated users to edit tickets
    # Removed admin/creator restriction to enable collaborative ticket management

    if request.method == 'POST':
        # Log all form data for debugging
        app.logger.debug(f"Form data received: {request.form}")
        
        old_group, old_assignee = ticket.group_id, ticket.assigned_to
        try:
            assignment = apply_assignment(
                ticket,
                _assignment_id(request.form.get('group_id', ticket.group_id)),
                _assignment_id(request.form.get('assigned_to', ticket.assigned_to)),
                actor_id=current_user.id, notify=False)
            if assignment['assignee_cleared']:
                flash('The assignee was cleared because they are not a member of the selected group.', 'warning')
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            flash(str(exc), 'error')
            return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket.id)

        # Get form data directly
        old_title = ticket.title
        old_description = ticket.description
        old_category_id = ticket.category_id
        old_priority = ticket.priority
        old_due_date = ticket.due_date
        app.logger.debug(f"Original due date: {old_due_date}")

        # Update ticket with form data
        ticket.title = request.form.get('title')
        ticket.description = request.form.get('description')
        ticket.category_id = request.form.get('category_id')
        
        # Handle priority conversion to int
        priority_val = request.form.get('priority')
        ticket.priority = int(priority_val) if priority_val else 0
        
        # Handle due date (could be empty)
        due_date_val = request.form.get('due_date')
        if due_date_val:
            try:
                # HTML date inputs return YYYY-MM-DD format, so we use strptime
                app.logger.debug(f"Processing due date: {due_date_val}")
                date_obj = datetime.strptime(due_date_val, '%Y-%m-%d')
                
                # Create a datetime at midnight in UTC for the given date
                # This ensures we have a timezone-aware datetime object
                ticket.due_date = datetime(
                    year=date_obj.year,
                    month=date_obj.month,
                    day=date_obj.day,
                    tzinfo=pytz.UTC
                )
                app.logger.debug(f"New due date set to: {ticket.due_date}")
            except ValueError as e:
                # If there's a parsing error, keep the existing date
                app.logger.warning(f"Invalid due date format: {due_date_val}, error: {str(e)}")
        else:
            ticket.due_date = None
            app.logger.debug("Due date cleared/not provided")

        # Log changes in ticket history
        changes = []
        if old_title != ticket.title:
            changes.append(f"Title changed from '{old_title}' to '{ticket.title}'")
        if old_description != ticket.description:
            changes.append("Description updated")
        if str(old_category_id) != str(ticket.category_id):
            changes.append(f"Category changed")
        if old_priority != ticket.priority:
            changes.append(f"Priority changed from {old_priority} to {ticket.priority}")
            
        # Check for due date changes
        if old_due_date != ticket.due_date:
            old_date_str = old_due_date.strftime('%Y-%m-%d') if old_due_date else 'None'
            new_date_str = ticket.due_date.strftime('%Y-%m-%d') if ticket.due_date else 'None'
            changes.append(f"Due date changed from {old_date_str} to {new_date_str}")
            app.logger.debug(f"Due date changed from {old_due_date} to {ticket.due_date}")

        # Always mark the ticket as modified to ensure due date changes are saved
        db.session.add(ticket)
        
        # Always commit ticket changes first
        db.session.commit()
        try:
            _notify_ticket_assignment(ticket, old_group, old_assignee)
        except Exception:
            app.logger.exception('Ticket saved but assignment notification failed')
            flash('Ticket saved, but notification delivery failed.', 'warning')
        
        # Create history entry directly if there are changes
        if changes:
            try:
                history = TicketHistory(
                    ticket_id=ticket.id,
                    user_id=current_user.id,
                    action="edited",
                    details=", ".join(changes),
                    created_at=datetime.now(pytz.UTC)
                )
                db.session.add(history)
                db.session.commit()
                app.logger.debug("Added edit history entry")
            except Exception as e:
                app.logger.error(f"Error creating edit history entry: {str(e)}")
                # Continue anyway since ticket edit was saved successfully
                pass
        
        if changes:
            flash('Ticket updated successfully', 'success')
        else:
            flash('No changes made to ticket', 'info')

        return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket.id)

    # GET requests should go to view ticket page
    return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket.id)


@tickets.route('/tickets/<int:ticket_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_ticket(ticket_id):
    """Delete a ticket (admin only)"""
    
    app.logger.info(f"Delete ticket request: Ticket #{ticket_id}, User: {current_user.username}, Admin: {current_user.is_admin}, Method: {request.method}")
    
    if not current_user.is_admin:
        app.logger.warning(f"Non-admin user {current_user.username} attempted to delete ticket #{ticket_id}")
        flash('You do not have permission to delete tickets', 'error')
        return mobile_aware_redirect('tickets.tickets_dashboard')
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    try:
        # Store data for logging
        ticket_title = ticket.title
        ticket_id_copy = ticket.id
        
        # Delete related records first to avoid foreign key constraint issues
        # This follows the proper cascading deletion order: views → history → comments → ticket
        
        # Delete ticket views (who viewed the ticket)
        deleted_views = TicketView.query.filter_by(ticket_id=ticket_id).delete()
        app.logger.info(f"Deleted {deleted_views} ticket_view records for ticket #{ticket_id}")
        
        # Delete ticket history (status changes, assignments, etc.)  
        deleted_history = TicketHistory.query.filter_by(ticket_id=ticket_id).delete()
        app.logger.info(f"Deleted {deleted_history} ticket_history records for ticket #{ticket_id}")
        
        # Delete ticket comments
        deleted_comments = TicketComment.query.filter_by(ticket_id=ticket_id).delete()
        app.logger.info(f"Deleted {deleted_comments} ticket_comment records for ticket #{ticket_id}")
        
        # Now delete the ticket itself
        db.session.delete(ticket)
        db.session.commit()
        
        app.logger.info(f"Ticket #{ticket_id_copy} ('{ticket_title}') and all related records deleted by {current_user.username}")
        flash(f'Ticket #{ticket_id_copy} has been permanently deleted', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting ticket #{ticket_id}: {str(e)}")
        flash('Error deleting ticket. Please try again.', 'error')
        
    return mobile_aware_redirect('tickets.tickets_dashboard')
    
@tickets.route('/tickets/comment/<int:comment_id>/delete')
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    comment = TicketComment.query.get_or_404(comment_id)
    ticket_id = comment.ticket_id
    
    # Check if user has permission to delete this comment
    if not (current_user.is_admin or comment.user_id == current_user.id):
        flash('You do not have permission to delete this comment', 'error')
        return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)
        
    try:
        # Get the ticket for the history entry
        ticket = Ticket.query.get(ticket_id)
        comment_user_username = comment.user.username if comment.user else "unknown user"
        
        # Delete the comment first
        db.session.delete(comment)
        db.session.commit()
        
        # Add history entry after deleting the comment
        if ticket:
            try:
                history = TicketHistory(
                    ticket_id=ticket.id,
                    user_id=current_user.id,
                    action="deleted_comment",
                    details=f"Comment by {comment_user_username} deleted",
                    created_at=datetime.now(pytz.UTC)
                )
                db.session.add(history)
                db.session.commit()
                app.logger.debug("Added comment deletion history entry")
            except Exception as e:
                app.logger.error(f"Error creating comment deletion history entry: {str(e)}")
                # Continue anyway since comment was deleted successfully
                pass
        
        flash('Comment deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting comment #{comment_id}: {str(e)}")
        flash('Error deleting comment', 'error')
        
    return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)

# Admin routes for managing ticket categories
@tickets.route('/tickets/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    """Manage ticket categories (admin only)"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return mobile_aware_redirect('tickets.tickets_dashboard')

    form = TicketCategoryForm()
    if form.validate_on_submit():
        category = TicketCategory(
            name=form.name.data,
            description=form.description.data,
            priority_level=form.priority_level.data
        )
        try:
            _category_assignment_defaults(category)
        except (ValueError, TypeError) as exc:
            flash(str(exc), 'error')
            return render_template('tickets/manage_categories.html', form=form,
                                   categories=TicketCategory.query.order_by(TicketCategory.name).all())
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully', 'success')
        return redirect(url_for('tickets.manage_categories'))

    categories = TicketCategory.query.order_by(TicketCategory.name).all()
    
    return render_template('tickets/manage_categories.html', 
                         categories=categories,
                         
                         form=form)

@tickets.route('/tickets/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit an existing ticket category"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return mobile_aware_redirect('tickets.tickets_dashboard')
        
    category = TicketCategory.query.get_or_404(category_id)
    
    form = TicketCategoryForm(obj=category)
    if form.validate_on_submit():
        try:
            _category_assignment_defaults(category)
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            flash(str(exc), 'error')
            return render_template('tickets/edit_category.html', form=form, category=category)
        category.name = form.name.data
        category.description = form.description.data
        category.priority_level = form.priority_level.data
        
        db.session.commit()
        flash('Category updated successfully', 'success')
        return redirect(url_for('tickets.manage_categories'))
    
    return render_template('tickets/edit_category.html',
                           category=category,
                           form=form,
                           )
                           
@tickets.route('/tickets/categories/delete/<int:category_id>')
@login_required
def delete_category(category_id):
    """Delete a ticket category"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return mobile_aware_redirect('tickets.tickets_dashboard')
        
    category = TicketCategory.query.get_or_404(category_id)
    
    # Check if the category is in use by any tickets
    if Ticket.query.filter_by(category_id=category_id).first():
        flash('Cannot delete category that is used by existing tickets', 'error')
        return redirect(url_for('tickets.manage_categories'))
    
    try:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting category: {str(e)}")
        flash('Error deleting category', 'error')
        
    return redirect(url_for('tickets.manage_categories'))
    
    
@tickets.route('/tickets/<int:ticket_id>/archive')
@login_required
def archive_ticket(ticket_id):
    """Archive a ticket (mark it as archived)"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Allow all authenticated users to archive tickets
    # Removed admin/creator/assignee restriction to enable collaborative ticket management
    
    try:
        # Mark the ticket as archived
        ticket.archived = True
        
        # Add a history entry
        history = TicketHistory(
            ticket_id=ticket.id,
            user_id=current_user.id,
            action="archived",
            details="Ticket was archived",
            created_at=datetime.now(pytz.UTC)
        )
        db.session.add(history)
        
        db.session.commit()
        flash('Ticket archived successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error archiving ticket: {str(e)}")
        flash('Error archiving ticket', 'error')
    
    # Redirect back to the tickets dashboard
    return mobile_aware_redirect('tickets.tickets_dashboard')


@tickets.route('/tickets/<int:ticket_id>/unarchive')
@login_required
def unarchive_ticket(ticket_id):
    """Unarchive a ticket (mark it as not archived)"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Allow all authenticated users to unarchive tickets
    # Removed admin/creator/assignee restriction to enable collaborative ticket management
    
    try:
        # Mark the ticket as not archived
        ticket.archived = False
        
        # Add a history entry
        history = TicketHistory(
            ticket_id=ticket.id,
            user_id=current_user.id,
            action="unarchived",
            details="Ticket was unarchived",
            created_at=datetime.now(pytz.UTC)
        )
        db.session.add(history)
        
        db.session.commit()
        flash('Ticket unarchived successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error unarchiving ticket: {str(e)}")
        flash('Error unarchiving ticket', 'error')
    
    # Redirect back to the tickets dashboard
    return mobile_aware_redirect('tickets.view_ticket', ticket_id=ticket_id)


@tickets.route('/tickets/archived')
@login_required
def archived_tickets():
    """View archived tickets"""
    # Get all archived tickets, ordered by creation date (newest first)
    query = _group_filtered_query(Ticket.query.filter(Ticket.archived == True))
    tickets = query.order_by(Ticket.group_id, Ticket.created_at.desc()).all() if request.args.get('group_by') == 'group' else query.order_by(Ticket.created_at.desc()).all()
    
    # Convert SQLAlchemy objects to simple dictionaries
    archived_tickets = []
    for ticket in tickets:
        ticket_dict = {
            'id': ticket.id,
            'title': ticket.title,
            'status': ticket.status,
            'priority': ticket.priority,
            'assigned_to': ticket.assigned_to,
            'created_by': ticket.created_by,
            'created_at': ticket.created_at,
            'updated_at': ticket.updated_at,
            'due_date': ticket.due_date,
            'group_id': ticket.group_id,
            'group': ticket.group,
            'category': {
                'id': ticket.category.id,
                'name': ticket.category.name
            }
        }
        
        # Add assigned technician info if available
        if ticket.assigned_technician:
            ticket_dict['assigned_technician'] = {
                'username': ticket.assigned_technician.username
            }
        else:
            ticket_dict['assigned_technician'] = None
            
        archived_tickets.append(ticket_dict)
    
    return render_template('tickets/archived.html', 
                         tickets=archived_tickets,
                         ticket_count=len(archived_tickets),
                         )
                         
                         
@tickets.route('/tickets/batch-archive', methods=['POST'])
@login_required
def batch_archive_tickets():
    """Batch archive tickets based on criteria"""
    if not current_user.is_admin:
        flash('Only administrators can perform batch archive operations', 'error')
        return mobile_aware_redirect('tickets.tickets_dashboard')
    
    # Get filter criteria from form
    status = request.form.get('status', 'all')
    date_before_str = request.form.get('date_before')
    
    # Build the query
    query = Ticket.query.filter(Ticket.archived == False)  # Only consider non-archived tickets
    
    # Apply status filter
    if status != 'all':
        query = query.filter(Ticket.status == status)
    
    # Apply date filter if provided
    if date_before_str:
        try:
            # Parse the date string into a datetime object
            date_before = datetime.strptime(date_before_str, '%Y-%m-%d')
            # Set to the end of the day
            date_before = date_before.replace(hour=23, minute=59, second=59, tzinfo=pytz.UTC)
            # Filter tickets updated before this date
            query = query.filter(Ticket.updated_at < date_before)
        except ValueError:
            flash('Invalid date format', 'error')
            return mobile_aware_redirect('tickets.tickets_dashboard')
    
    # Execute the query to get the tickets to archive
    tickets_to_archive = query.all()
    count = len(tickets_to_archive)
    
    if count == 0:
        flash('No tickets matched the criteria for archiving', 'info')
        return mobile_aware_redirect('tickets.tickets_dashboard')
    
    try:
        # Archive each ticket and create history entries
        for ticket in tickets_to_archive:
            ticket.archived = True
            
            # Add a history entry
            history = TicketHistory(
                ticket_id=ticket.id,
                user_id=current_user.id,
                action="archived",
                details="Ticket was archived in batch operation",
                created_at=datetime.now(pytz.UTC)
            )
            db.session.add(history)
        
        # Commit all changes at once
        db.session.commit()
        flash(f'Successfully archived {count} tickets', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in batch archiving tickets: {str(e)}")
        flash(f'Error archiving tickets: {str(e)}', 'error')
    
    return mobile_aware_redirect('tickets.tickets_dashboard')

@tickets.route('/tickets/attachment/<path:filename>')
@login_required
def download_attachment(filename):
    """Download a ticket attachment with proper headers to force download"""
    from flask import send_from_directory
    import os
    import re
    import mimetypes
    
    upload_dir = os.path.join('static', 'uploads', 'ticket_attachments')
    
    # Security check
    file_path = os.path.join(upload_dir, filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return "File not found", 404
    
    # Extract the original filename
    match = re.search(r'(?:ticket|comment)\d+_(.*)', filename)
    original_filename = match.group(1) if match else filename
    
    # Detect MIME type
    mimetype, _ = mimetypes.guess_type(original_filename)
    if not mimetype:
        mimetype = 'application/octet-stream'
    
    return send_from_directory(
        upload_dir,
        filename,
        as_attachment=True,
        download_name=original_filename,
        mimetype=mimetype,
        conditional=True
    )




# =====================================================================
# JSON API endpoints for inline editing & bulk actions on the dashboard
# =====================================================================

@tickets.route("/tickets/api/<int:ticket_id>/quick-update", methods=["POST"])
@login_required
def api_quick_update(ticket_id):
    """Inline edit a single ticket field (status / priority / assigned_to)."""
    ticket = Ticket.query.get_or_404(ticket_id)
    data = request.get_json(silent=True) or {}
    field = (data.get("field") or "").strip()
    value = data.get("value")

    valid_statuses = ["open", "in_progress", "pending", "resolved", "closed"]
    try:
        if field == "status":
            if value not in valid_statuses:
                return jsonify({"ok": False, "error": "Invalid status"}), 400
            old = ticket.status
            ticket.status = value
            db.session.add(TicketHistory(
                ticket_id=ticket.id, user_id=current_user.id,
                action="status_changed",
                details=f"Status changed from {old} to {value}",
                created_at=datetime.now(pytz.UTC),
            ))
        elif field == "priority":
            try:
                pv = int(value)
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "Invalid priority"}), 400
            if pv not in (0, 1, 2, 3):
                return jsonify({"ok": False, "error": "Invalid priority"}), 400
            old = ticket.priority
            ticket.priority = pv
            db.session.add(TicketHistory(
                ticket_id=ticket.id, user_id=current_user.id,
                action="priority_changed",
                details=f"Priority changed from {old} to {pv}",
                created_at=datetime.now(pytz.UTC),
            ))
        elif field == "assigned_to":
            if value in (None, "", "none", "unassigned"):
                ticket.assigned_to = None
                details = "Ticket was unassigned"
                action = "unassigned"
            elif value == "me":
                ticket.assigned_to = current_user.id
                details = f"Assigned to {current_user.username}"
                action = "assigned"
            else:
                try:
                    uid = int(value)
                except (TypeError, ValueError):
                    return jsonify({"ok": False, "error": "Invalid user id"}), 400
                user = User.query.get(uid)
                if not user:
                    return jsonify({"ok": False, "error": "User not found"}), 404
                ticket.assigned_to = user.id
                details = f"Assigned to {user.username}"
                action = "assigned"
            db.session.add(TicketHistory(
                ticket_id=ticket.id, user_id=current_user.id,
                action=action, details=details,
                created_at=datetime.now(pytz.UTC),
            ))
        else:
            return jsonify({"ok": False, "error": "Unknown field"}), 400

        try:
            ticket.mark_as_viewed(current_user.id)
        except Exception:
            pass
        db.session.commit()
        return jsonify({
            "ok": True,
            "ticket": {
                "id": ticket.id,
                "status": ticket.status,
                "priority": ticket.priority,
                "assigned_to": ticket.assigned_to,
                "assigned_username": ticket.assigned_technician.username if ticket.assigned_technician else None,
            },
        })
    except Exception as e:
        db.session.rollback()
        app.logger.exception("quick-update failed")
        return jsonify({"ok": False, "error": str(e)}), 500


@tickets.route("/tickets/api/bulk-update", methods=["POST"])
@login_required
def api_bulk_update():
    """Bulk update many tickets at once (status / priority / assigned_to)."""
    data = request.get_json(silent=True) or {}
    ids = data.get("ticket_ids") or []
    field = (data.get("field") or "").strip()
    value = data.get("value")

    if not isinstance(ids, list) or not ids:
        return jsonify({"ok": False, "error": "No ticket_ids provided"}), 400
    try:
        ids = [int(x) for x in ids]
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid ticket id"}), 400

    valid_statuses = ["open", "in_progress", "pending", "resolved", "closed"]
    updated = 0
    try:
        target_user_id = None
        if field == "assigned_to":
            if value in (None, "", "none", "unassigned"):
                target_user_id = None
            elif value == "me":
                target_user_id = current_user.id
            else:
                try:
                    target_user_id = int(value)
                except (TypeError, ValueError):
                    return jsonify({"ok": False, "error": "Invalid user id"}), 400
                if not User.query.get(target_user_id):
                    return jsonify({"ok": False, "error": "User not found"}), 404
        elif field == "status":
            if value not in valid_statuses:
                return jsonify({"ok": False, "error": "Invalid status"}), 400
        elif field == "priority":
            try:
                value = int(value)
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "Invalid priority"}), 400
            if value not in (0, 1, 2, 3):
                return jsonify({"ok": False, "error": "Invalid priority"}), 400
        else:
            return jsonify({"ok": False, "error": "Unknown field"}), 400

        tickets_q = Ticket.query.filter(Ticket.id.in_(ids)).all()
        for t in tickets_q:
            if field == "status":
                old = t.status
                t.status = value
                details = f"Status changed from {old} to {value} (bulk)"
                action = "status_changed"
            elif field == "priority":
                old = t.priority
                t.priority = value
                details = f"Priority changed from {old} to {value} (bulk)"
                action = "priority_changed"
            else:  # assigned_to
                t.assigned_to = target_user_id
                if target_user_id is None:
                    details = "Ticket was unassigned (bulk)"
                    action = "unassigned"
                else:
                    u = User.query.get(target_user_id)
                    details = f"Assigned to {u.username} (bulk)"
                    action = "assigned"
            db.session.add(TicketHistory(
                ticket_id=t.id, user_id=current_user.id,
                action=action, details=details,
                created_at=datetime.now(pytz.UTC),
            ))
            try:
                t.mark_as_viewed(current_user.id)
            except Exception:
                pass
            updated += 1

        db.session.commit()
        return jsonify({"ok": True, "updated": updated})
    except Exception as e:
        db.session.rollback()
        app.logger.exception("bulk-update failed")
        return jsonify({"ok": False, "error": str(e)}), 500

