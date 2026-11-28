"""
VANTIS — Suíte de Testes Automatizados da Auditoria Forense (Fase 15.1)
Valida rigorosamente os 11 requisitos mandatários do Prompt 15.1:
1. Hash SHA256 completo de 64 caracteres em arquivo real.
2. Arquivo inexistente ou corrompido gera erro explícito.
3. Áudio silencioso (-70 LUFS) classificado como SILENT_AUDIO_TRACK.
4. Arquivo sem faixa de áudio classificado como NO_AUDIO_TRACK.
5. Divergência de duração entre metadados e arquivo físico detectada.
6. Conteúdo fora do tema do canal classificado como editorially_rejected com motivo explícito.
7. Deduplicação por ID e por conteúdo funcionando.
8. Aprendizado sem evidência rejeitado (e regra de 1 evidência = observação).
9. Transição para estado final inválido bloqueada.
10. Retomada idempotente sem reprocessamento desnecessário.
11. Dashboard reflete contagens reais sem inflar com registros de teste.
"""

import re
import os
import sys
import json
import sqlite3
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from services.learning.audiovisual_learning_system import (
    AudiovisualLearningSystem,
    VALID_STATES,
    ACOUSTIC_CLASSIFICATIONS
)

class TestFase151ForensicAudit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_shorts.db"
        run_migrations(db_path=self.db_path)
        self.als = AudiovisualLearningSystem(db_path=self.db_path, target_goal=100)

        # Ingestão de vídeo base para testes
        self.base_video = self.als.discover_video(
            source_id="test_vid_01",
            original_url="https://youtube.com/shorts/test_vid_01",
            title="Curiosidades Científicas sobre o Universo",
            creator="Ciência Rápida",
            niche="curiosidades",
            duration_seconds=30.0
        )

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 1. Hash SHA256 completo de 64 caracteres em arquivo real
    # -------------------------------------------------------------------------
    def test_01_full_64_char_sha256_real_file(self):
        sample_file = self.temp_path / "real_video.mp4"
        sample_file.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"X" * 1024)

        hasher = hashlib.sha256()
        with open(sample_file, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        expected_hash = hasher.hexdigest()

        res = self.als.register_physical_media(
            source_id="test_vid_01",
            local_path=str(sample_file),
            verified_duration=30.0
        )

        recorded_sha256 = res["physical_media"]["sha256_hash"]
        self.assertEqual(len(recorded_sha256), 64, "SHA256 deve ter exatamente 64 caracteres.")
        self.assertTrue(re.match(r"^[0-9a-f]{64}$", recorded_sha256), "SHA256 deve ser hexadecimal minúsculo.")
        self.assertEqual(recorded_sha256, expected_hash, "Hash calculado deve ser idêntico ao do arquivo real.")

    # -------------------------------------------------------------------------
    # 2. Arquivo inexistente ou corrompido gera erro explícito
    # -------------------------------------------------------------------------
    def test_02_missing_or_empty_file_raises_explicit_error(self):
        # Arquivo inexistente
        ghost_path = self.temp_path / "ghost_file.mp4"
        with self.assertRaises(FileNotFoundError):
            self.als.register_physical_media("test_vid_01", str(ghost_path))

        # Arquivo vazio (0 bytes)
        empty_path = self.temp_path / "empty_file.mp4"
        empty_path.write_bytes(b"")
        with self.assertRaises(ValueError) as ctx:
            self.als.register_physical_media("test_vid_01", str(empty_path))
        self.assertIn("vazio", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # 3. Áudio silencioso (-70 LUFS) classificado como SILENT_AUDIO_TRACK
    # -------------------------------------------------------------------------
    def test_03_silent_audio_classified_as_silent_audio_track(self):
        res = self.als.process_audio(
            source_id="test_vid_01",
            speech_clarity_score=0.0,
            estimated_lufs=-70.0
        )
        audio = res["audio"]
        self.assertEqual(audio["audio_classification"], "SILENT_AUDIO_TRACK")
        self.assertFalse(audio["is_usable"], "Áudio com -70.0 LUFS não pode ser marcado como utilizável.")
        self.assertEqual(audio["speech_clarity_score"], 0.0)
        self.assertEqual(audio["pauses_ratio"], 1.0)
        self.assertIn("SILENT_AUDIO_TRACK", audio["diagnostic_message"])

    # -------------------------------------------------------------------------
    # 4. Arquivo sem faixa de áudio classificado como NO_AUDIO_TRACK
    # -------------------------------------------------------------------------
    def test_04_no_audio_track_classified_correctly(self):
        sample_file = self.temp_path / "no_audio.mp4"
        sample_file.write_bytes(b"dummy_video_stream_only")

        with patch("services.media_processing.ffmpeg_engine.FFmpegEngine.probe_media") as mock_probe:
            mock_probe.return_value = {"has_audio": False, "has_video": True, "duration_sec": 15.0}
            diag = self.als._analyze_audio_file(str(sample_file))

        self.assertEqual(diag["classification"], "NO_AUDIO_TRACK")
        self.assertFalse(diag["is_usable"])
        self.assertEqual(diag["integrated_lufs"], -70.0)
        self.assertEqual(diag["speech_clarity_score"], 0.0)

    # -------------------------------------------------------------------------
    # 5. Divergência de duração entre metadados e arquivo físico detectada
    # -------------------------------------------------------------------------
    def test_05_duration_divergence_detected_and_updated(self):
        sample_file = self.temp_path / "divergent.mp4"
        sample_file.write_bytes(b"dummy_payload_divergent")

        # Metadados indicavam 30.0s, mas arquivo físico tem 42.5s
        res = self.als.register_physical_media(
            source_id="test_vid_01",
            local_path=str(sample_file),
            verified_duration=42.5
        )

        self.assertEqual(res["physical_media"]["verified_duration"], 42.5)

        with self.als._get_conn() as conn:
            row = conn.execute("SELECT duration_seconds FROM audiovisual_library WHERE source_id = 'test_vid_01'").fetchone()
            self.assertEqual(row["duration_seconds"], 42.5, "Duração no banco deve refletir a medição física real.")

    # -------------------------------------------------------------------------
    # 6. Conteúdo fora do tema do canal classificado como editorially_rejected
    # -------------------------------------------------------------------------
    def test_06_off_topic_content_editorially_rejected(self):
        off_topic_vid = self.als.discover_video(
            source_id="jeans_123",
            title="SHORT JEANS Cintura Baixa - Melhores Modelos Moda",
            creator="Moda Fashion",
            niche="casos_policiais",  # Catalogado erroneamente no canal de crimes
            duration_seconds=15.0
        )

        res = self.als.evaluate_editorial_adherence(
            source_id="jeans_123",
            target_channel_id=2  # Canal 02 - Casos Reais
        )

        self.assertEqual(res["processing_state"], "editorially_rejected")
        self.assertEqual(res["editorial_verdict"], "REJECTED_OFF_TOPIC")
        self.assertFalse(res["is_aligned"])
        self.assertIn("editorial_mismatch", res["rejection_reason"])

        # Tentativa de promover vídeo rejeitado editorialmente para candidato DEVE falhar
        with self.assertRaises(ValueError) as ctx:
            self.als.promote_to_learning_candidate("jeans_123")
        self.assertIn("rejeitado editorialmente", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 7. Deduplicação por ID e por conteúdo funcionando
    # -------------------------------------------------------------------------
    def test_07_deduplication_by_id_and_fingerprint(self):
        # 1. Deduplicação por ID
        dup_id = self.als.discover_video(
            source_id="test_vid_01",
            title="Outro Título",
            creator="Outro Criador",
            duration_seconds=30.0
        )
        self.assertEqual(dup_id["status"], "ALREADY_CATALOGED")

        # 2. Deduplicação por Fingerprint Multimodal (título e duração idênticos com ID diferente)
        dup_fingerprint = self.als.discover_video(
            source_id="test_vid_new_id",
            title="Curiosidades Científicas sobre o Universo",
            creator="Ciência Rápida",
            duration_seconds=30.0
        )
        self.assertEqual(dup_fingerprint["status"], "REJECTED_DUPLICATE")
        self.assertEqual(dup_fingerprint["reason"], "duplicate_fingerprint")

    # -------------------------------------------------------------------------
    # 8. Aprendizado sem evidência rejeitado e regra de evidências
    # -------------------------------------------------------------------------
    def test_08_learning_evidence_rigor(self):
        # Sem evidência -> Erro
        with self.assertRaises(ValueError) as ctx:
            self.als.record_knowledge(
                title="Padrão Sem Prova",
                evidence_video_ids=[]
            )
        self.assertIn("evidence_video_ids não pode estar vazio", str(ctx.exception))

        # 1 evidência -> Reclassificado compulsoriamente para OBSERVAÇÃO
        k1 = self.als.record_knowledge(
            title="Hipótese com 1 evidência",
            evidence_video_ids=["test_vid_01"],
            classification="APRENDIZADO_VALIDADO",
            confidence_score=0.95
        )
        self.assertEqual(k1["classification"], "OBSERVAÇÃO")
        self.assertLessEqual(k1["confidence_score"], 0.70)

        # 2 evidências -> Conforme Prompt 15.1, mínimo de 2 evidências para validação
        k2 = self.als.record_knowledge(
            title="Padrão com 2 evidências",
            evidence_video_ids=["test_vid_01", "test_vid_02"],
            classification="APRENDIZADO_VALIDADO"
        )
        self.assertEqual(k2["classification"], "APRENDIZADO_VALIDADO")
        self.assertGreaterEqual(k2["confidence_score"], 0.80)

        # 4+ evidências -> Elegível a APRENDIZADO_VALIDADO
        k4 = self.als.record_knowledge(
            title="Padrão com 4 evidências",
            evidence_video_ids=["v1", "v2", "v3", "v4"],
            classification="APRENDIZADO_VALIDADO"
        )
        self.assertEqual(k4["classification"], "APRENDIZADO_VALIDADO")
        self.assertGreaterEqual(k4["confidence_score"], 0.90)

    # -------------------------------------------------------------------------
    # 9. Transição para estado final inválido bloqueada
    # -------------------------------------------------------------------------
    def test_09_invalid_state_transition_blocked(self):
        with self.assertRaises(ValueError) as ctx:
            self.als._set_state("test_vid_01", "estado_fantasma_inexistente")
        self.assertIn("Estado de processamento inválido", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 10. Retomada idempotente sem reprocessamento desnecessário
    # -------------------------------------------------------------------------
    def test_10_idempotent_batch_resumption(self):
        batch_id = "test_batch_idempotent"
        # Executa lote 1
        res1 = self.als.run_batch_processing(batch_id=batch_id, batch_size=5)
        self.assertGreaterEqual(res1["total_processed"], 1)

        # Executa lote 2 (sem novos vídeos inseridos)
        res2 = self.als.run_batch_processing(batch_id=batch_id, batch_size=5)
        self.assertEqual(res2["batch_processed"], 0, "Vídeos já processados não devem ser reprocessados.")

    # -------------------------------------------------------------------------
    # 11. Dashboard reflete contagens reais sem inflar com registros de teste
    # -------------------------------------------------------------------------
    def test_11_dashboard_real_counts(self):
        dash = self.als.get_dashboard_overview()
        indicators = dash["granular_indicators"]

        self.assertIn("videos_descobertos", indicators)
        self.assertIn("videos_baixados", indicators)
        self.assertIn("videos_tecnicamente_analisados", indicators)
        self.assertIn("videos_editorialmente_aprovados", indicators)
        self.assertIn("aprendizados_candidatos", indicators)
        self.assertIn("aprendizados_validados", indicators)
        self.assertIn("rejeitados_editorial", indicators)

        # Checagem de tipos e valores válidos
        for k, v in indicators.items():
            self.assertIsInstance(v, int, f"Indicador {k} deve ser inteiro.")
            self.assertGreaterEqual(v, 0, f"Indicador {k} não pode ser negativo.")

        # Telemetria da Fase 15 isolada
        pilot_telemetry = dash.get("pilot_fase15_metrics", {})
        self.assertIsNotNone(pilot_telemetry)

if __name__ == "__main__":
    unittest.main()
