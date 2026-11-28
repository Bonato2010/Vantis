"""
IAS Test Suite - Fase 4: Inteligência Editorial, Pesquisa Real & Portal 1 (Governança de Descoberta)
Valida:
1. Mineração de vídeos reais via yt-dlp sem dados sintéticos e registro em video_lifecycle.
2. Governança Humana no Portal 1: aprovação de pautas, liberação de direitos e avanço de estado.
3. Indexação semântica automática de ganchos aprovados na VectorMemoryService.
4. Rejeição fundamentada no Portal 1 e aprendizado da IA via memória central negativa.
5. Métricas e KPIs de governança editorial.
6. Extração de padrões no IntelligenceEngine utilizando ModelGatewayService protegido.
"""
import os
import sys
import tempfile
import unittest
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.discovery.youtube_crawler import RealYouTubeDiscoveryService
from services.discovery.portal1_service import Portal1GovernanceService, VALID_REJECTION_CATEGORIES
from services.semantic_memory.vector_memory import VectorMemoryService
from services.video_analysis.yt_metadata import VideoMetadataService
from core.intelligence_engine import IntelligenceEngine
from database.migrate import run_migrations

class TestFase4DiscoveryPortal1(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.temp_dir.name, "test_discovery.db")
        # Aplica migrações 001, 002, 003 e 004
        run_migrations(db_path=self.test_db)
        self.crawler = RealYouTubeDiscoveryService(db_path=self.test_db)
        self.portal1 = Portal1GovernanceService(db_path=self.test_db)
        self.vector_mem = VectorMemoryService(db_path=self.test_db)
        self.meta_svc = VideoMetadataService(db_path=self.test_db)
        self.intel_engine = IntelligenceEngine(db_path=self.test_db)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_real_youtube_discovery_no_fake_ids(self):
        """Valida que a descoberta retorna vídeos reais com URLs autênticas e métricas válidas."""
        opps = self.crawler.discover_shorts_by_niche(niche="curiosidades", limit=2, channel_id=4)
        self.assertGreaterEqual(len(opps), 1)

        for opp in opps:
            # 1. IDs e URLs devem ser reais do YouTube
            v_id = opp["video_id"]
            self.assertFalse(v_id.startswith("yt_174"), "ID sintético detectado!")
            self.assertIn("https://www.youtube.com/shorts/", opp["source_url"])

            # 2. Métricas autênticas
            self.assertGreater(opp["views"], 0)
            self.assertGreater(opp["likes"], 0)
            self.assertGreater(opp["confidence_score"], 60.0)
            self.assertEqual(opp["status"], "PENDING_REVIEW")
            self.assertEqual(opp["recommended_channel_id"], 4)

            # 3. Rastreabilidade na máquina de estados
            lifecycle = self.meta_svc.list_by_status("descoberto")
            lifecycle_ids = [item["video_id"] for item in lifecycle]
            self.assertIn(v_id, lifecycle_ids)

    def test_02_portal1_approval_gate(self):
        """Valida aprovação de pauta no Portal 1 com transição de direitos e indexação semântica."""
        # 1. Minera uma oportunidade
        opps = self.crawler.discover_shorts_by_niche(niche="futebol_outros", limit=1, channel_id=1)
        self.assertGreater(len(opps), 0)
        opp = opps[0]
        opp_id = opp["opportunity_id"]
        v_id = opp["video_id"]

        # 2. Operador humano aprova no Portal 1
        approve_res = self.portal1.approve_opportunity(
            opportunity_id=opp_id,
            reviewer="Diretor de Esportes",
            auto_dispatch=False
        )
        self.assertTrue(approve_res["success"])
        self.assertEqual(approve_res["status"], "APPROVED")

        # 3. Verifica transição de status na opportunities
        updated_opp = self.portal1.get_opportunity(opp_id)
        self.assertEqual(updated_opp["status"], "APPROVED")
        self.assertEqual(updated_opp["reviewed_by"], "Diretor de Esportes")

        # 4. Verifica avanço de direitos na video_lifecycle
        lifecycle_approved = self.meta_svc.list_by_status("aprovado_para_produção")
        approved_ids = [item["video_id"] for item in lifecycle_approved]
        self.assertIn(v_id, approved_ids)

        # 5. Verifica se o gancho foi indexado na memória semântica vetorial
        search_res = self.vector_mem.search_hooks("futebol lances incríveis", top_k=5)
        self.assertGreater(len(search_res), 0)

    def test_03_portal1_rejection_gate_and_negative_memory(self):
        """Valida rejeição fundamentada no Portal 1 e registro de aprendizado na memória central."""
        opps = self.crawler.discover_shorts_by_niche(niche="casos_policiais", limit=1, channel_id=2)
        self.assertGreater(len(opps), 0)
        opp = opps[0]
        opp_id = opp["opportunity_id"]
        v_id = opp["video_id"]

        # Rejeita pauta por risco de direitos autorais
        reject_res = self.portal1.reject_opportunity(
            opportunity_id=opp_id,
            rejection_reason="Uso excessivo de imagens jornalísticas de terceiros",
            rejection_category="direitos_autorais",
            reviewer="Chefe de Conformidade"
        )
        self.assertTrue(reject_res["success"])
        self.assertEqual(reject_res["status"], "REJECTED")

        # Verifica persistência da recusa
        updated_opp = self.portal1.get_opportunity(opp_id)
        self.assertEqual(updated_opp["status"], "REJECTED")
        self.assertEqual(updated_opp["rejection_category"], "direitos_autorais")
        self.assertIn("jornalísticas", updated_opp["rejection_reason"])

        # Verifica avanço para 'rejeitado' no ciclo de vida
        lifecycle_rejected = self.meta_svc.list_by_status("rejeitado")
        rejected_ids = [item["video_id"] for item in lifecycle_rejected]
        self.assertIn(v_id, rejected_ids)

    def test_04_portal1_governance_metrics(self):
        """Valida consolidação de métricas e taxa de aprovação do Portal 1."""
        # Cria 3 oportunidades
        opps = self.crawler.discover_shorts_by_niche(niche="humor", limit=3, channel_id=3)
        self.assertGreaterEqual(len(opps), 3)

        # Aprova 1 e rejeita 1
        self.portal1.approve_opportunity(opps[0]["opportunity_id"], reviewer="Curador 1")
        self.portal1.reject_opportunity(opps[1]["opportunity_id"], "Fora do tom do canal", "fora_da_persona", reviewer="Curador 2")

        metrics = self.portal1.get_governance_metrics()
        self.assertGreaterEqual(metrics["total_opportunities"], 3)
        self.assertGreaterEqual(metrics["approved"], 1)
        self.assertGreaterEqual(metrics["rejected"], 1)
        self.assertIn("fora_da_persona", metrics["rejections_by_category"])
        self.assertGreater(metrics["approval_rate_pct"], 0.0)

    def test_05_portal1_auto_dispatch_workflow(self):
        """Valida aprovação com despacho automático direto para a fila de produção LangGraph."""
        opps = self.crawler.discover_shorts_by_niche(niche="desenvolvimento_pessoal", limit=1, channel_id=5)
        self.assertGreater(len(opps), 0)
        opp_id = opps[0]["opportunity_id"]

        approve_res = self.portal1.approve_opportunity(
            opportunity_id=opp_id,
            reviewer="Diretor Geral",
            auto_dispatch=True
        )
        self.assertTrue(approve_res["success"])
        self.assertTrue(approve_res["dispatched_workflow"])
        self.assertIsNotNone(approve_res["workflow_state"])
        # O fluxo deve ter iniciado e pausado no Portal 2 (revisão humana final)
        self.assertEqual(approve_res["workflow_state"]["status"], "PAUSED_FOR_REVIEW")

    def test_06_intelligence_engine_pattern_extraction(self):
        """Valida que o IntelligenceEngine extrai padrões usando o ModelGateway seguro."""
        # Registra um vídeo de referência
        with sqlite3.connect(self.test_db) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO video_references (
                    category_id, video_id, title, url, views_count, likes_count, niche
                ) VALUES (1, 'vid_test_intel_01', 'O Segredo que Mudou o Jogo', 'https://youtube.com/shorts/vid01', 500000, 35000, 'futebol_outros')
            """)
            conn.commit()

        analysis = self.intel_engine.analyze_reference_video("vid_test_intel_01")
        self.assertIsNotNone(analysis)
        self.assertIn("hook_type", analysis)
        self.assertIn("narrative_structure", analysis)

if __name__ == "__main__":
    unittest.main()
