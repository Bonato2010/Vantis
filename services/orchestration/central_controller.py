"""
IAS Central Controller & Resilient Task Queue
Controlador central de operações, gerenciamento de concorrência por canal, priorização,
filas persistentes, recuperação de falhas, retentativas com backoff exponencial
e despacho unificado para o motor LangGraph.
"""
import os
import sys
import json
import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

logger = logging.getLogger("IAS.CentralController")

TASK_STATUS_QUEUED = "QUEUED"
TASK_STATUS_RUNNING = "RUNNING"
TASK_STATUS_PAUSED = "PAUSED_FOR_REVIEW"
TASK_STATUS_COMPLETED = "COMPLETED"
TASK_STATUS_FAILED = "FAILED"
TASK_STATUS_RETRYING = "RETRYING"
TASK_STATUS_CANCELLED = "CANCELLED"

class CentralOperationsController:
    """Controlador central de operações da empresa de mídia automatizada."""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            self.db_path = str(BASE_DIR / "database" / "shorts_central.db")
        else:
            self.db_path = db_path
        self._init_queue_table()

    def _init_queue_table(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    task_type TEXT NOT NULL,
                    channel_id INTEGER,
                    priority INTEGER DEFAULT 50,
                    status TEXT DEFAULT 'QUEUED',
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
                )
            """)
            conn.commit()

    def submit_task(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        channel_id: Optional[int] = None,
        priority: int = 50,
        max_attempts: int = 3,
        assigned_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submete uma nova tarefa para a fila persistente com proteção contra duplicidade."""
        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status FROM task_queue WHERE task_id = ?
            """, (task_id,))
            existing = cursor.fetchone()
            if existing:
                if existing[0] in (TASK_STATUS_QUEUED, TASK_STATUS_RUNNING, TASK_STATUS_PAUSED):
                    return {
                        "success": False,
                        "error": f"Tarefa '{task_id}' já está ativa com status '{existing[0]}'. Bloqueio de duplicidade acionado.",
                        "task_id": task_id
                    }

            cursor.execute("""
                INSERT OR REPLACE INTO task_queue 
                (task_id, task_type, channel_id, priority, status, assigned_agent, attempts, max_attempts, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            """, (task_id, task_type, channel_id, priority, TASK_STATUS_QUEUED, assigned_agent, max_attempts, json.dumps(payload, ensure_ascii=False), now_iso, now_iso))
            conn.commit()

        logger.info(f"[CentralController] Tarefa submetida: {task_id} (Tipo: {task_type}, Canal: {channel_id}, Prioridade: {priority})")
        return {
            "success": True,
            "task_id": task_id,
            "task_type": task_type,
            "channel_id": channel_id,
            "status": TASK_STATUS_QUEUED,
            "priority": priority
        }

    def claim_next_task(
        self,
        worker_agent: str = "general_worker",
        channel_id: Optional[int] = None,
        max_concurrent_per_channel: int = 2
    ) -> Optional[Dict[str, Any]]:
        """Recupera atomicamente a próxima tarefa de maior prioridade disponível respeitando limites de concorrência por canal."""
        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Identifica carga em execução por canal
            cursor.execute("SELECT channel_id, COUNT(*) FROM task_queue WHERE status = ? GROUP BY channel_id", (TASK_STATUS_RUNNING,))
            channel_running_counts = {r[0]: r[1] for r in cursor.fetchall() if r[0] is not None}

            query = """
                SELECT id, task_id, task_type, channel_id, priority, attempts, max_attempts, payload_json
                FROM task_queue
                WHERE (status = ? OR (status = ? AND (retry_after IS NULL OR retry_after <= ?)))
            """
            params = [TASK_STATUS_QUEUED, TASK_STATUS_RETRYING, now_iso]
            if channel_id is not None:
                query += " AND channel_id = ?"
                params.append(channel_id)
            query += " ORDER BY priority DESC, created_at ASC LIMIT 50"

            cursor.execute(query, params)
            candidates = cursor.fetchall()
            if not candidates:
                return None

            for row in candidates:
                t_db_id, task_id, task_type, ch_id, priority, attempts, max_attempts, payload_raw = row

                # Verifica concorrência do canal
                if ch_id is not None and channel_running_counts.get(ch_id, 0) >= max_concurrent_per_channel:
                    continue

                # Atualização atômica para RUNNING
                cursor.execute("""
                    UPDATE task_queue
                    SET status = ?, assigned_agent = ?, attempts = attempts + 1, started_at = ?, updated_at = ?
                    WHERE id = ? AND (status = ? OR status = ?)
                """, (TASK_STATUS_RUNNING, worker_agent, now_iso, now_iso, t_db_id, TASK_STATUS_QUEUED, TASK_STATUS_RETRYING))
                conn.commit()

                if cursor.rowcount > 0:
                    return {
                        "id": t_db_id,
                        "task_id": task_id,
                        "task_type": task_type,
                        "channel_id": ch_id,
                        "priority": priority,
                        "attempts": attempts + 1,
                        "max_attempts": max_attempts,
                        "payload": json.loads(payload_raw) if payload_raw else {}
                    }

            return None

    def complete_task(self, task_id: str, result: Dict[str, Any]) -> bool:
        """Marca a tarefa como concluída com sucesso e registra o resultado final."""
        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = ?, result_json = ?, completed_at = ?, updated_at = ?
                WHERE task_id = ?
            """, (TASK_STATUS_COMPLETED, json.dumps(result, ensure_ascii=False), now_iso, now_iso, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def pause_task_for_review(self, task_id: str, step_details: Dict[str, Any]) -> bool:
        """Pausa a tarefa aguardando aprovação humana expressa (Portal 1 ou 2)."""
        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = ?, result_json = ?, updated_at = ?
                WHERE task_id = ?
            """, (TASK_STATUS_PAUSED, json.dumps(step_details, ensure_ascii=False), now_iso, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def fail_task_with_retry(self, task_id: str, error_message: str, backoff_seconds: int = 30, permanent: bool = False) -> Dict[str, Any]:
        """Registra falha com retentativa exponencial ou marcação imediata de falha permanente."""
        now = datetime.datetime.now()
        now_iso = now.isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT attempts, max_attempts FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": "Tarefa não encontrada"}

            attempts, max_attempts = row
            if permanent:
                retry_time = None
                new_status = TASK_STATUS_FAILED
                action = "Falha permanente identificada. Reintentos cancelados."
            elif attempts < max_attempts:
                # Calcula backoff exponencial: 30s, 60s, 120s...
                delay = backoff_seconds * (2 ** max(0, attempts - 1))
                retry_time = (now + datetime.timedelta(seconds=delay)).isoformat()
                new_status = TASK_STATUS_RETRYING
                action = f"Agendada nova tentativa em {delay}s (Tentativa {attempts}/{max_attempts})"
            else:
                retry_time = None
                new_status = TASK_STATUS_FAILED
                action = "Tentativas máximas esgotadas. Escalonado para intervenção humana."

            cursor.execute("""
                UPDATE task_queue
                SET status = ?, error_log = ?, retry_after = ?, updated_at = ?
                WHERE task_id = ?
            """, (new_status, error_message, retry_time, now_iso, task_id))
            conn.commit()

        logger.warning(f"[CentralController] Tarefa {task_id} falhou: {error_message}. Ação: {action}")
        return {
            "success": True,
            "task_id": task_id,
            "status": new_status,
            "permanent_failure": permanent,
            "attempts": attempts,
            "max_attempts": max_attempts,
            "action": action
        }

    def cancel_task(self, task_id: str, reason: str = "Cancelado pelo operador") -> bool:
        """Cancela uma tarefa na fila."""
        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = ?, error_log = ?, updated_at = ?
                WHERE task_id = ?
            """, (TASK_STATUS_CANCELLED, reason, now_iso, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def recover_stalled_tasks(self, timeout_minutes: int = 30) -> int:
        """Recupera tarefas travadas em RUNNING após queda ou reinicialização inesperada."""
        threshold = (datetime.datetime.now() - datetime.timedelta(minutes=timeout_minutes)).isoformat()
        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = ?, error_log = 'Recuperado automaticamente após inatividade/crash', updated_at = ?
                WHERE status = ? AND started_at < ?
            """, (TASK_STATUS_QUEUED, now_iso, TASK_STATUS_RUNNING, threshold))
            conn.commit()
            recovered = cursor.rowcount
            if recovered > 0:
                logger.info(f"[CentralController] {recovered} tarefas travadas foram recuperadas e reenfileiradas.")
            return recovered

    def list_queue(self, status: Optional[str] = None, channel_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista tarefas na fila com filtros e prioridade decrescente."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = "SELECT task_id, task_type, channel_id, priority, status, assigned_agent, attempts, max_attempts, error_log, created_at, updated_at FROM task_queue WHERE 1=1"
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if channel_id:
                query += " AND channel_id = ?"
                params.append(channel_id)
            query += " ORDER BY priority DESC, created_at ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    "task_id": r[0],
                    "task_type": r[1],
                    "channel_id": r[2],
                    "priority": r[3],
                    "status": r[4],
                    "assigned_agent": r[5],
                    "attempts": r[6],
                    "max_attempts": r[7],
                    "error_log": r[8],
                    "created_at": r[9],
                    "updated_at": r[10]
                }
                for r in rows
            ]

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Recupera o estado completo e detalhado de uma tarefa específica."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT task_id, task_type, channel_id, priority, status, assigned_agent, 
                       attempts, max_attempts, payload_json, result_json, error_log, started_at, completed_at, updated_at
                FROM task_queue WHERE task_id = ?
            """, (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "task_id": row[0],
                "task_type": row[1],
                "channel_id": row[2],
                "priority": row[3],
                "status": row[4],
                "assigned_agent": row[5],
                "attempts": row[6],
                "max_attempts": row[7],
                "payload": json.loads(row[8]) if row[8] else {},
                "result": json.loads(row[9]) if row[9] else None,
                "error_log": row[10],
                "started_at": row[11],
                "completed_at": row[12],
                "updated_at": row[13]
            }

    def dispatch_workflow(
        self,
        task_id: str,
        target_id: str,
        niche: str = "futebol",
        channel_id: Optional[int] = 1,
        priority: int = 50,
        assigned_agent: str = "central_orchestrator",
        pipeline_mode: str = "legacy_12"
    ) -> Dict[str, Any]:
        """
        Submete e despacha a execução de um pipeline completo (VANTIS 17 etapas ou 12 etapas legadas)
        via LangGraph, sincronizando o ciclo de vida na task_queue.
        """
        payload = {
            "target_id": target_id,
            "niche": niche,
            "channel_id": channel_id,
            "pipeline_mode": pipeline_mode
        }
        submit_res = self.submit_task(
            task_id=task_id,
            task_type="full_production_workflow",
            payload=payload,
            channel_id=channel_id,
            priority=priority,
            assigned_agent=assigned_agent
        )
        if not submit_res.get("success") and "já está ativa" in submit_res.get("error", ""):
            status_data = self.get_task_status(task_id)
            return {
                "task_id": task_id,
                "status": status_data["status"] if status_data else "UNKNOWN",
                "error": submit_res.get("error")
            }

        # Atualiza status na fila para RUNNING
        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE task_queue 
                SET status = ?, assigned_agent = ?, started_at = ?, updated_at = ?
                WHERE task_id = ?
            """, (TASK_STATUS_RUNNING, assigned_agent, now_iso, now_iso, task_id))
            conn.commit()

        # Executa motor LangGraph com integração real
        from services.orchestration.langgraph_engine import IASOrchestrationEngine
        engine = IASOrchestrationEngine(db_path=self.db_path)
        state = engine.start_workflow(
            task_id=task_id,
            target_id=target_id,
            niche=niche,
            channel_id=channel_id,
            pipeline_mode=pipeline_mode
        )

        # Sincroniza estado resultante com a task_queue
        if state.get("status") == "PAUSED_FOR_REVIEW":
            self.pause_task_for_review(task_id, state)
        elif state.get("status") == "COMPLETED":
            self.complete_task(task_id, state)
        elif state.get("errors"):
            self.fail_task_with_retry(task_id, "; ".join(state["errors"]))

        return state

    def approve_and_resume_workflow(
        self,
        task_id: str,
        approval_token: str = "TOKEN_HUMAN_DIRECTOR_01"
    ) -> Optional[Dict[str, Any]]:
        """
        Aprova a etapa 11 (revisão humana expressa) e conclui a distribuição (etapa 12),
        atualizando o status na fila para COMPLETED.
        """
        from services.orchestration.langgraph_engine import IASOrchestrationEngine
        engine = IASOrchestrationEngine(db_path=self.db_path)
        
        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE task_queue 
                SET status = ?, updated_at = ?
                WHERE task_id = ?
            """, (TASK_STATUS_RUNNING, now_iso, task_id))
            conn.commit()

        state = engine.approve_and_resume(task_id, approval_token=approval_token)
        if state and state.get("status") == "COMPLETED":
            self.complete_task(task_id, state)
        return state
