-- ============================================================
-- Comprehensive schema verification and migration script
-- Safe to run multiple times (fully idempotent)
-- Checks every table and every column against the application models
-- ============================================================

-- ============================================================
-- 1. ENSURE ALL TABLES EXIST
-- ============================================================

CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256),
    color VARCHAR(7) DEFAULT '#3498db',
    is_admin BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50) DEFAULT 'America/Los_Angeles',
    theme_preference VARCHAR(20) DEFAULT 'dark',
    profile_picture VARCHAR(255),
    show_on_dashboard BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS location (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedule (
    id SERIAL PRIMARY KEY,
    technician_id INTEGER REFERENCES "user"(id),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    description TEXT,
    time_off BOOLEAN DEFAULT FALSE,
    all_day BOOLEAN DEFAULT FALSE,
    location_id INTEGER REFERENCES location(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quick_link (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    description VARCHAR(500) DEFAULT '',
    icon VARCHAR(50) DEFAULT 'link',
    category VARCHAR(100) NOT NULL,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50) DEFAULT 'help-circle',
    priority_level INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category_id INTEGER REFERENCES ticket_category(id),
    status VARCHAR(20) DEFAULT 'open',
    priority INTEGER DEFAULT 0,
    assigned_to INTEGER REFERENCES "user"(id),
    created_by INTEGER REFERENCES "user"(id) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    due_date TIMESTAMP WITH TIME ZONE,
    archived BOOLEAN DEFAULT FALSE,
    external_email VARCHAR(255),
    external_name VARCHAR(255),
    email_notifications BOOLEAN DEFAULT TRUE,
    email_thread_id VARCHAR(100),
    attachment VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS ticket_view (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    last_viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, ticket_id)
);

CREATE TABLE IF NOT EXISTS ticket_comment (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES ticket(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES "user"(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    attachment VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS ticket_history (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES ticket(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES "user"(id),
    action VARCHAR(50) NOT NULL,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recurring_schedule_template (
    id SERIAL PRIMARY KEY,
    technician_id INTEGER REFERENCES "user"(id) NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    location_id INTEGER REFERENCES location(id),
    active BOOLEAN DEFAULT TRUE,
    monday_start VARCHAR(5),
    monday_end VARCHAR(5),
    tuesday_start VARCHAR(5),
    tuesday_end VARCHAR(5),
    wednesday_start VARCHAR(5),
    wednesday_end VARCHAR(5),
    thursday_start VARCHAR(5),
    thursday_end VARCHAR(5),
    friday_start VARCHAR(5),
    friday_end VARCHAR(5),
    saturday_start VARCHAR(5),
    saturday_end VARCHAR(5),
    sunday_start VARCHAR(5),
    sunday_end VARCHAR(5),
    auto_generate BOOLEAN DEFAULT TRUE,
    weeks_ahead INTEGER DEFAULT 2,
    last_generated TIMESTAMP WITH TIME ZONE,
    self_service BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS email_settings (
    id SERIAL PRIMARY KEY,
    admin_email_group VARCHAR(120) NOT NULL DEFAULT 'alerts@obedtv.com',
    notify_on_create BOOLEAN DEFAULT TRUE,
    notify_on_update BOOLEAN DEFAULT TRUE,
    notify_on_delete BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 2. ENSURE ALL COLUMNS EXIST ON EVERY TABLE
--    (handles upgrades from older schema versions)
-- ============================================================

DO $$
DECLARE
    col_exists BOOLEAN;
BEGIN
    -- --------------------------------------------------------
    -- "user" table columns
    -- --------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='is_admin') THEN
        ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added user.is_admin';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='color') THEN
        ALTER TABLE "user" ADD COLUMN color VARCHAR(7) DEFAULT '#3498db';
        RAISE NOTICE 'Added user.color';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='timezone') THEN
        ALTER TABLE "user" ADD COLUMN timezone VARCHAR(50) DEFAULT 'America/Los_Angeles';
        RAISE NOTICE 'Added user.timezone';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='theme_preference') THEN
        ALTER TABLE "user" ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'dark';
        RAISE NOTICE 'Added user.theme_preference';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='profile_picture') THEN
        ALTER TABLE "user" ADD COLUMN profile_picture VARCHAR(255);
        RAISE NOTICE 'Added user.profile_picture';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='show_on_dashboard') THEN
        ALTER TABLE "user" ADD COLUMN show_on_dashboard BOOLEAN NOT NULL DEFAULT TRUE;
        RAISE NOTICE 'Added user.show_on_dashboard';
    END IF;

    -- --------------------------------------------------------
    -- "schedule" table columns
    -- --------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='schedule' AND column_name='time_off') THEN
        ALTER TABLE schedule ADD COLUMN time_off BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added schedule.time_off';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='schedule' AND column_name='all_day') THEN
        ALTER TABLE schedule ADD COLUMN all_day BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added schedule.all_day';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='schedule' AND column_name='location_id') THEN
        ALTER TABLE schedule ADD COLUMN location_id INTEGER REFERENCES location(id);
        RAISE NOTICE 'Added schedule.location_id';
    END IF;

    -- --------------------------------------------------------
    -- "quick_link" table columns
    -- --------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='quick_link' AND column_name='description') THEN
        ALTER TABLE quick_link ADD COLUMN description VARCHAR(500) DEFAULT '';
        RAISE NOTICE 'Added quick_link.description';
    END IF;

    -- --------------------------------------------------------
    -- "ticket" table columns
    -- --------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ticket' AND column_name='archived') THEN
        ALTER TABLE ticket ADD COLUMN archived BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added ticket.archived';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ticket' AND column_name='external_email') THEN
        ALTER TABLE ticket ADD COLUMN external_email VARCHAR(255);
        RAISE NOTICE 'Added ticket.external_email';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ticket' AND column_name='external_name') THEN
        ALTER TABLE ticket ADD COLUMN external_name VARCHAR(255);
        RAISE NOTICE 'Added ticket.external_name';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ticket' AND column_name='email_notifications') THEN
        ALTER TABLE ticket ADD COLUMN email_notifications BOOLEAN DEFAULT TRUE;
        RAISE NOTICE 'Added ticket.email_notifications';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ticket' AND column_name='email_thread_id') THEN
        ALTER TABLE ticket ADD COLUMN email_thread_id VARCHAR(100);
        RAISE NOTICE 'Added ticket.email_thread_id';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ticket' AND column_name='attachment') THEN
        ALTER TABLE ticket ADD COLUMN attachment VARCHAR(255);
        RAISE NOTICE 'Added ticket.attachment';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ticket' AND column_name='due_date') THEN
        ALTER TABLE ticket ADD COLUMN due_date TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Added ticket.due_date';
    END IF;

    -- --------------------------------------------------------
    -- "ticket_comment" table columns
    -- --------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ticket_comment' AND column_name='attachment') THEN
        ALTER TABLE ticket_comment ADD COLUMN attachment VARCHAR(255);
        RAISE NOTICE 'Added ticket_comment.attachment';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ticket_comment' AND column_name='updated_at') THEN
        ALTER TABLE ticket_comment ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'Added ticket_comment.updated_at';
    END IF;

    -- --------------------------------------------------------
    -- "recurring_schedule_template" table columns
    -- --------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recurring_schedule_template' AND column_name='self_service') THEN
        ALTER TABLE recurring_schedule_template ADD COLUMN self_service BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added recurring_schedule_template.self_service';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recurring_schedule_template' AND column_name='auto_generate') THEN
        ALTER TABLE recurring_schedule_template ADD COLUMN auto_generate BOOLEAN DEFAULT TRUE;
        RAISE NOTICE 'Added recurring_schedule_template.auto_generate';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recurring_schedule_template' AND column_name='weeks_ahead') THEN
        ALTER TABLE recurring_schedule_template ADD COLUMN weeks_ahead INTEGER DEFAULT 2;
        RAISE NOTICE 'Added recurring_schedule_template.weeks_ahead';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recurring_schedule_template' AND column_name='last_generated') THEN
        ALTER TABLE recurring_schedule_template ADD COLUMN last_generated TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Added recurring_schedule_template.last_generated';
    END IF;

    RAISE NOTICE '=== Column verification complete ===';
END $$;


-- ============================================================
-- 3. ENSURE ALL INDEXES EXIST
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_schedule_technician ON schedule(technician_id);
CREATE INDEX IF NOT EXISTS idx_schedule_time ON schedule(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_quick_link_order ON quick_link("order");
CREATE INDEX IF NOT EXISTS idx_ticket_status ON ticket(status);
CREATE INDEX IF NOT EXISTS idx_ticket_assigned_to ON ticket(assigned_to);
CREATE INDEX IF NOT EXISTS idx_ticket_category ON ticket(category_id);
CREATE INDEX IF NOT EXISTS idx_ticket_created_by ON ticket(created_by);
CREATE INDEX IF NOT EXISTS idx_ticket_comment_ticket ON ticket_comment(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_history_ticket ON ticket_history(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_view_user_id ON ticket_view(user_id);
CREATE INDEX IF NOT EXISTS idx_ticket_view_ticket_id ON ticket_view(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_view_last_viewed ON ticket_view(last_viewed_at);
CREATE INDEX IF NOT EXISTS idx_location_active ON location(active);
CREATE INDEX IF NOT EXISTS idx_recurring_template_active ON recurring_schedule_template(active);
CREATE INDEX IF NOT EXISTS idx_recurring_template_technician ON recurring_schedule_template(technician_id);
CREATE INDEX IF NOT EXISTS idx_ticket_external_email ON ticket(external_email);
CREATE INDEX IF NOT EXISTS idx_ticket_email_thread_id ON ticket(email_thread_id);

DO $$
BEGIN
    RAISE NOTICE '=== Schema verification and migration complete ===';
END $$;
