-- ============================================================================
-- ScamShield Supabase Schema & Hardened Row-Level Security (RLS) Configuration
-- ============================================================================
-- Design Principles:
-- 1. Strict Privacy: The RAW MESSAGE is NEVER saved. Only the HMAC-SHA256
--    cryptographic fingerprint, category flags, and bounded risk score are persisted.
-- 2. Principle of Least Privilege: NO unrestricted WITH CHECK (true) policies.
-- 3. Telemetry Isolation: Anonymous clients cannot query other users' telemetry.
-- 4. Server-Side Protection: Service-role keys must NEVER be exposed to browser clients.
-- ============================================================================

-- 1. Enable pgcrypto extension for secure UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Anonymized Scan Assessments Telemetry Table
CREATE TABLE IF NOT EXISTS public.scam_assessments (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    session_id     TEXT,
    fingerprint    TEXT NOT NULL CHECK (length(fingerprint) = 64),
    risk_score     INTEGER NOT NULL CHECK (risk_score >= 5 AND risk_score <= 98),
    risk_level     TEXT NOT NULL CHECK (risk_level IN ('HIGH RISK', 'ELEVATED RISK', 'LOW RISK (Caution Still Advised)')),
    channel        TEXT NOT NULL DEFAULT 'sms' CHECK (channel IN ('sms', 'email', 'payment_app', 'social_media', 'other')),
    preview_length INTEGER NOT NULL CHECK (preview_length > 0 AND preview_length <= 10000),
    warning_count  INTEGER NOT NULL DEFAULT 0 CHECK (warning_count >= 0),
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
CREATE INDEX IF NOT EXISTS idx_scam_assessments_session 
    ON public.scam_assessments(session_id);

-- 4. Verified Safety & Emergency Resources Table
CREATE TABLE IF NOT EXISTS public.safety_resources (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category    TEXT NOT NULL CHECK (category IN ('emergency', 'reporting', 'advisory')),
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    action_url  TEXT,
    phone       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Pre-seed safety resources (Idempotent insert)
INSERT INTO public.safety_resources (category, title, description, action_url, phone)
VALUES 
    ('emergency', 'Freeze Compromised Bank Cards', 'Call your financial institution immediately if you entered banking credentials or card numbers.', NULL, 'Check card back'),
    ('reporting', 'Amazon Phishing Hotline', 'Report suspicious Amazon-branded emails, texts, or calls directly to the Amazon security team.', 'https://www.amazon.com/gp/help/customer/display.html?nodeId=GRGRY7AQ3LMPXNCR', NULL),
    ('reporting', 'US FTC Fraud Reporting', 'Report fraudulent solicitations, fake prizes, and tech support scams to the Federal Trade Commission.', 'https://reportfraud.ftc.gov', '1-877-FTC-HELP'),
    ('reporting', 'India National Cyber Crime Portal (1930)', 'Report financial cyber fraud immediately to National Cyber Crime Reporting Portal or call 1930.', 'https://cybercrime.gov.in', '1930'),
    ('reporting', 'Forward SMS Phishing (7726)', 'Forward suspicious SMS messages directly to 7726 (SPAM) to alert telecommunications fraud filters.', NULL, '7726')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Row-Level Security (RLS) Policies
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.scam_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.safety_resources ENABLE ROW LEVEL SECURITY;

-- Drop legacy permissive policies if they exist
DROP POLICY IF EXISTS "Allow public insert for scan telemetry" ON public.scam_assessments;
DROP POLICY IF EXISTS "Users can view own scan history" ON public.scam_assessments;
DROP POLICY IF EXISTS "Public read for safety resources" ON public.safety_resources;

-- ── Policies: scam_assessments ───────────────────────────────────────────────

-- Policy 1: Authenticated users can insert their own telemetry records
-- Validates that the submitted user_id strictly matches the calling JWT.
CREATE POLICY "Authenticated users insert own telemetry"
    ON public.scam_assessments
    FOR INSERT
    TO authenticated
    WITH CHECK (
        auth.uid() = user_id
        AND risk_score >= 5 AND risk_score <= 98
        AND length(fingerprint) = 64
        AND preview_length <= 10000
    );

-- Policy 2: Authenticated users can query only their own historical records
CREATE POLICY "Authenticated users view own scan history"
    ON public.scam_assessments
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- Note on Service Role:
-- Server-side telemetry persistence via backend/supabase_client.py uses the
-- server-side SUPABASE_SERVICE_ROLE_KEY which automatically bypasses RLS.
-- This guarantees backend API mediation while preventing direct public client table tampering.

-- Policy 3: Append-Only Audit Trail
-- UPDATE and DELETE operations are explicitly NOT granted to any public/anon role.
-- (Default DENY preserves immutable audit trail)

-- ── Policies: safety_resources ───────────────────────────────────────────────

-- Policy 4: Public read access for verified emergency hotlines and safety guidelines
CREATE POLICY "Public read for safety resources"
    ON public.safety_resources
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- Mutations on safety_resources are denied to public/anon (managed exclusively by admins/service-role)
