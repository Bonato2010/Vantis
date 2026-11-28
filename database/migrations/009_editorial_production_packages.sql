-- Migração 009: Pacotes de Produção Editorial Inteligente (Fase 21)
CREATE TABLE IF NOT EXISTS editorial_production_packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_uid TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    parent_package_id INTEGER,
    channel_id INTEGER NOT NULL,
    channel_name TEXT,
    niche TEXT,
    theme TEXT NOT NULL,
    reference_source_id TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    target_duration_sec REAL DEFAULT 35.0,
    editorial_goal TEXT,
    content_restrictions TEXT,
    package_json TEXT NOT NULL,
    version_history_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_epp_channel_status ON editorial_production_packages(channel_id, status);
CREATE INDEX IF NOT EXISTS idx_epp_uid ON editorial_production_packages(package_uid);
