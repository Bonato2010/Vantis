"""
IAS Test Suite - Fase 2: Orquestração Central, Resiliência de Filas e Concorrência por Canal
Valida:
1. Fila persistente de tarefas, bloqueio de duplicidade e ordenação por prioridade.
2. Limites de concorrência por canal (evitando sobrecarga ou mistura de identidades editoriais).
3. Retentativas com backoff exponencial e recuperação automática de tarefas travadas.
4. Despacho unificado do pipeline de 12 etapas com LangGraph conectando serviços reais.
5. Portão de revisão humana (Portal 2) e retomada para distribuição privada.
6. Endpoints REST da fila e orquestração no FastAPI.
"""
import os
import sys
import tempfile
import unittest
import sqlite3
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.orchestration.central_controller import (
    CentralOperationsController,
    TASK_STATUS_QUEUED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_PAUSED,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_RETRYING,
    TASK_STATUS_CANCELLED
)
from services.orchestration.langgraph_engine import IASOrchestrationEngine
from database.migrate import run_migrations

class TestFase2Orchestration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.temp_dir.name, "test_queue.db")
        # Aplica migrações completas no banco de teste isolado
        run_migrations(db_path=self.test_db)
        self.controller = CentralOperationsController(db_path=self.test_db)
        self.engine = IASOrchestrationEngine(db_path=self.test_db)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_submit_and_duplicate_prevention(self):
        """Valida submissão e bloqueio de tarefas duplicadas enquanto ativas."""
        res1 = self.controller.submit_task(
            task_id="task_dup_100",
            task_type="video_processing",
            payload={"video_id": "vid_01"},
            channel_id=1,
            priority=50
        )
        self.assertTrue(res1["success"])
        self.assertEqual(res1["status"], TASK_STATUS_QUEUED)

        # Tentativa de reenfileirar a mesma tarefa com status ativo deve ser bloqueada
        res2 = self.controller.submit_task(
            task_id="task_dup_100",
            task_type="video_processing",
            payload={"video_id": "vid_01"},
            channel_id=1,
            priority=80
        )
        self.assertFalse(res2["success"])
        self.assertIn("Bloqueio de duplicidade acionado", res2["error"])

    def test_02_priority_ordering(self):
        """Valida que tarefas com maior prioridade são reivindicadas primeiro."""
        self.controller.submit_task("t_low", "cut", {}, channel_id=1, priority=10)
        self.controller.submit_task("t_high", "cut", {}, channel_id=2, priority=90)
        self.controller.submit_task("t_mid", "cut", {}, channel_id=3, priority=50)

        claimed = self.controller.claim_next_task(worker_agent="worker_alpha")
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["task_id"], "t_high")
        self.assertEqual(claimed["priority"], 90)

        claimed2 = self.controller.claim_next_task(worker_agent="worker_beta")
        self.assertIsNotNone(claimed2)
        self.assertEqual(claimed2["task_id"], "t_mid")

    def test_03_channel_concurrency_throttling(self):
        """Valida que o limite de tarefas concorrentes por canal é rigorosamente respeitado."""
        # Canal 1 recebe 3 tarefas; limite configurado é 2
        self.controller.submit_task("ch1_task1", "render", {}, channel_id=1, priority=90)
        self.controller.submit_task("ch1_task2", "render", {}, channel_id=1, priority=80)
        self.controller.submit_task("ch1_task3", "render", {}, channel_id=1, priority=70)
        # Canal 2 recebe 1 tarefa com prioridade menor que ch1_task3
        self.controller.submit_task("ch2_task1", "render", {}, channel_id=2, priority=60)

        # Reivindica tarefa 1 do canal 1
        t1 = self.controller.claim_next_task(worker_agent="w1", max_concurrent_per_channel=2)
        self.assertEqual(t1["task_id"], "ch1_task1")

        # Reivindica tarefa 2 do canal 1 (canal 1 atinge limite de 2 tarefas em RUNNING)
        t2 = self.controller.claim_next_task(worker_agent="w2", max_concurrent_per_channel=2)
        self.assertEqual(t2["task_id"], "ch1_task2")

        # Terceira reivindicação NÃO deve pegar ch1_task3 mesmo tendo prioridade 70 > 60,
        # deve saltar para ch2_task1 para respeitar o limite de 2 do canal 1!
        t3 = self.controller.claim_next_task(worker_agent="w3", max_concurrent_per_channel=2)
        self.assertIsNotNone(t3)
        self.assertEqual(t3["task_id"], "ch2_task1")
        self.assertEqual(t3["channel_id"], 2)

    def test_04_exponential_backoff_and_retry(self):
        """Valida retentativa automática com cálculo de backoff exponencial."""
        self.controller.submit_task("task_retry_test", "transcribe", {}, channel_id=1, max_attempts=3)
        claimed = self.controller.claim_next_task()
        self.assertEqual(claimed["attempts"], 1)

        # Falha 1: deve agendar RETRYING
        fail_res = self.controller.fail_task_with_retry("task_retry_test", "Timeout na conexão Whisper", backoff_seconds=10)
        self.assertEqual(fail_res["status"], TASK_STATUS_RETRYING)
        self.assertIn("Agendada nova tentativa em 10s", fail_res["action"])

        status_info = self.controller.get_task_status("task_retry_test")
        self.assertEqual(status_info["status"], TASK_STATUS_RETRYING)

    def test_05_stalled_task_recovery(self):
        """Valida recuperação automática de tarefas travadas após crash ou desligamento."""
        self.controller.submit_task("task_crashed", "render", {}, channel_id=1)
        self.controller.claim_next_task() # Status vira RUNNING

        # Força started_at para 40 minutos atrás diretamente no SQLite
        old_time = "2026-01-01T00:00:00"
        with sqlite3.connect(self.test_db) as conn:
            conn.execute("UPDATE task_queue SET started_at = ? WHERE task_id = ?", (old_time, "task_crashed"))
            conn.commit()

        recovered_count = self.controller.recover_stalled_tasks(timeout_minutes=30)
        self.assertEqual(recovered_count, 1)

        status_info = self.controller.get_task_status("task_crashed")
        self.assertEqual(status_info["status"], TASK_STATUS_QUEUED)
        self.assertIn("Recuperado automaticamente", status_info["error_log"])

    def test_06_cancellation(self):
        """Valida cancelamento de tarefa na fila."""
        self.controller.submit_task("task_to_cancel", "edit", {}, channel_id=1)
        success = self.controller.cancel_task("task_to_cancel", reason="Solicitação do operador")
        self.assertTrue(success)

        status_info = self.controller.get_task_status("task_to_cancel")
        self.assertEqual(status_info["status"], TASK_STATUS_CANCELLED)

    def test_07_full_workflow_dispatch_and_portal2_approval(self):
        """Valida o fluxo completo de 12 etapas via Central Controller e LangGraph com parada no Portal 2."""
        task_id = "wf_fase2_full_001"
        
        # 1. Despacha fluxo completo
        state = self.controller.dispatch_workflow(
            task_id=task_id,
            target_id="vid_futebol_fase2",
            niche="futebol",
            channel_id=1,
            priority=85
        )

        # Deve pausar na etapa 11 aguardando aprovação humana
        self.assertEqual(state["status"], TASK_STATUS_PAUSED)
        self.assertEqual(state["current_step"], "11_revisao_humana")
        self.assertFalse(state["human_approved"])

        # Verifica sincronização com a task_queue
        q_status = self.controller.get_task_status(task_id)
        self.assertIsNotNone(q_status)
        self.assertEqual(q_status["status"], TASK_STATUS_PAUSED)

        # Valida que serviços reais geraram artefatos no estado
        results = state["step_results"]
        self.assertIn("1_pesquisa_referencias", results)
        self.assertIn("2_catalogacao_videos", results)
        self.assertIn("7_avaliacao_agentes", results)
        self.assertIn("consensus_score", results["7_avaliacao_agentes"])
        self.assertIn("8_geracao_roteiros", results)
        self.assertIn("script", results["8_geracao_roteiros"])
        self.assertIn("9_preparacao_materiais", results)
        self.assertIn("ass_path", results["9_preparacao_materiais"])
        self.assertIn("10_edicao_audiovisual", results)
        self.assertEqual(results["10_edicao_audiovisual"]["render_profile"], "1080x1920_9x16_60fps")

        # 2. Operador concede aprovação humana (Portal 2)
        resumed = self.controller.approve_and_resume_workflow(
            task_id=task_id,
            approval_token="TOKEN_EDITORIAL_DIRECTOR_FASE2"
        )
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed["status"], TASK_STATUS_COMPLETED)
        self.assertEqual(resumed["current_step"], "12_distribuicao")
        self.assertTrue(resumed["human_approved"])
        self.assertEqual(resumed["human_approval_token"], "TOKEN_EDITORIAL_DIRECTOR_FASE2")

        # Valida etapa 12 (distribuição com segurança estrita: privacidade privada)
        dist_result = resumed["step_results"]["12_distribuicao"]
        self.assertEqual(dist_result["privacy_status"], "private")
        self.assertTrue(dist_result["publication_manifest_ready"])

        # Verifica sincronização final com a task_queue
        final_q_status = self.controller.get_task_status(task_id)
        self.assertEqual(final_q_status["status"], TASK_STATUS_COMPLETED)
        self.assertIsNotNone(final_q_status["completed_at"])

if __name__ == "__main__":
    unittest.main()
