-- ====================================================================
-- Migração 006: Arquitetura de Agentes Inteligentes VANTIS
-- Cria tabela de auditoria operacional de execução de agentes autônomos
-- ====================================================================

CREATE TABLE IF NOT EXISTS agent_execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    department TEXT NOT NULL,
    task_id TEXT,
    channel_id INTEGER,
    status TEXT NOT NULL, -- 'IDLE', 'RUNNING', 'SUCCESS', 'ERROR', 'PAUSED'
    inputs_json TEXT,
    outputs_json TEXT,
    execution_time_ms REAL DEFAULT 0.0,
    error_message TEXT,
    success_criteria_met INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_id ON agent_execution_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_task_id ON agent_execution_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_channel_id ON agent_execution_logs(channel_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_status ON agent_execution_logs(status);
