-- Create tables
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256),
    color VARCHAR(7) DEFAULT '#3498db',
    is_admin BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50) DEFAULT 'America/Los_Angeles',
    theme_preference VARCHAR(20) DEFAULT 'light',
    profile_picture VARCHAR(500)
);

-- Create location table first (referenced by schedule table)
CREATE TABLE location (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE schedule (
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

CREATE TABLE quick_link (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    icon VARCHAR(50) DEFAULT 'link',
    category VARCHAR(100) NOT NULL,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- New tables for ticket system
CREATE TABLE ticket_category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50) DEFAULT 'help-circle',
    priority_level INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ticket (
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
    -- External user support columns (Option 3)
    external_email VARCHAR(255),
    external_name VARCHAR(255),
    email_notifications BOOLEAN DEFAULT TRUE,
    email_thread_id VARCHAR(100)
);

CREATE TABLE ticket_comment (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES ticket(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES "user"(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ticket_history (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES ticket(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES "user"(id),
    action VARCHAR(50) NOT NULL,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create recurring schedule templates table
CREATE TABLE recurring_schedule_template (
    id SERIAL PRIMARY KEY,
    technician_id INTEGER REFERENCES "user"(id) NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    location_id INTEGER REFERENCES location(id),
    active BOOLEAN DEFAULT TRUE,
    
    -- Weekly schedule times (stored as time strings)
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
    
    -- Auto-generation settings
    auto_generate BOOLEAN DEFAULT TRUE,
    weeks_ahead INTEGER DEFAULT 2,
    last_generated TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create email settings table
CREATE TABLE email_settings (
    id SERIAL PRIMARY KEY,
    admin_email_group VARCHAR(120) NOT NULL DEFAULT 'alerts@obedtv.com',
    notify_on_create BOOLEAN DEFAULT TRUE,
    notify_on_update BOOLEAN DEFAULT TRUE,
    notify_on_delete BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_schedule_technician ON schedule(technician_id);
CREATE INDEX idx_schedule_time ON schedule(start_time, end_time);
CREATE INDEX idx_quick_link_order ON quick_link("order");
CREATE INDEX idx_ticket_status ON ticket(status);
CREATE INDEX idx_ticket_assigned_to ON ticket(assigned_to);
CREATE INDEX idx_ticket_category ON ticket(category_id);
CREATE INDEX idx_ticket_created_by ON ticket(created_by);
CREATE INDEX idx_ticket_comment_ticket ON ticket_comment(ticket_id);
CREATE INDEX idx_ticket_history_ticket ON ticket_history(ticket_id);
CREATE INDEX idx_location_active ON location(active);
CREATE INDEX idx_recurring_template_active ON recurring_schedule_template(active);
CREATE INDEX idx_recurring_template_technician ON recurring_schedule_template(technician_id);

-- Insert actual user data
INSERT INTO "user" (username, email, password_hash, color, is_admin, timezone) VALUES 
('Zach M', 'ZMorales@tbn.tv', 'scrypt:32768:8:1$1B6nYEmTU5n9syFc$8b177dda6a0c7ea752ab3a6c99b6d05cf65d8715a578ca990e9c1f88c36ac0f4647c8f6f4c0d46a11d9af448740b3ec56e584607451fcd75e1dd39418dc3362b', '#3edb33', false, 'UTC'),
('Thomas V', 'TValenzuela@tbn.tv', 'scrypt:32768:8:1$INIAFTTfa8ewFHUd$7a37190ab1d458dc29c28a8837c2122528719248e7965b04b470d2970e9db135a9bd117911484da66b9c3a1e7b52bfc4e77ed6689269594a5ed082b8a389a361', '#db5d33', false, 'UTC'),
('Adrian C', 'ACervantes@tbn.tv', 'scrypt:32768:8:1$dX32IZYJbTzyjIe6$93df119758950bfbbef81beb106f032f185eadf7067a365ba45184027e031b2ae556c7af2c2989ec5ab7d721766bcf56efb0a8940b074f3df759b15daa837a1b', '#7f33db', false, 'UTC'),
('Blake G', 'BGeorge@tbn.tv', 'scrypt:32768:8:1$DleVxI2IPzetpQ4Y$2859920ea702569a163eaa0e163a9eb863523fe8a0eb5995645ded9a87dc258d6c51fb4425112bac5c27a85c8bef8b9fc17b9ecd9c1746fe8dd0f542575a9a22', '#dbbf33', false, 'UTC'),
('Obed S', 'osandoval@tbn.tv', 'scrypt:32768:8:1$hjgRFe4gKlrJqjYk$13d64a3dbe3808f6fd2dee0448c89a727cd0f6aa40b9229a850e62f78bdefee22451d4d3be652ea467bd938589b72fec4f5dc3ce208c39f3810f2a68d8777946', '#3366db', false, 'America/Los_Angeles'),
('Nic C', 'NCasoria@tbn.tv', 'scrypt:32768:8:1$EcQQ1NkH3PMrMCPy$d716babad7d5faecb5d8a1a3bf1839d30ef8a754b5f218c4dd021779e60dfa46259446eb982295b65f0a31b9a6e781635a97dfc149e9aca17fd28f5bb32af854', '#004040', false, 'America/Los_Angeles'),
('Sarah H', 'SHusted@tbn.tv', 'scrypt:32768:8:1$OyMSd6GNRnSkw2Jc$7c250062d48092b25eb9ecea210f5e82bb8df8a3e40079b10d8925d8b5b28f3934d2eea2d47347033010d0a891b548e443b34f88bcd599dff05581282282364a', '#ae33db', true, 'America/Los_Angeles'),
('admin', 'admin@obedtv.com', 'scrypt:32768:8:1$YZ4gm91MkS075SE1$2df4a29d88adbcf82002b5db90c1d0a3634637fa7aa2e532e02358b095d0918c0454f9aa087a1d323d26c58365c1f6ff8620773a44f9b567b54f2a448a96b535', '#ff0000', true, 'America/Los_Angeles'),
('Marty C', 'MCruz@tbn.tv', 'scrypt:32768:8:1$6KwnqLHpzfp0tA07$a6c7f9d079fd75a87ed537ede7d7fa52f45898e7de48d5febef2c216748c0c986737f53db97a603ab2e659f00d7f27148e9d640788261ff69d05471ac2a8796a', '#3498db', false, 'America/Los_Angeles'),
('David H', 'DHarvilla@tbn.tv', 'scrypt:32768:8:1$igGtD8Nb2gevX5Uv$22778f15438c5bc52c557526070459637afbba7e2d813d948f64a6d5e3685aa4a0cab4c533880ddc33f323de0cd158dc9aee6a08984dff9e091308001683b62d', '#418171', true, 'America/Los_Angeles');

-- Insert sample locations
INSERT INTO location (name, description, active) VALUES
('Main Studio', 'Primary production studio', true),
('Studio B', 'Secondary production studio', true),
('Control Room', 'Master control room', true),
('Remote', 'Remote work location', true),
('Maintenance Bay', 'Equipment maintenance area', true);

INSERT INTO ticket_category (name, description, icon, priority_level) VALUES
('Hardware', 'Hardware-related issues and requests', 'hard-drive', 1),
('Software', 'Software installation and configuration', 'settings', 1),
('Network', 'Network connectivity issues', 'wifi', 2),
('Access', 'Account access and permissions', 'key', 2),
('General', 'General support requests', 'help-circle', 0);

-- Insert default email settings
INSERT INTO email_settings (admin_email_group, notify_on_create, notify_on_update, notify_on_delete) VALUES
('alerts@obedtv.com', true, true, true);

-- Note: Recurring schedule templates are stored in the recurring_schedule_template table
-- These templates define weekly work patterns that can automatically generate
-- schedule entries for technicians. Templates include:
-- - Weekly time patterns (start/end times for each day)
-- - Auto-generation settings (how many weeks ahead to generate)
-- - Location assignments for each template

-- Reset sequences
SELECT setval('user_id_seq', (SELECT MAX(id) FROM "user"));
SELECT setval('location_id_seq', (SELECT MAX(id) FROM location));
SELECT setval('schedule_id_seq', (SELECT MAX(id) FROM schedule));
SELECT setval('recurring_schedule_template_id_seq', (SELECT MAX(id) FROM recurring_schedule_template));
SELECT setval('quick_link_id_seq', (SELECT MAX(id) FROM quick_link));
SELECT setval('ticket_category_id_seq', (SELECT MAX(id) FROM ticket_category));
SELECT setval('ticket_id_seq', (SELECT MAX(id) FROM ticket));
SELECT setval('ticket_comment_id_seq', (SELECT MAX(id) FROM ticket_comment));
SELECT setval('ticket_history_id_seq', (SELECT MAX(id) FROM ticket_history));
SELECT setval('email_settings_id_seq', (SELECT MAX(id) FROM email_settings));

-- Create indexes for external user support (Option 3)
CREATE INDEX IF NOT EXISTS idx_ticket_external_email ON ticket(external_email);
CREATE INDEX IF NOT EXISTS idx_ticket_email_thread_id ON ticket(email_thread_id);
CREATE INDEX IF NOT EXISTS idx_ticket_external_notifications ON ticket(email_notifications) WHERE external_email IS NOT NULL;