---
name: Flat dashboard and schedule design
description: App-wide blended, borderless styling and dashboard-specific layout constraints.
---

Keep the main dashboard and schedules minimal, flat, and fluid. Separate sections with different background shades rather than decorative borders, shadows, or nested outlined cards. Support both light and dark themes.

Apply this same continuous, blended, borderless styling throughout the application, including admin, ticketing, mobile, sign-in and public pages.

**Why:** The user asked to apply “this same type of styling to every other page in our app,” with a complete inventory first so no pages were missed.

**How to apply:** Include nested dialogs, forms, tables and states in coverage, without altering routes or behavior. Retain focus indicators, checkbox affordances, icon strokes and meaningful chart lines; the prohibition is on decorative borders.

For the dashboard, use one continuous softly edged surface with no gutters between sections or KPIs. Blend distinct near-black color regions into each other instead of painting separate rounded cards. Keep content padding and smaller rounding on rows/badges.

**Why:** The user rejected a radius-only change, then clarified, “I don't want gaps between sections everything needs to flow and blend.”

**Why:** The user requested removing borders from schedules, then explicitly extended that direction to the dashboard with “different shades of colors to seperate sections.”

**How to apply:** Preserve this direction when adding or changing sections on these views. Keep keyboard focus indicators visible; calendar views should fill available page height with internal scrolling.

For the main dashboard, each section needs a clearly distinct dark color family, not nearly identical shades of blue. Keep the dark-mode page background neutral/dark, use the full available page height, and keep Active Tickets BELOW the timeline, filling the remaining space rather than moving it to a separate column.

**Why:** The user rejected near-identical section colors and unused page height, then clarified: “use all dark share of colors and do not move the tickets section just make it use the space available below the timeline.”

**How to apply:** Check visible hue differences and viewport utilization, not merely different color codes. Preserve readable light-mode equivalents without reintroducing borders or shadows. The user rejected the medium-dark palette too: dashboard surfaces should be near-black with distinct hue tints, including alternate rows and hover backgrounds, not bright colored panels.

Apply the same blended, borderless treatment to shared navigation: no sidebar outline, logo/clock separators, submenu rules, or outlined settings/mobile controls. Preserve menu order, branding, and keyboard focus indicators.

Current section styling: retain thin borders but make their contrast apparent in daylight across all pages. Keep blended surfaces, existing positions, navigation and individual controls unchanged.

**Why:** The user found the previously approved 3%-opacity lines hard to see during daylight and requested more apparent lines. This supersedes the barely visible contrast preference.

Horizontal schedule day rows should fit each day's own schedules, not stretch to match the busiest day.

**Why:** The user rejected oversized rows for days with only one or two schedules.

**How to apply:** Keep the calendar viewport full-height, but let individual horizontal rows remain compact and expand only for their own overlapping schedules and all-day entries.


**Why:** The user extended the direction to the sidebar: “I don't want to see borders anywhere.”
