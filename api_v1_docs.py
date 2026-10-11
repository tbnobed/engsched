"""Public, credential-free API reference and machine-readable OpenAPI contract."""
from flask import jsonify, render_template
from api_v1_core import api_v1


def spec():
    def prop(kind, **extra):
        return dict(type=kind, **extra)

    date = prop('string', format='date-time', description='ISO 8601 timestamp with Z or an explicit offset.')
    nullable_id = prop(['integer', 'null'], minimum=1)
    ticket_input = {
        'title': prop('string', minLength=1, maxLength=200),
        'description': prop('string', minLength=1, maxLength=50000, description='Plain text, escaped safely for the application.'),
        'category_id': prop('integer', minimum=1),
        'priority': prop('integer', minimum=0, maximum=3, default=0, description='0 Low, 1 Medium, 2 High, 3 Urgent'),
        'assigned_to': nullable_id, 'requester_id': prop('integer', minimum=1, description='Defaults to the API-key owner.'),
        'external_email': prop(['string', 'null'], format='email', maxLength=255),
        'external_name': prop(['string', 'null'], maxLength=100),
        'due_date': dict(date, type=['string', 'null']),
        'status': prop('string', enum=['open', 'in_progress', 'pending', 'resolved', 'closed'], default='open'),
        'archived': prop('boolean', default=False),
    }
    schedule_input = {
        'technician_id': prop('integer', minimum=1),
        'start_time': date, 'end_time': dict(date, description='Exclusive end; must be later than start_time.'),
        'location_id': nullable_id, 'description': prop('string', maxLength=200),
        'time_off': prop('boolean', default=False), 'all_day': prop('boolean', default=False),
    }
    schemas = {
        'TicketInput': {'type': 'object', 'additionalProperties': False, 'properties': ticket_input},
        'ScheduleInput': {'type': 'object', 'additionalProperties': False, 'properties': schedule_input},
        'ContentInput': {'type': 'object', 'additionalProperties': False, 'required': ['content'],
                         'properties': {'content': prop('string', minLength=1, maxLength=20000)}},
        'Ticket': {'type': 'object', 'properties': {
            **ticket_input, 'id': prop('integer'), 'description_html': prop('string'),
            'created_at': date, 'updated_at': date}},
        'Schedule': {'type': 'object', 'properties': {
            **schedule_input, 'id': prop('integer'), 'created_at': date, 'technician_timezone': prop('string')}},
        'Comment': {'type': 'object', 'properties': {
            'id': prop('integer'), 'ticket_id': prop('integer'), 'author_id': prop('integer'),
            'content': prop('string'), 'content_html': prop('string'), 'created_at': date}},
        'History': {'type': 'object', 'properties': {
            'id': prop('integer'), 'ticket_id': prop('integer'), 'author_id': prop('integer'),
            'action': prop('string'), 'details': prop(['string', 'null']), 'created_at': date}},
        'Technician': {'type': 'object', 'properties': {
            'id': prop('integer'), 'username': prop('string'), 'email': prop('string', format='email'),
            'timezone': prop('string'), 'show_on_dashboard': prop('boolean')}},
        'Category': {'type': 'object', 'properties': {
            'id': prop('integer'), 'name': prop('string'), 'description': prop(['string', 'null'])}},
        'Location': {'type': 'object', 'properties': {
            'id': prop('integer'), 'name': prop('string'), 'description': prop(['string', 'null']), 'active': prop('boolean')}},
        'ScheduleTemplate': {'type': 'object', 'properties': {
            'id': prop('integer'), 'name': prop('string'), 'technician_id': prop('integer'),
            'location_id': nullable_id, 'active': prop('boolean'), 'timezone': prop('string'),
            'weekly_hours': {'type': 'object', 'properties': {
                day: {'type': 'object', 'properties': {
                    'start': prop(['string', 'null'], description='Local HH:MM; null means no shift.'),
                    'end': prop(['string', 'null'], description='Local HH:MM; overnight patterns may end before they start.')}}
                for day in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')}}}},
        'ArchivedTicket': {'type': 'object', 'properties': {'id': prop('integer'), 'archived': prop('boolean')}},
        'DeletedSchedule': {'type': 'object', 'properties': {'id': prop('integer'), 'deleted': prop('boolean')}},
        'Error': {'type': 'object', 'properties': {
            'error': {'type': 'object', 'properties': {'code': prop('integer'), 'message': prop('string')}},
            'request_id': prop(['string', 'null'])}},
    }
    paths = {}
    pagination = [('page', prop('integer', minimum=1, maximum=1000000, default=1)),
                  ('page_size', prop('integer', minimum=1, maximum=100, default=50))]

    def operation(path, method, summary, scope=None, input_name=None, required=(), filters=(), listing=False, output=None):
        parameters = [{'name': name, 'in': 'path', 'required': True, 'schema': prop('integer', minimum=1)}
                      for name in ('ticket_id', 'schedule_id') if '{' + name + '}' in path]
        parameters += [{'name': name, 'in': 'query', 'schema': schema} for name, schema in (list(pagination) if listing else []) + list(filters)]
        if method == 'post':
            parameters.append({'name': 'Idempotency-Key', 'in': 'header', 'schema': prop('string', maxLength=128),
                               'description': 'Optional. Replays identical POSTs for 24 hours. Different payload/path returns 409.'})
        data_schema = {'$ref': '#/components/schemas/' + output} if output else {'type': 'object'}
        if listing:
            envelope = {'type': 'object', 'properties': {
                'data': {'type': 'array', 'items': data_schema},
                'meta': {'type': 'object', 'properties': {name: prop('integer') for name in ('page', 'page_size', 'total', 'pages')}}}}
        else:
            envelope = {'type': 'object', 'properties': {'data': data_schema, 'notifications_sent': prop('boolean')}}
        status = '201' if method == 'post' else '200'
        op = {
            'summary': summary, 'operationId': method + '_' + path.strip('/').replace('/', '_').replace('{', '').replace('}', '').replace('-', '_'),
            'description': f'Required scope: {scope}.' if scope else 'Any active API key.',
            'parameters': parameters,
            'responses': {status: {'description': 'Success', 'content': {'application/json': {'schema': envelope}}},
                          **{str(code): {'description': label, 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}}}
                             for code, label in ((400, 'Invalid input'), (401, 'Invalid credentials'), (403, 'Missing scope'),
                                                 (404, 'Not found'), (409, 'Conflict'), (413, 'Body too large'),
                                                 (415, 'Expected JSON'), (429, 'Rate limited'), (500, 'Request failed'))}},
        }
        if scope:
            op['x-required-scope'] = scope
        if input_name:
            schema = {'allOf': [{'$ref': '#/components/schemas/' + input_name}]}
            if required:
                schema['required'] = list(required)
            if method == 'patch':
                schema['minProperties'] = 1
            op['requestBody'] = {'required': True, 'content': {'application/json': {'schema': schema}}}
        paths.setdefault(path, {})[method] = op

    operation('/', 'get', 'API version and granted scopes')
    operation('/tickets', 'get', 'List tickets (unarchived by default)', 'tickets:read', listing=True, output='Ticket', filters=[
        ('status', ticket_input['status']), ('priority', prop('integer', minimum=0, maximum=3)),
        ('category_id', prop('integer')), ('assigned_to', prop('string', description='User ID or unassigned')),
        ('requester_id', prop('integer')), ('archived', prop('boolean', default=False)),
        ('updated_since', date), ('q', prop('string', maxLength=200))])
    operation('/tickets', 'post', 'Create a ticket; no email or AI side effects', 'tickets:write', 'TicketInput',
              ('title', 'description', 'category_id'), output='Ticket')
    operation('/tickets/{ticket_id}', 'get', 'Read a ticket, including archived tickets', 'tickets:read', output='Ticket')
    operation('/tickets/{ticket_id}', 'patch', 'Update ticket fields and record history', 'tickets:write', 'TicketInput', output='Ticket')
    operation('/tickets/{ticket_id}', 'delete', 'Archive a ticket (reversible with PATCH archived:false)', 'tickets:write', output='ArchivedTicket')
    operation('/tickets/{ticket_id}/comments', 'get', 'List recorded comments; internal notes are in history', 'tickets:read', listing=True, output='Comment')
    operation('/tickets/{ticket_id}/comments', 'post', 'Record a comment without emailing it', 'tickets:write', 'ContentInput', output='Comment')
    operation('/tickets/{ticket_id}/history', 'get', 'List status/assignment events and internal notes', 'tickets:read', listing=True, output='History')
    operation('/tickets/{ticket_id}/notes', 'post', 'Add a team-only internal note', 'tickets:write', 'ContentInput', output='History')
    operation('/schedules', 'get', 'List stored schedule entries overlapping a time window', 'schedules:read', listing=True, output='Schedule', filters=[
        ('technician_id', prop('integer')), ('location_id', prop('integer')),
        ('time_off', prop('boolean')), ('start', date), ('end', date)])
    operation('/schedules', 'post', 'Create a schedule entry; overlapping entries return 409', 'schedules:write',
              'ScheduleInput', ('technician_id', 'start_time', 'end_time'), output='Schedule')
    operation('/schedules/{schedule_id}', 'get', 'Read a schedule entry', 'schedules:read', output='Schedule')
    operation('/schedules/{schedule_id}', 'patch', 'Edit one schedule entry', 'schedules:write', 'ScheduleInput', output='Schedule')
    operation('/schedules/{schedule_id}', 'delete', 'Permanently delete one schedule entry', 'schedules:write', output='DeletedSchedule')
    operation('/schedule-templates', 'get', 'Read weekly patterns, not automatically expanded future bookings', 'schedules:read', listing=True,
              filters=[('technician_id', prop('integer')), ('active', prop('boolean'))], output='ScheduleTemplate')
    for path, title in (('technicians', 'technician IDs, names, email and timezone (all app users)'),
                        ('categories', 'ticket categories'), ('locations', 'locations including active flag')):
        operation('/' + path, 'get', 'List ' + title, 'directory:read', listing=True,
                  output={'technicians': 'Technician', 'categories': 'Category', 'locations': 'Location'}[path])
    return {
        'openapi': '3.1.0', 'info': {'title': 'Plex Engineering API', 'version': '1.0.0',
            'description': 'Server-to-server ticket and technician scheduling integration. Bearer API keys are managed by administrators.'},
        'servers': [{'url': '/api/v1'}],
        'security': [{'BearerAuth': []}, {'APIKeyAuth': []}],
        'paths': paths,
        'components': {'securitySchemes': {
            'BearerAuth': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'API key'},
            'APIKeyAuth': {'type': 'apiKey', 'in': 'header', 'name': 'X-API-Key'}}, 'schemas': schemas},
    }


@api_v1.get('/openapi.json')
def openapi():
    return jsonify(spec())


@api_v1.get('/docs')
def docs():
    return render_template('api/docs.html', spec=spec())
