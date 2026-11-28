import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from services.production.brand_registry import BrandRegistryService
from services.production.editorial_production_engine import EditorialProductionEngine


class TestFase27BrandIdentityAndYouTubeRegistry(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="vantis_f27_"))
        self.db_path = self.tmp_dir / "test_f27.db"
        run_migrations(str(self.db_path))
        self.reg = BrandRegistryService(db_path=str(self.db_path))
        self.eng = EditorialProductionEngine(db_path=str(self.db_path))

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_five_brands_seeded_with_category_separation_and_no_fake_ids(self):
        brands = self.reg.list_brands()
        self.assertEqual(len(brands), 5)
        expected = {
            1: ("Zona de Jogo", "Futebol"),
            2: ("Dossiê Oculto", "Arquivo Sombrio"),
            3: ("Caos em 60s", "Humor"),
            4: ("Horizonte Cósmico", "Ciência"),
            5: ("Modo Ascensão", "Produtividade"),
        }
        for b in brands:
            ch = b["channel_id"]
            self.assertEqual(b["brand_name"], expected[ch][0])
            self.assertEqual(b["editorial_category"], expected[ch][1])
            self.assertIsNone(b["youtube_channel_id"])
            self.assertIsNone(b["youtube_handle"])
            self.assertIsNone(b["youtube_url"])
            self.assertEqual(b["channel_status"], "CHANNEL_NOT_CREATED")
            self.assertEqual(b["oauth_status"], "OAUTH_DISCONNECTED")
            self.assertFalse(b["channel_exists_on_youtube"])
            self.assertEqual(b["branding_config"]["visual_approval_status"], "PENDING_HUMAN_APPROVAL")

    def test_02_historical_package_compatibility_and_brand_edit_persistence(self):
        pkg = self.eng.generate_package(channel_id=4, theme="Por que o céu noturno é escuro mesmo com bilhões de estrelas")
        self.assertEqual(pkg["niche"], "curiosidades")
        self.assertIn("Ciência", pkg["channel_name"])

        updated = self.reg.update_brand_identity(
            4,
            brand_name="Horizonte Cósmico Brasil",
            branding_config={"typography": "Space Grotesk Bold"},
        )
        self.assertEqual(updated["brand_name"], "Horizonte Cósmico Brasil")
        self.assertEqual(updated["editorial_category"], "Ciência")
        self.assertEqual(updated["branding_config"]["typography"], "Space Grotesk Bold")
        reloaded = self.reg.get_brand(4)
        self.assertEqual(reloaded["brand_name"], "Horizonte Cósmico Brasil")

    def test_03_validates_real_youtube_ids_and_rejects_fictitious_data(self):
        # Rejeita ID fictício / inválido
        for bad_id in ("UC_FAKE_123", "test_channel_id", "12345"):
            with self.assertRaises(ValueError):
                self.reg.register_youtube_channel(1, bad_id, "@zonadejogo_br", "https://www.youtube.com/@zonadejogo_br")

        # Rejeita URL inválida
        with self.assertRaises(ValueError):
            self.reg.register_youtube_channel(1, "UCxxxxxxxxxxxxxxxxxxxxxx", "@zonadejogo_br", "http://example.com/canal")

        # Aceita padrão válido sem simular OAuth ou verificação
        ok = self.reg.register_youtube_channel(
            1,
            "UCAbCdEfGhIjKlMnOpQrStUv",
            "@zonadejogo_oficial",
            "https://www.youtube.com/@zonadejogo_oficial",
        )
        self.assertEqual(ok["channel_status"], "CHANNEL_CREATED_UNVERIFIED")
        self.assertEqual(ok["oauth_status"], "OAUTH_DISCONNECTED")
        self.assertTrue(ok["channel_exists_on_youtube"])

    def test_04_oauth_never_simulated_and_blocks_unapproved_or_unverified_publish(self):
        pkg = self.eng.generate_package(channel_id=4, theme="Por que o céu noturno é escuro mesmo com bilhões de estrelas")

        # OAuth check sem token real continua OAUTH_DISCONNECTED
        oauth_res = self.reg.verify_oauth_connection(4)
        self.assertEqual(oauth_res["oauth_status"], "OAUTH_DISCONNECTED")

        # Bloqueio de publicação sem aprovação e sem canal verificado
        meta = self.reg.prepare_publish_metadata(pkg["id"])
        self.assertFalse(meta["ready_to_upload"])
        self.assertGreaterEqual(len(meta["blockers"]), 2)
        self.assertEqual(meta["brand_name"], "Horizonte Cósmico")
        self.assertEqual(meta["editorial_category"], "Ciência")

    def test_05_dashboard_api_integration(self):
        from fastapi.testclient import TestClient
        import web.app as webapp

        client = TestClient(webapp.app)
        r_list = client.get("/api/brands")
        self.assertEqual(r_list.status_code, 200)
        brands = r_list.json().get("brands", [])
        self.assertEqual(len(brands), 5)

        r_oauth = client.post("/api/brands/4/oauth-check")
        self.assertEqual(r_oauth.status_code, 200)
        self.assertEqual(r_oauth.json()["oauth_status"], "OAUTH_DISCONNECTED")


if __name__ == "__main__":
    unittest.main()
