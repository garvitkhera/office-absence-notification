-- =============================================
-- SUPABASE SETUP FOR OFFICE PRESENCE TRACKER
-- Run this in Supabase SQL Editor
-- =============================================

-- 1. Create employees table
CREATE TABLE IF NOT EXISTS employees (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    email TEXT,
    has_key BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create absences table
CREATE TABLE IF NOT EXISTS absences (
    id BIGSERIAL PRIMARY KEY,
    employee_name TEXT NOT NULL,
    absence_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_name, absence_date)
);

-- 3. Create email_log table (with followup tracking)
CREATE TABLE IF NOT EXISTS email_log (
    id BIGSERIAL PRIMARY KEY,
    alert_date DATE NOT NULL UNIQUE,
    followup_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create usual_absences table (for weekly patterns)
CREATE TABLE IF NOT EXISTS usual_absences (
    id BIGSERIAL PRIMARY KEY,
    employee_name TEXT NOT NULL UNIQUE,
    monday BOOLEAN DEFAULT FALSE,
    tuesday BOOLEAN DEFAULT FALSE,
    wednesday BOOLEAN DEFAULT FALSE,
    thursday BOOLEAN DEFAULT FALSE,
    friday BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create sync_log table (for tracking monthly sync operations)
CREATE TABLE IF NOT EXISTS sync_log (
    id BIGSERIAL PRIMARY KEY,
    sync_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_employees_has_key ON employees(has_key);
CREATE INDEX IF NOT EXISTS idx_absences_date ON absences(absence_date);
CREATE INDEX IF NOT EXISTS idx_absences_employee ON absences(employee_name);
CREATE INDEX IF NOT EXISTS idx_email_log_date ON email_log(alert_date);
CREATE INDEX IF NOT EXISTS idx_usual_absences_employee ON usual_absences(employee_name);

-- 7. Enable Row Level Security (RLS) with permissive policies
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE absences ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE usual_absences ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_log ENABLE ROW LEVEL SECURITY;

-- Allow all operations on all tables (internal tool)
CREATE POLICY "Allow all on employees" ON employees FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on absences" ON absences FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on email_log" ON email_log FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on usual_absences" ON usual_absences FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on sync_log" ON sync_log FOR ALL USING (true) WITH CHECK (true);

-- =============================================
-- SAMPLE DATA: Add your employees here
-- =============================================

INSERT INTO employees (name, email, has_key) VALUES
    ('Steve Etsebeth', 'setsebeth@parkagility.com', true),
    ('Jorge Molina', 'jmolina@parkagility.com', true),
    ('Sarah Jacobs', 'sjacobs@parkagility.com', true),
    ('Nicolas Souchaud', 'nsouchaud@parkagility.com', true),
    ('Garvit Khera', 'gkhera@parkagility.com', false),
    ('Brad Burrows', 'bburrows@parkagility.com', false),
    ('Armen Oganesian', 'aoganesian@parkagility.com', false),
    ('Jacob Burrows', 'jburrows@parkagility.com', false),
    ('Lisa Hyland', 'lhyland@parkagility.com', false),
    ('Simo Competiello', 'scompetiello@parkagility.com', false),
    ('Alex Johnson', 'ajohnson@parkagility.com', false)
ON CONFLICT (name) DO NOTHING;