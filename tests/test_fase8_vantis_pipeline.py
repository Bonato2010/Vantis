"""
Testes Automatizados - Fase 8 / VANTIS: Pipeline Central de 17 Etapas,
Embeddings Neurais Reais (FastEmbed), Isolamento Editorial Multicanal
e Telemetria 100% dos 7 Serviços Open Source.
"""

import os
import sys
import json
import unittest
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.semantic_memory.vector_memory import VectorMemoryService
from services.video_analysis.scene_detector import SceneDetectorService
from services.video_analysis.visual_analyzer import OpenCVVisualAnalyzer
from services.orchestration.langgraph_engine import (
    IASOrchestrationEngine,
    VANTIS_17_STEPS,
    WORKFLOW_STEPS
)
from services.service_registry import ServiceRegistry
from services.model_gateway.gateway import ModelGatewayService
from services.distribution.distribution_service import DistributionService
from database.db import get_db_connection

class TestFase8VantisPipeline(unittest.TestCase):

    def setUp(self):
        self.engine = IASOrchestrationEngine()
        self.vector_mem = VectorMemoryService()

    def test_real_semantic_embedding_fastembed(self):
        """Testa se a memória vetorial gera embeddings densos de 384 dimensões reais via FastEmbed."""
        text_a = "Golaço espetacular de bicicleta no clássico de futebol"
        text_b = "Gol incrível chutou no ângulo partida histórica esporte"
        text_c = "Mistério policial assassinato sem pistas e corpo na mansão"

        v_a = self.vector_mem.generate_embedding(text_a)
        v_b = self.vector_mem.generate_embedding(text_b)
        v_c = self.vector_mem.generate_embedding(text_c)

        # Valida dimensão densa (384) e normalização unitária L2
        self.assertEqual(v_a.shape[0], 384)
        self.assertAlmostEqual(float(np.linalg.norm(v_a)), 1.0, places=3)
        self.assertAlmostEqual(float(np.linalg.norm(v_b)), 1.0, places=3)

        # Similaridade semântica: A e B (futebol) devem ser mais similares entre si do que A e C (futebol vs crime)
        sim_ab = float(np.dot(v_a, v_b))
        sim_ac = float(np.dot(v_a, v_c))
        self.assertGreater(sim_ab, sim_ac, f"Similaridade semântica esperada: sim(A,B)={sim_ab:.4f} > sim(A,C)={sim_ac:.4f}")

    def test_multichannel_vector_isolation(self):
        """Testa o isolamento de memória editorial entre canais com compartilhamento de padrões universais."""
        id_ch1 = "hook_test_ch1_vantis"
        id_ch2 = "hook_test_ch2_vantis"
        id_univ = "hook_test_univ_vantis"

        # Indexa ganchos isolados
        self.vector_mem.index_hook(id_ch1, "A jogada mais polêmica do futebol brasileiro", channel_id=1, niche="futebol")
        self.vector_mem.index_hook(id_ch2, "O mistério macabro do serial killer de Curitiba", channel_id=2, niche="crime")
        self.vector_mem.index_hook(id_univ, "O segredo psicológico que 99% das pessoas ignoram", channel_id=None, niche="universal")

        # Canal 1 busca: deve encontrar id_ch1 e id_univ, mas NUNCA id_ch2
        results_ch1 = self.vector_mem.search_hooks("futebol", channel_id=1, top_k=500)
        ch1_ids = [r["id"] for r in results_ch1]
        self.assertIn(id_ch1, ch1_ids)
        self.assertIn(id_univ, ch1_ids)
        self.assertNotIn(id_ch2, ch1_ids, "Vazamento de memória editorial do Canal 2 para o Canal 1 detectado!")

        # Canal 2 busca: deve encontrar id_ch2 e id_univ, mas NUNCA id_ch1
        results_ch2 = self.vector_mem.search_hooks("crime assassinato", channel_id=2, top_k=50)
        ch2_ids = [r["id"] for r in results_ch2]
        self.assertIn(id_ch2, ch2_ids)
        self.assertIn(id_univ, ch2_ids)
        self.assertNotIn(id_ch1, ch2_ids, "Vazamento de memória editorial do Canal 1 para o Canal 2 detectado!")

        # Limpeza
        with get_db_connection() as conn:
            conn.execute("DELETE FROM semantic_vectors WHERE id IN (?, ?, ?)", (id_ch1, id_ch2, id_univ))
            conn.commit()

    def test_video_analysis_services_availability(self):
        """Testa se PySceneDetect e OpenCV estão ativos e operacionais."""
        sd = SceneDetectorService()
        self.assertTrue(sd.has_scenedetect)

        va = OpenCVVisualAnalyzer()
        self.assertTrue(va.available)

    def test_full_vantis_17_step_pipeline_execution(self):
        """Testa a execução completa do Pipeline Central VANTIS de 17 etapas ponta a ponta."""
        task_id = "task_test_vantis_17_suite"
        target_id = "video_vantis_opp_test"

        # 1. Inicia o pipeline de 17 etapas
        state = self.engine.start_vantis_pipeline(
            task_id=task_id,
            target_id=target_id,
            niche="futebol_outros",
            channel_id=1
        )

        # 2. Verifica retenção mandatória no Portal 2 (etapa 14)
        self.assertEqual(state["current_step"], "14_aprovacao_humana")
        self.assertEqual(state["status"], "PAUSED_FOR_REVIEW")

        # Verifica se etapas preliminares concluíram
        for expected_step in [
            "1_descoberta", "2_pesquisa", "3_analise_tendencias", "4_selecao",
            "5_analise_audiovisual", "6_transcricao", "7_identificacao_momentos",
            "8_roteirizacao", "9_preparacao_materiais", "10_edicao",
            "11_legendas", "12_renderizacao", "13_controle_qualidade"
        ]:
            self.assertIn(expected_step, state["completed_steps"], f"Etapa {expected_step} não completada")

        # Verifica auditoria do QC na etapa 13
        step13_res = state["step_results"]["13_controle_qualidade"]
        self.assertIn("qc_score", step13_res)
        self.assertGreaterEqual(step13_res["qc_score"], 0)

        # 3. Aprovação humana com token no Portal 2 e avanço até o fim
        token = "PORTAL2_TOKEN_VANTIS_VALIDATED"
        resumed = self.engine.approve_and_resume(
            task_id=task_id,
            human_approval_token=token
        )

        self.assertIsNotNone(resumed)
        self.assertEqual(resumed["status"], "COMPLETED")
        self.assertIn("14_aprovacao_humana", resumed["completed_steps"])
        self.assertIn("15_preparacao_publicacao", resumed["completed_steps"])
        self.assertIn("16_coleta_metricas", resumed["completed_steps"])
        self.assertIn("17_aprendizado", resumed["completed_steps"])

        # 4. Verifica publicação estritamente privada (YouTube Safety)
        step15_res = resumed["step_results"]["15_preparacao_publicacao"]
        self.assertEqual(step15_res["privacy_status"], "private")
        self.assertTrue(os.path.exists(step15_res["manifest_path"]))

        # 5. Verifica se o ciclo de aprendizado fechou (etapa 17)
        learned_hooks = self.vector_mem.search_hooks("futebol", channel_id=1, top_k=500)
        learned_ids = [h["id"] for h in learned_hooks]
        self.assertIn(f"learned_{task_id}", learned_ids)

        # Limpeza
        with get_db_connection() as conn:
            conn.execute("DELETE FROM workflow_checkpoints WHERE task_id = ?", (task_id,))
            conn.execute("DELETE FROM semantic_vectors WHERE id = ?", (f"learned_{task_id}",))
            conn.commit()

    def test_portal2_unauthorized_token_blocking(self):
        """Garante que tentativa de publicação sem token ou aprovação humana é barrada com PermissionError."""
        dist = DistributionService(db_path=self.engine.db_path)
        with self.assertRaises(PermissionError):
            dist.execute_distribution(
                task_id="task_hack_dist",
                channel_id=1,
                human_approved=False,
                human_approval_token=None,
                title="Short Inválido"
            )

    def test_service_registry_all_7_services_online(self):
        """Testa se todos os 7 serviços essenciais reportam status ONLINE e nota de saúde de 100%."""
        reg = ServiceRegistry()
        report = reg.check_all()

        self.assertEqual(report["total_services"], 7)
        self.assertEqual(report["operational_services"], 7)
        self.assertEqual(report["health_score"], 100)

        for svc_name, svc_info in report["services"].items():
            self.assertEqual(svc_info["status"], "ONLINE", f"Serviço {svc_name} não está ONLINE: {svc_info}")

if __name__ == "__main__":
    unittest.main()
