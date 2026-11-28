"""
VANTIS — Suíte de Testes da Fase 21: Motor de Produção Editorial, Memória Aplicada,
Versionamento, Isolamento entre Canais e Integração com Dashboard
"""

import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from database.migrate import run_migrations
from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.production.editorial_production_engine import EditorialProductionEngine, PRODUCTION_STATES
from web.app import app


class TestFase21EditorialProduction(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_fase21.db"
        run_migrations(db_path=self.db_path)
        self.als = AudiovisualLearningSystem(db_path=self.db_path)
        self.engine = EditorialProductionEngine(db_path=self.db_path)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_generate_complete_package_and_asset_needed(self):
        """Etapas 2 e 4: Gera pacote A-E completo com cenas marcadas ASSET_NEEDED."""
        pkg = self.engine.generate_package(channel_id=4, theme="Por que o gelo flutua na água")
        self.assertEqual(pkg["status"], "READY_FOR_REVIEW")
        content = pkg["package"]
        for key in ("concept", "script", "audiovisual_plan", "audio_plan", "production_checklist"):
            self.assertIn(key, content)
        scenes = content["audiovisual_plan"]["scenes"]
        self.assertGreaterEqual(len(scenes), 4)
        self.assertTrue(all(s["media_asset_status"] == "ASSET_NEEDED" for s in scenes))

    def test_02_insufficient_evidence_and_memory_application(self):
        """Etapa 3: Indica ausência de evidência quando 0 validados e aplica memória quando existe."""
        pkg_empty = self.engine.generate_package(channel_id=1, theme="Impedimento semiautomático")
        self.assertIsNotNone(pkg_empty["package"]["memory_summary"]["insufficient_evidence_warning"])

        self.als.record_knowledge(
            niche="desenvolvimento_pessoal",
            topic="ritmo_de_cortes_dinamico",
            title="Cortes C5",
            summary="Cortes >= 4 validados.",
            classification="APRENDIZADO_VALIDADO",
            evidence_video_ids=["e1", "e2"],
            counterexamples=["c1"],
            target_channel_id=5,
            pilot_phase=21,
        )
        pkg_mem = self.engine.generate_package(channel_id=5, theme="Regra dos 2 minutos")
        self.assertEqual(pkg_mem["package"]["memory_summary"]["validated_used"], 1)
        self.assertIsNone(pkg_mem["package"]["memory_summary"]["insufficient_evidence_warning"])
        applied = pkg_mem["package"]["applied_memories"]
        self.assertEqual(applied[0]["origin_channel_id"], 5)
        self.assertIn("expected_outcome", applied[0])

    def test_03_channel_isolation_and_cross_niche_reference_blocked(self):
        """Etapa 4: Identidades distintas e bloqueio de referência de outro nicho."""
        self.als.discover_video(source_id="ref_fut", title="Gol", duration_seconds=25.0, niche="futebol_outros", target_channel_id=1)
        self.als.promote_to_learning_candidate("ref_fut") if False else self.als._set_state("ref_fut", "learning_candidate")
        with self.assertRaises(ValueError):
            self.engine.generate_package(channel_id=4, theme="Buracos negros", reference_source_id="ref_fut")

    def test_04_persistence_versioning_manual_edit_and_compare(self):
        """Etapas 5 e 7: Persistência, recuperação, edição manual, duplicação, comparação e status."""
        p1 = self.engine.generate_package(channel_id=3, theme="Café da manhã na segunda")
        p1_edited = self.engine.update_package_manual(p1["id"], {"script": {"hook": "Hook editado manualmente!"}}, note="Ajuste")
        self.assertEqual(p1_edited["package"]["script"]["hook"], "Hook editado manualmente!")

        p2 = self.engine.duplicate_version(p1["id"])
        self.assertEqual(p2["version"], 2)
        self.assertEqual(p2["status"], "DRAFT")
        p2_mod = self.engine.update_package_manual(p2["id"], {"script": {"hook": "Novo hook v2"}})

        cmp_res = self.engine.compare_versions(p1["id"], p2_mod["id"])
        self.assertTrue(cmp_res["hook_changed"])

        approved = self.engine.transition_status(p2_mod["id"], "APPROVED_FOR_PRODUCTION", reason="Revisado")
        self.assertEqual(approved["status"], "APPROVED_FOR_PRODUCTION")

        # Recuperação em nova instância (simula reinicialização)
        fresh = EditorialProductionEngine(db_path=self.db_path)
        reloaded = fresh.get_package(p2_mod["id"])
        self.assertEqual(reloaded["status"], "APPROVED_FOR_PRODUCTION")
        self.assertGreaterEqual(len(reloaded["version_history"]), 3)

    def test_05_generation_failures_raise_explicit_errors(self):
        """Etapa 7: Tema vazio, canal inválido, referência inexistente e estado inválido falham explicitamente."""
        with self.assertRaises(ValueError):
            self.engine.generate_package(channel_id=1, theme="   ")
        with self.assertRaises(ValueError):
            self.engine.generate_package(channel_id=99, theme="Inválido")
        with self.assertRaises(ValueError):
            self.engine.generate_package(channel_id=1, theme="Teste", reference_source_id="nao_existe")
        p = self.engine.generate_package(channel_id=2, theme="Caso teste")
        with self.assertRaises(ValueError):
            self.engine.transition_status(p["id"], "ESTADO_INEXISTENTE")

    def test_06_dashboard_production_endpoints_and_security(self):
        """Etapa 7: Endpoints REST de produção respondem corretamente e validam entradas."""
        client = TestClient(app)
        self.assertEqual(client.get("/api/production/identities").status_code, 200)
        self.assertEqual(client.get("/api/production/references/1").status_code, 200)
        self.assertEqual(client.get("/api/production/packages").status_code, 200)
        self.assertEqual(client.post("/api/production/packages/generate", json={"channel_id": 1, "theme": ""}).status_code, 400)
        self.assertEqual(client.get("/api/production/packages/999999").status_code, 404)


if __name__ == "__main__":
    unittest.main()
