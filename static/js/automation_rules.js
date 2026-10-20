/* Accessible, dependency-free rule builder. All dynamic text uses textContent. */
(() => {
    'use strict';
    const bootstrap = JSON.parse(document.getElementById('automationData').textContent);
    const state = structuredClone(bootstrap.definition);
    const $ = id => document.getElementById(id);
    let lastTextField = null;
    let expressionTimer;
    const actionDefaults = {
        update_record: {fields: {priority: 3}},
        add_tag: {tag: 'follow-up'},
        add_comment: {body: '', private: true},
        send_notification: {recipients: [{kind: 'ticket_group'}], subject: 'Ticket #{{id}}: {{title}}', body: '{{ticket_url}}'},
        create_record: {fields: {title: 'Follow-up: {{title}}', description: '{{description}}', category_id: '{{category_id}}', created_by: '{{created_by}}'}},
        webhook: {url: '', headers: {}}
    };
    const labels = {
        update_record: 'Update record', add_tag: 'Add tag', add_comment: 'Add comment',
        send_notification: 'Send notification', create_record: 'Create linked ticket', webhook: 'Webhook'
    };
    function element(tag, classes, text) {
        const node = document.createElement(tag);
        if (classes) node.className = classes;
        if (text !== undefined) node.textContent = text;
        return node;
    }
    function button(text, callback, classes = 'btn btn-sm btn-outline-secondary') {
        const node = element('button', classes, text);
        node.type = 'button';
        node.onclick = callback;
        return node;
    }
    function input(value, callback, type = 'text') {
        const node = element('input', 'form-control');
        node.type = type;
        node.value = value ?? '';
        node.oninput = () => callback(type === 'number' ? Number(node.value) : node.value);
        return node;
    }
    function textarea(value, callback, rows = 3) {
        const node = element('textarea', 'form-control');
        node.rows = rows;
        node.value = value ?? '';
        node.oninput = () => callback(node.value);
        return node;
    }
    function select(options, value, callback) {
        const node = element('select', 'form-select');
        for (const option of options) {
            const [key, label] = Array.isArray(option) ? option : [option, option.replaceAll('_', ' ')];
            const item = element('option', '', label);
            item.value = key;
            item.selected = key === value;
            node.append(item);
        }
        node.onchange = () => callback(node.value);
        return node;
    }
    function field(parent, label, control, width = 'col-md-6') {
        const wrapper = element('label', width + ' d-block');
        wrapper.append(element('span', 'form-label', label), control);
        parent.append(wrapper);
        return control;
    }
    function check(parent, label, value, callback) {
        const wrapper = element('label', 'form-check ms-2');
        const node = input('', callback, 'checkbox');
        node.className = 'form-check-input';
        node.checked = Boolean(value);
        node.oninput = () => callback(node.checked);
        wrapper.append(node, document.createTextNode(' ' + label));
        parent.append(wrapper);
    }
    function error(message) {
        $('editorError').textContent = message;
        $('editorError').classList.remove('d-none');
    }
    function parseValue(condition, source) {
        const type = bootstrap.fields[condition.field_key]?.type;
        if (condition.operator === 'is one of' || (condition.operator === 'within' && source.startsWith('['))) {
            try { condition.value = JSON.parse(source); } catch (_) { condition.value = source; }
        } else {
            condition.value = type === 'number' && source !== '' ? Number(source) : source;
        }
    }
    function updateWarnings() {
        const timed = state.conditions.some(c => c.kind === 'time_based');
        const changed = state.conditions.some(c => c.kind === 'regular' && c.value_type !== 'current_value');
        $('mixWarning').textContent = timed && changed ? 'Cannot save: scheduled runs cannot use change/from/to comparisons. Remove one condition type.' : '';
        $('customTriggers').classList.toggle('d-none', $('ruleTrigger').value !== 'custom');
        $('expressionArea').classList.toggle('d-none', $('conditionLogic').value !== 'custom');
        if ($('saveRule')) $('saveRule').disabled = timed && changed;
        clearTimeout(expressionTimer);
        if ($('conditionLogic').value === 'custom') {
            expressionTimer = setTimeout(async () => {
                try {
                    const response = await fetch(bootstrap.validateUrl, {
                        method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': bootstrap.csrf},
                        body: JSON.stringify({expression: $('customExpression').value, numbers: state.conditions.map(c => c.number)})
                    });
                    const result = await response.json();
                    $('expressionFeedback').textContent = result.valid ? 'Valid expression' : result.error || 'Invalid expression';
                    $('expressionFeedback').className = 'small mt-1 ' + (result.valid ? 'text-success' : 'text-danger');
                } catch (_) {
                    $('expressionFeedback').textContent = 'Unable to validate expression. Saving will validate it on the server.';
                }
            }, 250);
        }
    }
    function renderConditions() {
        $('conditions').replaceChildren();
        state.conditions.forEach((condition, index) => {
            condition.number = index + 1;
            const card = element('div', 'border rounded p-3 mb-3');
            const header = element('div', 'd-flex justify-content-between align-items-center mb-3');
            header.append(element('strong', '', `${condition.number}. ${condition.kind === 'time_based' ? 'Time-based condition' : 'Regular condition'}`));
            header.append(button('Remove', () => { state.conditions.splice(index, 1); renderConditions(); }));
            const row = element('div', 'row g-3');
            if (condition.kind === 'time_based') {
                const amount = field(row, 'Amount (maximum 400 days)', input(condition.amount, value => {condition.amount = value;}, 'number'), 'col-md-3');
                amount.min = 0;
                field(row, 'Unit', select(['minutes', 'hours', 'days', 'business hours'], condition.unit, value => {condition.unit = value;}), 'col-md-3');
                field(row, 'Direction', select(['before', 'after'], condition.direction, value => {condition.direction = value;}), 'col-md-3');
                field(row, 'Anchor', select(bootstrap.anchors, condition.anchor_field, value => {condition.anchor_field = value; renderConditions();}), 'col-md-3');
                if (condition.anchor_field.startsWith('last_')) {
                    check(row, 'Public comments only', condition.public_only, value => {condition.public_only = value;});
                }
            } else {
                const options = Object.entries(bootstrap.fields).map(([key, info]) => [key, `${info.label} · ${info.origin} · ${info.type}`]);
                field(row, 'Ticket field', select(options, condition.field_key, value => {
                    condition.field_key = value;
                    condition.operator = bootstrap.operators[bootstrap.fields[value].type][0];
                    condition.value = '';
                    renderConditions();
                }), 'col-md-6');
                field(row, 'Value type', select(['current_value', 'any_change', 'updated_from', 'updated_to'], condition.value_type, value => {
                    condition.value_type = value; renderConditions();
                }), 'col-md-6');
                if (condition.value_type !== 'any_change') {
                    const ops = bootstrap.operators[bootstrap.fields[condition.field_key]?.type || 'text'];
                    field(row, 'Operator', select(ops, condition.operator, value => {condition.operator = value; renderConditions();}));
                    if (!['is empty', 'is not empty', 'during business hours', 'outside business hours'].includes(condition.operator)) {
                        const source = Array.isArray(condition.value) ? JSON.stringify(condition.value) : condition.value;
                        field(row, 'Value (lists/ranges use JSON)', input(source, value => parseValue(condition, value)));
                        if (bootstrap.fields[condition.field_key]?.type === 'date') {
                            row.append(element('p', 'small text-muted mb-0', 'ISO datetime, [start,end], last day, last 7/14/30/60/90 days, this/last week/month/quarter/year, or end of month/quarter/year.'));
                        }
                    }
                }
            }
            card.append(header, row);
            $('conditions').append(card);
        });
        if (!state.conditions.length) $('conditions').append(element('p', 'text-muted small', 'No conditions: this rule matches every selected trigger event.'));
        updateWarnings();
    }
    function jsonControl(value, callback, rows = 4) {
        const node = textarea(JSON.stringify(value, null, 2), source => {
            try {
                callback(JSON.parse(source));
                node.setCustomValidity('');
                node.classList.remove('is-invalid');
            } catch (_) {
                node.setCustomValidity('Enter valid JSON.');
                node.classList.add('is-invalid');
            }
        }, rows);
        node.classList.add('font-monospace');
        return node;
    }
    function renderActions() {
        $('actions').replaceChildren();
        state.actions.forEach((action, index) => {
            action.position = index + 1;
            const card = element('div', 'border rounded p-3 mb-3');
            const header = element('div', 'd-flex justify-content-between align-items-center mb-3');
            header.append(element('strong', '', `Action ${index + 1}`));
            const controls = element('div', 'd-flex gap-1');
            const move = delta => { [state.actions[index], state.actions[index + delta]] = [state.actions[index + delta], state.actions[index]]; renderActions(); };
            const up = button('↑', () => move(-1)); up.disabled = index === 0; up.setAttribute('aria-label', 'Move action up');
            const down = button('↓', () => move(1)); down.disabled = index === state.actions.length - 1; down.setAttribute('aria-label', 'Move action down');
            controls.append(up, down, button('Remove', () => {state.actions.splice(index, 1); renderActions();}));
            header.append(controls);
            const row = element('div', 'row g-3');
            field(row, 'Action type', select(Object.entries(labels), action.type, value => {
                action.type = value; action.config = structuredClone(actionDefaults[value]); renderActions();
            }), 'col-12');
            const config = action.config;
            if (['update_record', 'create_record'].includes(action.type)) {
                field(row, 'Field values (JSON object; variables allowed)', jsonControl(config.fields || {}, value => {config.fields = value;}), 'col-12');
                row.append(element('p', 'small text-muted mb-0', 'Writable keys: title, description, status, priority (0–3 or "raise_one"), category_id, group_id, assigned_to, created_by, due_date, archived, email_notifications, requester_department, requester_location and custom.key. Use null to clear assignment/due date. Create requires title, description, category_id and created_by. IDs, audit timestamps, source and file paths are read-only.'));
                if (action.type === 'update_record') {
                    field(row, 'CC changes (JSON list)', jsonControl(config.cc || [], value => {config.cc = value;}, 2), 'col-12');
                    row.append(element('p', 'small text-muted mb-0', 'Example: [{"kind":"user","id":1,"operation":"add"}]. Use kind "group" to add/remove a group; operation "remove" removes it.'));
                }
            } else if (action.type === 'add_tag') {
                field(row, 'Tag text', input(config.tag, value => {config.tag = value;}), 'col-12');
            } else if (action.type === 'add_comment') {
                field(row, 'Comment body', textarea(config.body, value => {config.body = value;}), 'col-12');
                check(row, 'Private internal note', config.private, value => {config.private = value;});
            } else if (action.type === 'send_notification') {
                const selectors = [
                    ['requester', 'Requester (internal only)'], ['assignee', 'Assignee'],
                    ['ticket_group', "Ticket's group members"], ['group_manager', "Ticket's group manager"], ['cc', 'Ticket CC list'],
                    ...bootstrap.users.map(user => ['user:' + user.id, 'User · ' + user.name]),
                    ...bootstrap.groups.map(group => ['group:' + group.id, 'Group · ' + group.name])
                ];
                let selectedRecipient = 'requester';
                const picker = field(row, 'Add internal recipient', select(selectors, selectedRecipient, value => {selectedRecipient = value;}));
                const addRecipient = button('Add recipient', () => {
                    const [kind, id] = selectedRecipient.split(':');
                    const recipient = id ? {kind, id: Number(id)} : {kind};
                    config.recipients = [...(config.recipients || []), recipient];
                    renderActions();
                });
                const pickerGroup = element('div', 'col-md-6 d-flex align-items-end');
                pickerGroup.append(addRecipient);
                row.append(pickerGroup);
                field(row, 'Internal recipients (JSON list)', jsonControl(config.recipients || [], value => {config.recipients = value;}, 3), 'col-12');
                row.append(element('p', 'small text-muted mb-0', 'Selectors: {"kind":"user","id":1}, {"kind":"group","id":1}, or {"kind":"requester"}, {"kind":"assignee"}, {"kind":"ticket_group"}, {"kind":"group_manager"}, {"kind":"cc"}. No external addresses. This app has no reusable notification templates.'));
                field(row, 'Subject', input(config.subject, value => {config.subject = value;}), 'col-12');
                field(row, 'Message', textarea(config.body, value => {config.body = value;}), 'col-12');
            } else if (action.type === 'webhook') {
                field(row, 'HTTPS URL (public destination only)', input(config.url, value => {config.url = value;}, 'url'), 'col-12');
                field(row, 'Optional headers (JSON object)', jsonControl(config.headers || {}, value => {config.headers = value;}, 3), 'col-12');
                row.append(element('p', 'small text-muted mb-0', 'POST includes the event ticket snapshot and rule information. Private/metadata destinations and redirects are blocked. URL must be static and use HTTPS port 443.'));
            }
            card.append(header, row);
            $('actions').append(card);
        });
    }
    function definition() {
        return {
            ...state,
            name: $('ruleName').value, description: $('ruleDescription').value,
            active: $('ruleActive').checked, position: Number($('rulePosition').value),
            trigger: $('ruleTrigger').value, scope: 'ticket',
            custom_triggers: Array.from(document.querySelectorAll('[data-custom-trigger]:checked')).map(n => n.dataset.customTrigger),
            condition_logic: $('conditionLogic').value, custom_expression: $('customExpression').value
        };
    }
    $('ruleName').value = state.name;
    $('ruleDescription').value = state.description;
    $('ruleActive').checked = state.active;
    $('rulePosition').value = state.position;
    $('ruleTrigger').value = state.trigger;
    $('conditionLogic').value = state.condition_logic;
    $('customExpression').value = state.custom_expression;
    document.querySelectorAll('[data-custom-trigger]').forEach(node => {node.checked = state.custom_triggers.includes(node.dataset.customTrigger);});
    $('addCondition').onclick = () => {
        state.conditions.push({kind: 'regular', number: state.conditions.length + 1, field_key: 'status', value_type: 'current_value', operator: 'is', value: 'open'});
        renderConditions();
    };
    $('addTimed').onclick = () => {
        state.conditions.push({kind: 'time_based', number: state.conditions.length + 1, amount: 1, unit: 'hours', direction: 'after', anchor_field: 'created_at', public_only: true});
        renderConditions();
    };
    $('addAction').onclick = () => {state.actions.push({type: 'update_record', position: state.actions.length + 1, config: structuredClone(actionDefaults.update_record)}); renderActions();};
    $('ruleTrigger').onchange = updateWarnings;
    $('conditionLogic').onchange = updateWarnings;
    $('customExpression').oninput = updateWarnings;
    $('ruleForm').onsubmit = event => {
        if (!bootstrap.admin) {event.preventDefault(); return;}
        $('definitionPayload').value = JSON.stringify(definition());
    };
    let ticketSearchTimer;
    let searchGeneration = 0;
    async function loadTickets() {
        const generation = ++searchGeneration;
        try {
            const response = await fetch(bootstrap.ticketChoicesUrl + '?q=' + encodeURIComponent($('previewSearch').value));
            if (!response.ok) throw new Error('Ticket search failed.');
            const result = await response.json();
            if (generation !== searchGeneration) return;
            $('previewTicket').replaceChildren();
            const empty = element('option', '', result.tickets.length ? 'Choose a ticket' : 'No matching tickets');
            empty.value = '';
            $('previewTicket').append(empty);
            for (const ticket of result.tickets) {
                const option = element('option', '', '#' + ticket.id + ' · ' + ticket.title.slice(0, 80));
                option.value = ticket.id;
                $('previewTicket').append(option);
            }
        } catch (exc) {error(exc.message);}
    }
    $('previewSearch').oninput = () => {clearTimeout(ticketSearchTimer); ticketSearchTimer = setTimeout(loadTickets, 250);};
    loadTickets();
    $('previewRule').onclick = async () => {
        $('editorError').classList.add('d-none');
        if (!$('previewTicket').value) {error('Enter an existing ticket ID to preview.'); return;}
        try {
            $('previewRule').disabled = true;
            const response = await fetch(bootstrap.previewUrl, {
                method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': bootstrap.csrf},
                body: JSON.stringify({definition: definition(), ticket_id: Number($('previewTicket').value)})
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Preview failed.');
            const output = $('previewDetails');
            output.replaceChildren(element('p', 'fw-semibold', result.matched ? 'Rule matches this ticket.' : 'Rule does not match this ticket.'));
            for (const [number, matched] of Object.entries(result.conditions)) {
                output.append(element('p', 'small mb-1', `Condition ${number}: ${matched ? 'matches' : 'does not match'}`));
            }
            if (result.future.length) output.append(element('p', 'small', 'Future evaluation times: ' + result.future.join(', ')));
            for (const action of result.actions) {
                output.append(element('pre', 'small text-wrap border rounded p-2', JSON.stringify(action, null, 2)));
            }
            for (const warning of result.errors) output.append(element('p', 'small text-danger', JSON.stringify(warning)));
            $('previewOutput').classList.remove('d-none');
        } catch (exc) {error(exc.message);}
        finally {$('previewRule').disabled = false;}
    };
    document.addEventListener('focusin', event => {
        if (event.target.matches('#actions input:not([type=checkbox]), #actions textarea')) lastTextField = event.target;
    });
    const variableKeys = [...new Set([...Object.keys(bootstrap.fields), 'requester_name', 'group', 'assignee', 'category', 'ticket_url'])].sort();
    function variables() {
        $('variableList').replaceChildren();
        const query = $('variableSearch').value.toLowerCase();
        for (const key of variableKeys.filter(k => k.toLowerCase().includes(query))) {
            $('variableList').append(button('{{' + key + '}}', () => {
                if (!lastTextField || !lastTextField.isConnected) {error('Focus an action text field before choosing a variable.'); $('variableDialog').close(); return;}
                const start = lastTextField.selectionStart ?? lastTextField.value.length;
                const end = lastTextField.selectionEnd ?? start;
                lastTextField.value = lastTextField.value.slice(0, start) + '{{' + key + '}}' + lastTextField.value.slice(end);
                lastTextField.dispatchEvent(new Event('input', {bubbles: true}));
                $('variableDialog').close();
                lastTextField.focus();
            }, 'btn btn-sm btn-outline-secondary text-start font-monospace'));
        }
    }
    $('showVariables').onclick = () => {variables(); $('variableDialog').showModal(); $('variableSearch').focus();};
    $('closeVariables').onclick = () => $('variableDialog').close();
    $('variableSearch').oninput = variables;
    renderConditions();
    renderActions();
})();
