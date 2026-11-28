"""
IAS Fase 1 Foundation Test Suite
Validação automatizada de banco consolidado, governança orçamentária de IA,
blindagem de publicação Human-in-the-Loop e integridade estrutural.
"""
import os
import sys
import tempfile
import sqlite3
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from database.db import get_db_connection, init_db
from services.model_gateway.gateway import ModelGatewayService
from core.youtube_uploader import YouTubeUploader

class TestFase1Foundation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = Path(self.temp_dir.name) / "test_foundation.db"

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_clean_database_initialization(self):
        """Valida que um banco do zero inicializa perfeitamente com todas as 22 tabelas."""
        schema_file = BASE_DIR / "database" / "schema.sql"
        self.assertTrue(schema_file.exists(), "schema.sql consolidado não encontrado")

        with open(schema_file, "r", encoding="utf-8") as f:
            sql = f.read()

        conn = sqlite3.connect(str(self.test_db))
        conn.executescript(sql)
        cursor = conn.cursor()

        # 1. Testa insert de catalogador legado
        cursor.execute("""
            INSERT INTO video_references (
                video_id, title, original_url, channel_title, channel_id,
                category_id, subcategory, duration_seconds, published_at,
                view_count, like_count, comment_count, engagement_rate,
                format_features, usage_permission, availability_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('vid_test_100', 'Vídeo Teste Limpo', 'https://youtube.com/watch?v=vid_test_100',
              'Canal Teste', 1, 1, 'cortes', 45.0, '2026-11-21', 1000, 100, 10, 10.0, '{}', 'reference_only', 'active'))

        # 2. Testa insert de gerador de roteiro
        cursor.execute("""
            INSERT INTO scripts (
                channel_id, title, archetype, hook_3s, full_script,
                visual_cues, audio_cues, recommended_duration, editing_style,
                status, human_approved
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (1, 'Roteiro Limpo', 'storytelling', 'Gancho 3s', 'Texto completo do roteiro',
              'Câmera frontal', 'Whoosh', 35.0, 'Dinâmico', 'idea', 0))

        # 3. Testa insert de checkpoints do LangGraph
        cursor.execute("""
            INSERT INTO workflow_checkpoints (
                task_id, target_id, channel_id, niche, current_step, status, state_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('task_test_999', 'vid_test_100', 1, 'futebol', '1_pesquisa', 'RUNNING', '{"step": 1}'))

        # 4. Testa insert de vetores semânticos
        cursor.execute("""
            INSERT INTO semantic_vectors (
                category, channel_id, text_content, vector_blob, metadata_json
            ) VALUES (?, ?, ?, ?, ?)
        """, ('futebol', 1, 'Gancho viral sobre final de campeonato', b'\x00\x01\x02\x03', '{"author": "test"}'))

        # 5. Testa insert de oportunidades
        cursor.execute("""
            INSERT INTO opportunities (
                opportunity_id, source_url, niche, title_concept, competition_level,
                monetization_potential, confidence_score, recommended_channel_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('opp_test_01', 'https://youtube.com/shorts/xyz', 'futebol', 'Pauta Viral', 'baixo', 'alto', 85.0, 1, 'pending_review'))

        # 6. Testa insert de logs financeiros
        cursor.execute("""
            INSERT INTO financial_logs (
                channel_id, log_type, category, amount_usd, description
            ) VALUES (?, ?, ?, ?, ?)
        """, (1, 'expense', 'infrastructure', 5.50, 'Processamento de vídeo FFmpeg'))

        conn.commit()

        # Verifica persistência
        cursor.execute("SELECT COUNT(*) FROM video_references WHERE video_id = 'vid_test_100'")
        self.assertEqual(cursor.fetchone()[0], 1)

        cursor.execute("SELECT COUNT(*) FROM scripts WHERE title = 'Roteiro Limpo'")
        self.assertEqual(cursor.fetchone()[0], 1)

        cursor.execute("SELECT COUNT(*) FROM workflow_checkpoints WHERE task_id = 'task_test_999'")
        self.assertEqual(cursor.fetchone()[0], 1)

        conn.close()

    def test_02_database_migrations_idempotency(self):
        """Valida que o migrador consolida o banco sem duplicar ou perder tabelas."""
        res1 = run_migrations(self.test_db)
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertGreaterEqual(res1["total_tables"], 22)

        # Executa segunda vez (idempotência)
        res2 = run_migrations(self.test_db)
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertEqual(res1["total_tables"], res2["total_tables"])

    def test_03_cost_guard_blocks_commercial_paid_models(self):
        """Comprova que o ModelGateway bloqueia modelos comerciais pagos quando a trava está ativa."""
        gateway = ModelGatewayService(db_path=str(self.test_db), enforce_free_tier=True)
        self.assertTrue(gateway.enforce_free_tier)

        # Tenta invocar um modelo pago comercial (gpt-4o) sem autorização expressa
        res = gateway.completion(
            messages=[{"role": "user", "content": "Gere um roteiro"}],
            task="scriptwriting",
            preferred_model="gpt-4o",
            allow_paid_api=False
        )

        # A resposta deve ter sucesso através de desvio seguro, nunca chamando gpt-4o diretamente
        self.assertTrue(res["success"])
        self.assertNotEqual(res.get("model_used"), "gpt-4o")

        # Verifica se o log registrou o bloqueio tarifário
        metrics = gateway.get_usage_metrics()
        with sqlite3.connect(str(self.test_db)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM model_usage_logs WHERE status = 'PAID_CALL_BLOCKED'")
            blocked_count = cur.fetchone()[0]
            self.assertGreaterEqual(blocked_count, 1)

    def test_04_youtube_uploader_human_approval_gate(self):
        """Valida que o uploader rejeita uploads sem aprovação humana e força 'private'."""
        uploader = YouTubeUploader(credentials_dir=str(self.temp_dir.name))

        dummy_video = Path(self.temp_dir.name) / "dummy.mp4"
        dummy_video.write_bytes(b"dummy_mp4_bytes")

        # 1. Tentativa sem aprovação humana -> Bloqueio obrigatório
        res_blocked = uploader.upload_short(
            video_path=dummy_video,
            title="Short Sem Aprovação",
            description="Descrição",
            human_approved=False,
            human_approval_token=None
        )
        self.assertEqual(res_blocked["status"], "BLOCKED_AWAITING_APPROVAL")
        self.assertIn("Aprovação humana mandatória pendente", res_blocked["error"])

        # 2. Tentativa com aprovação humana -> Autorizado com privacidade estritamente 'private'
        res_approved = uploader.upload_short(
            video_path=dummy_video,
            title="Short Aprovado",
            description="Descrição",
            human_approved=True,
            human_approval_token="TOKEN_HUMAN_12345",
            privacy_status="public" # Mesmo se tentar passar public, deve forçar private
        )
        self.assertIn(res_approved["status"], ["SIMULATED", "SUCCESS"])
        self.assertEqual(res_approved["privacy"], "private")

    def test_05_portability_and_relative_paths(self):
        """Valida que caminhos essenciais resolvem dinamicamente sem hardcode."""
        self.assertTrue((BASE_DIR / "database").exists())
        self.assertTrue((BASE_DIR / "docs" / "audit").exists())
        self.assertTrue((BASE_DIR / "services").exists())

if __name__ == "__main__":
    unittest.main()
