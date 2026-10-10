---
name: Direct ticket AI
description: Direct OpenAI replacement scope and operational boundaries
---

Ticket AI should use direct OpenAI, not n8n, and support shared technician follow-up questions.

**Why:** The user requested replacement of one-shot n8n analysis; n8n downtime previously delayed inbound email processing.

**How to apply:** Keep model calls outside inbound email requests. Preserve existing email deduplication. Do not claim all webhook delays are eliminated while notification emails still run synchronously. The user's production installation is separately hosted, so Replit secrets do not configure that installation.

First-boot table creation must be serialized across Gunicorn workers.

**Why:** Concurrent `create_all` calls raced on a new table's sequence and crashed startup; `checkfirst` does not make concurrent DDL atomic.

**How to apply:** Keep database-level coordination when adding tables or changing startup schema initialization.
