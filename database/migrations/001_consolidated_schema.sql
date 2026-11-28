-- ====================================================================
-- IAS DATABASE MIGRATION 001: CONSOLIDATED ENTERPRISE SCHEMA v3.0
-- Suporte a 20 Canais Independentes, Google Drive 5 TB, Memória
-- Semântica, Checkpoints LangGraph, Governança e Auditoria.
-- ====================================================================

-- 1. Categorias e Nichos Oficiais
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Os 20 Canais YouTube Shorts Independentes
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_number INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    youtube_channel_id TEXT,
    niche TEXT NOT NULL,
    subniche TEXT,
    target_audience TEXT,
    language TEXT DEFAULT 'pt-BR',
    country TEXT DEFAULT 'BR',
    visual_identity TEXT,
    editing_style TEXT,
    communication_tone TEXT,
    posting_frequency TEXT DEFAULT '2_por_dia',
    goals TEXT,
    editorial_strategy TEXT,
    oauth_refresh_token TEXT,
    gdrive_folder_id TEXT,
    daily_upload_limit INTEGER DEFAULT 3,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Configurações Operacionais Específicas por Canal
CREATE TABLE IF NOT EXISTS channel_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    setting_key TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(channel_id, setting_key)
);

-- 4. Perfis Editoriais e Arquétipos de Comunicação
CREATE TABLE IF NOT EXISTS editorial_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    archetype TEXT NOT NULL,
    tone TEXT NOT NULL,
    target_niches TEXT,
    hook_style TEXT,
    pacing_style TEXT,
    visual_style TEXT,
    catchphrases TEXT,
    prompt_modifiers TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Fila de Oportunidades Descobertas (Portal de Aprovação 1)
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id TEXT UNIQUE NOT NULL,
    source_platform TEXT DEFAULT 'youtube_shorts',
    source_url TEXT NOT NULL,
    niche TEXT NOT NULL,
    subniche TEXT,
    country TEXT DEFAULT 'BR',
    language TEXT DEFAULT 'pt-BR',
    title_concept TEXT NOT NULL,
    context_description TEXT,
    popularity_evidence TEXT,
    competition_level TEXT DEFAULT 'medio',
    monetization_potential TEXT DEFAULT 'medio',
    confidence_score REAL DEFAULT 50.0,
    recommended_channel_id INTEGER REFERENCES channels(id),
    technical_justification TEXT,
    status TEXT DEFAULT 'pending_review', -- pending_review, approved, rejected, needs_more_research
    reviewed_by TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Biblioteca de Vídeos de Referência e Estudo (Suporte a 200.000+ Shorts)
CREATE TABLE IF NOT EXISTS video_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER REFERENCES categories(id),
    channel_id INTEGER REFERENCES channels(id),
    video_id TEXT UNIQUE,
    youtube_id TEXT,
    original_url TEXT,
    url TEXT DEFAULT '',
    title TEXT,
    author TEXT,
    channel_title TEXT,
    views_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    engagement_rate REAL DEFAULT 0.0,
    duration_seconds REAL DEFAULT 0.0,
    hook_transcript TEXT,
    full_transcript TEXT,
    transcript_text TEXT,
    transcript_word_timestamps TEXT,
    niche TEXT,
    subcategory TEXT,
    pacing_bpm REAL DEFAULT 0.0,
    retention_score REAL DEFAULT 0.0,
    format_features TEXT,
    analysis_notes TEXT,
    availability_status TEXT DEFAULT 'active',
    usage_permission TEXT DEFAULT 'reference_only',
    gdrive_file_id TEXT,
    gdrive_backup_id TEXT,
    tags TEXT,
    collected_at TIMESTAMP,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Padrões de Sucesso e Fórmulas de Conteúdo
CREATE TABLE IF NOT EXISTS content_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER REFERENCES categories(id),
    channel_id INTEGER REFERENCES channels(id),
    pattern_type TEXT NOT NULL,
    archetype TEXT,
    title TEXT NOT NULL,
    hook_type TEXT,
    hook_duration_seconds REAL,
    hook_formula TEXT,
    structure_template TEXT NOT NULL,
    narrative_structure TEXT,
    editing_pace TEXT,
    retention_elements TEXT,
    ideal_duration_seconds REAL,
    typical_retention_rate REAL,
    performance_tier TEXT,
    sample_video_ids TEXT,
    source_reference_id INTEGER REFERENCES video_references(id),
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Grafo de Conhecimento Central
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_slug TEXT,
    channel_id INTEGER REFERENCES channels(id),
    node_type TEXT NOT NULL,
    title TEXT NOT NULL,
    pattern_data TEXT NOT NULL,
    sample_count INTEGER DEFAULT 1,
    effectiveness_score REAL DEFAULT 50.0,
    derived_from_references TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Roteiros Originais e Variantes Anti-Duplicação
CREATE TABLE IF NOT EXISTS scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER REFERENCES channels(id),
    category_id INTEGER REFERENCES categories(id),
    opportunity_id INTEGER REFERENCES opportunities(id),
    editorial_profile_id INTEGER REFERENCES editorial_profiles(id),
    title TEXT NOT NULL,
    archetype TEXT,
    hook TEXT,
    hook_3s TEXT NOT NULL,
    core_narrative TEXT,
    cta TEXT,
    full_script TEXT NOT NULL,
    full_script_json TEXT,
    visual_cues TEXT,
    audio_cues TEXT,
    target_duration REAL,
    recommended_duration REAL,
    editing_style TEXT,
    status TEXT DEFAULT 'draft',
    human_approved INTEGER DEFAULT 0,
    approval_notes TEXT,
    approved_by TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Pipeline de Produção Audiovisual (Drive 5 TB & FFmpeg)
CREATE TABLE IF NOT EXISTS production_pipeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER REFERENCES scripts(id),
    channel_id INTEGER REFERENCES channels(id),
    current_stage TEXT DEFAULT 'queue',
    progress_percent INTEGER DEFAULT 0,
    local_temp_file TEXT,
    gdrive_file_id TEXT,
    gdrive_web_link TEXT,
    rendered_at TIMESTAMP,
    final_duration REAL,
    error_log TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Episódios de Podcasts Longos Ingeridos
CREATE TABLE IF NOT EXISTS podcast_episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source_url TEXT,
    channel_name TEXT,
    duration_seconds REAL,
    audio_path TEXT,
    transcript_path TEXT,
    status TEXT DEFAULT 'ingested',
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Cortes Candidatos de Podcasts (Avaliados pelos Agentes)
CREATE TABLE IF NOT EXISTS podcast_candidate_cuts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER REFERENCES podcast_episodes(id),
    channel_id INTEGER REFERENCES channels(id),
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    transcript TEXT NOT NULL,
    theme TEXT,
    target_audience TEXT,
    content_type TEXT,
    hook_suggested TEXT,
    justification TEXT,
    narrative_potential REAL,
    editing_strategy TEXT,
    title_suggestion TEXT,
    caption_suggestion TEXT,
    quality_score INTEGER DEFAULT 0,
    confidence_score REAL DEFAULT 0.0,
    agent_evaluations TEXT,
    director_decision TEXT DEFAULT 'pending_review',
    production_id INTEGER REFERENCES production_pipeline(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. Decisões e Deliberações dos Agentes Especializados
CREATE TABLE IF NOT EXISTS agent_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    channel_id INTEGER REFERENCES channels(id),
    target_type TEXT NOT NULL,
    target_id INTEGER,
    input_data TEXT,
    analysis TEXT,
    score INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0.0,
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 14. Laboratório de Experimentos A/B
CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    variable_type TEXT NOT NULL,
    control_variant TEXT,
    test_variant TEXT,
    channel_id INTEGER REFERENCES channels(id),
    script_ids TEXT,
    metrics_control TEXT,
    metrics_test TEXT,
    status TEXT DEFAULT 'draft',
    winner TEXT,
    insights_learned TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    concluded_at TIMESTAMP
);

-- 15. Checkpoints de Orquestração LangGraph (12 Etapas)
CREATE TABLE IF NOT EXISTS workflow_checkpoints (
    task_id TEXT PRIMARY KEY,
    target_id TEXT,
    channel_id INTEGER REFERENCES channels(id),
    niche TEXT,
    current_step TEXT NOT NULL,
    status TEXT NOT NULL,
    state_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 16. Memória Semântica Vetorial (pgvector / SQLite fallback)
CREATE TABLE IF NOT EXISTS semantic_vectors (
    id TEXT PRIMARY KEY,
    category TEXT,
    channel_id INTEGER REFERENCES channels(id),
    text_content TEXT NOT NULL,
    vector_blob BLOB NOT NULL,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 17. Telemetria de Uso de Modelos e Custos de IA (LiteLLM)
CREATE TABLE IF NOT EXISTS model_usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT,
    channel_id INTEGER REFERENCES channels(id),
    model_used TEXT NOT NULL,
    provider TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0.0,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 18. Máquina de Estados de Governança de Vídeos (yt-dlp)
CREATE TABLE IF NOT EXISTS video_lifecycle (
    video_id TEXT PRIMARY KEY,
    title TEXT,
    channel_name TEXT,
    duration_sec REAL,
    published_date TEXT,
    original_url TEXT,
    status TEXT DEFAULT 'catalogado',
    has_subtitles INTEGER DEFAULT 0,
    license_notes TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 19. Publicações no YouTube (Portal de Aprovação 2 - Human-in-the-Loop)
CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_id INTEGER REFERENCES production_pipeline(id),
    channel_id INTEGER REFERENCES channels(id),
    youtube_video_id TEXT,
    published_url TEXT,
    scheduled_for TIMESTAMP,
    published_at TIMESTAMP,
    title TEXT NOT NULL,
    description TEXT,
    tags TEXT,
    privacy_status TEXT DEFAULT 'private',
    status TEXT DEFAULT 'scheduled',
    human_approval_token TEXT,
    approved_by TEXT,
    approved_at TIMESTAMP,
    gdrive_backup_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 20. Métricas de Desempenho Pós-Publicação
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_id INTEGER REFERENCES publications(id),
    channel_id INTEGER REFERENCES channels(id),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    estimated_retention_rate REAL,
    insights TEXT
);

-- 21. Registros Financeiros Informativos (Custos e Receitas)
CREATE TABLE IF NOT EXISTS financial_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER REFERENCES channels(id),
    log_type TEXT NOT NULL, -- 'expense', 'revenue', 'avoided_cost'
    category TEXT NOT NULL,  -- 'ai_tokens', 'infrastructure', 'adsense', 'sponsor'
    amount_usd REAL NOT NULL DEFAULT 0.0,
    description TEXT,
    metadata TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 22. Trilha de Auditoria Mandatória e Logs de Segurança
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    channel_id INTEGER REFERENCES channels(id),
    details TEXT,
    actor TEXT DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================================
-- ÍNDICES DE PERFORMANCE E INTEGRIDADE
-- ====================================================================
CREATE INDEX IF NOT EXISTS idx_video_references_video_id ON video_references(video_id);
CREATE INDEX IF NOT EXISTS idx_video_references_category ON video_references(category_id);
CREATE INDEX IF NOT EXISTS idx_scripts_channel ON scripts(channel_id);
CREATE INDEX IF NOT EXISTS idx_scripts_status ON scripts(status);
CREATE INDEX IF NOT EXISTS idx_production_channel ON production_pipeline(channel_id);
CREATE INDEX IF NOT EXISTS idx_publications_channel ON publications(channel_id);
CREATE INDEX IF NOT EXISTS idx_semantic_vectors_category ON semantic_vectors(category);
CREATE INDEX IF NOT EXISTS idx_workflow_checkpoints_status ON workflow_checkpoints(status);
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opportunities_channel ON opportunities(recommended_channel_id);
