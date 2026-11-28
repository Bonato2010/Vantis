"""
IAS Test Suite - Fase 6: Distribuição Segura, Google Drive & Publicação Privada
Testa:
1. Trava de segurança: Bloqueio imediato de distribuição sem aprovação humana e token do Portal 2
2. Geração e validação de manifestos de publicação (com privacyStatus 'private' forçado)
3. Roteamento de pastas no Google Drive 5 TB por canal (conforme config/gdrive_folders.json)
4. Persistência de auditoria nas tabelas 'publications', 'financial_logs' e 'video_lifecycle'
5. Execução do fluxo completo no LangGraph: Etapa 11 pausada -> Aprovação com token -> Etapa 12 concluída
"""
import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Ajusta path raiz
TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.channel_manager import ChannelManager
from core.gdrive_manager import GDriveManager
from core.youtube_uploader import YouTubeUploader
from services.distribution.distribution_service import DistributionService
from services.orchestration.langgraph_engine import IASOrchestrationEngine
from database.migrate import run_migrations


class TestFase6Distribution(unittest.TestCase):
    """Bateria de testes de distribuição segura, manifestos, Google Drive e blindagem do YouTube."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="test_distribution_")
        cls.db_path = Path(cls.temp_dir) / "test_distribution.db"
        run_migrations(db_path=cls.db_path)
        cls.channel_manager = ChannelManager(db_path=str(cls.db_path))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        self.clips_dir = Path(self.temp_dir) / "clips"
        self.clips_dir.mkdir(exist_ok=True)
        self.dist_service = DistributionService(
            db_path=str(self.db_path),
            channel_manager=self.channel_manager,
            clips_dir=self.clips_dir
        )

    def test_01_refusal_without_human_approval_token(self):
        """Valida que qualquer tentativa de publicação sem aprovação do Portal 2 é terminantemente rejeitada."""
        task_id = "task_unauthorized_dist"

        # 1. Sem aprovação humana
        with self.assertRaises(PermissionError) as ctx:
            self.dist_service.execute_distribution(
                task_id=task_id,
                channel_id=1,
                human_approved=False,
                human_approval_token=None
            )
        self.assertIn("Bloqueio de Segurança", str(ctx.exception))

        # 2. Com flag True mas token vazio
        with self.assertRaises(PermissionError) as ctx2:
            self.dist_service.execute_distribution(
                task_id=task_id,
                channel_id=1,
                human_approved=True,
                human_approval_token=""
            )
        self.assertIn("Bloqueio de Segurança", str(ctx2.exception))

        # Verifica que nenhuma publicação espúria foi inserida
        pubs = self.dist_service.list_publications(channel_id=1)
        self.assertEqual(len(pubs), 0)

    def test_02_publication_manifest_generation_and_privacy(self):
        """Gera manifesto oficial e valida obrigatoriedade de 'private' e caminhos estruturados."""
        task_id = "task_manifest_01"
        dummy_video = self.clips_dir / f"{task_id}.mp4"
        dummy_video.write_bytes(b"dummy_mp4_bytes")

        manifest = self.dist_service.generate_manifest(
            task_id=task_id,
            channel_id=1,
            title="Drible Incrível na Final do Campeonato",
            description="Análise tática detalhada em formato Shorts",
            tags=["futebol", "drible", "shorts"],
            video_path=str(dummy_video),
            qc_score=95,
            qc_status="APPROVED_BY_QC"
        )

        self.assertEqual(manifest["task_id"], task_id)
        self.assertEqual(manifest["channel_slug"], "canal_01")
        self.assertEqual(manifest["privacy_status"], "private")  # STRICT
        self.assertEqual(manifest["qc_score"], 95)
        self.assertTrue(os.path.exists(manifest["manifest_path"]))

        # Leitura pelo get_manifest
        retrieved = self.dist_service.get_manifest(task_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["title"], "Drible Incrível na Final do Campeonato")
        self.assertEqual(retrieved["privacy_status"], "private")

        # Listagem filtrada por canal
        manifests = self.dist_service.list_manifests(channel_id=1)
        self.assertGreaterEqual(len(manifests), 1)

    def test_03_gdrive_folder_routing_per_channel(self):
        """Valida que o roteamento de pastas no Google Drive corresponde a config/gdrive_folders.json."""
        f1 = self.dist_service.get_channel_gdrive_folder_id(1)
        f2 = self.dist_service.get_channel_gdrive_folder_id(2)
        f3 = self.dist_service.get_channel_gdrive_folder_id(3)
        f4 = self.dist_service.get_channel_gdrive_folder_id(4)
        f5 = self.dist_service.get_channel_gdrive_folder_id(5)

        self.assertEqual(f1, "1Qcd6DS3zA0OrNKSeDSPTHyl_P0y0l9jf")
        self.assertEqual(f2, "1fUETRbMIIjRTZyOyH_WPLNJcSUwjlPZ4")
        self.assertEqual(f3, "1Eno4d315MaTNf-JCsNjpcgbNrsrsU5nb")
        self.assertEqual(f4, "1wQVA6NifQrixcxVHAf9QHdqlt4g_My74")
        self.assertEqual(f5, "1JoPZhLzpcmiyRRSMS0050nvYOIJfk4Z0")

    def test_04_successful_distribution_and_db_audit(self):
        """Testa a execução autorizada da distribuição com gravação completa de auditoria."""
        task_id = "task_approved_dist_01"
        dummy_video = self.clips_dir / f"{task_id}.mp4"
        dummy_video.write_bytes(b"dummy_mp4_bytes")

        token = "TOKEN_PORTAL2_CH1_APPROVE"
        res = self.dist_service.execute_distribution(
            task_id=task_id,
            channel_id=1,
            human_approved=True,
            human_approval_token=token,
            title="Short Aprovado pelo Diretor",
            description="Descrição final do Short aprovado",
            tags=["futebol", "golaço"],
            video_path=str(dummy_video),
            qc_score=90
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["privacy_status"], "private")
        self.assertIsNotNone(res["publication_id"])
        self.assertIn("https://youtube.com/shorts/", res["published_url"])

        # 1. Auditoria na tabela publications
        pubs = self.dist_service.list_publications(channel_id=1)
        matching = [p for p in pubs if p["id"] == res["publication_id"]]
        self.assertEqual(len(matching), 1)
        pub = matching[0]
        self.assertEqual(pub["title"], "Short Aprovado pelo Diretor")
        self.assertEqual(pub["status"], "publicado_privado")
        self.assertEqual(pub["privacy_status"], "private")
        self.assertEqual(pub["human_approval_token"], token)

        # 2. Auditoria na tabela financial_logs
        with self.dist_service._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM financial_logs WHERE channel_id = 1")
            fin_rows = cur.fetchall()
            self.assertGreaterEqual(len(fin_rows), 1)
            last_fin = fin_rows[-1]
            self.assertEqual(last_fin["log_type"], "avoided_cost")
            self.assertEqual(last_fin["category"], "infrastructure")

        # 3. Auditoria na tabela video_lifecycle
        with self.dist_service._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM video_lifecycle WHERE video_id = ?", (task_id,))
            v_row = cur.fetchone()
            self.assertIsNotNone(v_row)
            self.assertEqual(v_row["status"], "publicado_privado")

    def test_05_langgraph_step11_pause_and_step12_resume(self):
        """Testa o ciclo LangGraph: pausa no Portal 2 e retomada para Etapa 12 após aprovação com token."""
        engine = IASOrchestrationEngine(db_path=str(self.db_path))

        # 1. Executa fluxo inicial
        task_id = "task_lg_dist_cycle"
        state = engine.start_workflow(
            task_id=task_id,
            target_id="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            niche="futebol",
            channel_id=1
        )

        # Deve pausar na etapa 11 para Portal 2
        self.assertEqual(state["status"], "PAUSED_FOR_REVIEW")
        self.assertEqual(state["current_step"], "11_revisao_humana")
        self.assertNotIn("12_distribuicao", state["completed_steps"])

        # 2. Diretor editorial aprova no Portal 2 com token
        approval_token = "PORTAL2_TOKEN_AUTHORIZED_DIRECTOR"
        resumed_state = engine.approve_and_resume(
            task_id=task_id,
            human_approval_token=approval_token
        )

        # Deve concluir a Etapa 12 e finalizar o fluxo como COMPLETED
        self.assertEqual(resumed_state["status"], "COMPLETED")
        self.assertIn("12_distribuicao", resumed_state["completed_steps"])

        step12 = resumed_state["step_results"]["12_distribuicao"]
        self.assertEqual(step12["privacy_status"], "private")
        self.assertEqual(step12["status"], "COMPLETED")
        self.assertIsNotNone(step12["publication_id"])


if __name__ == "__main__":
    unittest.main()
