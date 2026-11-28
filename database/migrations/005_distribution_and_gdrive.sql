-- Migration 005: Distribuição Segura, Google Drive & Publicação Privada
-- Garante índices para consultas rápidas por canal e status na tabela 'publications'.

CREATE INDEX IF NOT EXISTS idx_publications_channel ON publications(channel_id);
CREATE INDEX IF NOT EXISTS idx_publications_status ON publications(status);
