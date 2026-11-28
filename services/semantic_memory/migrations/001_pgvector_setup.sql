-- ====================================================================
-- IAS Semantic Memory - pgvector Migration Script
-- Suporte a embeddings vetoriais de 384 dimensões (Sentence-Transformers)
-- ====================================================================

-- 1. Habilita a extensão pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Tabela de Transcrições Semânticas
CREATE TABLE IF NOT EXISTS semantic_transcriptions (
    id SERIAL PRIMARY KEY,
    doc_id TEXT UNIQUE NOT NULL,
    video_id TEXT,
    title TEXT,
    transcript TEXT NOT NULL,
    category TEXT,
    embedding vector(384) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índice HNSW de alta performance para busca de cosseno
CREATE INDEX IF NOT EXISTS idx_semantic_transcriptions_embedding 
ON semantic_transcriptions USING hnsw (embedding vector_cosine_ops);

-- 3. Tabela de Ganchos Narrativos (0-3 segundos)
CREATE TABLE IF NOT EXISTS semantic_hooks (
    id SERIAL PRIMARY KEY,
    hook_id TEXT UNIQUE NOT NULL,
    hook_text TEXT NOT NULL,
    niche TEXT,
    retention_score FLOAT,
    embedding vector(384) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_semantic_hooks_embedding 
ON semantic_hooks USING hnsw (embedding vector_cosine_ops);

-- 4. Tabela de Padrões e Estruturas de Conteúdo
CREATE TABLE IF NOT EXISTS semantic_patterns (
    id SERIAL PRIMARY KEY,
    pattern_id TEXT UNIQUE NOT NULL,
    archetype TEXT NOT NULL,
    structure_template TEXT NOT NULL,
    ideal_duration_seconds INT,
    embedding vector(384) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_semantic_patterns_embedding 
ON semantic_patterns USING hnsw (embedding vector_cosine_ops);
