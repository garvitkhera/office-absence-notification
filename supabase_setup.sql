-- =============================================
-- SUPABASE SETUP FOR OFFICE KEY TRACKER
-- Run this in Supabase SQL Editor
-- =============================================

-- 1. Create absences table
CREATE TABLE IF NOT EXISTS absences (
    id BIGSERIAL PRIMARY KEY,
    key_bearer TEXT NOT NULL,
    absence_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(key_bearer, absence_date)
);

-- 2. Create email_log table
CREATE TABLE IF NOT EXISTS email_log (
    id BIGSERIAL PRIMARY KEY,
    alert_date DATE NOT NULL UNIQUE,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_absences_date ON absences(absence_date);
CREATE INDEX IF NOT EXISTS idx_absences_bearer ON absences(key_bearer);
CREATE INDEX IF NOT EXISTS idx_email_log_date ON email_log(alert_date);

-- 4. Enable Row Level Security (RLS) - but allow all operations for this app
-- Since this is an internal tool, we'll use the anon key with permissive policies

ALTER TABLE absences ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_log ENABLE ROW LEVEL SECURITY;

-- Allow all operations on absences table
CREATE POLICY "Allow all operations on absences" ON absences
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Allow all operations on email_log table
CREATE POLICY "Allow all operations on email_log" ON email_log
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- =============================================
-- VERIFICATION: Run these to check setup
-- =============================================
-- SELECT * FROM absences;
-- SELECT * FROM email_log;
