# Continuous workspace theme coverage

**Visual source:** `.agents/memory/flat-workspace-design.md`,
`templates/dashboard.html`, and `templates/_sidebar_styles.html`.
Continuous chromatic workspace: neutral near-black canvas with blue, evergreen,
plum, amber and rose washes; equivalent readable light tints. Existing typography,
layouts, content padding, routes, data, permissions and framework are retained.
No new animation, features, preference persistence or backend changes.

## Shared entrypoints

- `base.html` → `_flat_workspace_styles.html` → `flat-workspace.css`
- `mobile_base_enhanced.html` → the same include/sheet
- `auth_base.html` → `_standalone_theme.html` → the same include/sheet
- `tickets/standalone_dashboard.html` → `_standalone_theme.html` → same sheet
- `tickets/feedback.html`, `api/docs.html` → `_standalone_theme.html` → same sheet

Every document root opts in with `data-flat-workspace`. Anonymous auth/standalone
pages use the existing standalone system-theme handling; authenticated saved
preferences take priority. Repeated attribute specificity plus targeted
`!important` declarations beats late page-local styles, including modal inline
attributes. No reliance on asset arrival order. Print styling remains untouched
because all new presentation rules are screen-only.

## Complete route-template inventory

Derived by AST inspection of literal `render_template` calls, without importing
the application or accessing the database:

- Main: `dashboard.html`, `calendar.html`, `personal_schedule.html`, `profile.html`.
- Tickets: `overview.html`, `dashboard.html` (including filtered views),
  `standalone_dashboard.html`, `create.html`, `view.html` (responsive),
  `archived.html`, `manage_categories.html`, `edit_category.html`, `reports.html`
  (the overview workspace macro renders every report tab), `report_settings.html`.
- Admin: `dashboard.html` (users), `edit_user.html`, `locations.html`,
  `quick_links.html`, `backup.html`, `email_settings.html`,
  `recurring_schedules.html`, `recurring_schedule_form.html` (new/edit),
  `confirm_generate.html`, `recurring_schedule_preview.html`, `api_access.html`.
- Mobile: `mobile/dashboard.html`, `mobile/tickets.html`, `mobile/calendar.html`,
  `mobile/personal_schedule.html`, `mobile/quick_links.html`,
  `mobile_profile.html`, `tickets/mobile_dashboard.html`,
  `tickets/mobile_create.html`; ticket detail uses responsive `tickets/view.html`.
- Public/auth: `login.html`, `tickets/feedback.html` (open/error, submitted,
  unavailable/expired), `api/docs.html`.
- Dormant, not activated: `register.html`, `tickets/mobile_view_ticket.html`.

Embedded menus, drawers, native dialogs, Bootstrap modals, AI assistant,
rich-text composer chrome, tables, forms, validation, skeletons, error/empty
states, report settings lists and dynamically inserted mobile tiles inherit
the same treatment.

## Preservation / regression checks

Dashboard layout, ticket scrollbar/refresh logic, schedule-height script and
calendar 1504px columns (1440px day + 64px header) are unchanged. Calendar gutters
collapse without modifying event positions, grid column widths, sticky headers
or overflow. SVG/Feather/Quill strokes, chart baselines/data colors, native
checkbox/radio borders, select arrows, sort chevrons and spinner borders are
not reset. Keyboard focus is restored above legacy global focus suppression.
Selected tabs/requesters/chips retain an explicit tinted selected state.

`tests/test_flat_workspace.py`: AST route coverage, complete Jinja compilation,
dormant template inheritance, scope safety, geometry contracts, palette contrast,
and optional offline Chromium computed-style checks.
`tests/flat_workspace_browser.cjs`: real cascade tests at 1440px and 390px, dark
and light, deliberately loading all legacy styles **after** the new stylesheet.

These are static/offline presentation checks. Live authenticated pages, open
interactive modals, real populated reports and server-rendered CRUD workflows
still require an authenticated runtime check; these tests make no claims about
backend behavior.
