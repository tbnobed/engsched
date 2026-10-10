# Ticket AI setup

Ticket analysis and follow-up questions call OpenAI directly. n8n is no longer
called when a ticket is created. Existing AI comments remain unchanged.

## Configuration

- `OPENAI_API_KEY`: required server-side secret.
- `OPENAI_MODEL`: defaults to `gpt-4.1`; must support Chat Completions.
- `OPENAI_TICKET_AI_ENABLED`: defaults to `true`. Set `false` to pause AI.

The old `AI_ANALYSIS_ENABLED` flag only controlled n8n and is no longer used by
ticket creation. The new independent flag lets installations keep n8n disabled.
OpenAI charges are billed to the account owning the API key.

For the separately hosted Docker installation, securely set `OPENAI_API_KEY` in
the deployment environment (never commit it), then rebuild/recreate the web
service with the updated compose configuration. A Replit secret does not
automatically transfer to that server. Back up the database before upgrading.
The new conversation table is created by the application's existing startup
table-creation routine; no existing columns are changed.

## Behavior

New web and email tickets enqueue initial analysis. Existing tickets offer an
Analyze ticket button. Responses and follow-ups live in a separate, shared
AI Assistant panel on desktop and mobile, not in outbound email comments.
All signed-in team members can use it, matching existing ticket access.

The database-backed queue runs in the existing application scheduler every three
seconds. It processes one response at a time. Pending jobs survive restarts;
interrupted running jobs become retryable after five minutes. Errors are shown
without exposing API credentials. The scheduler must be running for work to
complete; preserve the existing non-preloaded Gunicorn startup configuration.

OpenAI receives the title, description (up to 16,000 characters), status, priority,
20 latest comments (up to 2,500 characters each), and 20 latest completed AI
conversation messages. Attachments are not analyzed. Full conversations stay in
the application database; older conversation turns beyond that context window
are not sent to the model. API response storage is disabled with `store: false`;
this does not override OpenAI's other data retention policies.

Analysis is advisory, cannot access equipment, and does not execute changes.
The prompt requires evidence-based hypotheses, clarifying questions for vague
tickets, and warnings before disruptive changes.

AI no longer delays inbound email requests. Existing notification emails still
run synchronously; this change does not move that separate delivery flow.
