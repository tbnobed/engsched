/* No browser, database or extra dependencies: exercise the actual runtime helpers. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Node {
  constructor(tag = 'div', text = '') {
    this.tag = tag; this.textContent = text; this.children = []; this.attributes = {}; this.dataset = {};
    this.style = { setProperty(key, value) { this[key] = value; } };
    this.events = {};
    this.classList = {
      contains: name => this.className.split(' ').includes(name),
      add: name => { this.className += ` ${name}`; }
    };
    this.className = '';
  }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(name, fn) { this.events[name] = fn; }
  querySelectorAll() { return this.inks || []; }
}
const root = new Node();
root.dataset = { page: 'overview' };
const preference = { matches: false, addEventListener(name, fn) { this.change = fn; } };
const context = vm.createContext({
  document: { getElementById: () => root, addEventListener() {}, createElement: tag => new Node(tag),
    createTextNode: text => new Node('text', text) },
  window: { matchMedia: () => preference, addEventListener() {} },
  location: { search: '', origin: 'https://example.invalid' },
  URLSearchParams, URL, Intl, Set, Map
});
const script = fs.readFileSync('static/js/ticket-insights.js', 'utf8');
// Remove only bootstrap/event wiring; keep all production helper definitions.
const body = script.slice(0, script.lastIndexOf("  form.addEventListener('submit'"));
vm.runInContext(body + `
  config = { user_id: 8 }; data = { timezone: 'UTC' };
  globalThis.helpers = { chartValue, distribution, queueDistribution, ticketsFor,
    renderBars, renderVolume, animateWidget, duration, renderWidgets,
    setupWidgets: (catalog, widgets, source) => {
      config = { user_id: 8, catalog }; layout = { widgets }; data = source; myData = source;
    },
    setQuery: value => { query = new URLSearchParams(value); },
    setOpenTickets: fn => { openTickets = fn; } };
})();`, context);
const h = context.helpers;
const plain = value => JSON.parse(JSON.stringify(value));
const walk = node => [node, ...node.children.flatMap(walk)];
for (const unknown of [null, undefined, '', '0', NaN, Infinity, -1]) assert.equal(h.chartValue(unknown), null);
assert.equal(h.chartValue(0), 0);
const dist = h.distribution([
  { id: 1, hours: 0 }, { id: 2, hours: 1 }, { id: 3, hours: 24 },
  { id: 4, hours: null }, { id: 5 }, { id: 6, hours: '' }
], 'hours', [1, 24], ['Under 1 hr', '1–24 hr', '24+ hr']);
assert.deepEqual(plain(dist), {
  groups: [{ label: 'Under 1 hr', count: 1, ids: [1] }, { label: '1–24 hr', count: 1, ids: [2] },
    { label: '24+ hr', count: 1, ids: [3] }], measured: 3, missing: 3
});
const tickets = [
  { id: 1, is_open: true, assignee_id: 8, priority: 0, age_days: 0, idle_days: 3 },
  { id: 2, is_open: true, assignee_id: null, priority: 3, age_days: 31, idle_days: 14, is_overdue: true },
  { id: 3, is_open: false, assignee_id: 8, priority: 2, in_created_period: true, in_resolved_period: true }
];
const source = { tickets, timezone: 'America/Los_Angeles', start: '2026-10-09', end: '2026-10-09',
  charts: { volume: [{ label: '2026-10-09', created: 0, resolved: 1 }] } };
for (const [type, ids] of Object.entries({
  my_open: [1], my_queue: [1], unassigned: [2], high_priority: [2], overdue: [2],
  created: [3], resolved: [3], stalled: [2]
})) assert.deepEqual(plain(h.ticketsFor(type, source).map(row => row.id)), ids);
h.setQuery('stalled_days=3');
assert.deepEqual(plain(h.ticketsFor('stalled', source).map(row => row.id)), [1, 2]);
assert.deepEqual(plain(h.queueDistribution('my_queue', tickets.slice(0, 2)).groups.map(g => g.count)), [1, 0, 0, 0, 0, 1]);
assert.deepEqual(plain(h.queueDistribution('high_priority', [tickets[1]]).groups.map(g => g.count)), [0, 0, 0, 1]);
const parent = new Node();
h.renderBars(parent, dist.groups, source, 'Duration', 6);
const buttons = walk(parent).filter(node => node.tag === 'button');
assert.equal(buttons[0].attributes['aria-label'], 'Under 1 hr: 1 tickets. Open matching tickets.');
let drilldown;
h.setOpenTickets((title, rows) => { drilldown = { title, rows }; });
buttons[0].events.click();
assert.deepEqual(plain(drilldown.rows.map(row => row.id)), [1]);
const missingBar = new Node();
h.renderBars(missingBar, [{ label: 'Unknown', count: null, ids: [] }], source, 'Test', 5);
assert.equal(walk(missingBar).find(node => node.className === 'ti-bar-fill').hidden, true);
assert.equal(walk(missingBar).find(node => node.tag === 'strong').textContent, 'Not tracked');
const unavailable = new Node();
h.renderBars(unavailable, undefined, source, 'Test', 5);
assert.equal(walk(unavailable).filter(node => node.tag === 'button').length, 0);
assert.ok(walk(unavailable).some(node => node.textContent.includes('unavailable')));
source.tickets[2].completed_at = '2026-10-10T01:00:00Z'; // Previous day in source timezone.
const volume = new Node();
h.renderVolume(volume, source, ['resolved'], true);
const column = walk(volume).find(node => node.className.includes('ti-column '));
assert.ok(column.attributes['aria-label'].includes('1 resolved tickets'));
column.events.click();
assert.deepEqual(plain(drilldown.rows.map(row => row.id)), [3]);
const zeroVolume = new Node();
h.renderVolume(zeroVolume, source, ['created'], true);
const zeroColumn = walk(zeroVolume).find(node => node.className.includes('ti-column '));
assert.equal(zeroColumn.style.height, '0px');
assert.ok(zeroColumn.className.includes('ti-chart-hit')); // CSS retains a 24px keyboard/click target.
assert.ok(zeroColumn.attributes['aria-label'].includes('0 created tickets'));
source.charts.volume[0].created = null;
const unknownVolume = new Node();
h.renderVolume(unknownVolume, source, ['created'], true);
assert.ok(walk(unknownVolume).find(node => node.className.includes('ti-column ')).attributes['aria-label'].includes('Not tracked'));
assert.equal(walk(unknownVolume).find(node => node.className === 'ti-column-ink').hidden, true);
const animations = [];
function animate(frames, options) {
  const animation = { frames, options, listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; },
    cancel() { this.cancelled = true; this.listeners.cancel?.(); } };
  animations.push(animation); return animation;
}
const card = new Node();
card.animate = animate;
const ink = new Node(); ink.className = 'ti-bar-fill'; ink.animate = animate;
card.inks = [ink];
const widget = { id: 'queue', type: 'my_open', scope: 'team', limit: 5 };
h.animateWidget(card, widget, source);
assert.equal(animations.length, 2);
assert.equal(animations[0].frames[1].opacity, 1);
assert.equal(animations[1].frames[1].transform, 'scaleX(1)');
h.animateWidget(card, widget, source); // Unchanged reorder/config/menu render.
assert.equal(animations.length, 2);
source.generated_at = 'updated';
h.animateWidget(card, widget, source);
assert.equal(animations.length, 4);
preference.matches = true;
preference.change({ matches: true });
assert.ok(animations.every(animation => animation.cancelled));
source.generated_at = 'updated again';
h.animateWidget(card, widget, source);
assert.equal(animations.length, 4);
preference.matches = false;
h.animateWidget(card, widget, source); // Reduced motion rendered final state, no later replay.
assert.equal(animations.length, 4);
const catalog = [...fs.readFileSync('ticket_insights_service.py', 'utf8')
  .split('CATALOG = [')[1].split('\n]')[0].matchAll(/\('([^']+)'/g)].map(match => match[1]);
const covered = ['my_open', 'unassigned', 'high_priority', 'overdue', 'created', 'resolved', 'volume',
  'aging', 'workload', 'categories', 'status', 'my_queue', 'stalled', 'first_response', 'resolution_time'];
assert.deepEqual(catalog, covered);
const allSource = { ...source,
  metrics: { first_response: 0, resolution_time: 0 },
  reports: { first_response: { rows: [{ ticket_id: 3, hours: 0 }] },
    resolution_time: { rows: [{ ticket_id: 3, hours: 0 }] } },
  charts: { ...source.charts, ...Object.fromEntries(['aging', 'workload', 'categories', 'status']
    .map(type => [type, [{ label: type, count: 1, ids: [1] }]])) }
};
h.setupWidgets(catalog.map(type => ({ type, title: type })), catalog.map(type => ({
  id: type, type, scope: type.startsWith('my_') ? 'me' : 'team', size: 'small', limit: 5
})), allSource);
h.renderWidgets();
assert.equal(root.children.length, 15);
for (const card of root.children) {
  assert.ok(walk(card).some(node => ['ti-bars', 'ti-volume'].includes(node.className)),
    `${card.dataset.widgetId} must contain a real-data graph`);
  const panel = walk(card).find(node => node.className === 'ti-widget-actions-panel');
  assert.equal(panel.hidden, true);
  assert.equal(panel.attributes.popover, 'manual');
}
const reportVolume = new Node();
h.renderVolume(reportVolume, source);
assert.equal(walk(reportVolume).filter(node => node.className === 'ti-column-ink').length, 0);
// Critical manual top-layer menu and report renderer isolation remain present.
assert.ok(script.includes("panel.setAttribute('popover', 'manual')"));
assert.ok(script.includes('positionWidgetActions();'));
assert.ok(script.includes("renderVolume(card, source, ['created', 'resolved'], true)"));
console.log('Ticket insights chart data, drilldowns, timezone, zero/missing and animation tests passed (15 catalog types).');
