-- AI-OpsPilot  –  Bootstrap SQL
-- Run automatically by Docker Compose on first start.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Incidents ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS incidents (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       TEXT NOT NULL,
    severity    VARCHAR(10) NOT NULL CHECK (severity IN ('low','medium','high','critical')),
    status      VARCHAR(20) NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','investigating','resolved','closed')),
    source      TEXT,
    raw_log     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Anomalies ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS anomalies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id     UUID REFERENCES incidents(id) ON DELETE SET NULL,
    metric_name     TEXT NOT NULL,
    metric_value    FLOAT NOT NULL,
    anomaly_score   FLOAT NOT NULL,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_acknowledged BOOLEAN NOT NULL DEFAULT FALSE
);

-- ── Analysis results (LLM output) ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analyses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id     UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    root_cause      TEXT,
    summary         TEXT,
    runbooks_used   JSONB DEFAULT '[]',
    llm_model       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Remediation actions ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS remediations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id     UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    action_name     TEXT NOT NULL,
    parameters      JSONB DEFAULT '{}',
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','approved','rejected','executed','failed')),
    approved_by     TEXT,
    executed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Log ingestion audit ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS log_entries (
    id          BIGSERIAL PRIMARY KEY,
    service     TEXT,
    level       VARCHAR(10),
    message     TEXT NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw         JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_incidents_status    ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity  ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_anomalies_detected  ON anomalies(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_log_entries_time    ON log_entries(timestamp DESC);
