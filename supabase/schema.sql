-- ============================================================================
-- ScamShield Supabase Schema & Row-Level Security (RLS) Configuration
-- Amazon Developer Hackathon — Production & Sandbox Migration
-- ============================================================================

-- 1. Enable pgcrypto / uuid-ossp for secure ID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Clean table for scam assessments (Privacy-First Telemetry)
-- NOTE: In compliance with ScamShield privacy guidelines, the RAW MESSAGE
-- is NEVER saved. Only the SHA-256 cryptographic fingerprint, category flags,
-- and risk score are persisted.
CREATE TABLE IF NOT EXISTS public.scam_assessments (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    fingerprint    TEXT NOT NULL,
    risk_score     INTEGER NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level     TEXT NOT NULL,
    channel        TEXT NOT NULL DEFAULT 'sms',
    preview_length INTEGER NOT NULL,
    warning_count  INTEGER NOT NULL DEFAULT 0,
    metadata       JSONB DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 3. Indexes for fast query resolution and pattern deduplication
CREATE INDEX IF NOT EXISTS idx_scam_assessments_fingerprint 
    ON public.scam_assessments(fingerprint);
CREATE INDEX IF NOT EXISTS idx_scam_assessments_created 
    ON public.scam_assessments(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scam_assessments_user 
    ON public.scam_assessments(user_id);

-- 4. Verified Safety & Emergency Resources Table
CREATE TABLE IF NOT EXISTS public.safety_resources (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category    TEXT NOT NULL,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    action_url  TEXT,
    phone       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Pre-seed safety resources
INSERT INTO public.safety_resources (category, title, description, action_url, phone)
VALUES 
    ('emergency', 'Freeze Compromised Bank Cards', 'Call your financial institution immediately if you entered banking credentials or card numbers.', NULL, 'Check card back'),
    ('reporting', 'Amazon Phishing Hotline', 'Report suspicious Amazon-branded emails, texts, or calls directly to the Amazon security team.', 'https://www.amazon.com/gp/help/customer/display.html?nodeId=GRGRY7AQ3LMPXNCR', NULL),
    ('reporting', 'US FTC Fraud Reporting', 'Report fraudulent solicitations, fake prizes, and tech support scams to the Federal Trade Commission.', 'https://reportfraud.ftc.gov', '1-877-FTC-HELP'),
    ('reporting', 'Forward SMS Phishing (7726)', 'Forward suspicious SMS messages directly to 7726 (SPAM) to alert telecommunications fraud filters.', NULL, '7726')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Row-Level Security (RLS) Policies
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.scam_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.safety_resources ENABLE ROW LEVEL SECURITY;

-- ── Policies: scam_assessments ───────────────────────────────────────────────

-- Policy A: Anyone (including anonymous users) can submit a scam assessment telemetry record
CREATE POLICY "Allow public insert for scan telemetry"
    ON public.scam_assessments
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Policy B: Authenticated users can view only their own past scan telemetry
CREATE POLICY "Users can view own scan history"
    ON public.scam_assessments
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- Policy C: Anonymous users cannot read private records (only service role or aggregated view)
-- Prevents data scraping while allowing users to utilize the tool safely.

-- Policy D: Disallow client-side UPDATE or DELETE to maintain audit integrity
-- (No UPDATE or DELETE policy is defined, defaulting to DENY)

-- ── Policies: safety_resources ───────────────────────────────────────────────

-- Policy E: All users (authenticated and anonymous) can view safety resources
CREATE POLICY "Public read for safety resources"
    ON public.safety_resources
    FOR SELECT
    TO anon, authenticated
    USING (true);
