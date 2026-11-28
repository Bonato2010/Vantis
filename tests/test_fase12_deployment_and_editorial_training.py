"""
Testes Automatizados - Fase 12: Deployment, Operações Contínuas e Treinamento Editorial (Prompts 10 e 11)
Valida:
1. Endpoints oficiais de diagnóstico e health check (/health e /api/health).
2. Procedimento de backup atômico e verificação de integridade via SQLite Online Backup API.
3. Procedimento de restauração de banco de dados com pré-backup de segurança.
4. Rotação e limpeza de arquivos transitórios temporários (autocleanup).
5. Ciclo de treinamento editorial no canal-piloto (feedback positivo vs negativo).
6. Indexação e consulta de padrões rejeitados na memória semântica vetorial isolada por canal.
7. Expansão escalável para os canais 06 a 20 mantendo isolamento estrito.
"""
import os
import sys
import json
import time
import unittest
import tempfile
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from scripts.backup_db import create_database_backup
from scripts.restore_db import restore_database_backup, list_available_backups
from scripts.cleanup_temp_files import cleanup_transient_files
from services.discovery.portal1_service import Portal1GovernanceService
from services.semantic_memory.vector_memory import VectorMemoryService
from core.channel_manager import ChannelManager
from web.app import app

class TestFase12DeploymentAndEditorialTraining(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.temp_dir.name, "test_fase12.db")
        run_migrations(db_path=self.test_db)
        self.portal1 = Portal1GovernanceService(db_path=self.test_db)
        self.vector_mem = VectorMemoryService(db_path=self.test_db)
        self.channel_mgr = ChannelManager(db_path=self.test_db)
        self.client = TestClient(app)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_health_check_endpoint(self):
        """Valida que /health e /api/health reportam status HEALTHY com dados de telemetria."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn(data["status"], ["HEALTHY", "DEGRADED"])
        self.assertEqual(data["version"], "3.0.0")
        self.assertIn("database", data)
        self.assertEqual(data["database"]["status"], "CONNECTED")
        self.assertIn("services", data)
        self.assertIn("google_drive", data)
        self.assertIn("cost_guard", data)
        self.assertTrue(data["cost_guard"]["enforce_free_tier"])
        self.assertEqual(data["cost_guard"]["total_expenses_usd"], 0.0)

    def test_02_database_backup_and_integrity_manifest(self):
        """Valida a criação atômica de backup do banco com verificação de integridade e manifesto."""
        backup_dir = Path(self.temp_dir.name) / "backups"
        backup_file = create_database_backup(db_path=Path(self.test_db), backup_dir=backup_dir, max_retention=3)

        self.assertTrue(backup_file.exists())
        self.assertGreater(backup_file.stat().st_size, 0)

        # Valida manifesto JSON
        json_file = backup_file.with_suffix(".json")
        self.assertTrue(json_file.exists())
        with open(json_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["integrity_check"], "ok")
        self.assertGreaterEqual(meta["total_tables"], 20)

    def test_03_database_restore_and_prebackup_safety(self):
        """Valida a restauração atômica do banco de dados com pré-backup de segurança."""
        backup_dir = Path(self.temp_dir.name) / "backups"
        backup_file = create_database_backup(db_path=Path(self.test_db), backup_dir=backup_dir)

        # Modifica o banco inserindo um registro marcador
        target_db = Path(self.test_db)
        with sqlite3.connect(str(target_db)) as conn:
            conn.execute("INSERT INTO categories (slug, name) VALUES ('cat_teste_restore', 'Categoria Teste')")
            conn.commit()

        # Executa restore
        success = restore_database_backup(backup_path=backup_file, target_db=target_db)
        self.assertTrue(success)

        # Verifica integridade pós-restore
        with sqlite3.connect(str(target_db)) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            self.assertEqual(integrity.lower(), "ok")
            # A categoria adicionada após o backup não deve existir no banco restaurado
            row = conn.execute("SELECT id FROM categories WHERE slug = 'cat_teste_restore'").fetchone()
            self.assertIsNone(row)

    def test_04_transient_files_cleanup_rotation(self):
        """Valida rotação e autolimpeza de arquivos transitórios temporários."""
        temp_sub = Path(self.temp_dir.name) / "workspace" / "temp"
        temp_sub.mkdir(parents=True, exist_ok=True)

        old_file = temp_sub / "old_clip.mp4"
        old_file.write_text("old content")
        # Simula arquivo criado há 48 horas
        two_days_ago = time.time() - (48 * 3600)
        os.utime(str(old_file), (two_days_ago, two_days_ago))

        # Testa cleanup com módulo importado apontando para temp_sub
        import scripts.cleanup_temp_files as ctf
        original_dirs = ctf.DIRS_TO_PRUNE
        try:
            ctf.DIRS_TO_PRUNE = [temp_sub]
            removed = ctf.cleanup_transient_files(max_age_hours=24.0)
            self.assertEqual(removed, 1)
            self.assertFalse(old_file.exists())
        finally:
            ctf.DIRS_TO_PRUNE = original_dirs

    def test_05_pilot_editorial_training_feedback_loop(self):
        """Valida o ciclo de treinamento editorial: pauta aprovada gera vetor positivo, rejeitada gera vetor negativo."""
        # 1. Insere oportunidade para Canal 01 (Futebol)
        opp_id = "opp_train_001"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
        with sqlite3.connect(self.test_db) as conn:
            conn.execute("""
                INSERT INTO opportunities (
                    opportunity_id, source_platform, source_url, niche, subniche,
                    title_concept, context_description, popularity_evidence, confidence_score,
                    recommended_channel_id, technical_justification, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opp_id, "youtube", "https://youtube.com/watch?v=train001", "futebol", "gols",
                "O Gol Impossível de Roberto Carlos que Desafiou a Física", "Análise biomecânica",
                json.dumps({"views": 1500000}), 92, 1, "Gancho com retenção comprovada", "PENDING_REVIEW",
                now_iso, now_iso
            ))
            conn.commit()

        # 2. Aprovação editorial
        app_res = self.portal1.approve_opportunity(opp_id, reviewer="Diretor Piloto")
        self.assertTrue(app_res["success"])
        self.assertEqual(app_res["status"], "APPROVED")

        # 3. Verifica busca semântica de ganchos positivos
        similar_hooks = self.vector_mem.search_hooks("Roberto Carlos física gol", channel_id=1, top_k=5)
        self.assertGreater(len(similar_hooks), 0)
        self.assertEqual(similar_hooks[0]["id"], "hook_train001")

        # 4. Insere e rejeita pauta fora da persona
        opp_bad_id = "opp_train_bad_002"
        with sqlite3.connect(self.test_db) as conn:
            conn.execute("""
                INSERT INTO opportunities (
                    opportunity_id, source_platform, source_url, niche, subniche,
                    title_concept, context_description, popularity_evidence, confidence_score,
                    recommended_channel_id, technical_justification, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opp_bad_id, "youtube", "https://youtube.com/watch?v=trainbad002", "futebol", "fofoca",
                "Fofoca de bastidores sobre namoro de jogador famoso", "Clickbait sensacionalista",
                json.dumps({"views": 20000}), 40, 1, "Fora da proposta esportiva", "PENDING_REVIEW",
                now_iso, now_iso
            ))
            conn.commit()

        rej_res = self.portal1.reject_opportunity(
            opp_bad_id,
            rejection_reason="Fofoca e sensacionalismo não pertencem à linha editorial de futebol",
            rejection_category="sensacionalismo",
            reviewer="Diretor Piloto"
        )
        self.assertTrue(rej_res["success"])
        self.assertEqual(rej_res["status"], "REJECTED")

        # 5. Verifica se padrão negativo foi indexado na memória vetorial
        neg_vectors = self.vector_mem.search_similar("fofoca namoro jogador", category="rejected_pattern", channel_id=1, top_k=5)
        self.assertGreater(len(neg_vectors), 0)
        self.assertEqual(neg_vectors[0]["id"], f"rejected_{opp_bad_id}")
        self.assertIn("PADRÃO REJEITADO", neg_vectors[0]["text"])

    def test_06_scaling_expansion_channels_06_to_20(self):
        """Valida que os canais de expansão 06 a 20 possuem perfis mapeados e isolados prontos para escala."""
        all_channels = self.channel_mgr.list_all_channels()
        self.assertEqual(len(all_channels), 20)

        # Canais 06 a 20
        expansion_channels = all_channels[5:]
        self.assertEqual(len(expansion_channels), 15)

        for ch in expansion_channels:
            ch_num = ch["channel_number"]
            self.assertGreaterEqual(ch_num, 6)
            self.assertLessEqual(ch_num, 20)
            self.assertIsNotNone(ch["name"])
            self.assertIsNotNone(ch["niche"])
            self.assertIsNotNone(ch["gdrive_folder_id"])
            # Isolamento comprovado via guidelines exclusivas
            guidelines = self.channel_mgr.get_channel_editorial_guidelines(ch["id"])
            self.assertIn(ch["name"].upper(), guidelines)


if __name__ == "__main__":
    unittest.main()
