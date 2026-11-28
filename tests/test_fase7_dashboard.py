"""
Testes Automatizados - Fase 7: Interface Visual Unificada & Dashboard de Controle
Verifica a integração dos portais 1 e 2, endpoints de KPIs, canais piloto,
reprodução de mídias e ciclo de aprovação humana expressa no Portal 2.
"""

import os
import sys
import json
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Adiciona raiz do projeto ao path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from web.app import app
from database.db import get_db_connection

class TestFase7DashboardUI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_dashboard_root_serves_html(self):
        """Testa se a raiz / serve o index.html com os Portais 1 e 2 e canais piloto."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("Portal 1", html)
        self.assertIn("Portal 2", html)
        self.assertIn("pilot-channels-grid", html)
        self.assertIn("p1-opportunities-tbody", html)
        self.assertIn("portal2-items-container", html)

    def test_dashboard_kpis_endpoint(self):
        """Testa o endpoint consolidado de KPIs com barreira de custo zero e armazenamento 5TB."""
        response = self.client.get("/api/dashboard/kpis")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Validação de canais
        self.assertIn("channels", data)
        self.assertEqual(data["channels"]["total"], 20)
        self.assertEqual(data["channels"]["pilot_active"], 5)

        # Validação de oportunidades e fila
        self.assertIn("opportunities", data)
        self.assertIn("queue", data)
        self.assertIn("portal2", data)
        self.assertIn("publications", data)

        # Barreira de custo zero
        self.assertIn("costs", data)
        self.assertEqual(data["costs"]["total_spent_usd"], 0.0)
        self.assertTrue(data["costs"]["enforce_free_tier"])

        # Armazenamento Google Drive 5 TB
        self.assertIn("storage", data)
        self.assertEqual(data["storage"]["total_gb"], 5120.0)
        self.assertGreaterEqual(data["storage"]["used_percent"], 0.0)

    def test_dashboard_channels_pilot_showcase(self):
        """Testa listagem dos 5 canais piloto com suas identidades editoriais e pastas no Drive."""
        response = self.client.get("/api/channels")
        self.assertEqual(response.status_code, 200)
        channels = response.json()
        self.assertGreaterEqual(len(channels), 20)

        pilots = [ch for ch in channels if ch["id"] <= 5]
        self.assertEqual(len(pilots), 5)

        for p in pilots:
            self.assertIsNotNone(p["name"])
            self.assertIsNotNone(p["niche"])
            self.assertIsNotNone(p["gdrive_folder_id"])
            self.assertGreater(len(p["gdrive_folder_id"]), 10)
            self.assertIn(p["daily_upload_limit"], [3, 6])

    def test_portal1_api_integration(self):
        """Testa consulta ao Portal 1 com filtros de status."""
        # Consulta pendentes
        res_pending = self.client.get("/api/portal1/opportunities?status=PENDING_REVIEW")
        self.assertEqual(res_pending.status_code, 200)
        self.assertIsInstance(res_pending.json(), list)

        # Consulta todas
        res_all = self.client.get("/api/portal1/opportunities?status=")
        self.assertEqual(res_all.status_code, 200)
        self.assertIsInstance(res_all.json(), list)

    def test_media_preview_security_and_streaming(self):
        """Testa o endpoint seguro de streaming de mídia para inspeção pré-publicação."""
        # 1. Tipo de mídia inválido rejeitado com 400
        res_invalid = self.client.get("/api/media/preview/hack/test.mp4")
        self.assertEqual(res_invalid.status_code, 400)

        # 2. Arquivo inexistente retorna 404
        res_not_found = self.client.get("/api/media/preview/clips/non_existent_clip_12345.mp4")
        self.assertEqual(res_not_found.status_code, 404)

        # 3. Cria arquivo temporário de áudio e testa streaming
        audio_dir = BASE_DIR / "workspace" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        test_file = audio_dir / "test_stream_audio.mp3"
        test_file.write_bytes(b"ID3TestFakeAudioContentForDashboardPreviewStream")

        try:
            res_stream = self.client.get(f"/api/media/preview/audio/{test_file.name}")
            self.assertEqual(res_stream.status_code, 200)
            self.assertEqual(res_stream.content, b"ID3TestFakeAudioContentForDashboardPreviewStream")
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_portal2_pending_and_human_approval_flow(self):
        """Testa o fluxo completo do Portal 2: retenção, inspeção QC e aprovação com publicação privada."""
        test_task_id = "task_dashboard_portal2_test_001"

        # 1. Cria um checkpoint simulado retido no Portal 2 (Step 11 PAUSED_FOR_REVIEW)
        state_data = {
            "task_id": test_task_id,
            "channel_id": 1,
            "target_id": "opp_futebol_preview_test",
            "niche": "futebol_outros",
            "current_step": "11_revisao_humana",
            "status": "PAUSED_FOR_REVIEW",
            "completed_steps": [
                "1_oportunidade", "2_analise_nicho", "3_estudo_referencias",
                "4_estrategia_editorial", "5_pesquisa_aprofundada", "6_direcao_criativa",
                "7_revisao_pauta", "8_geracao_roteiros", "9_preparacao_materiais",
                "10_edicao_audiovisual", "11_revisao_humana"
            ],
            "step_results": {
                "8_geracao_roteiros": {
                    "script": "HOOK: O dia em que o Pelé parou a guerra!\nCORPO: Em 1969 o Santos foi à Nigéria...\nCTA: Inscreva-se!"
                },
                "9_preparacao_materiais": {
                    "audio_path": "workspace/audio/test_audio.mp3",
                    "ass_path": "workspace/subs/test_sub.ass"
                },
                "10_edicao_audiovisual": {
                    "output_clip_path": "workspace/clips/test_clip.mp4"
                },
                "11_revisao_humana": {
                    "qc_score": 94,
                    "qc_status": "APPROVED_BY_QC",
                    "qc_report": {
                        "score": 94,
                        "status": "APPROVED_BY_QC",
                        "passed": True,
                        "checks": [
                            {"check": "aspect_ratio_9_16", "passed": True, "details": "1080x1920"},
                            {"check": "duration_bounds", "passed": True, "details": "32.5s"},
                            {"check": "audio_loudness_ebur128", "passed": True, "details": "-14.2 LUFS"},
                            {"check": "subtitle_events", "passed": True, "details": "ASS format conforme"}
                        ]
                    }
                }
            }
        }

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM workflow_checkpoints WHERE task_id = ?", (test_task_id,))
            cur.execute("""
                INSERT INTO workflow_checkpoints (task_id, target_id, niche, current_step, status, state_json, channel_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                test_task_id,
                "opp_futebol_preview_test",
                "futebol_outros",
                "11_revisao_humana",
                "PAUSED_FOR_REVIEW",
                json.dumps(state_data),
                1
            ))
            conn.commit()

        # 2. Verifica se aparece no GET /api/dashboard/portal2/pending
        res_pending = self.client.get("/api/dashboard/portal2/pending")
        self.assertEqual(res_pending.status_code, 200)
        pending_items = res_pending.json()
        target_item = next((item for item in pending_items if item["task_id"] == test_task_id), None)
        self.assertIsNotNone(target_item)
        self.assertEqual(target_item["qc_score"], 94)
        self.assertEqual(target_item["status"], "PAUSED_FOR_REVIEW")
        self.assertIn("HOOK: O dia em que o Pelé parou a guerra!", target_item["script_preview"])

        # 3. Dispara a aprovação humana expressa com token via POST /api/dashboard/portal2/approve/{task_id}
        approval_token = "PORTAL2_TOKEN_DASHBOARD_VERIFIED"
        res_approve = self.client.post(
            f"/api/dashboard/portal2/approve/{test_task_id}",
            json={"approval_token": approval_token, "channel_id": 1}
        )
        self.assertEqual(res_approve.status_code, 200)
        data = res_approve.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "COMPLETED")
        self.assertIn("12_distribuicao", data["completed_steps"])

        pub = data["publication_result"]
        self.assertEqual(pub["privacy_status"], "private")
        self.assertEqual(pub["gdrive_folder_id"], "1Qcd6DS3zA0OrNKSeDSPTHyl_P0y0l9jf")
        self.assertEqual(pub["channel_id"], 1)
        self.assertTrue(os.path.exists(pub["manifest_path"]))

        # 4. Verifica se saiu da lista de pendentes do Portal 2
        res_after = self.client.get("/api/dashboard/portal2/pending")
        self.assertEqual(res_after.status_code, 200)
        still_pending = [item for item in res_after.json() if item["task_id"] == test_task_id]
        self.assertEqual(len(still_pending), 0)

        # Limpeza do checkpoint de teste
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM workflow_checkpoints WHERE task_id = ?", (test_task_id,))
            conn.commit()

if __name__ == "__main__":
    unittest.main()
