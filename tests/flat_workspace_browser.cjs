/* Offline fixture checks; no application login, APIs, database or network. */
const fs = require("node:fs");
const assert = require("node:assert/strict");
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH);
const fixtureStyles = JSON.parse(fs.readFileSync(0, "utf8"));
const markup = `
<main class="container-fluid"><div class="row"><div class="col-12">
<div class="row"><div class="col-lg-5"><div class="card mb-4" id="card">
  <div class="card-header">Profile</div><div class="card-body">
  <input class="form-control" id="field" placeholder="Name">
  <input class="form-check-input" id="checkbox" type="checkbox">
  <svg id="icon" fill="none" stroke="currentColor" stroke-width="2"><path d="M0 0L8 8"></path></svg>
  <button class="btn btn-primary" id="focus">Save</button>
  </div></div></div><div class="col-lg-7"><div class="card" id="second-card">Schedule</div></div></div>
<div class="tk-shell"><div class="tk-body" id="ticket-grid"><div class="tk-panel" id="ticket-panel">Filters</div>
<table class="tk-table"><thead><tr><th id="table-head">Title</th></tr></thead>
<tbody><tr class="unread" id="table-row"><td id="table-cell">Ticket</td></tr></tbody></table></div></div>
<div class="admin-cc"><div class="ad-kpis" id="admin-grid"><div class="ad-kpi" id="admin-kpi">Users</div></div></div>
<div class="ti"><div class="ti-grid" id="report-grid"><div class="ti-panel ti-widget" id="report-panel">Report</div></div>
<div class="ti-directory-list" id="directory">Directory</div>
<button class="ti-requester-choice" aria-pressed="true" id="selected-requester">Selected</button>
<div class="ti-volume" id="chart-line"></div></div>
<div class="aa"><div class="aa-panel" id="api-panel">API</div><fieldset><fieldset id="scopes">
<input type="checkbox" id="api-check">Permissions</fieldset></fieldset><pre id="api-code">curl</pre></div>
<div class="ticket-reference-page"><div class="tr-columns" id="detail-grid">
<div class="tr-card" id="detail-card">Composer</div><div class="tr-side-card" id="detail-side">Details</div></div>
<div class="ticket-ai" id="assistant"><div class="ticket-ai-message" id="assistant-message">Suggestion</div></div>
<div class="ql-toolbar ql-snow"><svg><path class="ql-stroke" id="quill-stroke" style="stroke:rgb(170,180,195)" d="M0 0L8 8"></path></svg></div>
</div>
<div class="modern-mobile-calendar"><div class="calendar-header" id="mobile-header">Calendar</div>
<div class="timeline-wrapper" id="mobile-timeline">Timeline</div><div class="schedule-card" id="mobile-event">Schedule</div></div>
<div class="modern-schedule-container"><div class="stat-pill" id="mobile-stat">Hours</div>
<div class="empty-day" id="mobile-empty">No shifts</div></div>
<div class="quick-link-card" id="mobile-link">Quick link</div>
<div class="dropdown-menu" id="menu">Menu</div>
<div class="modal-content" id="modal" style="background:#2d2d2d;border:1px solid #3a3a3a;color:white">Modal</div>
<div class="tk-drawer" id="drawer">Edit ticket</div>
<div class="calendar-container schedule-flat" id="schedule-view">
<div class="calendar-grid" id="calendar-grid"><div class="time-column" id="time-column"></div>
<div class="day-column" id="calendar-day"></div></div></div>
</div></div></main>`;

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_EXECUTABLE_PATH,
    headless: true, args: ["--no-sandbox"],
  });
  try {
    for (const theme of ["dark", "light"]) {
      for (const width of [1440, 390]) {
        const page = await browser.newPage({ viewport: { width, height: 950 } });
        await page.route("**/*", route => route.abort());
        await page.setContent(`<html data-flat-workspace data-bs-theme="${theme}">
          <head><style>
          /* Offline Bootstrap affordance fixture; never fetch the CDN. */
          .form-check-input {appearance:none;width:1em;height:1em;border:1px solid #71869c}
          </style><style>${fixtureStyles[theme]}</style></head>
          <body class="${theme === "light" ? "light-theme" : ""}">${markup}</body></html>`);
        const computed = id => page.locator(`#${id}`).evaluate(el => {
          const s = getComputedStyle(el);
          return {
            border: [s.borderTopWidth, s.borderRightWidth, s.borderBottomWidth, s.borderLeftWidth],
            borderColor: s.borderTopColor,
            shadow: s.boxShadow, background: s.backgroundColor, image: s.backgroundImage,
            color: s.color, gap: s.gap, margin: s.marginBottom,
            outline: s.outlineWidth, height: s.height,
          };
        });
        for (const id of ["card", "ticket-panel", "admin-kpi", "report-panel", "directory",
          "api-panel", "scopes", "api-code", "detail-card", "detail-side", "assistant",
          "assistant-message", "menu", "modal", "drawer", "mobile-header", "mobile-timeline",
          "mobile-event", "mobile-stat", "mobile-empty", "mobile-link", "table-cell", "table-row"]) {
          const style = await computed(id);
          const sections = ["card", "ticket-panel", "admin-kpi", "report-panel",
            "api-panel", "detail-card", "detail-side", "modal", "drawer",
            "mobile-event", "mobile-link", "assistant"];
          if (sections.includes(id)) {
            assert(style.border.every(value => parseFloat(value) > 0 && parseFloat(value) <= 1), `${theme}/${width}/${id}: hairline separator`);
            assert.match(style.borderColor, /0\.03\b/, `${theme}/${width}/${id}: three-percent separator`);
          } else if (id === "mobile-header") {
            assert(parseFloat(style.border[2]) > 0 && parseFloat(style.border[2]) <= 1, "Mobile calendar header separator");
          } else {
            assert.deepEqual(style.border, ["0px", "0px", "0px", "0px"], `${theme}/${width}/${id}: no extra internal border`);
          }
          assert.equal(style.shadow, "none", `${theme}/${width}/${id}: decorative shadow`);
        }
        for (const id of ["ticket-grid", "admin-grid", "report-grid", "detail-grid", "calendar-grid"]) {
          assert.match((await computed(id)).gap, /^0px(?: 0px)?$/, `${theme}/${width}/${id}: section gutter`);
        }
        assert.equal((await computed("card")).margin, "0px", "Bootstrap mb-4 must not split surfaces");
        assert.notEqual((await computed("card")).image, (await computed("second-card")).image, "Adjacent sections need distinct hue washes");
        assert.notEqual((await computed("table-head")).background, "rgba(0, 0, 0, 0)", "Sticky header cannot be transparent");
        assert.equal((await computed("calendar-day")).height, "1504px", "24h + 64px header geometry");
        assert.equal((await computed("time-column")).height, "1504px", "Labels retain calendar geometry");
        assert.equal(await page.locator("#icon").evaluate(el => getComputedStyle(el).strokeWidth), "2px");
        assert.notEqual(await page.locator("#quill-stroke").evaluate(el => getComputedStyle(el).stroke), "none");
        assert.notEqual((await computed("checkbox")).border[0], "0px", "Native checkbox boundary must remain");
        assert.notEqual((await computed("chart-line")).border[2], "0px", "Chart baseline must remain");
        await page.locator("#checkbox").focus();
        await page.keyboard.press("Tab");
        assert.equal(await page.locator("#focus").evaluate(el => el.matches(":focus-visible")), true);
        assert.equal((await computed("focus")).outline, "2px", "Visible keyboard focus must beat legacy resets");
        await page.close();
        console.log(`PASS ${theme} ${width}px: blended surfaces, cascade, focus, icons, charts, geometry`);
      }
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
