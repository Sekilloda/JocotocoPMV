-- 001_initial_schema.sql
-- Jocotoco Smart Bioacoustic Monitor Platform
-- Schema definition with PostGIS support and Portable Multi-Tenant RLS

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS "postgis";
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'PostGIS extension not available in this environment, falling back to numeric coordinates.';
END $$;

-- 1. Organizations (Tenants)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Conservation Projects / Reserves
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    slug VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    reserve_code VARCHAR(32),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_org_project_slug UNIQUE (organization_id, slug)
);

-- 3. Edge Devices (Raspberry Pi 5 Smart Monitors)
CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR(64) PRIMARY KEY, -- e.g. 'joco-rpi5-buenaventura-01'
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    hardware_model VARCHAR(64) DEFAULT 'Raspberry Pi 5 8GB',
    firmware_version VARCHAR(32) DEFAULT '1.0.0',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    elevation_m DOUBLE PRECISION,
    status VARCHAR(32) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'MAINTENANCE', 'REVOKED', 'OFFLINE')),
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Cryptographic Device Keys (Ed25519 asymmetric identity)
CREATE TABLE IF NOT EXISTS device_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(64) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    public_key_hex VARCHAR(128) NOT NULL,
    key_algorithm VARCHAR(32) DEFAULT 'Ed25519',
    is_active BOOLEAN DEFAULT TRUE,
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    revocation_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_device_keys_active ON device_keys(device_id, is_active);

-- 5. Audio Clips (Custody in S3/Cloudflare R2 or Local Storage)
CREATE TABLE IF NOT EXISTS audio_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(64) NOT NULL REFERENCES devices(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    storage_uri VARCHAR(512) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    sha256_checksum VARCHAR(64) NOT NULL,
    audio_format VARCHAR(16) DEFAULT 'wav',
    sample_rate_hz INTEGER DEFAULT 22050,
    duration_seconds NUMERIC(6, 3) NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clips_device ON audio_clips(device_id, uploaded_at DESC);

-- 6. Bioacoustic Detection Events
CREATE TABLE IF NOT EXISTS bioacoustic_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    project_id UUID NOT NULL REFERENCES projects(id),
    device_id VARCHAR(64) NOT NULL REFERENCES devices(id),
    clip_id UUID REFERENCES audio_clips(id) ON DELETE SET NULL,
    idempotency_key UUID UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    species_scientific_name VARCHAR(255) NOT NULL,
    species_common_name VARCHAR(255) NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL,
    frequency_min_hz NUMERIC(8, 2),
    frequency_max_hz NUMERIC(8, 2),
    raw_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_species ON bioacoustic_events(species_scientific_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_project ON bioacoustic_events(project_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_device ON bioacoustic_events(device_id, timestamp DESC);

-- 7. Telemetry & Hardware Health Logs
CREATE TABLE IF NOT EXISTS telemetry_logs (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL REFERENCES devices(id),
    recorded_at TIMESTAMPTZ NOT NULL,
    battery_pct NUMERIC(5, 2),
    solar_input_mw NUMERIC(8, 2),
    cpu_temp_c NUMERIC(5, 2),
    disk_used_pct NUMERIC(5, 2),
    rssi_dbm INTEGER,
    queue_depth INTEGER DEFAULT 0,
    metrics JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_device ON telemetry_logs(device_id, recorded_at DESC);

-- 8. Machine Learning Models & OTA Versioning
CREATE TABLE IF NOT EXISTS ml_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    target_species TEXT[] NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    sha256_checksum VARCHAR(64) NOT NULL,
    chunk_size_bytes INTEGER DEFAULT 1048576, -- 1MB chunk standard
    total_chunks INTEGER NOT NULL,
    manifest JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- PORTABLE ROW-LEVEL SECURITY (RLS) POLICIES
-- Uses standard PostgreSQL session variables:
--   app.current_tenant_id  (UUID of the active organization)
--   app.current_role       ('admin', 'operator', 'auditor')
-- Bypasses when app.current_tenant_id is NULL or empty (for background migrations/superusers)
-- ============================================================================

ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE audio_clips ENABLE ROW LEVEL SECURITY;
ALTER TABLE bioacoustic_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_devices ON devices;
CREATE POLICY tenant_isolation_devices ON devices
    FOR ALL
    USING (
        NULLIF(current_setting('app.current_tenant_id', true), '') IS NULL
        OR organization_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    );

DROP POLICY IF EXISTS tenant_isolation_projects ON projects;
CREATE POLICY tenant_isolation_projects ON projects
    FOR ALL
    USING (
        NULLIF(current_setting('app.current_tenant_id', true), '') IS NULL
        OR organization_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    );

DROP POLICY IF EXISTS tenant_isolation_clips ON audio_clips;
CREATE POLICY tenant_isolation_clips ON audio_clips
    FOR ALL
    USING (
        NULLIF(current_setting('app.current_tenant_id', true), '') IS NULL
        OR organization_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    );

DROP POLICY IF EXISTS tenant_isolation_events ON bioacoustic_events;
CREATE POLICY tenant_isolation_events ON bioacoustic_events
    FOR ALL
    USING (
        NULLIF(current_setting('app.current_tenant_id', true), '') IS NULL
        OR organization_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    );
