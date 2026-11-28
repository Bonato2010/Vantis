-- ====================================================================
-- IAS / VANTIS MIGRATION 007: AUDIOVISUAL PRODUCTION PIPELINE
-- Rastreabilidade de 10 etapas, proveniência de direitos autorais,
-- telemetria técnica, controle de qualidade (QC) e auditoria de renderização.
-- ====================================================================

CREATE TABLE IF NOT EXISTS audiovisual_pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    channel_id INTEGER NOT NULL REFERENCES channels(id),
    source_media_path TEXT,
    output_media_path TEXT,
    thumbnail_path TEXT,
    source_url TEXT,
    source_author TEXT,
    source_license TEXT DEFAULT 'fair_use_transformative',
    transformative_type TEXT DEFAULT 'educational_analysis',
    status TEXT DEFAULT 'PENDING',
    current_stage TEXT DEFAULT 'INITIALIZED',
    duration_sec REAL DEFAULT 0.0,
    resolution TEXT DEFAULT '1080x1920',
    loudness_lufs REAL DEFAULT -14.0,
    qc_passed INTEGER DEFAULT 0,
    qc_score INTEGER DEFAULT 0,
    qc_details_json TEXT,
    stage_timings_json TEXT,
    metadata_json TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_av_pipeline_task_id ON audiovisual_pipeline_runs(task_id);
CREATE INDEX IF NOT EXISTS idx_av_pipeline_channel_id ON audiovisual_pipeline_runs(channel_id);
CREATE INDEX IF NOT EXISTS idx_av_pipeline_status ON audiovisual_pipeline_runs(status);
