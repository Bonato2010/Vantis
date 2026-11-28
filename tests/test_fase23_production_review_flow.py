import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from services.production.editorial_production_engine import EditorialProductionEngine
from services.production.package_renderer import PackageRendererService


def _create_color_png(path: Path, color: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:d=1",
            "-frames:v", "1", str(path),
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )


class TestFase23ProductionReviewFlow(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="vantis_f23_"))
        self.db_path = self.tmp_dir / "test_f23.db"
        run_migrations(str(self.db_path))
        self.eng = EditorialProductionEngine(db_path=str(self.db_path))
        self.renderer = PackageRendererService(
            db_path=str(self.db_path),
            output_dir=str(self.tmp_dir / "renders"),
        )
        # Cria pacote de teste para canal 1
        self.pkg = self.eng.generate_package(
            channel_id=1,
            theme="Teste Fase 23 fluxo completo de revisão",
            target_duration_sec=12.0,
        )
        # Gera 6 imagens físicas reais para simular assets verificados quando necessário
        self.assets = {}
        colors = ["#102030", "#203040", "#304050", "#405060", "#506070", "#607080"]
        for i in range(1, 7):
            p = self.tmp_dir / f"scene_{i}.png"
            _create_color_png(p, colors[i - 1])
            self.assets[i] = str(p)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_human_approval_reject_and_changes_requested_persistence(self):
        self.assertEqual(self.pkg["status"], "READY_FOR_REVIEW")
        ch_req = self.eng.transition_status(self.pkg["id"], "CHANGES_REQUESTED", reason="Ajustar hook inicial")
        self.assertEqual(ch_req["status"], "CHANGES_REQUESTED")
        rej = self.eng.transition_status(self.pkg["id"], "REJECTED", reason="Tema fora de pauta")
        self.assertEqual(rej["status"], "REJECTED")
        app = self.eng.transition_status(self.pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Aprovado pelo editor")
        self.assertEqual(app["status"], "APPROVED_FOR_PRODUCTION")
        reloaded = self.eng.get_package(self.pkg["id"])
        self.assertEqual(reloaded["status"], "APPROVED_FOR_PRODUCTION")
        self.assertGreaterEqual(len(reloaded["version_history"]), 3)

    def test_02_blocks_unapproved_or_rejected_packages(self):
        j1 = self.renderer.render_package(self.pkg["id"], available_assets=self.assets)
        self.assertEqual(j1["status"], "BLOCKED")
        self.assertIn("READY_FOR_REVIEW", j1["error_message"])

        self.eng.transition_status(self.pkg["id"], "REJECTED", reason="Rejeitado")
        j2 = self.renderer.render_package(self.pkg["id"], available_assets=self.assets)
        self.assertEqual(j2["status"], "BLOCKED")
        self.assertIn("REJECTED", j2["error_message"])

    def test_03_blocks_missing_assets_with_pending_report(self):
        self.eng.transition_status(self.pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Aprovado")
        job = self.renderer.render_package(self.pkg["id"], available_assets={1: self.assets[1]})
        self.assertEqual(job["status"], "BLOCKED")
        expected_pending = len(self.pkg["package"]["audiovisual_plan"]["scenes"]) - 1
        self.assertEqual(len(job["pending_assets"]), expected_pending)
        self.assertIn("ASSET_NEEDED", job["error_message"])

    def test_04_tts_failure_rejects_mock_fallback(self):
        self.eng.transition_status(self.pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Aprovado")
        with patch.object(
            self.renderer.tts,
            "generate_narration",
            return_value={"success": True, "mode": "mock_fallback", "audio_path": ""},
        ):
            job = self.renderer.render_package(self.pkg["id"], available_assets=self.assets)
        self.assertEqual(job["status"], "FAILED")
        self.assertIn("TTS", job["error_message"])

    def test_05_ffmpeg_failure_is_captured(self):
        self.eng.transition_status(self.pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Aprovado")
        fake_audio = self.tmp_dir / "fake_voice.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2", str(fake_audio)],
            capture_output=True,
            check=True,
        )
        with patch.object(
            self.renderer.tts,
            "generate_narration",
            return_value={"success": True, "mode": "real_neural", "audio_path": str(fake_audio), "duration_sec": 2.0},
        ), patch("services.production.package_renderer.subprocess.run") as mock_sub:
            mock_sub.return_value = subprocess.CompletedProcess(args=["ffmpeg"], returncode=1, stdout="", stderr="simulated ffmpeg error")
            job = self.renderer.render_package(self.pkg["id"], available_assets=self.assets)
        self.assertEqual(job["status"], "FAILED")
        self.assertIn("FFmpeg falhou", job["error_message"])

    def test_06_checkpoint_recovery_physical_render_and_human_final_review(self):
        self.eng.transition_status(self.pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Aprovado")
        # 1) Falha inicial por falta de assets gera job BLOCKED com checkpoint
        blocked_job = self.renderer.render_package(self.pkg["id"], available_assets={})
        self.assertEqual(blocked_job["status"], "BLOCKED")
        self.assertEqual(blocked_job["checkpoint_stage"], "PREPARING_ASSETS")

        # 2) Retoma mesmo job_id com assets completos -> renderização física real (Edge-TTS + FFmpeg)
        resumed = self.renderer.render_package(
            self.pkg["id"],
            available_assets=self.assets,
            resume_job_id=blocked_job["id"],
        )
        self.assertEqual(resumed["id"], blocked_job["id"])
        self.assertEqual(resumed["status"], "READY_FOR_REVIEW")
        self.assertTrue(Path(resumed["output_mp4_path"]).is_file())
        self.assertGreater(resumed["file_size_bytes"], 10000)
        self.assertEqual(resumed["resolution"], "1080x1920")
        self.assertEqual(resumed["video_codec"], "h264")
        self.assertEqual(resumed["audio_codec"], "aac")
        self.assertIsNotNone(resumed["measured_lufs"])
        self.assertEqual(len(resumed["sha256"]), 64)

        # 3) Nunca vai para COMPLETED antes da revisão humana final; registra defeito e depois aprova
        rev_changes = self.renderer.submit_human_review(
            resumed["id"],
            decision="REQUEST_CHANGES",
            notes="Ajustar ritmo da legenda no meio",
            defects=["subtitles", "rhythm"],
        )
        self.assertEqual(rev_changes["status"], "CHANGES_REQUESTED")
        self.assertEqual(rev_changes["review_defects"], ["subtitles", "rhythm"])

        rev_final = self.renderer.submit_human_review(
            resumed["id"],
            decision="APPROVE_FINAL",
            notes="Validado manualmente",
            defects=[],
        )
        self.assertEqual(rev_final["status"], "COMPLETED")
        self.assertEqual(rev_final["review_decision"], "APPROVE_FINAL")

    def test_07_channel_isolation_across_five_channels(self):
        created_ids = {}
        for ch in (1, 2, 3, 4, 5):
            p = self.eng.generate_package(channel_id=ch, theme=f"Tema isolado canal {ch}")
            created_ids[ch] = p["id"]
        for ch in (1, 2, 3, 4, 5):
            listed = self.eng.list_packages(channel_id=ch, limit=20)
            self.assertTrue(all(item["channel_id"] == ch for item in listed))
            self.assertIn(created_ids[ch], [item["id"] for item in listed])


if __name__ == "__main__":
    unittest.main()
