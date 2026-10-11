const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('static/js/ticket-insights.js', 'utf8');
const fn = source.slice(source.indexOf('  function compareReportValues('), source.indexOf('  function createTable('));
const context = {};
vm.runInNewContext(fn, context);
const compare = context.compareReportValues;
assert.ok(compare(2, 10, 'count', 'ascending') < 0);
assert.ok(compare(2, 10, 'count', 'descending') > 0);
assert.ok(compare('Ticket 2', 'Ticket 10', 'title', 'ascending') < 0);
assert.equal(compare('ADMIN', 'admin', 'technician', 'ascending'), 0);
assert.ok(compare('2026-01-02T01:00:00+02:00', '2026-01-02T00:00:00Z', 'created_at', 'ascending') < 0);
for (const direction of ['ascending', 'descending']) {
  assert.ok(compare(null, 0, 'hours', direction) > 0);
  assert.ok(compare(0, undefined, 'hours', direction) < 0);
  assert.equal(compare(null, undefined, 'hours', direction), 0);
}
assert.ok(compare(false, true, 'flag', 'ascending') < 0);
assert.ok(source.includes('const matching = sorted(rows.filter'));
assert.ok(source.includes("th.setAttribute('aria-sort'"));
assert.ok(source.includes('sorted(rows).forEach'));
console.log('Report sorting checks passed.');
