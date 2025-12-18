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

-- 2. Create email_log table (with followup tracking)
CREATE TABLE IF NOT EXISTS email_log (
    id BIGSERIAL PRIMARY KEY,
    alert_date DATE NOT NULL UNIQUE,
    followup_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create usual_absences table (for weekly patterns)
CREATE TABLE IF NOT EXISTS usual_absences (
    id BIGSERIAL PRIMARY KEY,
    key_bearer TEXT NOT NULL UNIQUE,
    monday BOOLEAN DEFAULT FALSE,
    tuesday BOOLEAN DEFAULT FALSE,
    wednesday BOOLEAN DEFAULT FALSE,
    thursday BOOLEAN DEFAULT FALSE,
    friday BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create sync_log table (for tracking monthly sync operations)
CREATE TABLE IF NOT EXISTS sync_log (
    id BIGSERIAL PRIMARY KEY,
    sync_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_absences_date ON absences(absence_date);
CREATE INDEX IF NOT EXISTS idx_absences_bearer ON absences(key_bearer);
CREATE INDEX IF NOT EXISTS idx_email_log_date ON email_log(alert_date);
CREATE INDEX IF NOT EXISTS idx_usual_absences_bearer ON usual_absences(key_bearer);

-- 6. Enable Row Level Security (RLS) with permissive policies

ALTER TABLE absences ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE usual_absences ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_log ENABLE ROW LEVEL SECURITY;

-- Allow all operations on all tables (internal tool)
CREATE POLICY "Allow all on absences" ON absences FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on email_log" ON email_log FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on usual_absences" ON usual_absences FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on sync_log" ON sync_log FOR ALL USING (true) WITH CHECK (true);
