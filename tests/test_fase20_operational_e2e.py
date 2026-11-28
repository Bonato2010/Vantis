"""
VANTIS — Suíte de Testes da Fase 20: Auditoria Operacional, Fluxo End-to-End,
Recomendações Baseadas em Memória e Integração Backend/Dashboard
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from database.migrate import run_migrations
from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.orchestration.vantis_core_pipeline import VantisCorePipeline, PIPELINE_STATES
from web.app import app


class TestFase20OperationalE2E(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_fase20.db"
        run_migrations(db_path=self.db_path)
        self.als = AudiovisualLearningSystem(db_path=self.db_path)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_pipeline_states_and_failure_no_false_success(self):
        """Seção 8: Falha de download ou arquivo corrompido não pode gerar sucesso falso."""
        for st in ("QUEUED", "DOWNLOADING", "DOWNLOAD_FAILED", "MEDIA_VERIFIED", "COMPLETED", "FAILED"):
            self.assertIn(st, PIPELINE_STATES)

        pipe = VantisCorePipeline(db_path=self.db_path, downloads_dir=self.temp_path / "dl")
        pipe.downloader.download_short = MagicMock(return_value={"success": False, "error": "network_404"})
        res = pipe.process_video_end_to_end({"id": "v_fail", "channel_id": 1, "niche": "futebol_outros", "title": "Fail"})
        self.assertEqual(res["final_state"], "DOWNLOAD_FAILED")
        self.assertIn("error", res)

        # Arquivo corrompido (0 bytes) -> FAILED
        corrupt = self.temp_path / "corrupt.mp4"
        corrupt.write_bytes(b"")
        res2 = pipe.process_video_end_to_end({"id": "v_corrupt", "channel_id": 1}, local_file_override=corrupt)
        self.assertEqual(res2["final_state"], "FAILED")

    def test_02_recommendations_use_persistent_channel_memory_without_leak(self):
        """Seção 5: Recomendações utilizam regras validadas e anti-patterns isolados por canal."""
        self.als.record_knowledge(
            niche="desenvolvimento_pessoal",
            topic="ritmo_de_cortes_dinamico",
            title="Regra Cortes C5",
            summary="Cortes >= 4 validado no Canal 5.",
            classification="APRENDIZADO_VALIDADO",
            evidence_video_ids=["v1", "v2"],
            counterexamples=["v3"],
            target_channel_id=5,
            pilot_phase=20,
        )
        self.als.record_knowledge(
            niche="desenvolvimento_pessoal",
            topic="anti_pattern_editorial_ou_acustico",
            title="Silêncio C5",
            summary="Áudio silencioso.",
            classification="ANTI_PATTERN",
            evidence_video_ids=["v4"],
            counterexamples=[],
            target_channel_id=5,
            pilot_phase=20,
        )

        pipe = VantisCorePipeline(db_path=self.db_path)
        recs_c5 = pipe.generate_recommendations_from_memory(
            5,
            {"cuts_count": 1, "has_narration": False, "audio_visual_relation": "silent_or_unusable_audio"},
        )
        self.assertTrue(any(r["classification"] == "APRENDIZADO_VALIDADO" for r in recs_c5))
        self.assertTrue(any(r["classification"] == "ANTI_PATTERN" for r in recs_c5))

        # Canal 1 não deve receber recomendações validadas do Canal 5
        recs_c1 = pipe.generate_recommendations_from_memory(
            1,
            {"cuts_count": 1, "has_narration": False, "audio_visual_relation": "silent_or_unusable_audio"},
        )
        self.assertFalse(any(r["classification"] == "APRENDIZADO_VALIDADO" for r in recs_c1))

    def test_03_fastapi_backend_and_dashboard_endpoints_operational(self):
        """Seção 6: Backend FastAPI inicializa, serve dashboard e endpoints retornam 200 OK."""
        client = TestClient(app)
        for ep in (
            "/",
            "/health",
            "/api/health",
            "/api/dashboard/kpis",
            "/api/channels",
            "/api/learning/overview",
            "/api/learning/patterns",
            "/api/learning/experiments",
            "/api/learning/recommendations/5",
            "/api/services/status",
            "/api/services/costs",
        ):
            r = client.get(ep)
            self.assertEqual(r.status_code, 200, f"Endpoint {ep} retornou {r.status_code}")

        rec_data = client.get("/api/learning/recommendations/5").json()
        self.assertEqual(rec_data["channel_id"], 5)
        self.assertGreater(len(rec_data["recommendations"]), 0)


if __name__ == "__main__":
    unittest.main()
