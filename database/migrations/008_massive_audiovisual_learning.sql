-- ====================================================================
-- Migração 008: Sistema de Aprendizado Audiovisual Massivo (7.000+ Vídeos)
-- ====================================================================

-- 1. Catálogo Inteligente da Biblioteca Audiovisual
CREATE TABLE IF NOT EXISTS audiovisual_library (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    title TEXT NOT NULL,
    creator TEXT,
    channel_id_source TEXT,
    published_at TIMESTAMP,
    duration_seconds REAL DEFAULT 0.0,
    language TEXT DEFAULT 'pt-BR',
    niche TEXT NOT NULL,
    subcategory TEXT,
    format_style TEXT,
    access_condition TEXT DEFAULT 'public_reference',
    views_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    engagement_ratio REAL DEFAULT 0.0,
    processing_state TEXT NOT NULL DEFAULT 'discovered',
    -- Estados permitidos: discovered, metadata_processed, transcript_processed, audio_processed, visual_processed, fully_analyzed, rejected, error
    last_analyzed_at TIMESTAMP,
    content_fingerprint TEXT,
    learning_report_id INTEGER,
    discard_reason TEXT,
    error_message TEXT,
    raw_metadata TEXT,
    analysis_payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_avl_source_id ON audiovisual_library(source_id);
CREATE INDEX IF NOT EXISTS idx_avl_state ON audiovisual_library(processing_state);
CREATE INDEX IF NOT EXISTS idx_avl_niche ON audiovisual_library(niche);
CREATE INDEX IF NOT EXISTS idx_avl_creator ON audiovisual_library(creator);
CREATE INDEX IF NOT EXISTS idx_avl_fingerprint ON audiovisual_library(content_fingerprint);

-- 2. Biblioteca de Conhecimento Editorial (Padrões, Princípios e Anti-patterns com Evidências)
CREATE TABLE IF NOT EXISTS editorial_knowledge_library (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    niche TEXT DEFAULT 'universal',
    target_channel_id INTEGER REFERENCES channels(id),
    knowledge_type TEXT NOT NULL,
    -- Tipos: hook_formula, narrative_structure, editing_principle, audio_technique, anti_pattern, topic_opportunity
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    classification TEXT NOT NULL DEFAULT 'evidence_based_conclusion',
    -- Classificações: observation, hypothesis, evidence_based_conclusion, experimental_recommendation
    confidence_score REAL DEFAULT 0.85,
    evidence_video_ids TEXT NOT NULL DEFAULT '[]', -- JSON array com os IDs dos vídeos que sustentam a conclusão
    evidence_count INTEGER DEFAULT 1,
    actionable_recommendation TEXT,
    anti_pattern_warning TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ekl_niche ON editorial_knowledge_library(niche);
CREATE INDEX IF NOT EXISTS idx_ekl_channel ON editorial_knowledge_library(target_channel_id);
CREATE INDEX IF NOT EXISTS idx_ekl_type ON editorial_knowledge_library(knowledge_type);

-- 3. Experimentos Editoriais Baseados em Evidências
CREATE TABLE IF NOT EXISTS editorial_experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL REFERENCES channels(id),
    title TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    evidence_motivation TEXT NOT NULL,
    knowledge_ref_id INTEGER REFERENCES editorial_knowledge_library(id),
    content_variation TEXT NOT NULL,
    evaluation_metric TEXT NOT NULL DEFAULT 'engagement_ratio',
    status TEXT NOT NULL DEFAULT 'PLANNED',
    -- Status: PLANNED, RUNNING, EVALUATED, ARCHIVED
    result_data TEXT DEFAULT '{}',
    conclusion TEXT,
    memory_updated BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ee_channel ON editorial_experiments(channel_id);
CREATE INDEX IF NOT EXISTS idx_ee_status ON editorial_experiments(status);

-- 4. Checkpoints de Processamento em Lotes (Suporte a Retomada e Metas Configuráveis)
CREATE TABLE IF NOT EXISTS learning_batch_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT UNIQUE NOT NULL,
    target_goal INTEGER DEFAULT 7000,
    processed_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_processed_source_id TEXT,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    -- Status: RUNNING, PAUSED, COMPLETED, FAILED
    config_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
