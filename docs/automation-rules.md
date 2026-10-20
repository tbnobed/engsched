# Automation rules

Open **Admin → Automation Rules**. Only admins may save, enable, reorder, clone,
or delete rules. Group managers have read-only access to rules and run logs.
Preview evaluates a supplied ticket without executing actions.

Rules support ordered actions, typed system/custom conditions, numbered boolean
expressions, elapsed/business-time conditions, and variables. Custom fields are
defined from the rules index. Ticket tags, CC members, linked tickets, and private
automation comments have dedicated storage. There is no native subcategory or
site model; define custom fields where these concepts are needed.

Configure the business calendar and timezone before enabling business-time rules.
The five migration examples are inactive and are installed once, so deleting or
renaming an example will not recreate it on restart. Critical maps to Urgent,
New to Open, and Awaiting Input to Pending. Select an actual on-call group before
enabling the after-hours example.

## Execution

Rule conditions and variables use the original event snapshot. Actions execute
in rule/action order; failed database actions roll back to a savepoint without
stopping subsequent actions. Automation writes suppress further triggers.
Scheduled checks run every minute, reload the ticket, and re-evaluate the full
rule. Pending timers are unique per rule/ticket and capped at 5,000; overflow is
logged and sends a rate-limited alert to admins.

External notifications and webhooks cannot be rolled back after delivery.
Avoid relying on exactly-once delivery: a process failure or transaction failure
after delivery can cause a repeated external effect. Webhooks use HTTPS,
validate and pin public destination addresses, and refuse redirects. Notification
recipients must resolve to internal users; arbitrary external addresses are not
accepted.

Existing API callers remain authenticated and permission-scoped. Unlike ordinary
API writes, an explicitly activated automation rule can intentionally send a
notification or webhook for a matching API-originated event. Review enabled
rules before bulk imports.

## Deployment and validation

Back up PostgreSQL before deploying. Docker/Flask startup applies the idempotent
Groups and automation SQL in serialized transactions. This adds nullable date
anchors and default-empty ticket metadata without rewriting historical events.
Historical anchors not previously tracked remain unknown.

No application runs, migration execution, test suites, seeds, or benchmarks were
performed during implementation, per request. Static syntax checks are not
runtime validation. Verify permissions, preview, notifications, and scheduled
checks in a safe environment before enabling rules on production tickets.
