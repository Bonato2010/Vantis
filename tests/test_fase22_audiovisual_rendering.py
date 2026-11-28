"""
VANTIS — Suíte de Testes da Fase 22: Renderização Audiovisual Real,
Validação Física (FFprobe/SHA256/LUFS), Bloqueios, Checkpoints e Dashboard
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
from services.production.editorial_production_engine import EditorialProductionEngine
from services.production.package_renderer import PackageRendererService, RENDER_STATES
from web.app import app


class TestFase22AudiovisualRendering(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_fase22.db"
        run_migrations(db_path=self.db_path)
        self.prod = EditorialProductionEngine(db_path=self.db_path)
        self.renderer = PackageRendererService(db_path=self.db_path, output_dir=self.temp_path / "renders")

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def _make_approved_pkg_and_assets(self, channel_id: int = 4):
        pkg = self.prod.generate_package(channel_id=channel_id, theme="Por que o céu é azul", target_duration_sec=20.0)
        approved = self.prod.transition_status(pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Teste aprovado")
        scenes = approved["package"]["audiovisual_plan"]["scenes"]
        # Usa imagem PNG própria válida gerada pelo OpenCV/numpy em temp_dir
        import numpy as np
        import cv2
        img_path = self.temp_path / f"scene_ch{channel_id}.png"
        frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
        frame[:, :] = (30, 60, 90)
        cv2.imwrite(str(img_path), frame)
        assets = {sc["scene_index"]: str(img_path) for sc in scenes}
        return approved, assets

    def test_01_unapproved_package_is_blocked(self):
        """Seção 3: Pacote em READY_FOR_REVIEW (não aprovado) deve bloquear renderização."""
        pkg = self.prod.generate_package(channel_id=1, theme="Gol de placa")
        job = self.renderer.render_package(pkg["id"])
        self.assertEqual(job["status"], "BLOCKED")
        self.assertIn("APPROVED_FOR_PRODUCTION", job["error_message"])

    def test_02_missing_assets_are_blocked_with_pending_report(self):
        """Seção 5: Cenas sem ativos físicos geram relatório de pendentes e estado BLOCKED."""
        pkg = self.prod.generate_package(channel_id=2, theme="Caso real")
        self.prod.transition_status(pkg["id"], "APPROVED_FOR_PRODUCTION")
        job = self.renderer.render_package(pkg["id"], available_assets={})
        self.assertEqual(job["status"], "BLOCKED")
        self.assertGreater(len(job["pending_assets"]), 0)

    def test_03_tts_unavailable_fails_without_mock_simulation(self):
        """Seção 4: Se Edge-TTS falhar/cair em mock_fallback, marca FAILED sem simular sucesso."""
        pkg, assets = self._make_approved_pkg_and_assets(channel_id=3)
        self.renderer.tts.generate_narration = MagicMock(return_value={"success": True, "mode": "mock_fallback", "audio_path": ""})
        job = self.renderer.render_package(pkg["id"], available_assets=assets)
        self.assertEqual(job["status"], "FAILED")
        self.assertEqual(job["checkpoint_stage"], "GENERATING_AUDIO")

    def test_04_ffmpeg_unavailable_or_failure_marks_failed_and_resumes(self):
        """Seções 9 e 11: Falha de FFmpeg registra FAILED com checkpoint e permite retomada."""
        pkg, assets = self._make_approved_pkg_and_assets(channel_id=5)
        bad_renderer = PackageRendererService(db_path=self.db_path, output_dir=self.temp_path / "r_bad")
        bad_renderer.ffmpeg.binary_path = "ffmpeg_inexistente_xyz"
        bad_renderer.tts.generate_narration = MagicMock(return_value={
            "success": True, "mode": "real_neural",
            "audio_path": str((self.temp_path / "dummy.mp3")), "duration_sec": 3.0,
            "boundaries": [{"text": "Teste", "start": 0.0, "end": 3.0}],
        })
        (self.temp_path / "dummy.mp3").write_bytes(b"ID3_not_valid")
        job = bad_renderer.render_package(pkg["id"], available_assets=assets)
        self.assertEqual(job["status"], "FAILED")
        self.assertEqual(job["checkpoint_stage"], "RENDERING")

    def test_05_real_end_to_end_render_with_edge_tts_ass_and_ffmpeg(self):
        """Seções 6, 7, 8 e 9: Renderização física real 1080x1920 com Edge-TTS, ASS, EBU R128 e SHA256."""
        pkg, assets = self._make_approved_pkg_and_assets(channel_id=4)
        job = self.renderer.render_package(pkg["id"], available_assets=assets)
        self.assertEqual(job["status"], "READY_FOR_REVIEW", f"Erro na renderização real: {job.get('error_message')}")
        self.assertTrue(Path(job["output_mp4_path"]).is_file())
        self.assertGreater(job["file_size_bytes"], 1000)
        self.assertGreater(job["duration_sec"], 1.0)
        self.assertEqual(job["resolution"], "1080x1920")
        self.assertEqual(job["video_codec"], "h264")
        self.assertEqual(job["audio_codec"], "aac")
        self.assertEqual(len(job["sha256"]), 64)
        self.assertIsNotNone(job["measured_lufs"])
        self.assertGreater(job["subtitles_count"], 0)

        # Persistência em nova instância
        fresh = PackageRendererService(db_path=self.db_path, output_dir=self.temp_path / "renders")
        reloaded = fresh.get_job(job["id"])
        self.assertEqual(reloaded["sha256"], job["sha256"])

    def test_06_dashboard_render_endpoints(self):
        """Seção 10: Endpoints de renderização respondem e protegem IDs inexistentes."""
        for st in ("QUEUED", "VALIDATING", "PREPARING_ASSETS", "GENERATING_AUDIO", "RENDERING", "VERIFYING", "READY_FOR_REVIEW", "BLOCKED", "FAILED"):
            self.assertIn(st, RENDER_STATES)
        client = TestClient(app)
        self.assertEqual(client.get("/api/production/renders").status_code, 200)
        self.assertEqual(client.get("/api/production/renders/999999").status_code, 404)
        self.assertEqual(client.get("/api/production/renders/999999/file").status_code, 404)


if __name__ == "__main__":
    unittest.main()
