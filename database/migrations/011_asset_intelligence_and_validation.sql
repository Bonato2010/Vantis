-- Migração 011: Asset Intelligence Library & Editorial Validation Reports (Fase 24)

CREATE TABLE IF NOT EXISTS production_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_uid TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    media_type TEXT NOT NULL,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    duration_sec REAL DEFAULT 0.0,
    file_size_bytes INTEGER DEFAULT 0,
    sha256 TEXT NOT NULL UNIQUE,
    origin TEXT NOT NULL,
    source_url TEXT,
    license_name TEXT NOT NULL DEFAULT 'UNKNOWN',
    license_status TEXT NOT NULL DEFAULT 'LICENSE_UNVERIFIED',
    attribution_required INTEGER DEFAULT 0,
    authorized_channels_json TEXT DEFAULT '[1,2,3,4,5]',
    validation_status TEXT NOT NULL DEFAULT 'PENDING',
    validation_notes TEXT,
    tags_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prod_assets_sha256 ON production_assets(sha256);
CREATE INDEX IF NOT EXISTS idx_prod_assets_license ON production_assets(license_status, validation_status);

CREATE TABLE IF NOT EXISTS editorial_validation_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    classification TEXT NOT NULL,
    quality_score REAL NOT NULL DEFAULT 0.0,
    passed INTEGER NOT NULL DEFAULT 0,
    checks_json TEXT DEFAULT '{}',
    failures_json TEXT DEFAULT '[]',
    warnings_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ed_val_pkg ON editorial_validation_reports(package_id, id DESC);
