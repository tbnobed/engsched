-- Caller owns the transaction. Applied after the Groups schema at deployment.
-- Definitions include inactive examples; they never execute ticket actions.
SELECT pg_advisory_xact_lock(72419031);

ALTER TABLE ticket ADD COLUMN IF NOT EXISTS custom_values json NOT NULL DEFAULT '{}';
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS tags json NOT NULL DEFAULT '[]';
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS cc_user_ids json NOT NULL DEFAULT '[]';
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS cc_group_ids json NOT NULL DEFAULT '[]';
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS assigned_at timestamptz;
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS resolved_at timestamptz;
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS closed_at timestamptz;
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS reopened_at timestamptz;
ALTER TABLE ticket_comment ADD COLUMN IF NOT EXISTS is_private boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS automation_rules (
    id serial PRIMARY KEY,
    name varchar(200) NOT NULL,
    description text NOT NULL DEFAULT '',
    position integer NOT NULL DEFAULT 0,
    active boolean NOT NULL DEFAULT true,
    trigger varchar(30) NOT NULL CHECK (trigger IN ('created','comment_added','updated','survey_submitted','custom')),
    custom_triggers jsonb NOT NULL DEFAULT '[]',
    scope varchar(30) NOT NULL DEFAULT 'ticket' CHECK (scope = 'ticket'),
    condition_logic varchar(20) NOT NULL DEFAULT 'all' CHECK (condition_logic IN ('all','any','custom')),
    custom_expression text NOT NULL DEFAULT '',
    created_by integer REFERENCES "user"(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS automation_conditions (
    id serial PRIMARY KEY,
    rule_id integer NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    number integer NOT NULL CHECK (number > 0),
    kind varchar(20) NOT NULL DEFAULT 'regular' CHECK (kind IN ('regular','time_based')),
    field_key varchar(100),
    value_type varchar(20) DEFAULT 'current_value',
    operator varchar(40),
    value jsonb,
    amount integer,
    unit varchar(20),
    direction varchar(10),
    anchor_field varchar(100),
    public_only boolean NOT NULL DEFAULT true,
    UNIQUE(rule_id,number)
);
CREATE TABLE IF NOT EXISTS automation_actions (
    id serial PRIMARY KEY,
    rule_id integer NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    position integer NOT NULL,
    type varchar(30) NOT NULL,
    config jsonb NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS automation_runs (
    id serial PRIMARY KEY,
    rule_id integer REFERENCES automation_rules(id) ON DELETE SET NULL,
    rule_name varchar(200) NOT NULL,
    ticket_id integer NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    trigger_event varchar(30) NOT NULL,
    matched boolean NOT NULL DEFAULT false,
    actions_executed jsonb NOT NULL DEFAULT '[]',
    errors jsonb NOT NULL DEFAULT '[]',
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);
CREATE INDEX IF NOT EXISTS ix_automation_runs_rule_id ON automation_runs(rule_id);
CREATE INDEX IF NOT EXISTS ix_automation_runs_ticket_id ON automation_runs(ticket_id);
CREATE TABLE IF NOT EXISTS automation_scheduled_jobs (
    id serial PRIMARY KEY,
    rule_id integer NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    ticket_id integer NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    run_at timestamptz NOT NULL,
    status varchar(15) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','done','cancelled')),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS automation_one_pending ON automation_scheduled_jobs(rule_id,ticket_id) WHERE status='pending';
CREATE INDEX IF NOT EXISTS ix_automation_scheduled_jobs_run_at ON automation_scheduled_jobs(run_at);
CREATE TABLE IF NOT EXISTS automation_custom_fields (
    key varchar(100) PRIMARY KEY,
    label varchar(150) NOT NULL,
    data_type varchar(20) NOT NULL,
    choices jsonb NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS automation_settings (
    id integer PRIMARY KEY,
    timezone varchar(60) NOT NULL DEFAULT 'UTC',
    business_hours jsonb NOT NULL DEFAULT '{}',
    overflow_alert_at timestamptz
);
CREATE TABLE IF NOT EXISTS automation_ticket_links (
    ticket_id integer NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    linked_ticket_id integer NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    PRIMARY KEY(ticket_id,linked_ticket_id)
);

-- These examples are definitions only, always inactive. Nothing evaluates them
-- in this migration. Existing native semantics: Critical=Urgent(3), New=open,
-- Awaiting Input=pending. The On-call group must be selected/created by an admin.
CREATE TABLE IF NOT EXISTS automation_schema_versions (
    version varchar(100) PRIMARY KEY
);
DO $examples$
DECLARE
    actor integer;
    rule integer;
BEGIN
    IF EXISTS (SELECT 1 FROM automation_schema_versions WHERE version='initial_examples') THEN
        RETURN;
    END IF;
    SELECT id INTO actor FROM "user" WHERE is_admin=true ORDER BY id LIMIT 1;
    IF NOT EXISTS (SELECT 1 FROM automation_rules WHERE name='Template: Urgent keyword routing') THEN
        INSERT INTO automation_rules(name,description,position,active,trigger,created_by)
        VALUES ('Template: Urgent keyword routing','Critical maps to native Urgent (3). Review group notification recipients before enabling.',10,false,'created',actor) RETURNING id INTO rule;
        INSERT INTO automation_conditions(rule_id,number,kind,field_key,value_type,operator,value)
        VALUES (rule,1,'regular','keyword','current_value','matches regex',to_jsonb('(urgent|down|off[\s-]?air|outage)'::text));
        INSERT INTO automation_actions(rule_id,position,type,config) VALUES
            (rule,1,'update_record','{"fields":{"priority":3}}'),
            (rule,2,'send_notification','{"recipients":[{"kind":"ticket_group"}],"subject":"Urgent ticket #{{id}}: {{title}}","body":"Please review {{ticket_url}}"}');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM automation_rules WHERE name='Template: After-hours routing') THEN
        INSERT INTO automation_rules(name,description,position,active,trigger,created_by)
        VALUES ('Template: After-hours routing','Configure the business calendar and select an actual On-call group before enabling. A missing group is an explicit action error.',20,false,'created',actor) RETURNING id INTO rule;
        INSERT INTO automation_conditions(rule_id,number,kind,field_key,value_type,operator,value)
        VALUES (rule,1,'regular','created_at','current_value','outside business hours','null');
        INSERT INTO automation_actions(rule_id,position,type,config)
        VALUES (rule,1,'update_record','{"fields":{"group_id":{"group_name":"On-call"}}}');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM automation_rules WHERE name='Template: Unassigned after one hour') THEN
        INSERT INTO automation_rules(name,description,position,active,trigger,created_by)
        VALUES ('Template: Unassigned after one hour','New maps to native Open. Raise priority one level and notify the ticket group manager.',30,false,'created',actor) RETURNING id INTO rule;
        INSERT INTO automation_conditions(rule_id,number,kind,amount,unit,direction,anchor_field)
        VALUES (rule,1,'time_based',1,'hours','after','created_at');
        INSERT INTO automation_conditions(rule_id,number,kind,field_key,value_type,operator,value) VALUES
            (rule,2,'regular','status','current_value','is','"open"'),
            (rule,3,'regular','assigned_to','current_value','is empty','null');
        INSERT INTO automation_actions(rule_id,position,type,config) VALUES
            (rule,1,'update_record','{"fields":{"priority":"raise_one"}}'),
            (rule,2,'send_notification','{"recipients":[{"kind":"group_manager"}],"subject":"Unassigned ticket #{{id}}","body":"Please assign {{ticket_url}}"}');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM automation_rules WHERE name='Template: Close resolved after three days') THEN
        INSERT INTO automation_rules(name,description,position,active,trigger,created_by)
        VALUES ('Template: Close resolved after three days','Schedules when a ticket is updated to Resolved. Re-checks the current status before closing.',40,false,'updated',actor) RETURNING id INTO rule;
        INSERT INTO automation_conditions(rule_id,number,kind,amount,unit,direction,anchor_field)
        VALUES (rule,1,'time_based',3,'days','after','resolved_at');
        INSERT INTO automation_conditions(rule_id,number,kind,field_key,value_type,operator,value)
        VALUES (rule,2,'regular','status','current_value','is','"resolved"');
        INSERT INTO automation_actions(rule_id,position,type,config)
        VALUES (rule,1,'update_record','{"fields":{"status":"closed"}}');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM automation_rules WHERE name='Template: Reopen on requester reply') THEN
        INSERT INTO automation_rules(name,description,position,active,trigger,created_by)
        VALUES ('Template: Reopen on requester reply','Awaiting Input maps to native Pending. A requester comment changes Pending to Open.',50,false,'comment_added',actor) RETURNING id INTO rule;
        INSERT INTO automation_conditions(rule_id,number,kind,field_key,value_type,operator,value) VALUES
            (rule,1,'regular','comment_author','current_value','is','"requester"'),
            (rule,2,'regular','status','current_value','is','"pending"');
        INSERT INTO automation_actions(rule_id,position,type,config)
        VALUES (rule,1,'update_record','{"fields":{"status":"open"}}');
    END IF;
    INSERT INTO automation_schema_versions(version) VALUES ('initial_examples');
END
$examples$;
