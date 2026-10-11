"""Build an offline, synthetic-only preview from actual production markup/JS/CSS.

Run: python tests/generate_widget_chart_preview.py
Optional temporary Flask-static copy:
  python tests/generate_widget_chart_preview.py --static-copy
Open ?theme=light or ?frame=300 (pause real WAAPI animations at 300ms).
No application imports, database access, authentication changes or network calls.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as NS

import pytz
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ticket_insights_service import CATALOG, build_insights  # noqa: E402


def build():
    now = datetime(2026, 10, 10, 19, tzinfo=timezone.utc)
    tickets, comments, histories = [], [], []
    users = {8: NS(username='Mara Chen'), 9: NS(username='Eli Brooks')}
    categories = {1: 'Access & identity', 2: 'Studio systems', 3: 'Endpoint support'}
    timezone_name = 'America/Los_Angeles'
    tz = pytz.timezone(timezone_name)
    # Deliberately synthetic identities and subjects. Includes a true zero day.
    for day, count in enumerate([3, 7, 0, 9, 4, 8, 5, 6]):
        for index in range(count):
            identifier = len(tickets) + 1
            created = now - timedelta(days=7 - day, hours=2 + index / 4)
            done = identifier % 3 == 0 and day < 7
            assigned = [8, 9, None][identifier % 3]
            item = NS(id=identifier, title=f'SYNTHETIC fixture ticket {identifier}',
                      created_at=created, status='resolved' if done else 'pending' if identifier % 4 == 0 else 'open',
                      priority=identifier % 4, assigned_to=assigned, created_by=1, external_email=None,
                      archived=False, due_date=created + timedelta(hours=30),
                      category_id=identifier % 3 + 1)
            tickets.append(item)
            if identifier % 5 != 0:
                reply = created + timedelta(hours=[0, 2, 5, 28, 74][identifier % 5])
                if reply <= now:
                    comments.append(NS(ticket_id=identifier, content='SYNTHETIC human reply',
                                       user_id=8, user=NS(username='Mara Chen', email='mara@example.invalid'),
                                       created_at=reply))
            if done:
                histories.append(NS(ticket_id=identifier, action='status_changed',
                                    details='Status changed from open to resolved',
                                    created_at=min(created + timedelta(hours=[2, 12, 27, 58, 95][identifier % 5]), now)))
    # Older backlog exercises actual age/idle buckets outside the selected period.
    for age in [11, 17, 23, 34, 42, 56, 9]:
        identifier = len(tickets) + 1
        tickets.append(NS(id=identifier, title=f'SYNTHETIC backlog fixture {identifier}',
                          created_at=now - timedelta(days=age), status='open', priority=identifier % 4,
                          assigned_to=8 if identifier % 2 else None, created_by=1, external_email=None,
                          archived=False, due_date=now - timedelta(days=2), category_id=identifier % 3 + 1))
    filters = dict(start=now.date() - timedelta(days=7), end=now.date(), source='all', stalled_days=7)
    team = build_insights(tickets, comments, histories, users, categories, set(), filters, 8, tz, now)
    mine = build_insights([ticket for ticket in tickets if ticket.assigned_to == 8],
                          comments, histories, users, categories, set(), filters, 8, tz, now)
    widgets = [
        dict(id=f'fixture-{kind}', type=kind, size='small',
             scope='me' if kind.startswith('my_') else 'team', limit=5)
        for kind, _, _ in CATALOG
    ]
    config = dict(user_id=8, timezone=timezone_name, is_admin=False,
                  catalog=[dict(type=kind, title=title, description=description) for kind, title, description in CATALOG],
                  layout=dict(version=1, preset='team', widgets=widgets),
                  options=dict(technicians=[], categories=[], priorities=[], statuses=[],
                               sources=[], departments=[], locations=[]))
    template = (ROOT / 'templates/tickets/overview.html').read_text()
    macro = template[template.index('{% macro workspace(page) %}'):template.index('{% endmacro %}') + len('{% endmacro %}')]
    env = Environment(autoescape=True)
    env.globals['url_for'] = lambda _, filename: '/static/' + filename
    markup = str(env.from_string(macro).module.workspace('overview'))
    markup = re.sub(r'<link[^>]+>|<script\b[^>]*>.*?</script>', '', markup, flags=re.S)
    # Keep production template structure; place fixture identification outside it.
    base = (ROOT / 'templates/base.html').read_text()
    base_inline = '\n'.join(re.findall(r'<style>(.*?)</style>', base, re.S))
    def css(name):
        value = (ROOT / 'static/css' / name).read_text()
        # Local application CSS remains in actual cascade order; fonts/images do
        # not trigger external requests in this self-contained offline fixture.
        value = re.sub(r'@import[^;]+;', '', value)
        return re.sub(r'url\([^)]*\)', 'url("data:,")', value)
    styles = (
        '<style>' + (ROOT / 'tests/fixtures/widget-preview-bootstrap-5.1.3.css').read_text()
        + '</style>'
        '<style>' + css('style.css') + '</style>'
        '<style id="fixture-light">' + css('light-theme.css') + '</style>'
        '<style id="fixture-dark">' + css('dark-theme.css') + '</style>'
        '<style>' + base_inline + '</style>'
        '<style>' + css('ticket-insights.css') + '</style>'
        '<style>' + css('flat-workspace.css') + '</style>'
    )
    payload = json.dumps(dict(config=config, team=team, mine=mine)).replace('</', '<\\/')
    runtime = (ROOT / 'static/js/ticket-insights.js').read_text().replace('</', '<\\/')
    fixture = """<!doctype html><html lang="en" data-flat-workspace data-bs-theme="dark">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SYNTHETIC fixture · Production ticket widgets</title>""" + styles + """
<script>
const previewParams = new URLSearchParams(location.search);
const theme = previewParams.get('theme') === 'light' ? 'light' : 'dark';
document.documentElement.dataset.bsTheme = theme;
document.getElementById('fixture-light').sheet.disabled = theme !== 'light';
document.getElementById('fixture-dark').sheet.disabled = theme !== 'dark';
// Freeze ACTUAL production animations at a known frame for screenshot comparison.
const frame = Number(previewParams.get('frame'));
if (previewParams.has('frame') && Number.isFinite(frame)) {
  const realAnimate = Element.prototype.animate;
  Element.prototype.animate = function(...args) {
    const animation = realAnimate.apply(this, args);
    animation.pause(); animation.currentTime = frame;
    return animation;
  };
}
</script></head><body>
<aside style="padding:14px 20px;color:var(--flat-ink);font:14px system-ui">
<strong>SYNTHETIC OFFLINE TEST FIXTURE — NOT CUSTOMER DATA</strong><br>
Actual production template + JS renderer + local legacy styles + flat-workspace cascade.
<a href="?theme=dark">Dark final</a> · <a href="?theme=light">Light final</a> ·
<a href="?frame=300">Animation at 300ms</a> · <a href="?frame=1200">Final animation frame</a>
</aside>""" + markup + '<script>\nconst syntheticFixture = ' + payload + """;
document.body.classList.toggle('light-theme', theme === 'light');
document.body.classList.toggle('dark-theme', theme !== 'light');
// Choose a focused set for above-the-fold screenshots without approximating any
// renderer. The real production layout still drives all widget construction.
if (previewParams.has('types')) {
  const types = previewParams.get('types').split(',');
  syntheticFixture.config.layout.widgets = types.flatMap(type =>
    syntheticFixture.config.layout.widgets.filter(widget => widget.type === type));
}
window.fetch = async (url, options = {}) => {
  const target = new URL(url, location.origin);
  let result;
  if (target.pathname === '/api/ticket-insights/config') result = syntheticFixture.config;
  else if (target.pathname === '/api/ticket-insights/data')
    result = target.searchParams.get('scope') === 'me' ? syntheticFixture.mine : syntheticFixture.team;
  else if (target.pathname === '/api/ticket-insights/layout')
    result = { layout: JSON.parse(options.body) };
  else throw new Error('Offline synthetic fixture: no API available for ' + target.pathname);
  return { ok: true, json: async () => JSON.parse(JSON.stringify(result)) };
};
// Synthetic ticket links must never navigate to a real ticket.
document.addEventListener('click', event => {
  if (event.target.closest('a[href*="/tickets/"]')) event.preventDefault();
});
""" + runtime + '</script></body></html>'
    return fixture


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--static-copy', action='store_true')
    args = parser.parse_args()
    html = build()
    path = ROOT / 'tests/widget-chart-preview.html'
    path.write_text(html)
    print(f'Generated {path.relative_to(ROOT)} ({len(html):,} characters)')
    if args.static_copy:
        target = ROOT / 'static/widget-chart-preview.html'
        target.write_text(html)
        print('Temporary preview: /static/widget-chart-preview.html (remove after screenshots)')
