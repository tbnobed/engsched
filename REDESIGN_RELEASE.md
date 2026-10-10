# Support workspace redesign

## Deployment

Back up the production database, sync the code, and rebuild/recreate only the web
service. Startup creates the new workspace and comment metadata tables under the
existing database schema lock. No existing columns or records are dropped.

```bash
docker compose up -d --build --no-deps web
docker compose logs --tail=80 web
```

## Data and workflow changes

- Existing incident deduplication remains enabled, with incoming References and
  In-Reply-To matching added where those IDs are known locally.
- Email intake uses an explicit Unsorted category and Untriaged priority.
  Unsorted is a sentinel category to preserve existing non-null category foreign
  keys; triage must choose a real category and priority.
- Manually created tickets require category and priority and can name a directory
  requester distinct from the creating technician.
- New email comments preserve sender metadata and retain sanitized quoted
  material for collapsed display.
- Internal notes do not send outbound email. Public replies retain normal
  notification delivery, excluding configured automated support senders.
- Administrators can merge selected tickets into a confirmed destination.
  Original descriptions/files become internal timeline entries; comments,
  history, AI conversation and email mappings follow the destination.
  Source tickets remain archived, with a redirect to the destination.
- Unread activity is per viewer rather than cleared globally by another user's
  visit.
- New intake timestamps are timezone-aware UTC. Workspace timestamps are rendered
  in the viewer's selected timezone.

## Interface

Shared responsive sidebar and command palette; four actionable queue KPIs;
saved-view tabs and filter chips; inline ticket fields; duplicate and unread
badges; controlled live refresh; bulk actions and explicit merge confirmation;
top reply composer with visibility tabs, canned replies and attachments;
requester history; collapsed AI panel and per-viewer pinned summary; attention
list and workload counts on Overview; team/week schedule with existing editing
views preserved.

## Historical records

No automatic historic merge, recategorization or priority assignment is performed.
Existing records need technician judgment. Historical timestamps that were
originally stored with an incorrect timezone are not shifted speculatively:
consistent rendering fixes presentation, not already-corrupted source values.
Verify the affected production records and original email/history evidence
before applying any timestamp repair.

## Verification

Development-only regression suite:
`python -m unittest test_ticket_workspace.WorkspaceTests -v`

It creates synthetic records and cleans them up; outbound email/AI are mocked.
Browser verification separately covers the signed-in desktop/mobile experience.
