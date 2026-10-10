---
name: Ticket reporting reliability
description: Why historical support metrics must treat AI authors and missing events carefully.
---
Do not infer historical response or completion times from current ticket status, the last-updated timestamp, or a comment's author account alone.

**Why:** Legacy AI analyses can be stored under a real technician, and inbound external replies can use an administrator's account as their database author. Existing completed tickets may also lack completion events. These quirks would make speed metrics misleading.

**How to apply:** Exclude recognized AI analyses and identify the actual email sender when measuring human responses. Expose missing event coverage rather than inventing durations. Keep current-backlog snapshots distinct from period-based reports.
