-- ====================================================================
-- IAS DATABASE MIGRATION 004: DISCOVERY ENGINE & PORTAL 1 GOVERNANCE
-- Ajuste da tabela de oportunidades para governança humana de pautas,
-- rastreabilidade de direitos e indexação semântica de ganchos reais.
-- ====================================================================

-- 1. Garante que a tabela de oportunidades tenha os campos de revisão e rejeição
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
    popularity_evidence TEXT, -- JSON com views, likes, velocidade
    competition_level TEXT DEFAULT 'medium',
    monetization_potential TEXT DEFAULT 'high',
    confidence_score REAL DEFAULT 80.0,
    recommended_channel_id INTEGER REFERENCES channels(id),
    technical_justification TEXT,
    status TEXT DEFAULT 'PENDING_REVIEW', -- PENDING_REVIEW, APPROVED, REJECTED
    rejection_reason TEXT,
    rejection_category TEXT, -- direitos_autorais, saturado, fora_da_persona, baixa_qualidade, sensacionalismo
    reviewed_by TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices de consulta rápida
CREATE INDEX IF NOT EXISTS idx_opportunities_status_channel ON opportunities(status, recommended_channel_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_niche ON opportunities(niche);
CREATE INDEX IF NOT EXISTS idx_opportunities_confidence ON opportunities(confidence_score DESC);

-- 2. Atualiza máquina de estados no ciclo de vida de vídeos para incluir status 'descoberto'
-- Garante campo original_url e license_notes
CREATE INDEX IF NOT EXISTS idx_video_lifecycle_status ON video_lifecycle(status);

-- 3. Garante que semantic_vectors utilize id TEXT para compatibilidade com VectorMemoryService
CREATE TABLE IF NOT EXISTS semantic_vectors_v2 (
    id TEXT PRIMARY KEY,
    category TEXT,
    channel_id INTEGER REFERENCES channels(id),
    text_content TEXT NOT NULL,
    vector_blob BLOB NOT NULL,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO semantic_vectors_v2 (id, category, channel_id, text_content, vector_blob, metadata_json, created_at)
SELECT CAST(id AS TEXT), category, channel_id, text_content, vector_blob, metadata_json, created_at FROM semantic_vectors;
DROP TABLE IF EXISTS semantic_vectors;
ALTER TABLE semantic_vectors_v2 RENAME TO semantic_vectors;
CREATE INDEX IF NOT EXISTS idx_semantic_vectors_category ON semantic_vectors(category);
CREATE INDEX IF NOT EXISTS idx_semantic_vectors_channel ON semantic_vectors(channel_id);
