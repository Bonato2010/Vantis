-- Migração 012: Identidade das 5 Marcas, Cadastro Real de Canais YouTube e Prontidão OAuth (Fase 27)

CREATE TABLE IF NOT EXISTS channel_brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL UNIQUE,
    brand_name TEXT NOT NULL,
    editorial_category TEXT NOT NULL,
    legacy_channel_name TEXT NOT NULL,
    youtube_channel_id TEXT,
    youtube_handle TEXT,
    youtube_url TEXT,
    name_availability_status TEXT NOT NULL DEFAULT 'AVAILABILITY_UNVERIFIED',
    channel_status TEXT NOT NULL DEFAULT 'CHANNEL_NOT_CREATED',
    oauth_status TEXT NOT NULL DEFAULT 'OAUTH_DISCONNECTED',
    branding_config_json TEXT DEFAULT '{}',
    editorial_identity_json TEXT DEFAULT '{}',
    pending_actions_json TEXT DEFAULT '[]',
    next_step TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_channel_brands_ch ON channel_brands(channel_id);
