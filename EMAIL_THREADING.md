# External incident threading

## Scope

The TBN support integration recognizes a single `Incident #<number>` in the
subject. It applies to messages from the known alert mailbox
`ITSupport@tbnalert.tv` and participant addresses in `tbn.tv`. Other senders
retain the existing local `[Ticket #N]` and subject/sender matching behavior.
Sender matching is routing, not sender authentication; retain the inbound
provider's existing security controls.

Different support systems must have separate source identifiers. Do not apply a
global incident-number match to every incoming email.

## Behavior

- A unique source/incident mapping selects one canonical local ticket.
- For incidents already represented by duplicates, the first incoming update
  adopts the oldest active, unarchived matching ticket. If none is active, it
  adopts the oldest matching ticket, including closed/archived tickets.
- Once recorded, the mapping is stable. New updates become comments without
  changing the ticket's status or archived flag.
- Existing duplicate tickets, comments and attachments are not merged or deleted.
- When the canonical ticket is deleted, its mapping is cleared by the database.
  The next update adopts another existing match or creates a new ticket.
- A PostgreSQL advisory lock serializes each incident across web workers. A busy
  incident returns HTTP 503 with Retry-After, without claiming the email, so the
  provider retries safely. The lock is released after the content commits,
  before notification delivery.
- Content, mapping and completed Message-ID claim commit together. Processing
  errors roll back content and release incomplete claims.
- Existing Message-ID retry deduplication remains enabled.

All application email delivery excludes addresses in `AUTOMATED_TICKET_SENDERS`
(comma-separated, defaults to the known TBN alert mailbox). Other recipients,
including internal technicians, remain eligible for notifications. To add a
sender, include the existing address as well as the new address. This prevents
the app from sending acknowledgments and comment/status emails to that automated
system; it does not stop that system from independently generating updates.

## Deploy

Sync these changes and rebuild the production web container. The existing
startup schema initialization creates the new mapping table; no existing
columns are changed. Back up the database before upgrading.

```bash
docker compose up -d --build --no-deps web
docker compose logs --tail=80 web
```

The Replit workspace update does not automatically update the separate server.

## Verification

`python -m unittest test_email_threading -v` exercises the real inbound route,
database mapping, concurrent requests, retries, closed/archived state, adoption
of existing tickets, failure rollback, and outgoing-recipient suppression.
Run only against development: tests create and delete synthetic ticket records,
with email delivery and AI analysis mocked.
