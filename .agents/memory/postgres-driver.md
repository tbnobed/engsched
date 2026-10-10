---
name: PostgreSQL driver compatibility
description: Keep SQLAlchemy driver selection aligned with the Docker dependencies
---

Use the installed psycopg2 driver explicitly rather than assuming a bare PostgreSQL URL will select it.

**Why:** A separately hosted production build tried to import psycopg v3 even though its image installed psycopg2-binary, causing a repeated worker boot failure.

**How to apply:** When upgrading SQLAlchemy or changing deployment dependencies, verify driver selection in both environments. Preserve all database URL credentials, connection options, and database identity when selecting the driver.
