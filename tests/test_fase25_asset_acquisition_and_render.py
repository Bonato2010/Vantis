import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from services.production.asset_intelligence import AssetIntelligenceEngine
from services.production.editorial_production_engine import EditorialProductionEngine
from services.production.package_renderer import PackageRendererService


def _make_png(path: Path, color: str = "#112233", size: str = "1080x1920") -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={size}:d=1", "-frames:v", "1", str(path)],
        capture_output=True,
        check=True,
        timeout=30,
    )


class _FakeResp:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestFase25AssetAcquisitionAndRender(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="vantis_f25_"))
        self.db_path = self.tmp_dir / "test_f25.db"
        run_migrations(str(self.db_path))
        self.aie = AssetIntelligenceEngine(db_path=str(self.db_path))
        self.eng = EditorialProductionEngine(db_path=str(self.db_path))
        self.renderer = PackageRendererService(db_path=str(self.db_path), output_dir=str(self.tmp_dir / "renders"))

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_search_empty_results(self):
        empty_json = json.dumps({"query": {}}).encode("utf-8")
        with patch("services.production.asset_intelligence.urlopen", return_value=_FakeResp(empty_json)):
            res = self.aie.search_wikimedia_commons("query_sem_resultados_xyz")
        self.assertTrue(res["success"])
        self.assertEqual(res["results"], [])

    def test_02_blocks_incompatible_and_unverified_licenses_on_acquire(self):
        with self.assertRaises(ValueError):
            self.aie.acquire_wikimedia_asset(
                {"title": "File:NC.jpg", "license_name": "CC BY-NC 4.0", "url": "https://example.com/a.jpg", "mime": "image/jpeg"},
                channel_id=4,
                download_dir=self.tmp_dir,
            )
        with self.assertRaises(ValueError):
            self.aie.acquire_wikimedia_asset(
                {"title": "File:Unk.jpg", "license_name": "UNKNOWN", "url": "https://example.com/b.jpg", "mime": "image/jpeg"},
                channel_id=4,
                download_dir=self.tmp_dir,
            )

    def test_03_interrupted_download_cleans_up_and_raises(self):
        with patch("services.production.asset_intelligence.urlopen", side_effect=OSError("connection reset")):
            with self.assertRaises(ValueError):
                self.aie.acquire_wikimedia_asset(
                    {"title": "File:Drop.jpg", "license_name": "CC0", "url": "https://example.com/drop.jpg", "mime": "image/jpeg"},
                    channel_id=4,
                    download_dir=self.tmp_dir,
                )
        self.assertEqual(list(self.tmp_dir.glob("ch4_*")), [])

    def test_04_corrupt_duplicate_and_low_res_inadequate_asset(self):
        # Arquivo corrompido baixado
        with patch("services.production.asset_intelligence.urlopen", return_value=_FakeResp(b"X" * 3000)):
            with self.assertRaises(ValueError):
                self.aie.acquire_wikimedia_asset(
                    {"title": "File:Bad.png", "license_name": "CC0", "url": "https://example.com/bad.png", "mime": "image/png"},
                    channel_id=4,
                    download_dir=self.tmp_dir,
                )

        # Baixa resolução inadequada (100x100)
        low = self.tmp_dir / "low.png"
        _make_png(low, "#111111", size="100x100")
        reg_low = self.aie.register_asset(str(low), origin="local", license_name="CC0")
        self.assertEqual(reg_low["validation_status"], "INCOMPATIBLE")

        # Hash duplicado
        good = self.tmp_dir / "good.png"
        _make_png(good, "#223344", size="1080x1920")
        r1 = self.aie.register_asset(str(good), origin="local", license_name="CC0")
        good2 = self.tmp_dir / "good2.png"
        shutil.copy2(good, good2)
        r2 = self.aie.register_asset(str(good2), origin="local", license_name="CC0")
        self.assertTrue(r2["deduplicated"])
        self.assertEqual(r1["sha256"], r2["sha256"])

    def test_05_unassign_incorrect_asset_and_blocks_missing_or_unapproved(self):
        pkg = self.eng.generate_package(channel_id=4, theme="Por que o céu noturno é escuro mesmo com bilhões de estrelas")
        p = self.tmp_dir / "sky.png"
        _make_png(p, "#001122")
        ast = self.aie.register_asset(str(p), origin="local", license_name="CC0", authorized_channels=[4])

        # Associa e depois remove associação incorreta
        self.eng.assign_asset_to_scene(pkg["id"], 1, ast["id"])
        unassigned = self.eng.unassign_asset_from_scene(pkg["id"], 1)
        s1 = unassigned["package"]["package"]["audiovisual_plan"]["scenes"][0]
        self.assertEqual(s1["media_asset_status"], "ASSET_NEEDED")

        # Bloqueio sem aprovação
        j_unapproved = self.renderer.render_package(pkg["id"])
        self.assertEqual(j_unapproved["status"], "BLOCKED")

        # Aprovado mas sem assets -> bloqueio com pendências
        self.eng.transition_status(pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Aprovado no teste")
        j_no_assets = self.renderer.render_package(pkg["id"])
        self.assertEqual(j_no_assets["status"], "BLOCKED")
        self.assertEqual(j_no_assets["checkpoint_stage"], "PREPARING_ASSETS")

    def test_06_checkpoint_recovery_physical_render_and_persistence(self):
        pkg = self.eng.generate_package(
            channel_id=4,
            theme="Por que o céu noturno é escuro mesmo com bilhões de estrelas",
            target_duration_sec=12.0,
        )
        self.eng.transition_status(pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Aprovado")
        # 1) Falha por falta de assets cria checkpoint BLOCKED
        j1 = self.renderer.render_package(pkg["id"])
        self.assertEqual(j1["status"], "BLOCKED")

        # 2) Associa ativos reais às cenas e retoma mesmo job_id
        scenes = pkg["package"]["audiovisual_plan"]["scenes"]
        for sc in scenes:
            img = self.tmp_dir / f"sc_{sc['scene_index']}.png"
            _make_png(img, f"#1010{sc['scene_index']}0")
            ast = self.aie.register_asset(str(img), origin="own_library", license_name="CC0", authorized_channels=[4])
            self.eng.assign_asset_to_scene(pkg["id"], sc["scene_index"], ast["id"])

        j2 = self.renderer.render_package(pkg["id"], resume_job_id=j1["id"])
        self.assertEqual(j2["id"], j1["id"])
        self.assertEqual(j2["status"], "READY_FOR_REVIEW")
        self.assertTrue(Path(j2["output_mp4_path"]).is_file())
        self.assertEqual(j2["resolution"], "1080x1920")
        self.assertEqual(len(j2["sha256"]), 64)
        reloaded = self.renderer.get_job(j2["id"])
        self.assertEqual(reloaded["sha256"], j2["sha256"])


if __name__ == "__main__":
    unittest.main()
