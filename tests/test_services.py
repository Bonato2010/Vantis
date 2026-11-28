"""
IAS Test Suite - Validação Automatizada de Serviços e Integrações Open Source
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Adiciona o diretório raiz ao sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.service_registry import ServiceRegistry
from services.orchestration.langgraph_engine import IASOrchestrationEngine, WORKFLOW_STEPS
from services.semantic_memory.vector_memory import VectorMemoryService
from services.transcription.whisper_service import WhisperTranscriptionService
from services.video_analysis.scene_detector import SceneDetectorService
from services.video_analysis.visual_analyzer import OpenCVVisualAnalyzer
from services.video_analysis.yt_metadata import VideoMetadataService
from services.model_gateway.gateway import ModelGatewayService
from services.media_processing.ffmpeg_engine import FFmpegEngine

class TestIASServices(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.temp_dir.name, "test_central.db")

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_service_registry(self):
        registry = ServiceRegistry()
        report = registry.check_all()
        self.assertEqual(report["total_services"], 7)
        self.assertGreaterEqual(report["health_score"], 80)
        self.assertIn("orchestration_langgraph", report["services"])
        self.assertIn("media_processing_ffmpeg", report["services"])

    def test_02_langgraph_orchestration(self):
        engine = IASOrchestrationEngine(db_path=self.test_db)
        task_id = "task_test_001"
        
        # Inicia o fluxo: deve executar até a etapa 11 e pausar para revisão humana
        state = engine.start_workflow(task_id=task_id, target_id="vid_123", niche="futebol")
        self.assertEqual(state["status"], "PAUSED_FOR_REVIEW")
        self.assertEqual(state["current_step"], "11_revisao_humana")
        self.assertIn("1_pesquisa_referencias", state["completed_steps"])

        # Recupera do checkpoint
        saved = engine.get_task_state(task_id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["task_id"], task_id)

        # Aprova e conclui
        resumed = engine.approve_and_resume(task_id)
        self.assertEqual(resumed["status"], "COMPLETED")
        self.assertEqual(resumed["current_step"], "12_distribuicao")

    def test_03_semantic_memory_cosine(self):
        mem = VectorMemoryService(db_path=self.test_db)
        
        # Indexa ganchos
        mem.index_hook("h1", "O segredo chocante que ninguém te contou sobre a final", 92.0, "futebol")
        mem.index_hook("h2", "Como treinar finalização para acertar o ângulo em qualquer jogo", 88.0, "esportes")
        mem.index_hook("h3", "Receita prática de bolo de cenoura com chocolate", 50.0, "culinária")

        # Busca por significado
        results = mem.search_hooks("revelação e polêmica de futebol", top_k=2)
        self.assertGreater(len(results), 0)
        # O primeiro resultado deve ser sobre futebol/segredo
        self.assertEqual(results[0]["id"], "h1")
        self.assertGreater(results[0]["similarity_score"], 0.5)

    def test_04_transcription_and_ass(self):
        whisper = WhisperTranscriptionService(model_size="tiny")
        
        # Teste de formatação e timestamps
        time_str = whisper.format_ass_time(65.45)
        self.assertEqual(time_str, "0:01:05.45")

        # Gera ASS a partir de segmentos simulados
        dummy_segments = [{
            "start": 0.0,
            "end": 2.5,
            "text": "GANCHO INCRÍVEL PARA O SHORTS",
            "words": [
                {"word": "Gancho", "start": 0.0, "end": 0.5},
                {"word": "incrível", "start": 0.5, "end": 1.2},
                {"word": "para", "start": 1.2, "end": 1.6},
                {"word": "Shorts", "start": 1.6, "end": 2.5}
            ]
        }]
        out_ass = os.path.join(self.temp_dir.name, "test_viral.ass")
        whisper.generate_viral_ass_subtitles(dummy_segments, out_ass)
        self.assertTrue(os.path.exists(out_ass))
        with open(out_ass, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("PlayResY: 1920", content)
            self.assertIn("Dialogue:", content)

    def test_05_scene_detection_and_bpm(self):
        detector = SceneDetectorService()
        self.assertTrue(detector.has_scenedetect)

    def test_06_opencv_framing(self):
        analyzer = OpenCVVisualAnalyzer()
        self.assertTrue(analyzer.available)

    def test_07_model_gateway_completion_and_cost(self):
        gateway = ModelGatewayService(db_path=self.test_db)
        res = gateway.completion(
            messages=[{"role": "user", "content": "Analise este roteiro"}],
            task="critical_analysis"
        )
        self.assertTrue(res["success"])
        self.assertIn("usage", res)
        self.assertGreater(res["usage"]["total_tokens"], 0)

        # Checa métricas de consumo
        metrics = gateway.get_usage_metrics()
        self.assertGreater(metrics["total_calls"], 0)

    def test_08_video_lifecycle_state_machine(self):
        meta_svc = VideoMetadataService(db_path=self.test_db)
        v_id = "test_yt_999"
        
        meta_svc.record_cataloged({
            "video_id": v_id,
            "title": "Vídeo Teste",
            "channel_name": "Canal 01",
            "duration_sec": 45.0,
            "status": "catalogado"
        })

        # Avança estados
        r1 = meta_svc.advance_status(v_id, "acessível")
        self.assertTrue(r1["success"])
        
        r2 = meta_svc.advance_status(v_id, "autorizado", notes="Autorização confirmada pelo criador")
        self.assertTrue(r2["success"])

        r3 = meta_svc.advance_status(v_id, "aprovado_para_produção")
        self.assertTrue(r3["success"])

        approved_list = meta_svc.list_by_status("aprovado_para_produção")
        self.assertEqual(len(approved_list), 1)
        self.assertEqual(approved_list[0]["video_id"], v_id)

    def test_09_ffmpeg_engine(self):
        ffmpeg = FFmpegEngine()
        status = ffmpeg.get_status()
        self.assertTrue(status.get("available"))
        self.assertIsNotNone(status.get("binary_path"))

if __name__ == "__main__":
    unittest.main()
