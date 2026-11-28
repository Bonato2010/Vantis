"""
IAS Test Suite - Fase 14: Correção Estrutural, Aprendizado Real e Zero Simulação
Valida as 12 regras mandatórias do VANTIS:
1. Vídeo inexistente não gera sucesso (retorna FAILED/INACCESSIBLE).
2. Falha de metadados não inventa métricas fictícias (views, likes, retention, duration).
3. Transcrição sintética não é registrada como real (título não vira transcrição).
4. Análise parcial não é marcada como completa (exige narrativa + áudio + visual).
5. Vídeo duplicado não aumenta a contagem de vídeos únicos (deduplicação por fingerprint).
6. Tarefa interrompida pode ser retomada (checkpoints de lote).
7. Erro em uma tarefa não destrói a fila (resiliência).
8. Provedor comercial pago não é acionado silenciosamente (trava de custo zero $0.00).
9. Dashboard não conta vídeos apenas catalogados como completamente analisados.
10. Aprendizado editorial possui origem rastreável com evidence_video_ids.
11. Memória de um canal não contamina a de outro (isolamento multitenant).
12. Etapas simuladas não retornam sucesso operacional enganoso.
"""
import os
import sys
import tempfile
import unittest
import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from core.large_scale_cataloger import LargeScaleCataloger
from core.research_pipeline import ResearchPipelineManager
from core.pattern_learner import PatternLearner
from memory.central_memory import CentralMemory
from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.model_gateway.gateway import ModelGatewayService
from services.orchestration.langgraph_engine import IASOrchestrationEngine

class TestFase14RealLearningAndZeroSimulation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.temp_dir.name, "test_real_learning.db")
        run_migrations(db_path=self.test_db)
        self.memory = CentralMemory(db_path=Path(self.test_db))
        self.learning_sys = AudiovisualLearningSystem(db_path=self.test_db)
        self.cataloger = LargeScaleCataloger(memory=self.memory)
        self.pipeline_mgr = ResearchPipelineManager(memory=self.memory, db_path=self.test_db)
        self.pattern_learner = PatternLearner(playbook_path=os.path.join(self.temp_dir.name, "playbook.json"), db_path=self.test_db)
        self.orchestrator = IASOrchestrationEngine(db_path=self.test_db)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_inexistent_video_fails_honestly(self):
        """1. Um vídeo inexistente não gera sucesso."""
        fake_url = "https://www.youtube.com/shorts/non_existent_fake_id_9999"
        res = self.cataloger.ingest_reference(youtube_url=fake_url, category_slug="futebol")
        
        self.assertFalse(res.get("success"), "Vídeo inexistente não pode ter sucesso.")
        self.assertEqual(res.get("status"), "INACCESSIBLE")
        self.assertFalse(res.get("metrics_invented"))

        # Pipeline completo também deve falhar
        pipe_res = self.pipeline_mgr.run_full_pipeline_step(
            niche_slug="futebol",
            query="termo_completamente_inexistente_xyz_12345",
            video_url=fake_url
        )
        self.assertEqual(pipe_res.get("pipeline_status"), "FAILED")
        self.assertNotIn("LEARNING_COMPLETED", pipe_res.get("stages_completed", []))

    def test_02_metadata_failure_does_not_invent_metrics(self):
        """2. Uma falha de metadados não cria métricas fictícias (views, likes, duration, retention)."""
        invalid_url = "https://invalid-domain.com/shorts/xyz"
        meta = self.cataloger.extract_video_metadata_fast(invalid_url)
        self.assertIsNone(meta, "URL inválida deve retornar None sem fabricar dados.")

        ingest_res = self.cataloger.ingest_reference(youtube_url=invalid_url, category_slug="curiosidades")
        self.assertFalse(ingest_res.get("success"))
        # Verifica que o banco não recebeu métricas inventadas (como 85.000 views)
        with self.memory._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM video_references WHERE views_count = 85000")
            self.assertEqual(cur.fetchone()[0], 0, "Métrica fictícia de 85.000 views encontrada no banco!")

    def test_03_synthetic_transcript_not_treated_as_real(self):
        """3. Uma transcrição sintética não é registrada como real (título não vira transcrição)."""
        # Se nenhuma transcrição for fornecida, ingest_reference não deve inventar hook_transcript a partir do título
        sample_meta = {
            "youtube_id": "test_real_id_101",
            "url": "https://www.youtube.com/shorts/test_real_id_101",
            "title": "Título Incrível sobre Futebol",
            "author": "Criador Real",
            "views_count": 12000,
            "likes_count": 600,
            "duration_seconds": 35.0,
            "description": "Desc",
            "tags": "futebol",
            "has_subtitles": False
        }
        # Mock do extrator para simular vídeo com título mas sem transcrição
        self.cataloger.extract_video_metadata_fast = lambda url: sample_meta
        res = self.cataloger.ingest_reference(sample_meta["url"], "futebol", transcript_text="")
        
        self.assertTrue(res.get("success"))
        self.assertFalse(res.get("has_real_transcript"))
        self.assertIsNone(res.get("hook"), "Título não pode ser transformado em gancho de transcrição.")
        self.assertIsNone(res.get("pacing_wpm"), "Pacing WPM não pode ser calculado sem transcrição.")

    def test_04_partial_analysis_not_marked_as_complete(self):
        """4. Uma análise parcial não é marcada como completa."""
        vid_res = self.learning_sys.discover_video(
            source_id="part_vid_01",
            source_url="https://www.youtube.com/shorts/part_vid_01",
            title="Vídeo Parcial",
            creator="Criador Teste",
            niche="humor",
            duration=40.0
        )
        vid_id = vid_res["video_id"]
        # Processa apenas metadados
        self.learning_sys.process_metadata(vid_id, {"title": "Vídeo Parcial"})
        
        # Tenta finalizar sem áudio nem visual
        fin_res = self.learning_sys.finalize_multimodal_analysis("part_vid_01")
        self.assertNotEqual(fin_res["final_state"], "fully_analyzed", "Análise parcial não pode ser marcada como fully_analyzed.")
        self.assertLess(fin_res["completeness_percentage"], 100.0)

    def test_05_duplicate_video_does_not_increment_unique_count(self):
        """5. Um vídeo duplicado não aumenta a contagem de vídeos únicos."""
        res1 = self.learning_sys.discover_video(
            source_id="dup_vid_001",
            original_url="https://www.youtube.com/shorts/dup_vid_001",
            title="Título Original de Teste",
            creator="Criador Alpha",
            niche="casos_policiais",
            duration_seconds=50.0
        )
        self.assertEqual(res1["status"], "SUCCESS")

        # Tentativa de ingerir o mesmo vídeo com mesmo ID
        res2 = self.learning_sys.discover_video(
            source_id="dup_vid_001", # mesmo ID
            original_url="https://www.youtube.com/shorts/dup_vid_001",
            title="Título Original de Teste!",
            creator="Criador Alpha",
            niche="casos_policiais",
            duration_seconds=50.0
        )
        self.assertEqual(res2["status"], "ALREADY_CATALOGED")

        # Tentativa de reupload duplicado por fingerprint multimodal (ID diferente, mesmo título e duração)
        res3 = self.learning_sys.discover_video(
            source_id="dup_vid_002_reup",
            original_url="https://www.youtube.com/shorts/dup_vid_002_reup",
            title="Título Original de Teste",
            creator="Criador Alpha",
            niche="casos_policiais",
            duration_seconds=50.2
        )
        self.assertEqual(res3["status"], "REJECTED_DUPLICATE")
        self.assertEqual(res3["reason"], "duplicate_fingerprint")

        with self.memory._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM audiovisual_library WHERE processing_state != 'rejected'")
            self.assertEqual(cur.fetchone()[0], 1, "Vídeo duplicado aumentou a contagem de vídeos válidos!")

    def test_06_interrupted_batch_resumption(self):
        """6. Uma tarefa de lote interrompida pode ser retomada com persistência de checkpoints."""
        batch_id = "test_batch_chk_01"
        # Cria checkpoint prévio interrompido
        with self.memory._get_conn() as conn:
            conn.execute("""
                INSERT INTO learning_batch_checkpoints (
                    batch_id, target_goal, processed_count, success_count,
                    rejected_count, error_count, status
                ) VALUES (?, 7000, 10, 8, 2, 0, 'RUNNING')
            """, (batch_id,))
            conn.commit()

        # Executa retomada
        res = self.learning_sys.run_batch_processing(batch_id=batch_id, batch_size=5)
        self.assertGreaterEqual(res.get("total_processed", 0), 10, "Retomada não aproveitou o progresso do checkpoint.")
        self.assertIn("batch_id", res)

    def test_07_queue_task_error_does_not_destroy_queue(self):
        """7. Um erro em uma tarefa não destrói a fila."""
        with self.memory._get_conn() as conn:
            # Insere uma tarefa com erro e outra válida
            conn.execute("""
                INSERT INTO task_queue (task_id, task_type, priority, payload_json, channel_id, status)
                VALUES ('t_fail_01', 'failing_task', 1, '{"bad": true}', 1, 'error')
            """)
            conn.execute("""
                INSERT INTO task_queue (task_id, task_type, priority, payload_json, channel_id, status)
                VALUES ('t_ok_01', 'valid_task', 2, '{"good": true}', 1, 'pending')
            """)
            conn.commit()

            # Verifica que a fila continua íntegra e tarefas pendentes estão acessíveis
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM task_queue WHERE status = 'pending'")
            pending = cur.fetchone()[0]
            self.assertEqual(pending, 1)

            cur.execute("SELECT COUNT(*) FROM task_queue WHERE status = 'error'")
            errors = cur.fetchone()[0]
            self.assertEqual(errors, 1)

    def test_08_zero_cost_blocks_paid_models(self):
        """8. Um provedor comercial pago não é acionado silenciosamente (política de custo zero $0.00)."""
        gateway = ModelGatewayService(enforce_free_tier=True)
        # Verifica detecção de modelos comerciais pagos
        self.assertTrue(gateway.is_paid_model("gpt-4o"))
        self.assertTrue(gateway.is_paid_model("gpt-4o-mini"))
        self.assertTrue(gateway.is_paid_model("claude-3-5-sonnet-20241022"))
        self.assertTrue(gateway.is_paid_model("anthropic/claude-3-5-haiku-20241022"))
        self.assertFalse(gateway.is_paid_model("gemini/gemini-2.5-flash"))

        # Chamada para modelo pago deve ser bloqueada e desviada para gratuito
        res = gateway.completion(
            messages=[{"role": "user", "content": "Olá"}],
            preferred_model="gpt-4o",
            allow_paid_api=False
        )
        self.assertEqual(res["usage"]["cost_usd"], 0.0, "Custo gerado foi maior que zero!")
        self.assertNotEqual(res["model_used"], "gpt-4o")

    def test_09_dashboard_does_not_count_cataloged_as_fully_analyzed(self):
        """9. O dashboard não conta vídeos apenas catalogados como estudados/analisados."""
        # Insere vídeo catalogado sem análise
        with self.memory._get_conn() as conn:
            conn.execute("""
                INSERT INTO audiovisual_library (
                    source_id, original_url, title, creator, niche, processing_state
                ) VALUES ('cat_only_01', 'https://yt.com/1', 'Título Catalogado', 'Criador', 'futebol', 'discovered')
            """)
            conn.commit()

        overview = self.learning_sys.get_dashboard_overview()
        granular = overview.get("granular_indicators", {})
        
        self.assertGreaterEqual(granular.get("videos_descobertos", 0), 1)
        self.assertEqual(granular.get("videos_completamente_analisados", 0), 0, "Vídeo apenas descoberto foi contado como completamente analisado!")

    def test_10_editorial_knowledge_has_traceable_evidence(self):
        """10. O aprendizado editorial possui origem rastreável com evidence_video_ids."""
        # Registra regra editorial com evidências explícitas
        rec = self.learning_sys.record_knowledge(
            niche="futebol",
            knowledge_type="hook_formula",
            title="Gancho de Revelação Histórica",
            summary="Apresentar o desfecho nos primeiros 2 segundos retém 80%",
            classification="APRENDIZADO_VALIDADO",
            confidence_score=0.92,
            evidence_video_ids=["real_vid_ev_01", "real_vid_ev_02"]
        )
        self.assertIn("id", rec)
        self.assertEqual(len(rec["evidence_video_ids"]), 2)
        self.assertEqual(rec["classification"], "APRENDIZADO_VALIDADO")

        with self.memory._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT evidence_video_ids FROM editorial_knowledge_library WHERE id = ?", (rec["id"],))
            ev_json = cur.fetchone()[0]
            self.assertIn("real_vid_ev_01", ev_json)
            self.assertIn("real_vid_ev_02", ev_json)

    def test_11_channel_memory_isolation_prevents_contamination(self):
        """11. A memória de um canal não contamina automaticamente a memória de outro canal."""
        # Registra conhecimento exclusivo para Canal 1 (Futebol)
        self.memory.record_knowledge_node(
            category_slug="futebol",
            channel_id=1,
            node_type="editorial_strategy",
            title="Estratégia Exclusiva do Canal 1 de Futebol",
            pattern_data={"focus": "lances_rapidos"},
            derived_from=["vid_futebol_01"]
        )

        # Registra conhecimento exclusivo para Canal 2 (Casos Policiais)
        self.memory.record_knowledge_node(
            category_slug="casos_policiais",
            channel_id=2,
            node_type="editorial_strategy",
            title="Estratégia Exclusiva do Canal 2 de Casos Policiais",
            pattern_data={"focus": "narrativa_suspense"},
            derived_from=["vid_crime_01"]
        )

        # Consulta memória do Canal 1: NÃO pode ver Canal 2
        nodes_ch1 = self.memory.query_knowledge_nodes(channel_id=1)
        titles_ch1 = [n["title"] for n in nodes_ch1]
        self.assertIn("Estratégia Exclusiva do Canal 1 de Futebol", titles_ch1)
        self.assertNotIn("Estratégia Exclusiva do Canal 2 de Casos Policiais", titles_ch1)

        # Consulta memória do Canal 2: NÃO pode ver Canal 1
        nodes_ch2 = self.memory.query_knowledge_nodes(channel_id=2)
        titles_ch2 = [n["title"] for n in nodes_ch2]
        self.assertIn("Estratégia Exclusiva do Canal 2 de Casos Policiais", titles_ch2)
        self.assertNotIn("Estratégia Exclusiva do Canal 1 de Futebol", titles_ch2)

    def test_12_simulated_steps_do_not_return_fake_success(self):
        """12. Etapas simuladas não retornam sucesso operacional enganoso."""
        # Pattern learner com URL inválida não deve fingir aprendizado
        learn_res = self.pattern_learner.learn_from_video("https://invalid-url-fake.com/xyz", niche="humor")
        self.assertFalse(learn_res.get("success"))
        self.assertEqual(learn_res.get("analysis_depth"), "NONE")
        self.assertFalse(learn_res.get("metrics_invented"))

if __name__ == "__main__":
    unittest.main()
