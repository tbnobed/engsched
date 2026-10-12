---
name: Direct ticket AI
description: Direct OpenAI replacement scope and operational boundaries
---

Ticket AI should use direct OpenAI, not n8n, and support shared technician follow-up questions.

Show the AI conversation as a bounded, scrollable chat with the latest response at the bottom, not an indefinitely growing panel or newest-first feed.

**Why:** The user explicitly requested a chat window after rejecting the expanding history panel.

**How to apply:** Preserve chronological history, keep the composer outside the scroller, and preserve reading position when the user scrolls back.

AI output should not display emojis, including legacy analysis headings.

**Why:** The user said these look unprofessional.

**How to apply:** Use plain headings in AI output and preserve ordinary user-authored comments.

**Why:** The user requested replacement of one-shot n8n analysis; n8n downtime previously delayed inbound email processing.

**How to apply:** Keep model calls outside inbound email requests. Preserve existing email deduplication. Do not claim all webhook delays are eliminated while notification emails still run synchronously. The user's production installation is separately hosted, so Replit secrets do not configure that installation.

First-boot table creation must be serialized across Gunicorn workers.

**Why:** Concurrent `create_all` calls raced on a new table's sequence and crashed startup; `checkfirst` does not make concurrent DDL atomic.

**How to apply:** Keep database-level coordination when adding tables or changing startup schema initialization.
