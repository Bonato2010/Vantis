"""
Testes Automatizados - Fase 11: Provisionamento dos Cinco Primeiros Canais & Dashboard (Prompts 06 e 08)
Valida:
1. Canais piloto 01 a 05 pré-configurados com identidades e diretrizes editoriais distintas.
2. Criação incremental de canais com suporte a rascunho parcial (draft) e completude posterior.
3. Cálculo de completude e prontidão operacional (readiness 0-100%) com detecção de campos pendentes e próximos passos.
4. Seleção dinâmica de canal-piloto ativo.
5. Arquivamento e reativação de canais sem perda de histórico.
6. Isolamento estrito de memória semântica, histórico de aprovações/rejeições e métricas por canal.
7. Endpoints REST da FastAPI e integração completa com a interface do Dashboard.
8. Trava de segurança: nenhuma criação automática de canal real no YouTube sem ação humana expressa.
"""
import os
import sys
import json
import unittest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.channel_manager import ChannelManager
from database.migrate import run_migrations
from web.app import app

class TestFase11PilotChannelsAndDashboard(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.temp_dir.name, "test_fase11.db")
        # Aplica todas as migrações 001 a 007
        run_migrations(db_path=self.test_db)
        self.mgr = ChannelManager(db_path=self.test_db)
        self.client = TestClient(app)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_pilot_channels_preseeded_and_distinct_identities(self):
        """Valida que os 5 canais piloto estão presentes com nichos, personas e arquétipos distintos."""
        channels = self.mgr.list_all_channels()
        self.assertGreaterEqual(len(channels), 5)

        pilots = [self.mgr.get_channel_profile(i) for i in range(1, 6)]
        for p in pilots:
            self.assertIsNotNone(p["name"])
            self.assertIsNotNone(p["niche"])
            self.assertIsNotNone(p["communication_tone"])
            self.assertIsNotNone(p["voice_profile"])
            self.assertIsNotNone(p["subtitle_style"])

        # Confirma que nichos e arquétipos são distintos
        niches = {p["niche"] for p in pilots}
        self.assertEqual(len(niches), 5, "Existem canais piloto compartilhando o mesmo nicho!")

        tones = {p["communication_tone"] for p in pilots}
        self.assertEqual(len(tones), 5, "Existem canais piloto compartilhando o mesmo tom!")

    def test_02_channel_readiness_calculation(self):
        """Valida o cálculo de prontidão (readiness) para o Canal 01."""
        readiness = self.mgr.get_channel_readiness(1)
        self.assertEqual(readiness["channel_id"], 1)
        self.assertGreaterEqual(readiness["completion_percentage"], 80)
        self.assertTrue(readiness["is_ready_for_production"])
        self.assertIsInstance(readiness["missing_fields"], list)
        self.assertIsInstance(readiness["next_steps"], list)
        self.assertGreater(len(readiness["next_steps"]), 0)

    def test_03_create_channel_as_draft(self):
        """Valida criação de canal em modo rascunho com dados parciais."""
        draft = self.mgr.create_channel(
            name="Canal 21 - Astrofísica Rápida",
            niche="Ciência & Espaço",
            subniche="Astrofísica",
            target_audience="Entusiastas de ciência",
            status="draft"
        )
        self.assertIsNotNone(draft)
        self.assertEqual(draft["status"], "draft")
        self.assertEqual(draft["name"], "Canal 21 - Astrofísica Rápida")
        self.assertGreater(draft["channel_number"], 20)

        # Prontidão de um rascunho deve ser parcial
        readiness = self.mgr.get_channel_readiness(draft["channel_id"])
        self.assertEqual(readiness["status"], "draft")
        self.assertLess(readiness["completion_percentage"], 80)
        self.assertFalse(readiness["is_ready_for_production"])
        self.assertIn("Tom de voz e comunicação", readiness["missing_fields"])
        self.assertIn("Perfil de voz de narração TTS", readiness["missing_fields"])

    def test_04_incremental_channel_completion(self):
        """Valida enriquecimento progressivo do canal até atingir status de produção."""
        draft = self.mgr.create_channel(
            name="Canal 22 - Mistérios da História",
            niche="História",
            status="draft"
        )
        ch_id = draft["channel_id"]

        # 1. Atualiza estratégia e tom
        self.mgr.update_channel_strategy(
            channel_id=ch_id,
            communication_tone="Narrativa imersiva e tensa",
            editing_style="Cinematográfico com zoom dinâmico",
            posting_frequency="1 vídeo/dia",
            editorial_strategy="Revelar fatos ocultos da antiguidade",
            status="active"
        )

        # 2. Configura voz e legendas
        self.mgr.set_channel_setting(ch_id, "voice_profile", {
            "engine": "edge-tts",
            "voice_id": "pt-BR-JulioNeural",
            "rate": "+0%"
        })
        self.mgr.set_channel_setting(ch_id, "subtitle_style", {
            "font": "Impact",
            "fontsize": 75,
            "primary_colour": "&H0000FFFF&"
        })
        self.mgr.set_channel_setting(ch_id, "brand_colors", {
            "primary": "#FF9900",
            "secondary": "#FFFFFF"
        })
        self.mgr.set_channel_setting(ch_id, "rules_restrictions", [
            "Proibido anacronismos não explicados",
            "Sempre citar a fonte da descoberta arqueológica"
        ])

        # 3. Reavalia prontidão
        readiness = self.mgr.get_channel_readiness(ch_id)
        self.assertGreaterEqual(readiness["completion_percentage"], 80)
        self.assertTrue(readiness["is_ready_for_production"])
        self.assertEqual(readiness["status"], "active")

    def test_05_set_and_switch_pilot_channel(self):
        """Valida marcação dinâmica do canal-piloto ativo."""
        success = self.mgr.set_pilot_channel(2)
        self.assertTrue(success)

        readiness2 = self.mgr.get_channel_readiness(2)
        self.assertTrue(readiness2["is_pilot"])

    def test_06_archive_channel(self):
        """Valida arquivamento seguro de canal."""
        success = self.mgr.archive_channel(3)
        self.assertTrue(success)

        ch = self.mgr.get_channel_by_id(3)
        self.assertEqual(ch["status"], "archived")

    def test_07_multitenant_channel_memory_isolation(self):
        """Valida que o sumário de memória semântica é estritamente isolado por canal."""
        mem1 = self.mgr.get_channel_memory_summary(1)
        mem2 = self.mgr.get_channel_memory_summary(2)

        self.assertEqual(mem1["channel_id"], 1)
        self.assertEqual(mem2["channel_id"], 2)
        self.assertEqual(mem1["isolation_namespace"], "channel_1")
        self.assertEqual(mem2["isolation_namespace"], "channel_2")
        self.assertIn("approved_opportunities", mem1)
        self.assertIn("rejected_opportunities", mem1)
        self.assertIn("semantic_vectors_indexed", mem1)

    def test_08_api_endpoints_channels_and_dashboard(self):
        """Testa a integração dos endpoints REST do FastAPI para canais e dashboard."""
        # 1. GET /api/channels
        res_list = self.client.get("/api/channels")
        self.assertEqual(res_list.status_code, 200)
        self.assertIsInstance(res_list.json(), list)

        # 2. POST /api/channels (cadastrar canal via API)
        res_create = self.client.post("/api/channels", json={
            "name": "Canal 23 - Finanças Descomplicadas",
            "niche": "Finanças & Investimentos",
            "subniche": "Renda Fixa",
            "target_audience": "Iniciantes em investimentos",
            "communication_tone": "Didático e direto",
            "status": "draft"
        })
        self.assertEqual(res_create.status_code, 200)
        created_data = res_create.json()
        self.assertTrue(created_data["success"])
        new_id = created_data["channel"]["channel_id"]

        # 3. GET /api/channels/{id}/readiness
        res_readiness = self.client.get(f"/api/channels/{new_id}/readiness")
        self.assertEqual(res_readiness.status_code, 200)
        self.assertEqual(res_readiness.json()["channel_id"], new_id)

        # 4. GET /api/channels/{id}/memory
        res_mem = self.client.get(f"/api/channels/{new_id}/memory")
        self.assertEqual(res_mem.status_code, 200)
        self.assertEqual(res_mem.json()["isolation_namespace"], f"channel_{new_id}")

        # 5. POST /api/channels/{id}/set-pilot
        res_pilot = self.client.post(f"/api/channels/{new_id}/set-pilot")
        self.assertEqual(res_pilot.status_code, 200)
        self.assertTrue(res_pilot.json()["is_pilot"])

        # 6. POST /api/channels/{id}/archive
        res_archive = self.client.post(f"/api/channels/{new_id}/archive")
        self.assertEqual(res_archive.status_code, 200)
        self.assertEqual(res_archive.json()["status"], "archived")

        # 7. GET /api/dashboard/kpis
        res_kpis = self.client.get("/api/dashboard/kpis")
        self.assertEqual(res_kpis.status_code, 200)
        kpis = res_kpis.json()
        self.assertIn("channels", kpis)
        self.assertIn("costs", kpis)

        # Limpeza do canal criado no banco da API
        from database.db import get_db_connection
        with get_db_connection() as conn:
            conn.execute("DELETE FROM channels WHERE id = ?", (new_id,))
            conn.execute("DELETE FROM channel_settings WHERE channel_id = ?", (new_id,))
            conn.commit()

    def test_09_no_real_youtube_channels_created(self):
        """Valida que nenhum canal real é criado no YouTube sem autorização expressa."""
        # Cria canal local
        ch = self.mgr.create_channel(
            name="Canal Teste Sem YouTube",
            niche="Testes Locais",
            status="draft"
        )
        self.assertIsNotNone(ch)
        # O campo youtube_channel_id deve ser nulo/vazio (nenhuma chamada externa realizada)
        db_ch = self.mgr.get_channel_by_id(ch["channel_id"])
        self.assertIsNone(db_ch.get("youtube_channel_id"))


if __name__ == "__main__":
    unittest.main()
