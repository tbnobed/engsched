/* Ticket insights is deliberately isolated from dashboard and ticket-detail code. */
(() => {
  'use strict';
  const root = document.getElementById('ticket-insights');
  if (!root) return;
  const $ = id => document.getElementById(id);
  const page = root.dataset.page;
  const form = $('ti-filters');
  const reportNames = {
    volume: 'Ticket volume', aging: 'Backlog aging', first_response: 'First response',
    resolution_time: 'Resolution time', workload: 'Technician workload',
    categories: 'Categories', stalled: 'Stalled tickets',
    targets: 'Service targets', requesters: 'Requester demand', reopened: 'Reopened tickets',
    handoffs: 'Assignment handoffs', satisfaction: 'Customer satisfaction', ai_usage: 'AI assistance usage'
  };
  const keys = ['start', 'end', 'technician', 'category', 'priority', 'status', 'source', 'department', 'location', 'stalled_days'];
  let config, data, myData, savedLayout, layout, dirty = false, saving = false;
  let autosaveTimer;
  let query = new URLSearchParams(location.search);
  let controller, generation = 0, dragId, dialogReturn;
  let reportKey = Object.hasOwn(reportNames, query.get('report')) ? query.get('report') : 'volume';
  let tableStates = [];
  let openWidgetActions;
  function positionWidgetActions() {
    if (!openWidgetActions) return;
    const { panel, toggle } = openWidgetActions;
    const anchor = toggle.getBoundingClientRect();
    const viewport = window.visualViewport;
    const leftEdge = (viewport?.offsetLeft || 0) + 8;
    const topEdge = (viewport?.offsetTop || 0) + 8;
    const rightEdge = leftEdge + (viewport?.width || document.documentElement.clientWidth) - 16;
    const bottomEdge = topEdge + (viewport?.height || window.innerHeight) - 16;
    if (anchor.bottom < topEdge || anchor.top > bottomEdge || anchor.right < leftEdge || anchor.left > rightEdge) {
      closeWidgetActions();
      return;
    }
    const above = Math.max(0, anchor.top - topEdge - 4);
    const below = Math.max(0, bottomEdge - anchor.bottom - 4);
    const preferBelow = panel.scrollHeight <= below || below > above;
    panel.style.maxHeight = `${preferBelow ? below : above}px`;
    panel.style.left = `${Math.max(leftEdge, Math.min(anchor.right - panel.offsetWidth, rightEdge - panel.offsetWidth))}px`;
    panel.style.top = `${Math.max(topEdge, Math.min(preferBelow ? anchor.bottom + 4 : anchor.top - panel.offsetHeight - 4, bottomEdge - panel.offsetHeight))}px`;
  }
  function closeWidgetActions(restoreFocus = false) {
    if (!openWidgetActions) return;
    const { panel, toggle } = openWidgetActions;
    if (panel.hidePopover && panel.matches(':popover-open')) panel.hidePopover();
    panel.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
    openWidgetActions = null;
    if (restoreFocus && toggle.isConnected) toggle.focus();
  }
  document.addEventListener('click', event => {
    if (openWidgetActions && !openWidgetActions.tools.contains(event.target)) closeWidgetActions();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && openWidgetActions) {
      event.preventDefault();
      closeWidgetActions(true);
    }
  });
  document.addEventListener('focusin', event => {
    if (openWidgetActions && !openWidgetActions.tools.contains(event.target)) closeWidgetActions();
  });
  window.addEventListener('resize', positionWidgetActions);
  document.addEventListener('scroll', positionWidgetActions, true);
  window.visualViewport?.addEventListener('resize', positionWidgetActions);
  window.visualViewport?.addEventListener('scroll', positionWidgetActions);

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function button(text, fn, cls = '') {
    const node = el('button', cls, text);
    node.type = 'button';
    node.addEventListener('click', fn);
    return node;
  }
  function copy(value) { return JSON.parse(JSON.stringify(value)); }
  function number(value) { return new Intl.NumberFormat().format(value); }
  function duration(value) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return 'Not tracked';
    const hours = Number(value);
    if (hours === 0) return '0 min';
    if (hours < 1) return `${Math.max(1, Math.round(hours * 60))} min`;
    if (hours < 24) return `${Number(hours.toFixed(1))} hr`;
    return `${Number((hours / 24).toFixed(1))} days`;
  }
  function safeLink(url, text, cls = '') {
    const node = el('a', cls, text);
    try {
      const target = new URL(url, location.origin);
      if (!['http:', 'https:'].includes(target.protocol)) throw new Error('Invalid ticket link');
      node.href = target.href;
    } catch (_) { return el('span', cls, text); }
    return node;
  }
  async function request(url, options = {}) {
    const response = await fetch(url, { credentials: 'include', ...options });
    let payload;
    try { payload = await response.json(); } catch (_) { throw new Error('The server did not return a valid response. Please try again.'); }
    if (!response.ok) {
      const message = typeof payload.error === 'string' ? payload.error : typeof payload.message === 'string' ? payload.message : `Request failed (${response.status}).`;
      throw new Error(message);
    }
    return payload;
  }
  function showError(message, retry) {
    const box = el('div', 'ti-state ti-error');
    box.append(el('h2', '', 'Unable to load ticket insights'), el('p', '', message));
    if (retry) box.append(button('Try again', retry));
    $('ti-status').replaceChildren(box);
  }
  function clearStatus() { $('ti-status').replaceChildren(); }
  function syncLinks() {
    root.querySelectorAll('[data-page-link]').forEach(link => {
      const params = new URLSearchParams(query);
      params.delete('report');
      if (link.dataset.pageLink === 'reports') params.set('report', reportKey);
      link.href = `/tickets/${link.dataset.pageLink}?${params}`;
    });
    if (page === 'reports') {
      const nav = $('ti-report-nav');
      nav.replaceChildren();
      Object.entries(reportNames).forEach(([key, name]) => {
        const params = new URLSearchParams(query);
        params.set('report', key);
        const link = safeLink(`/tickets/reports?${params}`, name);
        if (key === reportKey) link.setAttribute('aria-current', 'page');
        nav.append(link);
      });
    }
  }
  function reportURL(type, scope = 'team') {
    const params = new URLSearchParams(query);
    params.set('report', type);
    if (scope === 'me') params.set('scope', 'me');
    else params.delete('scope');
    return `/tickets/reports?${params}`;
  }
  function fillFilters() {
    const sources = { technician: 'technicians', category: 'categories', priority: 'priorities', status: 'statuses', source: 'sources', department: 'departments', location: 'locations' };
    Object.entries(sources).forEach(([key, source]) => {
      const select = form.elements.namedItem(key);
      const existing = new Set(Array.from(select.options, option => option.value));
      (config.options[source] || []).forEach(option => {
        if (!existing.has(String(option.id))) {
          const node = el('option', '', option.name);
          node.value = String(option.id);
          select.append(node);
        }
      });
    });
    if (page === 'reports' && !form.elements.namedItem('scope')) {
      const label = el('label', '', 'Assignment scope');
      const select = el('select');
      select.name = 'scope';
      [['team', 'Whole team'], ['me', 'Assigned to me only']].forEach(([value, name]) => {
        const option = el('option', '', name); option.value = value; select.append(option);
      });
      label.append(select);
      form.querySelector('.ti-filter-grid').append(label);
    }
    [...keys, 'scope'].forEach(key => {
      const input = form.elements.namedItem(key);
      if (!input) return;
      if (query.has(key)) input.value = query.get(key);
    });
    $('ti-timezone').textContent = `Dates & activity in ${config.timezone}`;
    if (config.is_admin && config.settings_url) {
      $('ti-settings-link').href = config.settings_url;
      $('ti-settings-link').hidden = false;
    }
    $('ti-apply').disabled = false;
    syncLinks();
  }
  function filterQuery() {
    const params = new URLSearchParams();
    [...keys, ...(page === 'reports' ? ['scope'] : [])].forEach(key => {
      const value = form.elements.namedItem(key)?.value;
      if (value) params.set(key, value);
    });
    if (page === 'reports') params.set('report', reportKey);
    return params;
  }
  function validateDates() {
    const start = form.elements.namedItem('start').value;
    const end = form.elements.namedItem('end').value;
    const endInput = form.elements.namedItem('end');
    endInput.setCustomValidity('');
    if (start && end) {
      const days = (Date.parse(end) - Date.parse(start)) / 86400000;
      if (days < 0) endInput.setCustomValidity('End date must be on or after the start date.');
      else if (days > 365) endInput.setCustomValidity('Choose an inclusive range of no more than 366 days.');
    }
    return form.reportValidity();
  }
  function needsMine() { return page === 'overview' && layout.widgets.some(widget => widget.scope === 'me'); }
  function skeleton() {
    cleanupChartAnimations();
    const container = page === 'overview' ? $('ti-widgets') : $('ti-report');
    container.replaceChildren(el('div', 'ti-skeleton'), el('div', 'ti-skeleton'));
    container.setAttribute('aria-busy', 'true');
    if (page === 'reports') {
      $('ti-export').hidden = true;
      $('ti-print').disabled = true;
    }
  }
  async function loadData() {
    if (!config) return;
    if (controller) controller.abort();
    controller = new AbortController();
    const current = ++generation;
    const params = new URLSearchParams(query);
    params.delete('report');
    if (page === 'overview') params.delete('scope');
    skeleton();
    clearStatus();
    $('ti-apply').disabled = true;
    try {
      const jobs = [request(`/api/ticket-insights/data?${params}`, { signal: controller.signal })];
      if (needsMine()) {
        const mine = new URLSearchParams(params); mine.set('scope', 'me');
        jobs.push(request(`/api/ticket-insights/data?${mine}`, { signal: controller.signal }));
      }
      const result = await Promise.all(jobs);
      if (current !== generation) return;
      [data, myData] = result;
      if (!data || !Array.isArray(data.tickets) || !data.reports || !data.charts) throw new Error('The ticket insights response is incomplete.');
      ['start', 'end'].forEach(key => {
        if (!query.has(key) && data[key]) {
          form.elements.namedItem(key).value = data[key];
          query.set(key, data[key]);
        }
      });
      history.replaceState(null, '', `${location.pathname}?${query}`);
      $('ti-generated').textContent = `Updated ${displayDate(data.generated_at)} · ${data.timezone} · Period: ${data.start} through ${data.end}`;
      renderMethodology();
      if (page === 'overview') renderWidgets();
      else renderReport();
      syncLinks();
    } catch (error) {
      if (error.name === 'AbortError' || current !== generation) return;
      data = undefined; myData = undefined;
      (page === 'overview' ? $('ti-widgets') : $('ti-report')).replaceChildren();
      showError(error.message, loadData);
    } finally {
      if (current === generation) {
        $('ti-apply').disabled = false;
        (page === 'overview' ? $('ti-widgets') : $('ti-report')).removeAttribute('aria-busy');
      }
    }
  }
  function displayDate(value) {
    if (!value) return 'Not tracked';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(undefined, { timeZone: data?.timezone || config?.timezone || 'UTC', dateStyle: 'medium', timeStyle: 'short' }).format(date);
  }
  function dayOf(value, timezone = data.timezone) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(date);
    const part = key => parts.find(item => item.type === key)?.value;
    return `${part('year')}-${part('month')}-${part('day')}`;
  }
  function renderMethodology() {
    const container = $('ti-methodology-content');
    const list = el('ul');
    (data.methodology || []).forEach(text => list.append(el('li', '', text)));
    list.append(el('li', '', 'Aging, workload, stalled tickets and open-queue metrics show the current state, not a historical snapshot. Dates do not restrict current backlog.'));
    list.append(el('li', '', 'Categories compare tickets created during the selected period with the current backlog. These are different populations.'));
    list.append(el('li', '', 'A missing duration means no qualifying tracked event. It is not zero. Widget assignment scope is independent of saved filters.'));
    const coverage = data.coverage || {};
    container.replaceChildren(list, el('p', '', `Resolution history missing: ${number(coverage.missing_resolution_history ?? 0)} tickets. AI comments excluded: ${number(coverage.excluded_ai_comments ?? 0)}.`));
  }
  function openDialog(title) {
    const dialog = $('ti-dialog');
    if (dialog.open) dialog.close();
    dialogReturn = document.activeElement;
    $('ti-dialog-title').textContent = title;
    $('ti-dialog-body').replaceChildren();
    dialog.showModal();
    $('ti-dialog-close').focus();
    return $('ti-dialog-body');
  }
  function openTickets(title, tickets) {
    const body = openDialog(title);
    body.append(el('p', 'ti-muted', `${number(tickets.length)} matching tickets · Current workspace filters applied`));
    const columns = [
      { key: 'id', label: 'Ticket' }, { key: 'title', label: 'Subject' }, { key: 'status', label: 'Status' },
      { key: 'priority', label: 'Priority' }, { key: 'assignee', label: 'Technician' },
      { key: 'category', label: 'Category' }, { key: 'age_days', label: 'Age (days)' }, { key: 'idle_days', label: 'Idle (days)' }
    ];
    body.append(createTable(columns, tickets, { tickets: true }));
  }
  function ticketCell(row, key, options) {
    const value = row[key];
    if (key === '_review') {
      if (options.plain) return el('span');
      return canReview(row) ? button('Review / rate', () => reviewAI(row), 'ti-link-button') : el('span', 'ti-muted', 'Unavailable');
    }
    if (options.tickets && (key === 'id' || key === 'title')) return safeLink(row.url, key === 'id' ? `#${value}` : value);
    if (row.ticket_id && ['ticket_id', 'ticket', 'title', 'subject'].includes(key)) {
      const url = row.ticket_url || data?.tickets.find(ticket => String(ticket.id) === String(row.ticket_id))?.url;
      if (url) return safeLink(url, value ?? `#${row.ticket_id}`);
    }
    if (value === null || value === undefined) return el('span', 'ti-muted', options.report === 'targets' && ['response_target', 'resolution_target'].includes(key) ? 'Not configured' : 'Not tracked');
    if (/_hours$/.test(key) || key === 'hours') return el('span', '', number(value));
    if (['first_response', 'resolution_time'].includes(key)) return el('span', '', duration(value));
    if (/_at$/.test(key) || ['last_reopened', 'interval_start', 'interval_end'].includes(key)) return el('span', '', displayDate(value));
    if (typeof value === 'boolean') return el('span', '', value ? 'Yes' : 'No');
    if (Array.isArray(value)) return el('span', '', value.join(', '));
    if (typeof value === 'object') return el('span', '', JSON.stringify(value));
    if (!options.plain && ['volume', 'workload', 'categories', 'requesters'].includes(options.report) && typeof value === 'number' &&
        ['created', 'resolved', 'completed', 'open', 'high_priority', 'overdue'].includes(key)) {
      return button(number(value), () => openReportRow(row, options.report, key), 'ti-link-button');
    }
    return el('span', '', typeof value === 'number' ? number(value) : String(value));
  }
  function openReportRow(row, report, key) {
    const matching = data.tickets.filter(ticket => {
      if (report === 'volume') {
        return key === 'created'
          ? ticket.in_created_period && ticket.created_display.slice(0, 10) === row.date
          : ticket.in_resolved_period && dayOf(ticket.completed_at) === row.date;
      }
      if (report === 'workload' && ticket.assignee !== row.technician) return false;
      if (report === 'categories' && ticket.category !== row.category) return false;
      if (report === 'requesters' && ticket.requester_key !== row.requester_key) return false;
      if (key === 'created') return ticket.in_created_period;
      if (key === 'completed' || key === 'resolved') return ticket.in_resolved_period;
      if (key === 'high_priority') return ticket.is_open && ticket.priority >= 2;
      if (key === 'overdue') return ticket.is_overdue;
      return ticket.is_open;
    });
    openTickets(`${row.date || row.requester || row.technician || row.category} / ${key.replaceAll('_', ' ')}`, matching);
  }
  function compareReportValues(a, b, key, direction) {
    // Unknown measurements remain last in either direction, never become zero.
    const missing = value => value === null || value === undefined || value === '';
    if (missing(a) || missing(b)) return Number(missing(a)) - Number(missing(b));
    let result;
    if (typeof a === 'number' && typeof b === 'number') result = a - b;
    else if (typeof a === 'boolean' && typeof b === 'boolean') result = Number(a) - Number(b);
    else if ((/_at$/.test(key) || ['date', 'last_reopened', 'interval_start', 'interval_end'].includes(key)) &&
      Number.isFinite(Date.parse(a)) && Number.isFinite(Date.parse(b))) result = Date.parse(a) - Date.parse(b);
    else result = String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
    return direction === 'descending' ? -result : result;
  }
  function createTable(columns, rows, options = {}) {
    let sortKey = null, sortDirection = 'ascending';
    const sortHeaders = [];
    const sorted = items => sortKey ? [...items].sort((a, b) => compareReportValues(a[sortKey], b[sortKey], sortKey, sortDirection)) : items;
    const panel = el('div', 'ti-table-block');
    const controls = el('div', 'ti-table-controls');
    const searchLabel = el('label', '', 'Search these rows');
    const search = el('input');
    search.type = 'search'; search.placeholder = 'Search report rows…';
    searchLabel.append(search);
    const sizeLabel = el('label', '', 'Rows per page');
    const size = el('select');
    [25, 50, 100].forEach(value => { const option = el('option', '', value); option.value = value; size.append(option); });
    sizeLabel.append(size); controls.append(searchLabel, sizeLabel);
    const tableWrap = el('div', 'ti-table-wrap ti-screen-table');
    const table = el('table');
    const caption = el('caption', '', options.tickets ? 'Matching tickets' : 'Filtered report rows');
    caption.style.captionSide = 'top'; caption.style.padding = '0 20px 10px'; caption.style.color = 'var(--ti-muted)';
    const head = el('thead'), headRow = el('tr');
    columns.forEach(column => {
      const th = el('th', column.key === '_review' ? 'ti-no-print' : '');
      th.scope = 'col';
      if (column.key === '_review') th.textContent = column.label;
      else {
        const indicator = el('span', 'ti-sort-indicator', '↕');
        indicator.setAttribute('aria-hidden', 'true');
        const toggle = button(column.label, () => {
          sortDirection = sortKey === column.key && sortDirection === 'ascending' ? 'descending' : 'ascending';
          sortKey = column.key;
          currentPage = 1;
          render();
        }, 'ti-sort-button');
        toggle.append(indicator);
        th.append(toggle);
        sortHeaders.push({ th, toggle, indicator, column });
      }
      headRow.append(th);
    });
    head.append(headRow);
    const tbody = el('tbody');
    table.append(caption, head, tbody); tableWrap.append(table);
    const footer = el('div', 'ti-pagination'), counter = el('span');
    counter.setAttribute('aria-live', 'polite');
    const actions = el('div', 'ti-actions');
    let currentPage = 1;
    const previous = button('Previous', () => { currentPage--; render(); });
    const next = button('Next', () => { currentPage++; render(); });
    actions.append(previous, next); footer.append(counter, actions);
    panel.append(controls, tableWrap, footer);
    const printable = el('div', 'ti-print-table');
    if (options.print) panel.append(printable);
    function makeRow(row, plain = false) {
      const tr = el('tr');
      columns.forEach(column => {
        const td = el('td', column.key === '_review' ? 'ti-no-print' : ''); td.append(ticketCell(row, column.key, { ...options, plain: options.plain || plain })); tr.append(td);
      });
      return tr;
    }
    function render() {
      const term = search.value.trim().toLocaleLowerCase();
      const matching = sorted(rows.filter(row => columns.some(column => String(row[column.key] ?? '').toLocaleLowerCase().includes(term))));
      sortHeaders.forEach(({ th, toggle, indicator, column }) => {
        const active = sortKey === column.key;
        th.setAttribute('aria-sort', active ? sortDirection : 'none');
        indicator.textContent = active ? (sortDirection === 'ascending' ? '↑' : '↓') : '↕';
        toggle.setAttribute('aria-label', `${column.label}: sort ${active && sortDirection === 'ascending' ? 'descending' : 'ascending'}`);
      });
      const limit = Number(size.value);
      const pages = Math.max(1, Math.ceil(matching.length / limit));
      currentPage = Math.max(1, Math.min(currentPage, pages));
      tbody.replaceChildren();
      matching.slice((currentPage - 1) * limit, currentPage * limit).forEach(row => tbody.append(makeRow(row)));
      if (!matching.length) {
        const row = el('tr'), cell = el('td');
        cell.colSpan = Math.max(1, columns.length);
        const empty = el('div', 'ti-state');
        empty.append(el('h3', '', term ? 'No rows match your search' : 'No qualifying rows'), el('p', '', term ? 'Try another ticket, name or category.' : 'Change the workspace filters or choose another report.'));
        if (term) empty.append(button('Clear search', () => { search.value = ''; currentPage = 1; render(); }));
        cell.append(empty); row.append(cell); tbody.append(row);
      }
      counter.textContent = matching.length ? `${number((currentPage - 1) * limit + 1)}–${number(Math.min(currentPage * limit, matching.length))} of ${number(matching.length)} rows${term ? ` (${number(rows.length)} before search)` : ''}` : `0 of ${number(rows.length)} rows`;
      previous.disabled = currentPage <= 1; next.disabled = currentPage >= pages;
      if (options.print) {
        // Print and CSV retain every server-filtered row, independently of client search/pagination.
        const printTable = el('table'), printBody = el('tbody');
        printTable.append(head.cloneNode(true));
        sorted(rows).forEach(row => printBody.append(makeRow(row, true)));
        printTable.append(printBody);
        printable.replaceChildren(printTable);
      }
    }
    search.addEventListener('input', () => { currentPage = 1; render(); });
    size.addEventListener('change', () => { currentPage = 1; render(); });
    render();
    if (options.print) tableStates = [render];
    return panel;
  }
  function mutationOptions(method, payload) {
    return { method, headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '' }, body: JSON.stringify(payload) };
  }
  function feedbackControls() {
    const section = el('section', 'ti-interaction');
    section.append(el('h3', '', 'Collect feedback'), el('p', '', 'Manually share this permission-bearing link only with the requester. No email is sent automatically. Links expire after 30 days. Creating another link invalidates the previous unsubmitted link; an existing response cannot be replaced.'));
    const controls = el('div', 'ti-feedback-controls'), label = el('label', '', 'Resolved or closed ticket');
    const select = el('select'), placeholder = el('option', '', 'Choose a ticket…'); placeholder.value = ''; select.append(placeholder);
    (data.feedback_eligible || []).forEach(ticket => {
      const option = el('option', '', `#${ticket.id} · ${ticket.title}`); option.value = String(ticket.id); select.append(option);
    });
    label.append(select);
    const status = el('p', 'ti-inline-status'); status.setAttribute('role', 'status');
    const result = el('div', 'ti-feedback-result'); result.hidden = true;
    const create = button('Create feedback link', async () => {
      if (!select.value) return;
      if (!window.confirm('Create a feedback link? This replaces any old unsubmitted link for this ticket. An existing response cannot be replaced. No email will be sent. Share only with the requester.')) return;
      create.disabled = true; select.disabled = true; result.replaceChildren(); result.hidden = true;
      status.dataset.error = 'false'; status.textContent = 'Creating feedback link…';
      try {
        const response = await request('/api/ticket-insights/feedback-links', mutationOptions('POST', { ticket_id: Number(select.value) }));
        if (typeof response.path !== 'string' || !/^\/feedback\/[^/?#]+$/.test(response.path)) throw new Error('The server did not return a valid feedback link. Please retry.');
        const url = window.location.origin + response.path;
        const linkLabel = el('label', '', 'Private requester feedback link'), input = el('input');
        input.readOnly = true; input.value = url; input.addEventListener('focus', () => input.select()); linkLabel.append(input);
        const actions = el('div', 'ti-actions');
        const copyButton = button('Copy link', async () => {
          try {
            if (!navigator.clipboard?.writeText) throw new Error('Clipboard access is unavailable.');
            await navigator.clipboard.writeText(url);
            status.dataset.error = 'false'; status.textContent = 'Link copied. Share it only with the requester.';
          } catch (_) {
            status.dataset.error = 'true'; status.textContent = 'Could not copy the link. Select the link above and copy it manually, or try Copy link again.';
            input.focus(); input.select();
          }
        });
        const open = safeLink(url, 'Open link in new tab', 'ti-button'); open.target = '_blank'; open.rel = 'noopener noreferrer';
        actions.append(copyButton, open); result.append(linkLabel, actions);
        result.hidden = false;
        status.textContent = `Link created. Expires ${displayDate(response.expires_at)}. No email has been sent.`;
      } catch (error) {
        result.replaceChildren(); result.hidden = true; status.dataset.error = 'true'; status.textContent = `${error.message} You can retry creating the link.`;
      } finally {
        select.disabled = false; create.disabled = !select.value;
      }
    }, 'ti-primary');
    create.disabled = true;
    select.addEventListener('change', () => { create.disabled = !select.value; result.replaceChildren(); result.hidden = true; status.textContent = ''; });
    controls.append(label, create); section.append(controls, result, status);
    if (!(data.feedback_eligible || []).length) section.append(el('p', '', 'No resolved or closed tickets are eligible in the current filters. Adjust the workspace filters to find a ticket.'));
    return section;
  }
  function canReview(row) {
    return Number.isInteger(row.message_id) && row.status === 'completed';
  }
  function reviewAI(row) {
    const body = openDialog(`AI response / Ticket #${row.ticket_id}`);
    body.append(el('p', 'ti-muted', row.title), el('div', 'ti-response-content', row.response_content || 'No response content recorded.'));
    const status = el('p', 'ti-inline-status'); status.setAttribute('role', 'status');
    const votes = el('p', 'ti-muted'), actions = el('div', 'ti-actions');
    const choices = [[true, 'Helpful'], [false, 'Not helpful'], [null, 'Clear my rating']];
    const buttons = choices.map(([helpful, label]) => {
      const control = button(label, async () => {
        buttons.forEach(item => { item.disabled = true; });
        status.dataset.error = 'false'; status.textContent = 'Saving your rating…';
        try {
          const response = await request(`/api/ticket-insights/ai/${encodeURIComponent(row.message_id)}/rating`, mutationOptions('PUT', { helpful }));
          if (typeof response.helpful_votes !== 'number' || typeof response.not_helpful_votes !== 'number' || ![true, false, null].includes(response.my_rating)) throw new Error('The server did not confirm your rating. Try again.');
          Object.assign(row, { helpful_votes: response.helpful_votes, not_helpful_votes: response.not_helpful_votes, my_rating: response.my_rating });
          update(); await loadData();
          status.textContent = helpful === null ? 'Your rating was cleared.' : 'Your rating was saved.';
        } catch (error) { status.dataset.error = 'true'; status.textContent = `${error.message} Please try again.`; }
        finally { update(); }
      });
      actions.append(control); return control;
    });
    function update() {
      votes.textContent = `${number(row.helpful_votes || 0)} helpful · ${number(row.not_helpful_votes || 0)} not helpful · Your rating: ${row.my_rating === true ? 'Helpful' : row.my_rating === false ? 'Not helpful' : 'Not rated'}`;
      buttons.forEach((control, index) => {
        control.disabled = choices[index][0] === null && row.my_rating == null;
        if (index < 2) control.setAttribute('aria-pressed', String(row.my_rating === choices[index][0]));
      });
    }
    body.append(votes, actions, status); update();
  }
  function renderReport() {
    const report = data.reports[reportKey];
    if (!report || !Array.isArray(report.rows) || !Array.isArray(report.columns)) {
      $('ti-report').replaceChildren();
      showError('This report is not available in the server response.', loadData);
      return;
    }
    const panel = el('section', 'ti-panel');
    const header = el('div', 'ti-report-head');
    const top = el('div', 'ti-panel-head');
    top.append(el('h2', '', report.title || reportNames[reportKey]), button(`${number(report.rows.length)} report rows`, () => {
      const body = openDialog(report.title || reportNames[reportKey]);
      body.append(createTable(report.columns, report.rows, { plain: true }));
    }, 'ti-link-button'));
    header.append(top, el('p', '', report.description));
    const snapshot = ['aging', 'workload', 'stalled'].includes(reportKey);
    header.append(el('p', '', snapshot ? 'Current snapshot · Date range does not restrict these rows.' : reportKey === 'categories' ? 'Created in the selected period and current backlog are reported separately.' : `Period: ${data.start} through ${data.end}, inclusive · ${data.timezone}`));
    header.append(el('p', '', 'Search and pagination affect the on-screen table only. CSV and Print / Save PDF include all rows from the applied workspace filters.'));
    const applied = el('p', 'ti-print-filters', filterDescription());
    header.append(applied);
    if (['first_response', 'resolution_time'].includes(reportKey)) {
      const summary = el('div', 'ti-report-summary');
      summary.append(
        el('strong', '', `Median: ${duration(report.median_hours)}`),
        el('strong', '', `90th percentile: ${duration(report.p90_hours)}`),
        el('span', 'ti-muted', `${number(report.measured || 0)} measured tickets${report.total !== undefined ? ` of ${number(report.total)} in the creation cohort` : ''}`)
      );
      header.append(summary);
      if (report.missing_history) header.append(el('p', 'ti-muted', `${number(report.missing_history)} completed tickets in the filtered dataset have no recorded completion timestamp and cannot be assigned to a historical period.`));
    }
    if (Array.isArray(report.summary)) {
      const summary = el('div', 'ti-report-summary');
      report.summary.forEach(metric => {
        const item = el('div', 'ti-summary-metric');
        item.append(el('span', '', metric.label), el('strong', '', metric.value == null ? (reportKey === 'targets' ? 'Not configured' : 'Not tracked') : metric.value));
        summary.append(item);
      });
      header.append(summary);
    }
    if (reportKey === 'targets') {
      header.append(el('p', '', 'Unset service targets are not configured, not zero. Targets use calendar hours, without business-hour schedules or pauses. Current policies apply retrospectively.'));
      if (config.is_admin && config.settings_url) header.append(safeLink(config.settings_url, 'Configure service targets', 'ti-no-print'));
      else header.append(el('p', 'ti-muted', 'An administrator can configure service targets in Report settings.'));
    }
    const columns = report.columns.filter(column => !['response_content', '_review'].includes(column.key));
    if (reportKey === 'ai_usage') columns.push({ key: '_review', label: 'Review' });
    panel.append(header);
    if (reportKey === 'satisfaction') panel.append(feedbackControls());
    panel.append(createTable(columns, report.rows, { report: reportKey, print: true }));
    $('ti-report').replaceChildren(panel);
    const params = new URLSearchParams(query); params.delete('report');
    const exportLink = $('ti-export');
    exportLink.href = `/api/ticket-insights/export/${reportKey}.csv?${params}`;
    exportLink.hidden = false; exportLink.setAttribute('download', '');
    $('ti-print').disabled = false;
  }
  function filterDescription() {
    const labels = [];
    [...keys, 'scope'].forEach(key => {
      const field = form.elements.namedItem(key);
      if (!field || ['start', 'end'].includes(key)) return;
      const value = query.get(key) || (key === 'stalled_days' ? '7' : 'all');
      if (value === 'all' || value === 'team') return;
      const selected = Array.from(field.options || []).find(option => option.value === value);
      labels.push(`${key.replaceAll('_', ' ')}: ${selected?.textContent || value}`);
    });
    return labels.length ? `Applied filters — ${labels.join(' · ')}` : 'Applied filters — All technicians, categories, priorities, statuses, sources, departments and locations.';
  }
  function ticketsFor(type, source) {
    const tickets = source.tickets;
    const mine = ticket => String(ticket.assignee_id) === String(config.user_id);
    const threshold = Number(query.get('stalled_days') || 7);
    switch (type) {
      case 'my_open': case 'my_queue': return tickets.filter(ticket => ticket.is_open && mine(ticket));
      case 'unassigned': return tickets.filter(ticket => ticket.is_open && !ticket.assignee_id);
      case 'high_priority': return tickets.filter(ticket => ticket.is_open && Number(ticket.priority) >= 2);
      case 'overdue': return tickets.filter(ticket => ticket.is_overdue);
      case 'created': return tickets.filter(ticket => ticket.in_created_period);
      case 'resolved': return tickets.filter(ticket => ticket.in_resolved_period);
      case 'stalled': return tickets.filter(ticket => ticket.is_open && Number(ticket.idle_days) >= threshold);
      default: return tickets;
    }
  }
  // Null/empty strings are unknown, not measured zero. Never invent history.
  function chartValue(value) {
    return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
  }
  function distribution(rows, key, thresholds, labels, idKey = 'id') {
    const groups = labels.map(label => ({ label, count: 0, ids: [] }));
    let missing = 0;
    rows.forEach(row => {
      const value = chartValue(row[key]);
      if (value === null) { missing++; return; }
      const group = groups[thresholds.filter(threshold => value >= threshold).length];
      group.count++;
      group.ids.push(row[idKey]);
    });
    return { groups, missing, measured: rows.length - missing };
  }
  function queueDistribution(type, matching) {
    if (['my_queue', 'stalled'].includes(type)) {
      return { title: type === 'stalled' ? 'Days without human activity' : 'Current ticket age',
        ...distribution(matching, type === 'stalled' ? 'idle_days' : 'age_days',
          [1, 3, 7, 14, 30], ['Under 1 day', '1–3 days', '3–7 days', '7–14 days', '14–30 days', '30+ days']) };
    }
    return { title: 'Current priority · Ticket counts',
      ...distribution(matching, 'priority', [1, 2, 3], ['Low', 'Medium', 'High', 'Urgent']) };
  }
  const widgetChartSignatures = new Map();
  const runningChartAnimations = new Set();
  const pendingChartEntries = new Map();
  const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const chartObserver = typeof IntersectionObserver === 'function' ? new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const play = pendingChartEntries.get(entry.target);
      chartObserver.unobserve(entry.target);
      pendingChartEntries.delete(entry.target);
      if (entry.target.isConnected) play?.();
    });
  }, { threshold: 0.12 }) : null;
  function cleanupChartAnimations() {
    runningChartAnimations.forEach(animation => animation.cancel());
    pendingChartEntries.forEach((_, card) => {
      chartObserver?.unobserve(card);
      card.classList.remove('ti-chart-pending');
    });
    pendingChartEntries.clear();
  }
  motionPreference.addEventListener?.('change', event => {
    if (event.matches) {
      runningChartAnimations.forEach(animation => animation.cancel());
      pendingChartEntries.forEach(play => play());
      pendingChartEntries.clear();
      chartObserver?.disconnect();
    }
  });
  function animateWidget(card, widget, source) {
    // Reordering, saving and opening an actions menu must not replay charts.
    const signature = JSON.stringify([widget.type, widget.scope, widget.limit, source]);
    const previous = widgetChartSignatures.get(widget.id);
    if (previous === signature) return;
    function run(node, frames, options) {
      const animation = node.animate(frames, options);
      runningChartAnimations.add(animation);
      const done = () => runningChartAnimations.delete(animation);
      animation.addEventListener('finish', done, { once: true });
      animation.addEventListener('cancel', done, { once: true });
    }
    function play() {
      widgetChartSignatures.set(widget.id, signature);
      card.classList.remove('ti-chart-pending');
      if (motionPreference.matches || !card.animate) return;
      // Never transform the article: the actions popover must stay viewport-fixed.
      run(card, [{ opacity: .45 }, { opacity: 1 }], { duration: 800, easing: 'ease-out' });
      card.querySelectorAll('.ti-bar-fill, .ti-column-ink, .ti-ring-segment').forEach((ink, index) => {
        const ring = ink.classList.contains('ti-ring-segment');
        const axis = ink.classList.contains('ti-bar-fill') ? 'X' : 'Y';
        run(ink, ring ? [{ opacity: 0, transform: 'scale(.88)' }, { opacity: 1, transform: 'scale(1)' }]
          : [{ transform: `scale${axis}(0)` }, { transform: `scale${axis}(1)` }],
        { duration: 950, delay: Math.min(index * 35, 150), easing: 'cubic-bezier(.16,.65,.3,1)', fill: 'backwards' });
      });
    }
    if (motionPreference.matches || !card.animate || !chartObserver) { play(); return; }
    card.classList.add('ti-chart-pending');
    pendingChartEntries.set(card, play);
    chartObserver.observe(card);
  }
  function svgNode(tag, attributes = {}) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }
  function renderRing(container, groups, source, title) {
    if (!Array.isArray(groups)) { container.append(el('p', 'ti-muted', 'Breakdown unavailable.')); return; }
    const complete = groups.every(group => chartValue(group.count) !== null);
    const total = groups.reduce((sum, group) => sum + (chartValue(group.count) ?? 0), 0);
    const plot = el('div', 'ti-ring-plot');
    const ring = svgNode('svg', { viewBox: '0 0 160 160', role: 'img', 'aria-label': `${title}: ${complete ? `${number(total)} tickets` : 'Total not tracked'}. Breakdown listed alongside.` });
    ring.append(svgNode('circle', { cx: 80, cy: 80, r: 59, class: 'ti-ring-track' }));
    let offset = 0;
    groups.forEach((group, index) => {
      const count = chartValue(group.count);
      if (!complete || !count || !total) return;
      const length = count / total * 100;
      const arc = svgNode('circle', { cx: 80, cy: 80, r: 59, pathLength: 100,
        'stroke-dasharray': `${length} ${100 - length}`, 'stroke-dashoffset': -offset,
        class: `ti-ring-segment ti-series-${index % 5}` });
      const rotated = svgNode('g', { transform: 'rotate(-90 80 80)' });
      rotated.append(arc);
      ring.append(rotated); offset += length;
    });
    const center = svgNode('text', { x: 80, y: 78, 'text-anchor': 'middle', class: 'ti-ring-total' });
    center.textContent = complete ? number(total) : '—';
    const caption = svgNode('text', { x: 80, y: 99, 'text-anchor': 'middle', class: 'ti-ring-caption' });
    caption.textContent = !complete ? 'not tracked' : total ? 'tickets' : 'no tickets';
    ring.append(center, caption);
    const legend = el('div', 'ti-ring-legend');
    groups.forEach((group, index) => {
      const ids = new Set((group.ids || []).map(String));
      const count = chartValue(group.count);
      const row = button('', () => openTickets(`${title} / ${group.label}`,
        source.tickets.filter(ticket => ids.has(String(ticket.id)))), 'ti-ring-row');
      row.setAttribute('aria-label', `${group.label}: ${count === null ? 'Not tracked' : number(count)} tickets. Open matching tickets.`);
      row.append(el('i', `ti-series-${index % 5}`), el('span', '', group.label),
        el('strong', '', count === null ? '—' : number(count)));
      legend.append(row);
    });
    plot.append(ring, legend); container.append(plot);
  }
  function renderHistogram(container, groups, source, title) {
    const maximum = Math.max(1, ...groups.map(group => chartValue(group.count) ?? 0));
    const plot = el('div', 'ti-histogram');
    plot.style.setProperty('--ti-plot-max', maximum);
    const scale = el('div', 'ti-plot-scale');
    [maximum, Math.round(maximum / 2), 0].forEach(value => scale.append(el('span', '', number(value))));
    const columns = el('div', 'ti-hist-columns');
    groups.forEach(group => {
      const count = chartValue(group.count);
      const ids = new Set(group.ids.map(String));
      const column = button('', () => openTickets(`${title} / ${group.label}`,
        source.tickets.filter(ticket => ids.has(String(ticket.id)))), 'ti-hist-column');
      column.setAttribute('aria-label', `${group.label}: ${count === null ? 'Not tracked' : number(count)} tickets. Open matching tickets.`);
      const track = el('span', 'ti-hist-track'), ink = el('span', 'ti-column-ink');
      ink.hidden = count === null;
      ink.style.height = `${(count ?? 0) / maximum * 100}%`;
      ink.setAttribute('aria-hidden', 'true');
      track.append(ink, el('strong', 'ti-hist-value', count === null ? '—' : number(count)));
      column.append(track, el('span', 'ti-hist-label', group.label));
      columns.append(column);
    });
    plot.append(scale, columns); container.append(plot);
  }
  function renderDistribution(container, result, source, title) {
    container.append(el('p', 'ti-chart-heading', result.title || 'Tracked calendar hours · Ticket counts'));
    if (!result.measured && result.missing) {
      container.append(el('p', 'ti-widget-caption', 'Distribution unavailable: no qualifying measured values.'));
    } else if (result.title?.startsWith('Current priority')) renderRing(container, result.groups, source, title);
    else if (!result.title) renderHistogram(container, result.groups, source, title);
    else renderBars(container, result.groups, source, title, result.groups.length);
    if (result.missing) container.append(el('p', 'ti-widget-caption', `${number(result.missing)} rows not tracked; excluded from the distribution (not zero).`));
  }
  function renderBars(container, groups, source, title, limit) {
    if (!Array.isArray(groups)) {
      container.append(el('p', 'ti-muted', 'This breakdown is unavailable: group data was not supplied.'));
      return;
    }
    const all = groups;
    const shown = all.slice(0, limit);
    const max = Math.max(1, ...all.map(item => chartValue(item.count) ?? 0));
    const bars = el('div', 'ti-bars');
    if (container.classList.contains('ti-widget')) {
      const axis = el('div', 'ti-bar-axis');
      [0, Math.round(max / 2), max].forEach(value => axis.append(el('span', '', number(value))));
      bars.append(axis);
    }
    shown.forEach(group => {
      const ids = new Set((group.ids || []).map(String));
      const matching = source.tickets.filter(ticket => ids.has(String(ticket.id)));
      const bar = button('', () => openTickets(`${title} / ${group.label}`, matching), 'ti-bar');
      const count = chartValue(group.count);
      bar.setAttribute('aria-label', `${group.label}: ${count === null ? 'Not tracked' : number(count)} tickets. Open matching tickets.`);
      const track = el('span', 'ti-bar-track'), fill = el('span', 'ti-bar-fill');
      fill.style.width = `${count === null ? 0 : count / max * 100}%`;
      fill.hidden = count === null;
      track.setAttribute('aria-hidden', 'true');
      track.append(fill); bar.append(el('span', '', group.label), track, el('strong', '', count === null ? 'Not tracked' : number(count)));
      bars.append(bar);
    });
    if (!shown.length) bars.append(el('p', 'ti-muted', 'No qualifying tickets for this breakdown.'));
    container.append(bars);
    if (all.length > shown.length) {
      container.append(button(`View all ${number(all.length)} groups`, () => {
        const body = openDialog(title);
        renderBars(body, all, source, title, all.length);
      }, 'ti-link-button'));
    }
  }
  function renderVolume(container, source, series = ['created', 'resolved'], overview = false) {
    const days = source.charts.volume || [];
    if (!days.length) { container.append(el('p', 'ti-muted', 'Daily activity data is unavailable for this period.')); return; }
    const maximum = Math.max(1, ...days.flatMap(day => series.map(type => chartValue(day[type]) ?? 0)));
    const legend = el('div', 'ti-legend');
    series.forEach(type => { const span = el('span', type === 'resolved' ? 'resolved' : ''); span.append(el('i'), document.createTextNode(type === 'created' ? 'Created' : 'Completed')); legend.append(span); });
    const scroll = el('div', 'ti-chart-scroll'); scroll.tabIndex = 0; scroll.setAttribute('aria-label', 'Daily ticket volume. Scroll horizontally to view all dates.');
    const chart = el('div', 'ti-volume');
    if (overview) {
      chart.classList.add('ti-daily-plot');
      scroll.classList.add('ti-daily-scroll');
      const axis = el('div', 'ti-plot-scale');
      [maximum, Math.round(maximum / 2), 0].forEach(value => axis.append(el('span', '', number(value))));
      scroll.append(axis);
    }
    days.forEach(day => {
      const group = el('div', 'ti-day'), bars = el('div', 'ti-day-bars');
      series.forEach(type => {
        const count = chartValue(day[type]);
        const label = count === null ? 'Not tracked' : number(count);
        const matching = () => source.tickets.filter(ticket => {
          if (type === 'created') return ticket.in_created_period && (String(ticket.created_display || '').slice(0, 10) === day.label || dayOf(ticket.created_at, source.timezone) === day.label);
          return ticket.in_resolved_period && dayOf(ticket.completed_at, source.timezone) === day.label;
        });
        const bar = button('', () => openTickets(`${day.label} / ${type}`, matching()), `ti-column ${type === 'resolved' ? 'resolved' : ''}`);
        const height = (count ?? 0) / maximum * 121;
        bar.style.height = `${height}px`;
        if (overview) {
          bar.classList.add('ti-chart-hit');
          bar.style.setProperty('--ti-column-height', `${height}px`);
          const ink = el('span', 'ti-column-ink');
          ink.setAttribute('aria-hidden', 'true');
          ink.hidden = count === null;
          bar.append(ink);
        }
        bar.setAttribute('aria-label', `${day.label}: ${label} ${type} tickets. Open matching tickets.`);
        bar.title = `${day.label}: ${label} ${type}`;
        bar.append(el('span', '', count === null ? '—' : label));
        bars.append(bar);
      });
      group.append(bars, el('small', '', day.label.slice(5))); chart.append(group);
    });
    scroll.append(chart); container.append(legend, scroll, el('p', 'ti-widget-caption', `${source.start}–${source.end} · Daily ticket counts · All ${days.length} days shown; scroll to explore.`));
  }
  function widgetConfig(widget) {
    const box = el('div', 'ti-config');
    const controls = [
      ['size', 'Widget width', [['small', 'Small'], ['medium', 'Medium'], ['large', 'Large']]],
      ['scope', 'Assignment scope', [['team', 'Team'], ['me', 'Assigned to me']]],
      ['limit', 'List / group limit', [[5, '5 rows'], [10, '10 rows'], [20, '20 rows']]]
    ];
    controls.forEach(([key, title, options]) => {
      const label = el('label', '', title), select = el('select');
      options.forEach(([value, text]) => { const option = el('option', '', text); option.value = value; select.append(option); });
      select.value = String(widget[key]);
      select.addEventListener('change', () => {
        widget[key] = key === 'limit' ? Number(select.value) : select.value;
        markDirty();
        if (key === 'scope' && widget.scope === 'me' && !myData) loadData();
        else renderWidgets();
      });
      label.append(select); box.append(label);
    });
    return box;
  }
  function renderWidgets() {
    cleanupChartAnimations();
    closeWidgetActions();
    if (!data) return;
    const grid = $('ti-widgets');
    grid.replaceChildren();
    if (!layout.widgets.length) {
      const empty = el('div', 'ti-state');
      empty.append(el('h2', '', 'Make room for the work that matters'), el('p', '', 'Add a queue, a trend or a workload breakdown. Your empty layout is valid and can be saved.'), button('Add your first widget', openPicker, 'ti-primary'));
      grid.append(empty); return;
    }
    layout.widgets.forEach((widget, index) => {
      const definition = config.catalog.find(item => item.type === widget.type);
      const title = definition?.title || widget.type.replaceAll('_', ' ');
      const source = widget.scope === 'me' ? myData : data;
      const card = el('article', 'ti-panel ti-widget');
      card.dataset.size = widget.size;
      card.dataset.widgetId = widget.id;
      const header = el('div', 'ti-widget-heading');
      const heading = el('div');
      heading.append(el('h3', '', title), el('div', 'ti-widget-caption', `${widget.scope === 'me' ? 'Assigned to me' : 'Team'} · ${['created', 'resolved', 'volume', 'first_response', 'resolution_time'].includes(widget.type) ? 'Selected period' : widget.type === 'categories' ? 'Period & current backlog' : 'Current snapshot'}`));
      const configure = button('Configure', () => {
        settings.hidden = !settings.hidden;
        configure.setAttribute('aria-expanded', String(!settings.hidden));
        closeWidgetActions(true);
        if (!settings.hidden) settings.querySelector('select')?.focus();
      });
      configure.setAttribute('aria-label', `Configure ${title}`);
      configure.setAttribute('aria-expanded', 'false');
      header.append(heading);
      const settings = widgetConfig(widget); settings.hidden = true;
      card.append(header, settings);
      if (!source) {
        card.append(el('p', 'ti-muted', 'Assignment data is not loaded.'), button('Load assignment data', loadData));
      } else if (['aging', 'workload', 'categories', 'status'].includes(widget.type)) {
        if (widget.type === 'status') renderRing(card, source.charts.status, source, title);
        else renderBars(card, source.charts[widget.type], source, title, widget.limit);
        if (widget.type === 'categories') card.append(el('p', 'ti-widget-caption', 'Groups use the server-provided ticket membership. The Categories report separates period arrivals and current backlog.'), safeLink(reportURL('categories', widget.scope), 'Open category report'));
      } else if (widget.type === 'volume') {
        renderVolume(card, source, ['created', 'resolved'], true);
      } else if (['first_response', 'resolution_time'].includes(widget.type)) {
        const value = source.metrics[widget.type];
        card.append(safeLink(reportURL(widget.type, widget.scope), duration(value), 'ti-number'), el('p', 'ti-widget-caption', value == null ? 'No qualifying tracked event in this period.' : 'Tracked duration · Open report for exact qualifying rows and definitions.'));
        const rows = source.reports?.[widget.type]?.rows;
        if (!Array.isArray(rows)) card.append(el('p', 'ti-widget-caption', 'Duration distribution is unavailable: qualifying rows were not supplied.'));
        else {
          const result = distribution(rows, 'hours', [1, 4, 24, 72, 168],
            ['Under 1 hr', '1–4 hr', '4–24 hr', '1–3 days', '3–7 days', '7+ days'], 'ticket_id');
          if (!result.measured && !rows.length) card.append(el('p', 'ti-widget-caption', 'No qualifying duration rows in this period; distribution unavailable.'));
          else renderDistribution(card, result, source, title);
        }
      } else {
        const matching = ticketsFor(widget.type, source);
        const metric = button(number(matching.length), () => openTickets(title, matching), 'ti-metric ti-number');
        metric.setAttribute('aria-label', `${matching.length} matching tickets. Open ${title}.`);
        card.append(metric);
        if (['created', 'resolved'].includes(widget.type)) renderVolume(card, source, [widget.type], true);
        else renderDistribution(card, queueDistribution(widget.type, matching), source, title);
        if (widget.type === 'my_queue' || widget.type === 'stalled') {
          const ordered = [...matching].sort((a, b) => widget.type === 'stalled' ? b.idle_days - a.idle_days : Number(b.is_overdue) - Number(a.is_overdue) || Number(b.priority) - Number(a.priority) || b.age_days - a.age_days);
          const list = el('ul', 'ti-list');
          ordered.slice(0, widget.limit).forEach(ticket => {
            const li = el('li');
            li.append(safeLink(ticket.url, `#${ticket.id}  ${ticket.title}`), el('small', '', `${ticket.assignee || 'Unassigned'} · ${ticket.status} · ${ticket.idle_days} days idle`));
            list.append(li);
          });
          card.append(list, el('p', 'ti-widget-caption', `${Math.min(matching.length, widget.limit)} of ${matching.length} shown${widget.type === 'stalled' ? ` · At least ${query.get('stalled_days') || 7} days without human activity` : ' · Overdue first, then priority and age'}`));
        } else card.append(el('p', 'ti-widget-caption', matching.length ? 'Open matching tickets →' : 'No qualifying tickets under the current filters.'));
      }
      const tools = el('div', 'ti-widget-tools');
      const panel = el('div', 'ti-widget-actions-panel');
      panel.id = `ti-widget-actions-${widget.id}`;
      panel.hidden = true;
      // The top layer escapes overflow clipping without detaching inherited styles.
      panel.setAttribute('popover', 'manual');
      panel.setAttribute('role', 'group');
      panel.setAttribute('aria-label', `${title} actions`);
      const toggle = button('⋯', () => {
        const wasOpen = !panel.hidden;
        closeWidgetActions();
        if (!wasOpen) {
          panel.hidden = false;
          toggle.setAttribute('aria-expanded', 'true');
          openWidgetActions = { tools, panel, toggle };
          panel.showPopover?.();
          positionWidgetActions();
          panel.querySelector('button:not(:disabled)')?.focus();
        }
      }, 'ti-widget-actions-toggle');
      toggle.setAttribute('aria-label', `Actions for ${title}`);
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-controls', panel.id);
      const handle = el('span', 'ti-drag-handle', 'Drag to reorder');
      handle.draggable = true;
      handle.title = 'Drag this handle, or use Move up / Move down';
      handle.addEventListener('dragstart', event => {
        dragId = widget.id; event.dataTransfer.setData('text/plain', widget.id); event.dataTransfer.effectAllowed = 'move'; card.classList.add('dragging');
      });
      handle.addEventListener('dragend', () => { dragId = undefined; card.classList.remove('dragging'); closeWidgetActions(); });
      card.addEventListener('dragover', event => { if (dragId && dragId !== widget.id) { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; } });
      card.addEventListener('drop', event => {
        event.preventDefault();
        const from = layout.widgets.findIndex(item => item.id === dragId);
        if (from < 0 || dragId === widget.id) return;
        const [moving] = layout.widgets.splice(from, 1);
        const to = layout.widgets.findIndex(item => item.id === widget.id);
        layout.widgets.splice(to, 0, moving); markDirty(); renderWidgets(); dragId = undefined;
      });
      const up = button('Move up', () => moveWidget(index, -1));
      up.dataset.move = 'up'; up.disabled = index === 0;
      const down = button('Move down', () => moveWidget(index, 1)); down.disabled = index === layout.widgets.length - 1;
      const remove = button('Remove', () => {
        if (!window.confirm(`Remove “${title}” from your workspace?`)) return;
        layout.widgets = layout.widgets.filter(item => item.id !== widget.id); markDirty(); renderWidgets();
      });
      panel.append(configure, handle, up, down, remove);
      tools.append(toggle, panel); card.append(tools); grid.append(card);
      if (source) animateWidget(card, widget, source);
    });
    const activeIds = new Set(layout.widgets.map(widget => widget.id));
    widgetChartSignatures.forEach((_, id) => { if (!activeIds.has(id)) widgetChartSignatures.delete(id); });
  }
  function moveWidget(index, delta) {
    const id = layout.widgets[index].id;
    const [widget] = layout.widgets.splice(index, 1);
    layout.widgets.splice(index + delta, 0, widget);
    markDirty(); renderWidgets();
    const card = Array.from($('ti-widgets').children).find(node => node.dataset.widgetId === id);
    card?.querySelector('.ti-widget-actions-toggle')?.focus();
  }
  function markDirty() {
    dirty = true;
    $('ti-save-state').textContent = 'Saving your workspace…';
    $('ti-save').disabled = saving;
    $('ti-add').disabled = layout.widgets.length >= 20;
    clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(saveLayout, 250);
  }
  function rememberFilters() {
    if (page !== 'overview') return;
    layout.filters = Object.fromEntries(keys.filter(key => query.has(key)).map(key => [key, query.get(key)]));
    markDirty();
  }
  function makeWidget(type, scope = 'team', size = 'small') {
    return { id: window.crypto?.randomUUID ? window.crypto.randomUUID() : `widget-${Date.now()}-${Math.random().toString(36).slice(2)}`, type, size, scope, limit: 5 };
  }
  function openPicker() {
    const body = openDialog('Add a widget');
    const message = el('p', 'ti-muted', `Choose what belongs in your daily workspace. ${layout.widgets.length} of 20 slots used. You can add a widget more than once.`);
    const searchLabel = el('label', '', 'Find a widget'), search = el('input');
    search.type = 'search'; search.placeholder = 'Search queues, trends, reports…'; searchLabel.append(search);
    const picker = el('div', 'ti-picker'); picker.style.marginTop = '18px';
    body.append(message, searchLabel, picker);
    function draw() {
      picker.replaceChildren();
      const matching = config.catalog.filter(item => `${item.title} ${item.description}`.toLowerCase().includes(search.value.toLowerCase()));
      matching.forEach(item => {
        const card = el('div', 'ti-picker-item'), text = el('div');
        text.append(el('h3', '', item.title), el('p', '', item.description));
        const add = button('Add', () => {
          if (layout.widgets.length >= 20) return;
          const size = ['volume', 'aging', 'workload', 'categories', 'status', 'my_queue', 'stalled'].includes(item.type) ? 'medium' : 'small';
          const scope = ['my_open', 'my_queue'].includes(item.type) ? 'me' : 'team';
          layout.widgets.push(makeWidget(item.type, scope, size));
          markDirty();
          $('ti-dialog').close();
          if (needsMine() && !myData) loadData(); else renderWidgets();
        }, 'ti-primary');
        add.disabled = layout.widgets.length >= 20; add.setAttribute('aria-label', `Add ${item.title}`);
        card.append(text, add); picker.append(card);
      });
      if (!matching.length) picker.append(el('p', 'ti-muted', 'No widgets match that search.'));
    }
    search.addEventListener('input', draw); draw();
  }
  async function saveLayout() {
    if (saving || !dirty) return;
    saving = true;
    $('ti-save').disabled = true;
    $('ti-reset').disabled = true;
    const outgoing = copy(layout);
    let confirmed = false;
    $('ti-save-state').textContent = 'Saving your layout…';
    try {
      const result = await request('/api/ticket-insights/layout', {
        method: 'PUT',
        keepalive: true,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '' },
        body: JSON.stringify(outgoing)
      });
      if (!result.layout || !Array.isArray(result.layout.widgets)) throw new Error('The server did not confirm the saved layout.');
      savedLayout = copy(result.layout);
      confirmed = true;
      dirty = JSON.stringify(layout) !== JSON.stringify(outgoing);
      if (JSON.stringify(layout) === JSON.stringify(outgoing)) {
        layout = copy(result.layout); dirty = false;
        $('ti-save-state').textContent = 'Layout saved to your account.';
      } else $('ti-save-state').textContent = 'Earlier changes saved. Newer layout changes still need saving.';
      $('ti-status').replaceChildren();
    } catch (error) {
      const box = el('div', 'ti-state ti-error');
      box.append(el('p', '', `Layout not saved. ${error.message}`), button('Retry save', saveLayout));
      $('ti-status').replaceChildren(box);
      $('ti-save-state').textContent = 'Save failed · Your changes remain on this page.';
    } finally {
      saving = false; $('ti-save').disabled = !dirty;
      $('ti-reset').disabled = false;
      if (dirty && confirmed) {
        clearTimeout(autosaveTimer);
        autosaveTimer = setTimeout(saveLayout, 0);
      }
    }
  }
  function applyPreset(preset) {
    if (!preset) return;
    if (!window.confirm('Replace your widgets with this preset? Your choice will be saved automatically.')) { $('ti-preset').value = layout.preset; return; }
    const types = preset === 'my' ? ['my_open', 'overdue', 'high_priority', 'my_queue', 'stalled'] : ['unassigned', 'high_priority', 'overdue', 'volume', 'workload', 'aging'];
    const catalog = new Set(config.catalog.map(item => item.type));
    layout = { version: 1, preset, filters: layout.filters || {}, widgets: types.filter(type => catalog.has(type)).map(type => makeWidget(type, preset === 'my' ? 'me' : 'team', ['volume', 'workload', 'aging', 'my_queue', 'stalled'].includes(type) ? 'medium' : 'small')) };
    markDirty(); $('ti-preset').value = preset;
    if (needsMine() && !myData) loadData(); else renderWidgets();
  }
  async function init() {
    clearStatus();
    try {
      config = await request('/api/ticket-insights/config');
      if (!config.layout || !Array.isArray(config.catalog) || !config.options) throw new Error('Your insights configuration is incomplete.');
      savedLayout = copy(config.layout); layout = copy(config.layout);
      if (page === 'overview' && !keys.some(key => query.has(key))) {
        query = new URLSearchParams(layout.filters || {});
        history.replaceState(null, '', `${location.pathname}?${query}`);
      }
      fillFilters();
      if (page === 'overview') {
        $('ti-add').disabled = layout.widgets.length >= 20;
        $('ti-reset').disabled = false; $('ti-preset').disabled = false;
        $('ti-preset').value = layout.preset;
        $('ti-save-state').textContent = 'Saved to your account · Open a widget’s ⋯ menu to reorder or remove it.';
      }
      await loadData();
    } catch (error) {
      (page === 'overview' ? $('ti-widgets') : $('ti-report')).replaceChildren();
      showError(error.message, init);
    }
  }
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!config || !validateDates()) return;
    query = filterQuery();
    rememberFilters();
    history.replaceState(null, '', `${location.pathname}?${query}`);
    syncLinks(); loadData();
  });
  form.elements.namedItem('start').addEventListener('change', () => form.elements.namedItem('end').setCustomValidity(''));
  form.elements.namedItem('end').addEventListener('change', () => form.elements.namedItem('end').setCustomValidity(''));
  $('ti-clear').addEventListener('click', () => {
    form.reset(); form.elements.namedItem('end').setCustomValidity('');
    query = new URLSearchParams();
    if (page === 'reports') query.set('report', reportKey);
    rememberFilters();
    history.replaceState(null, '', `${location.pathname}?${query}`);
    syncLinks(); loadData();
  });
  $('ti-dialog-close').addEventListener('click', () => $('ti-dialog').close());
  $('ti-dialog').addEventListener('close', () => {
    if (dialogReturn?.isConnected) dialogReturn.focus();
    else $('ti-add')?.focus();
  });
  if (page === 'overview') {
    $('ti-add').addEventListener('click', openPicker);
    $('ti-save').addEventListener('click', saveLayout);
    $('ti-preset').addEventListener('change', event => applyPreset(event.target.value));
    $('ti-reset').addEventListener('click', () => {
      if (!window.confirm('Discard unsaved changes and restore the last server-saved layout?')) return;
      layout = copy(savedLayout); dirty = false;
      clearTimeout(autosaveTimer);
      $('ti-preset').value = layout.preset;
      query = new URLSearchParams(layout.filters || {});
      form.reset();
      fillFilters();
      history.replaceState(null, '', `${location.pathname}?${query}`);
      syncLinks();
      $('ti-save').disabled = true; $('ti-add').disabled = layout.widgets.length >= 20;
      $('ti-save-state').textContent = 'Restored the last server-saved layout.';
      loadData();
    });
    window.addEventListener('beforeunload', event => {
      if (!dirty) return;
      event.preventDefault(); event.returnValue = '';
    });
  } else {
    $('ti-print').addEventListener('click', () => { tableStates.forEach(render => render()); window.print(); });
  }
  syncLinks();
  init();
})();
