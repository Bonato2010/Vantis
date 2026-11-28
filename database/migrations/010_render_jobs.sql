-- Migração 010: Fila e Auditoria de Renderização Audiovisual (Fase 22)
CREATE TABLE IF NOT EXISTS render_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    checkpoint_stage TEXT DEFAULT 'QUEUED',
    output_mp4_path TEXT,
    file_size_bytes INTEGER DEFAULT 0,
    duration_sec REAL DEFAULT 0.0,
    resolution TEXT,
    video_codec TEXT,
    audio_codec TEXT,
    sha256 TEXT,
    measured_lufs REAL,
    scenes_count INTEGER DEFAULT 0,
    subtitles_count INTEGER DEFAULT 0,
    pending_assets_json TEXT DEFAULT '[]',
    assets_used_json TEXT DEFAULT '[]',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rj_package_status ON render_jobs(package_id, status);
