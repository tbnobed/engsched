---
name: Inbound email webhook (SendGrid Inbound Parse)
description: Behaviors, failure modes, and conventions of the /api/inbound-email handler
---

# Inbound email webhook (`/api/inbound-email`)

SendGrid Inbound Parse posts the entire raw MIME (body + all attachments) in a single
form field named `email`. Two non-obvious failure modes have bitten us:

## 1. HTTP 413 on large emails
**Symptom:** webhook returns 413 ("data value transmitted exceeds the capacity limit"),
no ticket created, no email-send logs at all.
**Cause:** Werkzeug 3 defaults reject any single form field >~500KB / request >~1MB.
**Fix:** raise `MAX_CONTENT_LENGTH` / `MAX_FORM_MEMORY_SIZE` (and `MAX_FORM_PARTS`) in app config.

## 2. Duplicate tickets created over and over
**Symptom:** same-subject tickets created repeatedly with increasing time gaps
(1m,1m,2m,3m,4m,9m,13m,30m). That backoff pattern == SendGrid retrying the webhook.
**Cause:** SendGrid retries when it doesn't get a timely 2xx. The handler does a
synchronous n8n AI call (30s timeout) + notification emails to all users BEFORE
returning 200, exceeding SendGrid's webhook timeout → retry → no idempotency → new ticket.
**Fix:** idempotency on the email `Message-ID` via the `ProcessedEmail` table
(unique `message_id`). Pattern is **claim-first**: insert the message_id row
(ticket_id=None) and commit *before* any work; on `IntegrityError` treat as a
duplicate retry and return 200. After the ticket/comment commit, fill in `ticket_id`.
On processing failure, *release* the claim (delete the row) so a genuine retry can
reprocess. Placing the claim before the slow n8n/email steps is what actually stops
the duplicates.

**Why claim-first (not check-then-create):** a plain "lookup then create then mark"
still races — two concurrent retries both pass the lookup. The unique-constraint
insert is the atomic guard.

## 3. Duplicate tickets from repeated automated alerts (NOT retries)
**Symptom:** many tickets with the *identical* subject (e.g. "File Catalyst Fails
Again"), created hours apart, each a distinct email with its own Message-ID.
**Cause:** a monitoring system re-sends the same alert as a brand-new email. The
Message-ID idempotency (failure mode #2) can't catch these — they're genuinely
different messages. Reply detection only keys off `[Ticket #N]`, which alerts lack.
**Decision:** Known external support incidents must keep a stable, source-scoped
incident-to-ticket identity, including after closure. Different incoming
Message-IDs are distinct updates to preserve as comments, not duplicates to drop.
Keep subject/sender matching as a fallback for emails without a recognized
incident identity.

**Why:** Production evidence showed bursts of distinct messages for the same
external incident, sometimes following a human reply. Message-ID dedup alone
cannot handle this, and same-subject matching races across workers.

**How to apply:** Serialize incident matching and creation across workers; commit
the content, incident mapping and completed delivery claim together. Preserve
closed/archived state on incoming updates. Never silently merge or delete old
duplicates. Suppress outgoing notifications to automated support senders, but
keep internal recipients. Timing alone is not proof of an email loop.

## Conventions
- External incident identity must take precedence over stale local ticket tags
  referring to old duplicates. Unrecognized systems retain local reply matching.
- AI assistance must not trigger outbound email notifications.
- New tables added to models are auto-created on boot via `db.create_all()` in app.py
  (runs in dev and prod docker), so a new dedup table needs no manual migration — but
  adding a COLUMN to an existing table would (create_all doesn't alter existing tables).
