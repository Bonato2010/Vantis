-- ====================================================================
-- IAS DATABASE MIGRATION 002: TASK QUEUE & RESILIENT CONTROL TABLE
-- Fila persistente de tarefas, controle de concorrência, retentativas
-- com backoff e recuperação após reinicialização.
-- ====================================================================

CREATE TABLE IF NOT EXISTS task_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    task_type TEXT NOT NULL,
    channel_id INTEGER REFERENCES channels(id),
    priority INTEGER DEFAULT 50, -- 1 a 100 (100 = prioridade máxima)
    status TEXT DEFAULT 'QUEUED', -- QUEUED, RUNNING, PAUSED_FOR_REVIEW, COMPLETED, FAILED, RETRYING, CANCELLED
    assigned_agent TEXT,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    payload_json TEXT NOT NULL,
    result_json TEXT,
    error_log TEXT,
    retry_after TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_queue_status_priority ON task_queue(status, priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_task_queue_channel ON task_queue(channel_id);
CREATE INDEX IF NOT EXISTS idx_task_queue_task_id ON task_queue(task_id);
