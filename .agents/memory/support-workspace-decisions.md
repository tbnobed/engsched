---
name: Support workspace data boundaries
description: Preserve historical data and distinguish internal notes from public replies
---

Treat internal notes as non-email content; only explicitly public replies may use
requester notification delivery.

**Why:** The approved UX report identified that technicians could not tell whether
their comment would email the requester.

**How to apply:** Preserve this privacy boundary in retries, merge operations,
new composers, and notification changes.

Do not guess historical timestamps or silently merge old tickets during upgrades.

**Why:** The approved report found conflicting dates, but a display correction
cannot establish which historical database values are wrong. Duplicate records
may contain distinct updates and attachments.

**How to apply:** Normalize future writes and display consistently; require source
evidence for historical timestamp repairs and explicit confirmation for merges.
