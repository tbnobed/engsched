/* Offline, source-backed mock DOM: no auth, network, dependencies or database. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/schedule-orientation.js', 'utf8');
function event(top, height, left = '0%', width = '100%', allDay = false) {
    return {
        dataset: { allDay: String(allDay) },
        style: {
            top: `${top}px`, height: `${height}px`, left, width,
            setProperty(key, value) { this[key] = value; }
        }
    };
}
function fixture(events, stored = null, blocked = false) {
    const classes = new Set();
    const grid = { scrollLeft: 0, scrollTop: 0, style: { setProperty(k, v) { this[k] = v; } } };
    const buttons = ['vertical', 'horizontal'].map(mode => ({
        dataset: { scheduleOrientation: mode },
        setAttribute(k, v) { this[k] = v; },
        addEventListener(k, handler) { this[k] = handler; }
    }));
    const root = {
        classList: { contains: k => classes.has(k), toggle(k, active) { active ? classes.add(k) : classes.delete(k); } },
        querySelector: () => grid,
        querySelectorAll(selector) {
            return selector === '.day-slots' ? [{ querySelectorAll: () => events }] : buttons;
        }
    };
    let start;
    const storage = { value: stored,
        getItem() { if (blocked) throw Error('denied'); return this.value; },
        setItem(k, value) { if (blocked) throw Error('denied'); this.value = value; }
    };
    const context = {
        window: {}, localStorage: storage,
        document: { getElementById: () => root, addEventListener: (name, fn) => { start = fn; } }
    };
    vm.runInNewContext(source, context);
    start();
    return { api: context.window.ScheduleOrientation, grid, buttons, classes, storage };
}
const early = event(0, 60);
const noon = event(720, 120, '50%', '50%');
const overlap = event(720, 120, '0%', '50%');
const midnight = event(1380, 120); // Clamp an existing segment at 24:00.
const ooo = event(540, 54, '0%', '100%', true);
const original = [early, noon, overlap, midnight, ooo].map(e => ({ ...e.style }));
const f = fixture([early, noon, overlap, midnight, ooo]);
assert.equal(f.api.preference(), 'vertical');
assert.equal(f.classes.has('schedule-horizontal'), false);
f.grid.scrollTop = 620;
f.buttons[1].click();
assert.equal(f.classes.has('schedule-horizontal'), true);
assert.equal(noon.style['--horizontal-start'], '50%');
assert.equal(early.style['--horizontal-start'], '0%');
assert.equal(midnight.style['--horizontal-duration'], `${60 / 1440 * 100}%`);
assert.ok(Math.abs(f.api.geometry(midnight).start + f.api.geometry(midnight).duration - 100) < 1e-9);
assert.notEqual(noon.style['--horizontal-lane'], overlap.style['--horizontal-lane']);
assert.equal(ooo.style['--horizontal-lane'], '2px');
assert.equal(f.buttons[1]['aria-pressed'], 'true');
assert.equal(f.storage.value, 'horizontal');
f.grid.scrollLeft = 720;
f.api.setMode('vertical');
assert.equal(f.grid.scrollTop, 620);
[early, noon, overlap, midnight, ooo].forEach((e, i) => {
    for (const k of ['top', 'height', 'left', 'width']) assert.equal(e.style[k], original[i][k]);
});
f.api.setMode('horizontal');
assert.equal(f.grid.scrollLeft, 720);
// Fresh geometry is published after layout updates; never use a stale cache.
noon.style.top = '360px';
f.api.refresh();
assert.equal(noon.style['--horizontal-start'], '25%');
const personal = [event(540, 180), event(600, 120), event(780, 60)];
fixture(personal, 'horizontal');
assert.notEqual(personal[0].style['--horizontal-lane'], personal[1].style['--horizontal-lane']);
assert.equal(personal[0].style['--horizontal-lane'], personal[2].style['--horizontal-lane']);
const busy = fixture(Array.from({ length: 9 }, () => event(600, 120)));
assert.equal(busy.grid.style['--horizontal-row-min'], '404px');
assert.equal(fixture([], 'horizontal').classes.has('schedule-horizontal'), true);
assert.equal(fixture([], 'garbage').classes.has('schedule-horizontal'), false);
const denied = fixture([], null, true);
assert.doesNotThrow(() => denied.api.setMode('horizontal'));
assert.equal(denied.classes.has('schedule-horizontal'), true);
for (const path of ['templates/calendar.html', 'templates/personal_schedule.html']) {
    const template = fs.readFileSync(path, 'utf8');
    assert.ok(template.includes('_schedule_orientation.html'));
    assert.ok(template.includes('js/schedule-orientation.js'));
}
const css = fs.readFileSync('static/css/schedule-orientation.css', 'utf8');
assert.ok(css.includes('repeat(24, minmax(72px, 1fr))'));
assert.ok(css.includes('repeat(7, minmax(var(--horizontal-row-min), 1fr))'));
assert.ok(css.includes('overflow: auto !important'));
const calendar = fs.readFileSync('static/js/calendar.js', 'utf8');
assert.ok(calendar.includes('window.ScheduleOrientation.refresh()'));
assert.ok(calendar.includes("'--horizontal-now'"));
console.log('Schedule orientation: 24-hour geometry, overlap, all-day, busy rows, round-trip, scroll, storage and integration checks passed.');
