# Ticket groups

Admins manage teams under **Admin → Users & Groups · Groups**. Group managers
can manage their own memberships through **Manage My Groups** in their profile
menu. Members can be users or other groups; resolved membership is deduplicated
and cyclic membership is rejected.

Tickets support a group, an individual, or both. Group assignment filters the
individual picker by default; admins can turn this off on the Groups page.
Disabling a group removes it from new assignment choices without removing its
tickets, members, history, or report attribution.

Category defaults apply only to unspecified assignments. Selecting “Unassigned”
explicitly prevents a default individual assignment. Group notifications have a
master switch plus separate new-assignment, reassignment, and unassigned-comment
switches. Notification recipients are resolved through nested membership.

The sidebar includes **My Groups' Tickets** and **Unassigned in my groups**.
Ticket views offer **Assign to me** to group members. Dashboards and reports
support group filters and grouping. Reports attribute historical measurements to
the ticket's **current group**, clearly labeled, and do not fabricate response or
resolution measurements for missing history.

## API

Ticket read/write resources expose nullable `group_id`; ticket responses also
include `group_name`. Filter tickets using `group_id=<id>` or `group_id=none`.
`GET /api/v1/groups` requires `directory:read` and returns group configuration and
resolved member IDs. Category directory responses include assignment defaults.
Existing API idempotency and authorization continue to apply. API writes do not
automatically send email or run AI.

## Deployment

Back up the production PostgreSQL database before deploying. This release adds
group/member/settings tables and nullable ticket/category foreign keys; it does
not rewrite existing ticket assignments. The idempotent migration is
`ticket_groups_schema.sql`. Docker startup applies it transactionally, and Flask
startup applies it under the existing schema advisory lock.

The code was checked for syntax only. No test suites, seeds, benchmarks,
application runtime, or migrations were executed as part of this implementation.
After deployment, verify the authenticated group-management and assignment flows
before relying on them for production routing.

The current application has no subcategory, ticket-task, approval, or automation
rule models, so no new unrelated subsystems were introduced. Queue/round-robin
distribution remains intentionally out of scope; membership is independently
modeled so queues can be linked later.
