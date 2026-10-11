/* Admin report settings; independent from the ticket dashboard. */
(() => {
  'use strict';
  const root = document.getElementById('ticket-report-settings');
  if (!root) return;
  const $ = id => root.querySelector(`#${id}`);
  const priorities = ['Low', 'Medium', 'High', 'Urgent'];
  const targetForm = $('trs-target-form'), requesterForm = $('trs-requester-form');
  let requesters = [], selected = null, busy = false;
  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }
  async function request(url, method = 'GET', payload) {
    const options = { method, credentials: 'include' };
    if (payload !== undefined) {
      options.headers = { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '' };
      options.body = JSON.stringify(payload);
    }
    const response = await fetch(url, options);
    let result;
    try { result = await response.json(); } catch (_) { throw new Error('The server returned an invalid response. Please try again.'); }
    if (!response.ok) throw new Error(typeof result.error === 'string' ? result.error : typeof result.message === 'string' ? result.message : `Request failed (${response.status}).`);
    return result;
  }
  function status(id, text, error = false, retry) {
    const container = $(id); container.replaceChildren();
    container.className = error ? 'ti-status-text ti-inline-status' : 'ti-status-text';
    container.dataset.error = String(error);
    container.append(el('p', '', text));
    if (retry) {
      const button = el('button', '', 'Try again'); button.type = 'button';
      button.addEventListener('click', retry); container.append(button);
    }
  }
  function drawTargets(targets) {
    if (!Array.isArray(targets) || !priorities.every((_, index) => targets.some(target => Number(target.priority) === index))) throw new Error('The server must provide all four service priorities.');
    const fields = $('trs-target-fields'); fields.replaceChildren();
    priorities.forEach((name, priority) => {
      const target = targets.find(item => Number(item.priority) === priority), row = el('div', 'ti-target-row');
      row.append(el('h3', '', name));
      [['response_hours', 'First response'], ['resolution_hours', 'Resolution']].forEach(([key, labelText]) => {
        const label = el('label', '', `${labelText} · hours`), input = el('input');
        input.type = 'number'; input.min = '0.01'; input.max = '8760'; input.step = 'any';
        input.name = `${key}_${priority}`; input.placeholder = 'Not configured'; input.value = target[key] ?? '';
        input.setAttribute('aria-label', `${name} ${labelText.toLowerCase()} target in hours`);
        label.append(input); row.append(label);
      });
      fields.append(row);
    });
  }
  function updated(value) {
    const date = value ? new Date(value) : null;
    $('trs-updated').textContent = date && !Number.isNaN(date.getTime()) ? `Last saved ${date.toLocaleString()}` : 'No saved update recorded.';
  }
  async function loadTargets() {
    $('trs-target-loading').hidden = false; targetForm.hidden = true;
    status('trs-target-status', 'Loading service policy…');
    try {
      const result = await request('/api/ticket-insights/settings');
      drawTargets(result.targets); updated(result.updated_at);
      targetForm.hidden = false; status('trs-target-status', 'Blank targets remain explicitly not configured in reports.');
    } catch (error) { status('trs-target-status', error.message, true, loadTargets); }
    finally { $('trs-target-loading').hidden = true; }
  }
  targetForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (!targetForm.reportValidity()) return;
    const targets = priorities.map((_, priority) => {
      const value = key => {
        const input = targetForm.elements.namedItem(`${key}_${priority}`);
        return input.value.trim() === '' ? null : Number(input.value);
      };
      return { priority, response_hours: value('response_hours'), resolution_hours: value('resolution_hours') };
    });
    Array.from(targetForm.elements).forEach(input => { input.disabled = true; });
    status('trs-target-status', 'Saving service targets…');
    try {
      const result = await request('/api/ticket-insights/settings', 'PUT', { targets });
      drawTargets(result.targets); updated(result.updated_at);
      status('trs-target-status', 'Service targets saved. Reports now use these policies, including for historical tickets.');
    } catch (error) { status('trs-target-status', `${error.message} Your entries are still here. Choose Save targets to retry.`, true); }
    finally { Array.from(targetForm.elements).forEach(input => { input.disabled = false; }); }
  });
  function selectRequester(requester) {
    if (busy) return;
    if (selected && (requesterForm.elements.department.value !== (selected.department || '') || requesterForm.elements.location.value !== (selected.location || ''))) {
      if (!window.confirm('Discard unsaved requester details?')) return;
    }
    selected = requester;
    $('trs-requester-name').textContent = requester.name || requester.email || requester.key;
    requesterForm.elements.department.value = requester.department || '';
    requesterForm.elements.location.value = requester.location || '';
    $('trs-requester-fields').disabled = false; drawDirectory();
    status('trs-directory-status', 'Editing requester reporting details.');
  }
  function drawDirectory() {
    const list = $('trs-directory'), term = $('trs-search').value.trim().toLocaleLowerCase();
    list.replaceChildren();
    const matching = requesters.filter(item => [item.name, item.email, item.department, item.location].some(value => String(value || '').toLocaleLowerCase().includes(term)));
    matching.forEach(item => {
      const choice = el('button', 'ti-requester-choice'); choice.type = 'button'; choice.disabled = busy;
      choice.setAttribute('aria-pressed', String(selected?.key === item.key));
      choice.append(el('strong', '', item.name || item.email || 'Unnamed requester'), el('span', '', item.email || 'No email recorded'), el('span', '', `${item.department || 'Department not assigned'} · ${item.location || 'Location not assigned'}`));
      choice.addEventListener('click', () => selectRequester(item)); list.append(choice);
    });
    if (!matching.length) {
      const empty = el('div', 'ti-state');
      empty.append(el('h3', '', requesters.length ? 'No matching requesters' : 'No requesters yet'), el('p', '', requesters.length ? 'Try a different name, email or department.' : 'Requesters will appear here when the directory contains them.'));
      list.append(empty);
    }
  }
  async function loadDirectory() {
    status('trs-directory-status', 'Loading requester directory…');
    try {
      const result = await request('/api/ticket-insights/requesters');
      if (!Array.isArray(result.requesters)) throw new Error('The server did not return a requester directory.');
      requesters = result.requesters; $('trs-search').disabled = false; drawDirectory();
      status('trs-directory-status', `${requesters.length} requesters · Choose a requester to edit their details.`);
    } catch (error) { $('trs-directory').replaceChildren(); status('trs-directory-status', error.message, true, loadDirectory); }
  }
  async function saveRequester(clear = false) {
    if (!selected || busy || !requesterForm.reportValidity()) return;
    if (clear && !window.confirm('Clear this requester’s department and location mapping? The user and all tickets will remain.')) return;
    const payload = { key: selected.key, department: clear ? '' : requesterForm.elements.department.value.trim(), location: clear ? '' : requesterForm.elements.location.value.trim() };
    busy = true; $('trs-requester-fields').disabled = true; drawDirectory();
    status('trs-directory-status', clear ? 'Clearing requester details…' : 'Saving requester details…');
    try {
      const result = await request('/api/ticket-insights/requesters', 'PUT', payload);
      if (!result.requester || result.requester.key !== selected.key) throw new Error('The server did not confirm the updated requester.');
      selected = result.requester;
      requesters = requesters.map(item => item.key === selected.key ? selected : item);
      requesterForm.elements.department.value = selected.department || '';
      requesterForm.elements.location.value = selected.location || '';
      status('trs-directory-status', !payload.department && !payload.location ? 'Mapping removed. The user and their tickets are unchanged.' : 'Requester details saved.');
    } catch (error) { status('trs-directory-status', `${error.message} No successful change was confirmed. Please try again.`, true); }
    finally { busy = false; $('trs-requester-fields').disabled = false; drawDirectory(); }
  }
  $('trs-search').addEventListener('input', drawDirectory);
  requesterForm.addEventListener('submit', event => { event.preventDefault(); saveRequester(); });
  $('trs-clear').addEventListener('click', () => saveRequester(true));
  loadTargets(); loadDirectory();
})();
