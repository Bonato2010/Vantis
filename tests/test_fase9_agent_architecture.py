"""
Testes de Integração e Verificação — Fase 9: Arquitetura de Agentes Inteligentes VANTIS
Valida o catálogo de agentes, contratos Pydantic, máquina de estados, persistência SQLite,
isolamento por canal, trava de custo $0.00, segurança no YouTube e orquestração LangGraph.
"""
import unittest
import os
import sys
import json
import sqlite3
import tempfile
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.agent_registry import AgentRegistry
from agents.base_vantis_agent import AgentState, AgentTaskContext, AgentExecutionResult
from agents.opportunity_research_agent import OpportunityResearchAgent
from agents.trend_analysis_agent import TrendAnalysisAgent
from agents.editorial_planning_agent import EditorialPlanningAgent
from agents.scriptwriting_agent import ScriptwritingAgent
from agents.audiovisual_analysis_agent import AudiovisualAnalysisAgent
from agents.transcription_agent import TranscriptionAgent
from agents.media_prep_editing_agent import MediaPrepEditingAgent
from agents.quality_review_agent import QualityReviewAgent
from agents.performance_analytics_agent import PerformanceAnalyticsAgent
from agents.task_coordinator_agent import TaskCoordinatorAgent
from services.orchestration.langgraph_engine import IASOrchestrationEngine
from database.db import get_db_connection, init_db


class TestFase9AgentArchitecture(unittest.TestCase):
    """Bateria de testes oficiais da arquitetura multiagente VANTIS."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vantis_fase9_")
        cls.test_db_path = Path(cls.test_dir) / "shorts_central.db"
        
        # Copia banco oficial ou inicializa um novo
        main_db = BASE_DIR / "database" / "shorts_central.db"
        if main_db.exists():
            shutil.copy(main_db, cls.test_db_path)
        else:
            init_db(cls.test_db_path)

        cls.registry = AgentRegistry(db_path=str(cls.test_db_path))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_agent_registry_discovery_and_metadata(self):
        """Valida que todos os 10 agentes operacionais estão cadastrados com seus metadados."""
        agents = self.registry.list_all_agents()
        self.assertEqual(len(agents), 10, f"Esperado 10 agentes registrados, encontrado {len(agents)}")

        expected_ids = {
            "agt_opp_research",
            "agt_trend_analysis",
            "agt_editorial_planner",
            "agt_scriptwriter",
            "agt_audiovisual_analyzer",
            "agt_transcription",
            "agt_media_prep_editing",
            "agt_quality_reviewer",
            "agt_performance_analytics",
            "agt_coordinator_distributor"
        }

        registered_ids = {a["agent_id"] for a in agents}
        self.assertEqual(expected_ids, registered_ids)

        for a in agents:
            self.assertTrue(a["name"], f"Agente {a['agent_id']} sem nome")
            self.assertTrue(a["department"], f"Agente {a['agent_id']} sem departamento")
            self.assertTrue(a["responsibility"], f"Agente {a['agent_id']} sem responsabilidade")
            self.assertTrue(a["has_input_schema"])
            self.assertTrue(a["has_output_schema"])

    def test_02_agent_state_machine_and_lifecycle(self):
        """Valida o ciclo de vida e transições de estado: IDLE -> RUNNING -> SUCCESS."""
        agent = self.registry.get_agent("agt_opp_research")
        self.assertIsNotNone(agent)
        self.assertEqual(agent.state, AgentState.IDLE)

        ctx = AgentTaskContext(
            task_id="task_fase9_lifecycle_01",
            channel_id=1,
            niche="tecnologia",
            target_id="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

        result = agent.run(ctx)
        self.assertIsInstance(result, AgentExecutionResult)
        self.assertEqual(result.status, AgentState.SUCCESS)
        self.assertEqual(agent.state, AgentState.SUCCESS)
        self.assertGreater(result.execution_time_ms, 0.0)
        self.assertTrue(result.success_criteria_met)

    def test_03_input_output_contract_enforcement(self):
        """Valida que entradas e saídas são rigidamente validadas via Pydantic."""
        agent = self.registry.get_agent("agt_trend_analysis")
        
        # 1. Execução válida
        valid_res = agent.run({
            "task_id": "task_contract_valid",
            "channel_id": 2,
            "niche": "curiosidades",
            "target_id": "video_test_123"
        })
        self.assertEqual(valid_res.status, AgentState.SUCCESS)
        self.assertIn("velocity_score", valid_res.data)
        self.assertIn("projected_virality", valid_res.data)

        # 2. Execução com falha de validação de entrada (task_id ausente)
        invalid_res = agent.run({
            "channel_id": 2,
            "niche": "curiosidades"
            # task_id é obrigatório no AgentTaskContext
        })
        self.assertEqual(invalid_res.status, AgentState.ERROR)
        self.assertIn("Falha de validação", invalid_res.error_message)

    def test_04_sqlite_audit_logging_to_agent_execution_logs(self):
        """Comprova que execuções de agentes são persistidas na tabela agent_execution_logs."""
        agent = self.registry.get_agent("agt_editorial_planner")
        task_id = "task_audit_log_verify_001"
        
        ctx = AgentTaskContext(
            task_id=task_id,
            channel_id=3,
            niche="financas",
            target_id="btc_analysis_01"
        )
        agent.run(ctx)

        with get_db_connection(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_id, agent_name, department, task_id, channel_id, status, execution_time_ms, success_criteria_met
                FROM agent_execution_logs
                WHERE task_id = ?
            """, (task_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, "Registro não encontrado na tabela agent_execution_logs")
            self.assertEqual(row["agent_id"], "agt_editorial_planner")
            self.assertEqual(row["channel_id"], 3)
            self.assertEqual(row["status"], "SUCCESS")
            self.assertEqual(row["success_criteria_met"], 1)

    def test_05_channel_editorial_isolation_across_agents(self):
        """Garante que cada canal mantém suas características editoriais e memórias isoladas."""
        script_agent = self.registry.get_agent("agt_scriptwriter")
        
        # Execução para Canal 1
        res_ch1 = script_agent.run({
            "task_id": "task_iso_ch1",
            "channel_id": 1,
            "niche": "futebol",
            "target_id": "gols_da_rodada"
        })
        self.assertEqual(res_ch1.status, AgentState.SUCCESS)

        # Execução para Canal 2
        res_ch2 = script_agent.run({
            "task_id": "task_iso_ch2",
            "channel_id": 2,
            "niche": "podcast",
            "target_id": "entrevista_reveladora"
        })
        self.assertEqual(res_ch2.status, AgentState.SUCCESS)

        # Roteiros gerados devem ser distintos e respeitar seus respectivos nichos
        self.assertNotEqual(res_ch1.data["full_script"], res_ch2.data["full_script"])

    def test_06_cost_guard_zero_dollar_enforcement(self):
        """Valida a trava tarifária de custo estritamente $0.00 e registro de custo evitado."""
        script_agent = self.registry.get_agent("agt_scriptwriter")
        res = script_agent.run({
            "task_id": "task_cost_guard",
            "channel_id": 1,
            "niche": "investimentos",
            "target_id": "renda_fixa_dicas"
        })
        self.assertEqual(res.status, AgentState.SUCCESS)
        self.assertEqual(res.data.get("cost_usd"), 0.0, "Custo do roteirista deve ser estritamente $0.00")

        # Telemetria financeira pelo PerformanceAnalyticsAgent
        perf_agent = self.registry.get_agent("agt_performance_analytics")
        p_res = perf_agent.run({
            "task_id": "task_cost_guard",
            "channel_id": 1,
            "niche": "investimentos",
            "target_id": "renda_fixa_dicas"
        })
        self.assertEqual(p_res.status, AgentState.SUCCESS)
        self.assertEqual(p_res.data.get("total_cost_usd"), 0.0)
        self.assertGreater(p_res.data.get("avoided_cost_usd"), 0.0)

    def test_07_youtube_safety_and_portal_2_enforcement(self):
        """Valida que uploads públicos são bloqueados e que o token do Portal 2 é obrigatório."""
        coord_agent = self.registry.get_agent("agt_coordinator_distributor")

        # 1. Sem token de aprovação humana -> Rejeição mandatória
        res_blocked = coord_agent.run({
            "task_id": "task_safety_no_token",
            "channel_id": 1,
            "niche": "esportes",
            "target_id": "clip_seguro_01",
            "human_approval_token": None
        })
        self.assertEqual(res_blocked.status, AgentState.ERROR)
        self.assertIn("Bloqueio de Segurança", res_blocked.error_message)

        # 2. Com token de aprovação humana -> Sucesso com publicação restrita como 'private'
        res_ok = coord_agent.run({
            "task_id": "task_safety_with_token",
            "channel_id": 1,
            "niche": "esportes",
            "target_id": "clip_seguro_01",
            "human_approval_token": "TOKEN_HUMAN_DIRECTOR_AUTH_VALID"
        })
        self.assertEqual(res_ok.status, AgentState.SUCCESS)
        self.assertEqual(res_ok.data.get("publication_privacy"), "private")
        self.assertTrue(res_ok.data.get("human_approval_validated"))
        self.assertTrue(res_ok.data.get("distribution_manifest_ready"))

    def test_08_error_handling_and_resilience(self):
        """Valida que falhas operacionais não causam crash do sistema e registram erro no SQLite."""
        agent = self.registry.get_agent("agt_quality_reviewer")
        
        # Executa com parâmetros inválidos (duração absurda)
        res = agent.run({
            "task_id": "task_qc_failure_check",
            "channel_id": 1,
            "niche": "comedia",
            "target_id": "clip_invalido",
            "parameters": {
                "duration": 500.0, # Shorts aceita até 59s
                "resolution": "1920x1080" # Deveria ser vertical 1080x1920
            }
        })
        self.assertEqual(res.status, AgentState.ERROR)
        self.assertFalse(res.data.get("passed"))
        self.assertLess(res.data.get("qc_score"), 70)
        self.assertGreater(len(res.data.get("recommendations", [])), 0)

    def test_09_end_to_end_langgraph_multiagent_orchestration(self):
        """Executa o pipeline completo de 17 etapas via LangGraph engine com checkpoints e agentes."""
        engine = IASOrchestrationEngine(db_path=str(self.test_db_path))
        task_id = "task_vantis_langgraph_full_orchestration_01"

        # 1. Inicia o pipeline até a pausa obrigatória de aprovação humana (Portal 2)
        state = engine.start_vantis_pipeline(
            task_id=task_id,
            target_id="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            niche="futebol",
            channel_id=1
        )

        self.assertEqual(state["status"], "PAUSED_FOR_REVIEW")
        self.assertEqual(state["current_step"], "14_aprovacao_humana")
        self.assertTrue(state["step_results"]["14_aprovacao_humana"]["waiting_approval"])

        # 2. Concede aprovação humana via token e conclui o pipeline
        resumed_state = engine.approve_and_resume(
            task_id=task_id,
            human_approval_token="TOKEN_DIRECTOR_ORCHESTRATION_PASS"
        )

        self.assertEqual(resumed_state["status"], "COMPLETED")
        self.assertIn("15_preparacao_publicacao", resumed_state["completed_steps"])
        self.assertIn("16_coleta_metricas", resumed_state["completed_steps"])
        self.assertIn("17_aprendizado", resumed_state["completed_steps"])

        # 3. Comprova que os agentes gravaram na tabela de logs durante a orquestração
        with get_db_connection(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM agent_execution_logs WHERE task_id = ?", (task_id,))
            agent_logs_count = cursor.fetchone()[0]
            self.assertGreater(agent_logs_count, 3, "Múltiplos agentes devem ter registrado logs na orquestração")


if __name__ == "__main__":
    unittest.main(verbosity=2)
