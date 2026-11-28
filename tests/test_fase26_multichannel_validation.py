import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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


class TestFase26MultichannelValidation(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="vantis_f26_"))
        self.db_path = self.tmp_dir / "test_f26.db"
        run_migrations(str(self.db_path))
        self.aie = AssetIntelligenceEngine(db_path=str(self.db_path))
        self.eng = EditorialProductionEngine(db_path=str(self.db_path))
        self.renderer = PackageRendererService(db_path=str(self.db_path), output_dir=str(self.tmp_dir / "renders"))

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_audit_first_render_and_job2_physical_files_if_present(self):
        # Valida integridade física do render mais recente se presente no workspace
        mp4_job2 = BASE_DIR / "workspace" / "renders" / "vantis_ch4_pkg7_job2.mp4"
        if mp4_job2.is_file():
            dec = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(mp4_job2), "-f", "null", "-"],
                capture_output=True,
                text=True,
                timeout=45,
            )
            self.assertEqual(dec.returncode, 0)
            self.assertGreater(mp4_job2.stat().st_size, 100000)

    def test_02_five_channels_editorial_identity_separation_and_validation(self):
        themes = {
            1: "A regra esquecida do impedimento que decidiu uma semifinal",
            2: "O detalhe cronológico que revelou a contradição de um álibi real",
            3: "Quando a reunião online de segunda-feira dura mais que o projeto",
            4: "Por que o céu noturno é escuro mesmo com bilhões de estrelas",
            5: "A armadilha dos micro-objetivos que destrói seu bloco de foco",
        }
        hooks = set()
        for ch_id, theme in themes.items():
            pkg = self.eng.generate_package(channel_id=ch_id, theme=theme)
            hooks.add(pkg["package"]["script"]["hook"])
            val = self.eng.validate_package_and_store(pkg["id"])
            self.assertEqual(val["classification"], "ASSETS_INCOMPLETE")
            self.assertTrue(val["checks"]["complete_script_no_none"])
            self.assertTrue(val["checks"]["channel_isolation_and_fit"])
        self.assertEqual(len(hooks), 5)

    def test_03_blocks_unverified_license_and_incomplete_packages(self):
        img = self.tmp_dir / "unverified.png"
        _make_png(img, "#334455")
        ast_unv = self.aie.register_asset(str(img), origin="web", license_name="UNKNOWN")
        self.assertEqual(ast_unv["license_status"], "LICENSE_UNVERIFIED")

        pkg = self.eng.generate_package(channel_id=1, theme="A regra esquecida do impedimento que decidiu uma semifinal")
        with self.assertRaises(ValueError):
            self.eng.assign_asset_to_scene(pkg["id"], 1, ast_unv["id"])

        # Sem aprovação -> BLOCKED
        j1 = self.renderer.render_package(pkg["id"])
        self.assertEqual(j1["status"], "BLOCKED")

        # Aprovado mas sem assets completos -> BLOCKED
        self.eng.transition_status(pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Aprovado no teste")
        j2 = self.renderer.render_package(pkg["id"])
        self.assertEqual(j2["status"], "BLOCKED")
        self.assertGreater(len(j2["pending_assets"]), 0)

    def test_04_review_states_and_no_auto_publish(self):
        pkg = self.eng.generate_package(
            channel_id=5,
            theme="A armadilha dos micro-objetivos que destrói seu bloco de foco",
            target_duration_sec=12.0,
        )
        self.eng.transition_status(pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Aprovado no teste")
        for sc in pkg["package"]["audiovisual_plan"]["scenes"]:
            p = self.tmp_dir / f"p_{sc['scene_index']}.png"
            _make_png(p, f"#2030{sc['scene_index']}0")
            ast = self.aie.register_asset(str(p), origin="own_library", license_name="CC0", authorized_channels=[5])
            self.eng.assign_asset_to_scene(pkg["id"], sc["scene_index"], ast["id"])

        job = self.renderer.render_package(pkg["id"])
        self.assertEqual(job["status"], "READY_FOR_REVIEW")

        # Transição explícita para APPROVED_AFTER_REVIEW
        reviewed = self.renderer.submit_human_review(
            job["id"],
            decision="APPROVE_AFTER_REVIEW",
            notes="Aprovado após revisão editorial",
            defects=[],
        )
        self.assertEqual(reviewed["status"], "APPROVED_AFTER_REVIEW")
        self.assertNotIn("youtube_url", reviewed)

        # Persistência
        reloaded = self.renderer.get_job(job["id"])
        self.assertEqual(reloaded["status"], "APPROVED_AFTER_REVIEW")

    def test_05_checkpoint_failure_recovery(self):
        pkg = self.eng.generate_package(channel_id=3, theme="Quando a reunião online de segunda-feira dura mais que o projeto", target_duration_sec=12.0)
        self.eng.transition_status(pkg["id"], "APPROVED_FOR_PRODUCTION", reason="Aprovado")
        j_fail = self.renderer.render_package(pkg["id"])
        self.assertEqual(j_fail["status"], "BLOCKED")

        for sc in pkg["package"]["audiovisual_plan"]["scenes"]:
            p = self.tmp_dir / f"h_{sc['scene_index']}.png"
            _make_png(p, f"#4020{sc['scene_index']}0")
            ast = self.aie.register_asset(str(p), origin="own_library", license_name="CC0", authorized_channels=[3])
            self.eng.assign_asset_to_scene(pkg["id"], sc["scene_index"], ast["id"])

        j_ok = self.renderer.render_package(pkg["id"], resume_job_id=j_fail["id"])
        self.assertEqual(j_ok["id"], j_fail["id"])
        self.assertEqual(j_ok["status"], "READY_FOR_REVIEW")


if __name__ == "__main__":
    unittest.main()
