(() => {
  'use strict';
  const root = document.getElementById('api-access');
  if (!root) return;
  const el = id => document.getElementById(`aa-${id}`);
  const endpoint = '/api/admin/api-keys';
  let keys = [];
  let secret = null;
  let action = null;
  let mutating = false;
  let lifecycle = 0;
  let keyLoad = 0;
  let auditLoad = 0;
  const createDialog = el('create-dialog');
  const confirmDialog = el('confirm-dialog');
  const tokenDialog = el('token-dialog');
  const utcDate = value => {
    if (!value) return null;
    // Naive backend timestamps represent UTC, never the browser's local zone.
    let text = String(value).trim().replace(' ', 'T');
    if (!/(Z|[+-]\d{2}:?\d{2})$/i.test(text)) text += 'Z';
    const date = new Date(text);
    return Number.isNaN(date.getTime()) ? null : date;
  };
  const statusOf = key => key.revoked_at ? 'Revoked' : key.disabled ? 'Disabled' : (utcDate(key.expires_at) && utcDate(key.expires_at).getTime() <= Date.now() ? 'Expired' : 'Active');
  const node = (tag, text, cls) => {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = String(text);
    if (cls) item.className = cls;
    return item;
  };
  const button = (text, handler, cls) => {
    const item = node('button', text, cls);
    item.type = 'button';
    item.addEventListener('click', handler);
    return item;
  };
  const feedback = (text, error = false) => {
    el('feedback').textContent = text;
    el('feedback').dataset.error = String(error);
  };
  const clearSecret = () => {
    secret = null;
    el('token').textContent = '';
    el('token-name').textContent = '';
    el('copy-status').textContent = '';
    if (tokenDialog.open) tokenDialog.close();
  };
  async function request(path, method = 'GET', data) {
    const headers = { Accept: 'application/json' };
    if (method !== 'GET') {
      const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
      if (!csrf) throw new Error('The security token is missing. Reload this page before trying again.');
      headers['X-CSRFToken'] = csrf;
      headers['Content-Type'] = 'application/json';
    }
    let response;
    try {
      response = await fetch(path, { method, credentials: 'same-origin', cache: 'no-store', headers, ...(data !== undefined ? { body: JSON.stringify(data) } : {}) });
    } catch (_) {
      throw new Error('Cannot reach the server. Check your connection and retry.');
    }
    if (!response.ok) {
      const messages = {
        400: 'The request was not accepted. Check your input and retry.',
        401: 'Your session has expired. Sign in again and reload this page.',
        403: 'Access denied or security token expired. Administrator access is required; reload before retrying.',
        404: 'This key or API endpoint is no longer available. Refresh the list.',
        409: 'This key has expired or been revoked and cannot be rotated. Refresh the list.',
        422: 'Check the name, expiry, and selected scopes before retrying.',
        429: 'Too many requests. Wait a moment before retrying.'
      };
      // Do not surface arbitrary server responses: they may contain sensitive data.
      throw new Error(messages[response.status] || 'The server could not complete this request. Please retry.');
    }
    try { return await response.json(); }
    catch (_) { throw new Error('The server returned an unexpected response. Reload and retry.'); }
  }
  function state(container, title, message, retry) {
    container.replaceChildren();
    const box = node('div', undefined, `aa-state${retry ? ' aa-error' : ''}`);
    box.append(node('h3', title), node('p', message));
    if (retry) box.append(button('Retry', retry));
    container.append(box);
  }
  function skeleton(container, label) {
    container.setAttribute('aria-busy', 'true');
    const item = node('div', undefined, 'aa-skeleton');
    item.setAttribute('role', 'status');
    item.setAttribute('aria-label', label);
    container.replaceChildren(item);
  }
  function dateCell(value, missing) {
    const cell = node('td');
    const date = utcDate(value);
    if (!date) cell.textContent = value ? 'Unavailable' : missing;
    else {
      const time = node('time', new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date));
      time.dateTime = date.toISOString();
      time.title = `${date.toISOString()} (UTC)`;
      cell.append(time);
    }
    return cell;
  }
  function table(headers, label) {
    const wrap = node('div', undefined, 'aa-table-wrap');
    wrap.tabIndex = 0;
    wrap.setAttribute('role', 'region');
    wrap.setAttribute('aria-label', `${label}; scroll horizontally for more columns`);
    const grid = node('table');
    const caption = node('caption', label);
    caption.className = 'visually-hidden';
    const head = node('thead');
    const row = node('tr');
    headers.forEach(text => {
      const th = node('th', text);
      th.scope = 'col';
      row.append(th);
    });
    head.append(row);
    const body = node('tbody');
    grid.append(caption, head, body);
    wrap.append(grid);
    return { wrap, body };
  }
  function renderKeys() {
    el('count').textContent = `(${keys.length})`;
    if (!keys.length) {
      state(el('keys'), 'No integration keys yet', 'Create a scoped key for your first server integration. Start with the minimum permissions needed.');
      return;
    }
    const { wrap, body } = table(['Name / prefix', 'Status', 'Scopes', 'Created', 'Expires', 'Last used', 'Actions'], 'API keys');
    keys.forEach(key => {
      const row = node('tr');
      const name = node('td');
      name.append(node('strong', key.name), node('code', key.prefix));
      const status = statusOf(key);
      const statusCell = node('td');
      statusCell.append(node('span', status, `aa-status aa-status-${status.toLowerCase()}`));
      if (key.revoked_at) {
        const date = utcDate(key.revoked_at);
        statusCell.append(node('small', date ? `Revoked ${date.toLocaleString()}` : 'Revoked'));
      }
      const scopes = node('td');
      (key.scopes || []).forEach(scope => scopes.append(node('span', scope, 'aa-scope')));
      const actions = node('td');
      const group = node('div', undefined, 'aa-actions');
      const rotate = button('Rotate', () => beginAction('rotate', key));
      rotate.disabled = mutating || status !== 'Active';
      rotate.setAttribute('aria-label', `Rotate ${key.name}`);
      if (status !== 'Active') rotate.title = 'Only active keys can be rotated.';
      const revoke = button('Revoke', () => beginAction('revoke', key), 'aa-danger');
      revoke.disabled = mutating || status === 'Revoked';
      revoke.setAttribute('aria-label', `Revoke ${key.name}`);
      group.append(rotate, revoke);
      actions.append(group);
      row.append(name, statusCell, scopes, dateCell(key.created_at, 'Unavailable'), dateCell(key.expires_at, 'No expiry'), dateCell(key.last_used_at, 'Never used'), actions);
      body.append(row);
    });
    el('keys').replaceChildren(wrap);
  }
  function configure(data) {
    const basePath = /^\/api\/v1(?:\/[a-zA-Z0-9/_-]*)?$/.test(data.base_path || '') ? data.base_path : '/api/v1';
    const base = new URL(basePath, window.location.origin).href;
    el('base').textContent = base;
    el('example').textContent = `curl --request GET '${base.replace(/\/$/, '')}/tickets' \\\n  --header 'Authorization: Bearer YOUR_API_KEY'`;
    el('docs').href = /^\/api\/v1\/[a-zA-Z0-9/_-]*$/.test(data.docs_url || '') ? data.docs_url : '/api/v1/docs';
    el('rate').textContent = `${Number(data.rate_limit) || 120} requests / minute`;
    el('scopes').replaceChildren();
    (data.scopes || []).forEach(scope => {
      const label = node('label', undefined, 'aa-check');
      const input = node('input');
      input.type = 'checkbox';
      input.name = 'scopes';
      input.value = scope.id;
      const text = node('span', scope.label);
      text.append(node('small', ` (${scope.id})`));
      label.append(input, text);
      el('scopes').append(label);
    });
    el('create').disabled = mutating || !(data.scopes || []).length;
  }
  async function loadKeys() {
    const load = ++keyLoad;
    const life = lifecycle;
    el('refresh-keys').disabled = true;
    skeleton(el('keys'), 'Loading API keys');
    try {
      const data = await request(endpoint);
      if (life !== lifecycle || load !== keyLoad) return;
      if (!Array.isArray(data.keys) || !Array.isArray(data.scopes)) throw new Error('Unexpected key data. Retry or reload the page.');
      keys = data.keys;
      configure(data);
      renderKeys();
    } catch (error) {
      if (life !== lifecycle || load !== keyLoad) return;
      el('create').disabled = true;
      el('count').textContent = '';
      state(el('keys'), 'Keys could not be loaded', error.message, loadKeys);
    } finally {
      if (life === lifecycle && load === keyLoad) {
        el('keys').setAttribute('aria-busy', 'false');
        el('refresh-keys').disabled = mutating;
      }
    }
  }
  async function loadAudit() {
    const load = ++auditLoad;
    const life = lifecycle;
    el('refresh-audit').disabled = true;
    skeleton(el('audit'), 'Loading API activity');
    try {
      const data = await request('/api/admin/api-audit');
      if (life !== lifecycle || load !== auditLoad) return;
      if (!Array.isArray(data.events)) throw new Error('Unexpected activity data. Retry or reload the page.');
      if (!data.events.length) {
        state(el('audit'), 'No successful writes recorded', 'Successful ticket, schedule, and directory writes will appear here. Read requests and failed attempts are not listed.');
      } else {
        const { wrap, body } = table(['Time', 'Key name', 'Method', 'Path', 'Status', 'Request ID'], 'Latest successful API writes');
        data.events.slice(0, 50).forEach(event => {
          const row = node('tr');
          row.append(dateCell(event.created_at, 'Unavailable'), node('td', event.key_name), node('td', event.method), node('td', event.path, 'aa-audit-path'), node('td', event.status), node('td', event.request_id, 'aa-audit-path'));
          body.append(row);
        });
        el('audit').replaceChildren(wrap);
      }
    } catch (error) {
      if (life === lifecycle && load === auditLoad) state(el('audit'), 'Activity could not be loaded', error.message, loadAudit);
    } finally {
      if (life === lifecycle && load === auditLoad) {
        el('audit').setAttribute('aria-busy', 'false');
        el('refresh-audit').disabled = mutating;
      }
    }
  }
  function setBusy(busy) {
    mutating = busy;
    ['submit-create', 'cancel-create', 'close-create', 'confirm-submit', 'confirm-cancel', 'refresh-keys', 'refresh-audit'].forEach(id => { el(id).disabled = busy; });
    el('create-fields').disabled = busy;
    el('create').disabled = busy || !el('scopes').children.length;
    el('create-form').setAttribute('aria-busy', String(busy));
    if (el('keys').getAttribute('aria-busy') === 'false' && el('keys').querySelector('table')) renderKeys();
  }
  function reveal(data, name) {
    clearSecret();
    if (typeof data.token !== 'string' || !data.token.startsWith('plex_')) {
      feedback('The action completed, but no valid token was returned. Refresh the list and rotate the key to obtain a new token.', true);
      return;
    }
    secret = data.token;
    el('token').textContent = secret;
    el('token-name').textContent = `Integration: ${name}`;
    tokenDialog.showModal();
  }
  function beginAction(type, key) {
    if (mutating) return;
    clearSecret();
    feedback('');
    action = { type, key };
    el('confirm-error').textContent = '';
    el('confirm-title').textContent = type === 'rotate' ? 'Rotate this API key?' : 'Revoke this API key?';
    el('confirm-name').textContent = `Integration: ${key.name} · Prefix: ${key.prefix}`;
    el('confirm-description').textContent = type === 'rotate'
      ? 'The old key is revoked immediately. Your integration must update to the new token immediately or its requests will fail. The new key retains the original expiry; rotation does not extend it. The new token is shown only once.'
      : 'Requests using this key will stop working immediately. Revocation cannot be undone. The key remains in the list for reference.';
    el('confirm-submit').textContent = type === 'rotate' ? 'Rotate and revoke old key' : 'Revoke key';
    confirmDialog.showModal();
  }
  el('create').addEventListener('click', () => {
    if (mutating) return;
    clearSecret();
    feedback('');
    el('create-form').reset();
    el('create-error').textContent = '';
    createDialog.showModal();
    el('name').focus();
  });
  ['close-create', 'cancel-create'].forEach(id => el(id).addEventListener('click', () => { if (!mutating) createDialog.close(); }));
  el('confirm-cancel').addEventListener('click', () => { if (!mutating) confirmDialog.close(); });
  [createDialog, confirmDialog].forEach(dialog => dialog.addEventListener('cancel', event => { if (mutating) event.preventDefault(); }));
  confirmDialog.addEventListener('close', () => { action = null; });
  tokenDialog.addEventListener('close', () => { if (!tokenDialog.open) clearSecret(); });
  tokenDialog.addEventListener('cancel', event => { event.preventDefault(); clearSecret(); });
  el('hide').addEventListener('click', clearSecret);
  el('copy').addEventListener('click', async () => {
    if (!secret) return;
    const life = lifecycle;
    const current = secret;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(current);
      if (life === lifecycle && current === secret) el('copy-status').textContent = 'Copied. Paste into a secure server-side secret store.';
    } catch (_) {
      if (life === lifecycle && current === secret) el('copy-status').textContent = 'Clipboard access is unavailable. Select the token and copy it manually.';
    }
  });
  el('create-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (mutating) return;
    clearSecret();
    const name = el('name').value.trim();
    const days = Number(el('days').value);
    const scopes = Array.from(el('scopes').querySelectorAll('input:checked'), input => input.value);
    if (!name || name.length > 80 || !Number.isInteger(days) || days < 1 || days > 365 || !scopes.length) {
      el('create-error').textContent = 'Enter a name (1–80 characters), an expiry of 1–365 whole days, and at least one scope.';
      return;
    }
    const life = lifecycle;
    el('create-error').textContent = '';
    setBusy(true);
    try {
      const data = await request(endpoint, 'POST', { name, scopes, expires_days: days });
      if (life !== lifecycle) return;
      createDialog.close();
      feedback('API key created. Save the one-time token before dismissing.');
      reveal(data, name);
      // Refresh metadata independently; never reset the one-time token on a refetch.
      void loadKeys();
      void loadAudit();
    } catch (error) {
      if (life === lifecycle) el('create-error').textContent = error.message;
    } finally {
      if (life === lifecycle) setBusy(false);
    }
  });
  el('confirm-submit').addEventListener('click', async () => {
    if (mutating || !action) return;
    clearSecret();
    const { type, key } = action;
    const life = lifecycle;
    el('confirm-error').textContent = '';
    setBusy(true);
    try {
      const path = `${endpoint}/${encodeURIComponent(key.id)}`;
      const data = await request(type === 'rotate' ? `${path}/rotate` : path, type === 'rotate' ? 'POST' : 'DELETE', type === 'rotate' ? {} : undefined);
      if (life !== lifecycle) return;
      confirmDialog.close();
      feedback(type === 'rotate' ? 'Key rotated. The old token is revoked; update your integration immediately.' : 'Key revoked. Requests using this token are now disabled.');
      if (type === 'rotate') reveal(data, key.name);
      void loadKeys();
      void loadAudit();
    } catch (error) {
      if (life === lifecycle) el('confirm-error').textContent = error.message;
    } finally {
      if (life === lifecycle) setBusy(false);
    }
  });
  el('refresh-keys').addEventListener('click', () => { if (!mutating) void loadKeys(); });
  el('refresh-audit').addEventListener('click', () => { if (!mutating) void loadAudit(); });
  window.addEventListener('pagehide', () => {
    lifecycle++;
    clearSecret();
    action = null;
    createDialog.close();
    confirmDialog.close();
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted) {
      clearSecret();
      setBusy(false);
      void loadKeys();
      void loadAudit();
    }
  });
  // Re-evaluate expiry while the page stays open, using UTC instants.
  window.setInterval(() => {
    if (!mutating && el('keys').getAttribute('aria-busy') === 'false' && el('keys').querySelector('table')) renderKeys();
  }, 60000);
  configure({ scopes: [], base_path: '/api/v1', docs_url: '/api/v1/docs', rate_limit: 120 });
  el('rate').textContent = 'Loading…';
  void loadKeys();
  void loadAudit();
})();
