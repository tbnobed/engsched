-- Shared by serialized Flask initialization and the Docker entrypoint.
-- Caller owns the transaction; safe to run repeatedly on an existing database.
SELECT pg_advisory_xact_lock(72419031);

CREATE TABLE IF NOT EXISTS ticket_group (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    manager_user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    notify_new_ticket BOOLEAN NOT NULL DEFAULT TRUE,
    notify_reassigned BOOLEAN NOT NULL DEFAULT TRUE,
    notify_comment BOOLEAN NOT NULL DEFAULT TRUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ticket_group_member (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES ticket_group(id) ON DELETE CASCADE,
    member_user_id INTEGER REFERENCES "user"(id) ON DELETE CASCADE,
    member_group_id INTEGER REFERENCES ticket_group(id) ON DELETE CASCADE,
    CONSTRAINT ck_ticket_group_member_one_target CHECK ((member_user_id IS NULL) <> (member_group_id IS NULL)),
    CONSTRAINT ck_ticket_group_member_not_self CHECK (group_id <> member_group_id),
    CONSTRAINT uq_ticket_group_member_user UNIQUE (group_id, member_user_id),
    CONSTRAINT uq_ticket_group_member_group UNIQUE (group_id, member_group_id)
);
CREATE TABLE IF NOT EXISTS ticket_group_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    filter_assignees BOOLEAN NOT NULL DEFAULT TRUE
);

ALTER TABLE ticket ADD COLUMN IF NOT EXISTS group_id INTEGER;
ALTER TABLE ticket_category ADD COLUMN IF NOT EXISTS default_group_id INTEGER;
ALTER TABLE ticket_category ADD COLUMN IF NOT EXISTS default_assignee_id INTEGER;

-- Do not rely on ADD COLUMN IF NOT EXISTS ... REFERENCES to repair a column
-- installed by a previous schema revision without its foreign key.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_attribute a
                   ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
                   WHERE c.conrelid = 'ticket'::regclass AND c.contype = 'f' AND a.attname = 'group_id') THEN
        ALTER TABLE ticket ADD CONSTRAINT fk_ticket_group FOREIGN KEY (group_id) REFERENCES ticket_group(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_attribute a
                   ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
                   WHERE c.conrelid = 'ticket_category'::regclass AND c.contype = 'f' AND a.attname = 'default_group_id') THEN
        ALTER TABLE ticket_category ADD CONSTRAINT fk_ticket_category_default_group FOREIGN KEY (default_group_id) REFERENCES ticket_group(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_attribute a
                   ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
                   WHERE c.conrelid = 'ticket_category'::regclass AND c.contype = 'f' AND a.attname = 'default_assignee_id') THEN
        ALTER TABLE ticket_category ADD CONSTRAINT fk_ticket_category_default_assignee FOREIGN KEY (default_assignee_id) REFERENCES "user"(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_ticket_group_id ON ticket(group_id);
CREATE INDEX IF NOT EXISTS ix_ticket_category_default_group_id ON ticket_category(default_group_id);
CREATE INDEX IF NOT EXISTS ix_ticket_category_default_assignee_id ON ticket_category(default_assignee_id);
CREATE INDEX IF NOT EXISTS ix_ticket_group_manager_user_id ON ticket_group(manager_user_id);
CREATE INDEX IF NOT EXISTS ix_ticket_group_enabled ON ticket_group(enabled);
CREATE INDEX IF NOT EXISTS ix_ticket_group_member_group_id ON ticket_group_member(group_id);
CREATE INDEX IF NOT EXISTS ix_ticket_group_member_member_user_id ON ticket_group_member(member_user_id);
CREATE INDEX IF NOT EXISTS ix_ticket_group_member_member_group_id ON ticket_group_member(member_group_id);

-- Defense in depth for writers outside the ORM. The table lock serializes
-- the graph check across different parents. Contending direct SQL writers
-- may deadlock (one transaction is aborted), but can never commit a cycle.
CREATE OR REPLACE FUNCTION ticket_group_prevent_cycle() RETURNS trigger AS $$
BEGIN
    LOCK TABLE ticket_group_member IN SHARE ROW EXCLUSIVE MODE;
    IF NEW.member_group_id IS NOT NULL AND EXISTS (
        WITH RECURSIVE descendants(id) AS (
            SELECT NEW.member_group_id
            UNION
            SELECT m.member_group_id
              FROM ticket_group_member m JOIN descendants d ON m.group_id = d.id
             WHERE m.member_group_id IS NOT NULL AND m.id <> NEW.id
        )
        SELECT 1 FROM descendants WHERE id = NEW.group_id
    ) THEN
        RAISE EXCEPTION 'Groups cannot contain cycles' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql VOLATILE;
DROP TRIGGER IF EXISTS ticket_group_no_cycles ON ticket_group_member;
CREATE TRIGGER ticket_group_no_cycles BEFORE INSERT OR UPDATE ON ticket_group_member
FOR EACH ROW EXECUTE FUNCTION ticket_group_prevent_cycle();
