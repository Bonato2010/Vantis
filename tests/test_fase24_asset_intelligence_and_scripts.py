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
from services.production.asset_intelligence import AssetIntelligenceEngine, normalize_license_status
from services.production.editorial_production_engine import EditorialProductionEngine
from services.production.script_quality_engine import EditorialValidator, clean_accidental_repetitions


def _make_png(path: Path, color: str = "#112233", size: str = "1080x1920") -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={size}:d=1", "-frames:v", "1", str(path)],
        capture_output=True,
        check=True,
        timeout=30,
    )


class TestFase24AssetIntelligenceAndScripts(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="vantis_f24_"))
        self.db_path = self.tmp_dir / "test_f24.db"
        run_migrations(str(self.db_path))
        self.aie = AssetIntelligenceEngine(db_path=str(self.db_path))
        self.eng = EditorialProductionEngine(db_path=str(self.db_path))

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_asset_integrity_hash_deduplication_and_benchmark_block(self):
        # Arquivo corrompido
        bad = self.tmp_dir / "corrupt.png"
        bad.write_bytes(b"not a real png")
        res_bad = self.aie.register_asset(str(bad), origin="local", license_name="CC0")
        self.assertEqual(res_bad["validation_status"], "CORRUPT")

        # Arquivo válido + deduplicação SHA256
        good = self.tmp_dir / "valid.png"
        _make_png(good, "#224466")
        res1 = self.aie.register_asset(str(good), origin="own_library", license_name="CC0", tags=["futebol", "lance"])
        self.assertEqual(res1["validation_status"], "VALID")
        self.assertEqual(res1["license_status"], "VERIFIED_CC0")
        self.assertFalse(res1["deduplicated"])

        dup_copy = self.tmp_dir / "valid_copy.png"
        shutil.copy2(good, dup_copy)
        res2 = self.aie.register_asset(str(dup_copy), origin="own_library", license_name="CC0")
        self.assertTrue(res2["deduplicated"])
        self.assertEqual(res1["sha256"], res2["sha256"])

        # Proibição de vídeos do benchmark250
        bm_dir = self.tmp_dir / "benchmark250"
        bm_dir.mkdir()
        bm_file = bm_dir / "ref.png"
        shutil.copy2(good, bm_file)
        with self.assertRaises(ValueError):
            self.aie.register_asset(str(bm_file), origin="benchmark", license_name="CC0")

    def test_02_license_verification_and_unverified_handling(self):
        self.assertEqual(normalize_license_status("CC0 1.0")[0], "VERIFIED_CC0")
        self.assertEqual(normalize_license_status("CC BY 4.0")[0], "VERIFIED_CC_BY")
        self.assertEqual(normalize_license_status("CC BY-NC 4.0")[0], "RESTRICTED")
        self.assertEqual(normalize_license_status("Royalty Free", commercial_confirmed=False)[0], "LICENSE_UNVERIFIED")
        self.assertEqual(normalize_license_status("UNKNOWN")[0], "LICENSE_UNVERIFIED")

    def test_03_channel_isolation_and_scene_asset_association(self):
        img = self.tmp_dir / "futebol_estadio.png"
        _make_png(img, "#005522")
        ast = self.aie.register_asset(
            str(img),
            origin="own_library",
            license_name="CC0",
            tags=["futebol", "impedimento", "abertura"],
            authorized_channels=[1],
        )
        pkg_ch1 = self.eng.generate_package(channel_id=1, theme="A regra esquecida do impedimento que decidiu uma semifinal")
        pkg_ch2 = self.eng.generate_package(channel_id=2, theme="O detalhe cronológico que revelou a contradição de um álibi real")

        # Canal 2 não pode receber ativo exclusivo do Canal 1
        with self.assertRaises(ValueError):
            self.eng.assign_asset_to_scene(pkg_ch2["id"], 1, ast["id"])

        # Canal 1 recebe na cena 1; demais cenas permanecem ASSET_NEEDED sem preenchimento aleatório
        prep = self.eng.prepare_package_assets(pkg_ch1["id"])
        scenes = prep["package"]["package"]["audiovisual_plan"]["scenes"]
        self.assertEqual(scenes[0]["media_asset_status"], "ASSET_READY")
        self.assertTrue(all(s["media_asset_status"] == "ASSET_NEEDED" for s in scenes[1:]))

    def test_04_validator_catches_incomplete_none_repetitions_and_missing_sources(self):
        pkg = self.eng.generate_package(channel_id=4, theme="Por que o céu noturno é escuro mesmo com bilhões de estrelas")
        val = EditorialValidator()

        # Simula roteiro defeituoso com campo None, repetição acidental e sem fontes
        broken = dict(pkg)
        broken_content = {
            "script": {
                "hook": "Sabe quando Quando isso acontece?",
                "context": "Contexto.",
                "development": "Dev.",
                "climax": None,
                "closing": "Fim.",
                "cta": "Comenta.",
                "sources": [],
            },
            "audiovisual_plan": pkg["package"]["audiovisual_plan"],
            "audio_plan": {"narration_text": "Sabe quando Quando isso acontece? Contexto. Dev. Fim. Comenta."},
            "applied_memories": [],
        }
        broken["package"] = broken_content
        rep = val.validate_package(broken)
        self.assertFalse(rep["checks"]["complete_script_no_none"])
        self.assertFalse(rep["checks"]["no_accidental_repetitions"])
        self.assertFalse(rep["checks"]["sources_verified_when_required"])
        self.assertIn(rep["classification"], ("REFERENCE_INSUFFICIENT", "SCRIPT_NEEDS_REVISION"))

        # Limpeza automática remove repetição acidental
        self.assertEqual(clean_accidental_repetitions("Sabe quando Quando isso"), "Sabe quando isso")

    def test_05_acquisition_failure_is_handled_gracefully(self):
        with patch("services.production.asset_intelligence.urlopen", side_effect=OSError("offline")):
            res = self.aie.search_wikimedia_commons("football stadium")
        self.assertFalse(res["success"])
        self.assertEqual(res["results"], [])

    def test_06_persistence_versioning_and_editorially_ready_after_all_assets(self):
        pkg = self.eng.generate_package(channel_id=5, theme="Como usar blocos de 25 minutos sem cair em fadiga decisória")
        self.assertEqual(pkg["status"], "READY_FOR_REVIEW")
        # Registra 6 ativos válidos e associa às 6 cenas
        for idx in range(1, 7):
            p = self.tmp_dir / f"prod_{idx}.png"
            _make_png(p, f"#1020{idx}0")
            ast = self.aie.register_asset(str(p), origin="own_library", license_name="CC0", authorized_channels=[5])
            out = self.eng.assign_asset_to_scene(pkg["id"], idx, ast["id"])

        self.assertEqual(out["validation"]["classification"], "EDITORIALLY_READY")
        self.assertEqual(out["validation"]["quality_score"], 100.0)
        # Nunca auto-aprova!
        self.assertEqual(out["package"]["status"], "READY_FOR_REVIEW")

        # Versionamento + comparação preservados
        v2 = self.eng.duplicate_version(pkg["id"], new_theme="Versão 2 blocos de 25 minutos")
        cmp_res = self.eng.compare_versions(pkg["id"], v2["id"])
        self.assertEqual(cmp_res["package_a"]["version"], 1)
        self.assertEqual(cmp_res["package_b"]["version"], 2)

    def test_07_dashboard_api_integration(self):
        from fastapi.testclient import TestClient
        import web.app as webapp

        client = TestClient(webapp.app)
        r_assets = client.get("/api/production/assets")
        self.assertEqual(r_assets.status_code, 200)
        r_pkgs = client.get("/api/production/packages?limit=5")
        self.assertEqual(r_pkgs.status_code, 200)
        pkgs = r_pkgs.json().get("packages", [])
        if pkgs:
            r_val = client.post(f"/api/production/packages/{pkgs[0]['id']}/validate")
            self.assertEqual(r_val.status_code, 200)
            self.assertIn("classification", r_val.json())


if __name__ == "__main__":
    unittest.main()
