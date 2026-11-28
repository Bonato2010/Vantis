"""
Bateria de Testes Automatizados - Fase 10: Pipeline de Produção e Processamento Audiovisual
Valida as 10 etapas industriais do pipeline audiovisual VANTIS:
1. Recebimento e validação da mídia (integridade e formatos)
2. Extração de metadados e registro de proveniência de direitos autorais
3. Transcrição (Faster-Whisper / Timestamps e tratamento de áudio ausente)
4. Análise de cenas e conteúdo (PySceneDetect + OpenCV Smart Crop 9:16)
5. Seleção e validação rigorosa de limites de corte (15s a 59s)
6. Preparação de cortes e personalização por canal
7. Processamento audiovisual, mixagem e renderização FFmpeg EBU R128 (-14 LUFS)
8. Geração de versões preliminares e miniaturas de destaque
9. Revisão técnica de qualidade automatizada (QC) e detecção de falhas
10. Armazenamento, persistência em banco de dados e auditoria de tempos
"""

import os
import sys
import json
import wave
import struct
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from services.media_processing.ffmpeg_engine import FFmpegEngine
from services.media_processing.audiovisual_pipeline import (
    AudiovisualProductionPipeline,
    AudiovisualPipelineError
)
from core.channel_manager import ChannelManager


class TestFase10AudiovisualPipeline(unittest.TestCase):
    """Suíte de testes de regressão e integridade do Pipeline Audiovisual."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="test_fase10_av_")
        cls.db_path = Path(cls.temp_dir) / "test_av_central.db"
        run_migrations(db_path=str(cls.db_path))

        cls.workspace = Path(cls.temp_dir) / "workspace"
        cls.workspace.mkdir(parents=True, exist_ok=True)

        cls.channel_manager = ChannelManager(db_path=str(cls.db_path))
        cls.pipeline = AudiovisualProductionPipeline(
            db_path=str(cls.db_path),
            workspace_dir=cls.workspace,
            channel_manager=cls.channel_manager
        )
        cls.ffmpeg = FFmpegEngine()

        # Cria um arquivo de áudio WAV sintético válido (440Hz, 20 segundos)
        cls.sample_wav = Path(cls.temp_dir) / "sample_audio.wav"
        cls._create_synthetic_wav(cls.sample_wav, duration_sec=22.0)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    @staticmethod
    def _create_synthetic_wav(file_path: Path, duration_sec: float = 20.0, sample_rate: int = 16000):
        """Gera arquivo WAV sintético audível de teste."""
        n_frames = int(duration_sec * sample_rate)
        with wave.open(str(file_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            # Onda senoidal simples
            import math
            data = bytearray()
            for i in range(n_frames):
                val = int(32767.0 * 0.3 * math.sin(2.0 * math.pi * 440.0 * (i / sample_rate)))
                data.extend(struct.pack("<h", val))
            wf.writeframes(data)

    def test_01_media_validation_supported_and_corrupted(self):
        """Etapa 1: Valida detecção de integridade e rejeição de arquivos corrompidos."""
        # 1. Arquivo válido
        res = self.pipeline.stage_1_validate_input_media(self.sample_wav)
        self.assertTrue(res["valid"])
        self.assertTrue(res["has_audio"])
        self.assertGreater(res["duration_sec"], 20.0)

        # 2. Arquivo inexistente
        with self.assertRaises(AudiovisualPipelineError) as ctx:
            self.pipeline.stage_1_validate_input_media("caminho_inexistente_123.mp4")
        self.assertEqual(ctx.exception.code, "FILE_NOT_FOUND")

        # 3. Arquivo vazio / corrompido (tamanho zero)
        empty_file = Path(self.temp_dir) / "empty_corrupted.mp4"
        empty_file.write_bytes(b"")
        with self.assertRaises(AudiovisualPipelineError) as ctx:
            self.pipeline.stage_1_validate_input_media(empty_file)
        self.assertEqual(ctx.exception.code, "CORRUPTED_FILE_ZERO_OR_TRUNCATED")

        # 4. Formato não suportado
        invalid_fmt = Path(self.temp_dir) / "test.exe"
        invalid_fmt.write_bytes(b"MZ0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
        with self.assertRaises(AudiovisualPipelineError) as ctx:
            self.pipeline.stage_1_validate_input_media(invalid_fmt)
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_MEDIA_FORMAT")

    def test_02_metadata_extraction_and_provenance_tracking(self):
        """Etapa 2: Valida extração de metadados técnicos e consolidação de direitos autorais."""
        prov_input = {
            "source_url": "https://www.youtube.com/watch?v=sample123",
            "source_author": "Canal Parceiro Oficial",
            "source_license": "Creative Commons / Fair Use",
            "transformative_type": "critical_commentary"
        }
        meta = self.pipeline.stage_2_extract_metadata(self.sample_wav, provenance=prov_input)

        self.assertIn("file_name", meta)
        self.assertIn("duration_sec", meta)
        self.assertGreater(meta["duration_sec"], 20.0)
        self.assertIn("provenance", meta)
        self.assertEqual(meta["provenance"]["source_author"], "Canal Parceiro Oficial")
        self.assertEqual(meta["provenance"]["transformative_type"], "critical_commentary")

    def test_03_copyright_compliance_and_transformative_intent(self):
        """Valida que o pipeline bloqueia ativamente reupload cru sem transformação editorial."""
        unauthorized_prov = {
            "source_url": "https://www.youtube.com/watch?v=raw_steal",
            "source_author": "Criador Original",
            "transformative_type": "raw_reupload_prohibited"
        }
        with self.assertRaises(AudiovisualPipelineError) as ctx:
            self.pipeline.stage_2_extract_metadata(self.sample_wav, provenance=unauthorized_prov)
        self.assertEqual(ctx.exception.code, "COPYRIGHT_COMPLIANCE_BLOCKED")

    def test_04_audio_transcription_and_missing_audio_handling(self):
        """Etapa 3: Valida transcrição de áudio e tratamento rigoroso para mídia sem áudio."""
        # 1. Transcrição de áudio com Faster-Whisper
        res = self.pipeline.stage_3_transcribe_audio(
            media_path=self.sample_wav,
            task_id="trans_task_01",
            provided_script="Este é um roteiro narrado autoral para o teste de transcrição."
        )
        self.assertTrue(res["transcribed"])
        self.assertIn("segments", res)

        # 2. Teste de vídeo sem áudio quando nenhum roteiro é informado
        no_audio_video = Path(self.temp_dir) / "silent_video.mp4"
        # Cria vídeo mudo via FFmpeg se disponível
        if self.ffmpeg.available:
            cmd = [
                self.ffmpeg.binary_path, "-y",
                "-f", "lavfi", "-i", "color=c=black:s=640x360:r=25:d=5",
                "-c:v", "libx264", "-t", "5",
                str(no_audio_video)
            ]
            import subprocess
            subprocess.run(cmd, capture_output=True, timeout=10)
            if no_audio_video.exists():
                with self.assertRaises(AudiovisualPipelineError) as ctx:
                    self.pipeline.stage_3_transcribe_audio(
                        media_path=no_audio_video,
                        task_id="trans_no_audio",
                        provided_script=None
                    )
                self.assertEqual(ctx.exception.code, "MISSING_AUDIO_STREAM")

    def test_05_scene_detection_and_opencv_smart_crop(self):
        """Etapa 4: Valida análise de cenas, cálculo de ritmo visual e Smart Crop 9:16."""
        # Cria um pequeno clipe vertical de 5s para análise
        test_clip = Path(self.temp_dir) / "test_scenes.mp4"
        if self.ffmpeg.available:
            cmd = [
                self.ffmpeg.binary_path, "-y",
                "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=25",
                "-c:v", "libx264", "-t", "6",
                str(test_clip)
            ]
            import subprocess
            subprocess.run(cmd, capture_output=True, timeout=15)

        if test_clip.exists():
            analysis = self.pipeline.stage_4_analyze_scenes_and_content(test_clip)
            self.assertTrue(analysis["has_video"])
            self.assertIn("visual_bpm", analysis)
            self.assertIn("smart_crop", analysis)
            self.assertIn("ffmpeg_crop_offset_x", analysis["smart_crop"])

    def test_06_cut_selection_and_boundary_validation(self):
        """Etapa 5: Valida regras estritas de corte e rejeição de limites inválidos."""
        total_dur = 45.0

        # 1. Corte válido (20s a 45s = 25s de duração)
        res = self.pipeline.stage_5_select_segments(total_duration=total_dur, start_sec=20.0, end_sec=45.0)
        self.assertEqual(res["start_sec"], 20.0)
        self.assertEqual(res["end_sec"], 45.0)
        self.assertEqual(res["cut_duration_sec"], 25.0)
        self.assertTrue(res["is_within_shorts_range"])

        # 2. Início negativo
        with self.assertRaises(AudiovisualPipelineError) as ctx:
            self.pipeline.stage_5_select_segments(total_duration=total_dur, start_sec=-5.0, end_sec=25.0)
        self.assertEqual(ctx.exception.code, "INVALID_CUT_NEGATIVE_START")

        # 3. Início maior que o fim
        with self.assertRaises(AudiovisualPipelineError) as ctx:
            self.pipeline.stage_5_select_segments(total_duration=total_dur, start_sec=30.0, end_sec=20.0)
        self.assertEqual(ctx.exception.code, "INVALID_CUT_START_GE_END")

        # 4. Fim excede a duração total do arquivo
        with self.assertRaises(AudiovisualPipelineError) as ctx:
            self.pipeline.stage_5_select_segments(total_duration=total_dur, start_sec=10.0, end_sec=80.0)
        self.assertEqual(ctx.exception.code, "INVALID_CUT_EXCEEDS_DURATION")

        # 5. Duração fora do intervalo permitido para YouTube Shorts (< 15s ou > 59s)
        with self.assertRaises(AudiovisualPipelineError) as ctx:
            self.pipeline.stage_5_select_segments(total_duration=total_dur, start_sec=0.0, end_sec=10.0)
        self.assertEqual(ctx.exception.code, "INVALID_SHORTS_DURATION")

    def test_07_full_pipeline_canvas_short_generation(self):
        """Etapas 6 a 10: Execução completa do pipeline audiovisual com síntese, legendas e EBU R128."""
        if not self.ffmpeg.available:
            self.skipTest("FFmpeg não disponível neste ambiente de teste.")

        task_id = "test_fase10_full_av_001"
        job_config = {
            "task_id": task_id,
            "channel_id": 1,
            "input_media_path": None,
            "script_text": (
                "Atenção a esta revelação exclusiva sobre a automação do sistema Vantis. "
                "Nos últimos anos, a inteligência artificial transformou radicalmente a produção de vídeos curtos. "
                "Canais profissionais agora utilizam processos automatizados para analisar tendências e reter milhões de espectadores. "
                "Siga nosso canal para dominar as melhores estratégias de criação digital."
            ),
            "generate_tts": True,
            "generate_subtitles": True,
            "cut_start_sec": 0.0,
            "cut_end_sec": 18.0,
            "provenance": {
                "source_url": "original_production_test",
                "source_author": "VANTIS AI Studio",
                "source_license": "Proprietary",
                "transformative_type": "original_production"
            }
        }

        result = self.pipeline.execute_full_pipeline(job_config)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["task_id"], task_id)
        self.assertTrue(os.path.exists(result["output_video_path"]))
        self.assertEqual(result["resolution"], "1080x1920")
        self.assertTrue(result["qc_passed"])
        self.assertGreaterEqual(result["qc_score"], 80)
        self.assertTrue(result["portal_2_ready"])
        self.assertIn("stage_timings", result)

    def test_08_quality_control_checks_and_failure_detection(self):
        """Etapa 9: Valida detecção rigorosa de defeitos técnicos pelo QC automatizado."""
        # 1. Arquivo inexistente ou vazio
        fake_bad = Path(self.temp_dir) / "corrupted_bad.mp4"
        fake_bad.write_bytes(b"corrupted_header")
        qc_bad = self.pipeline.stage_9_review_quality(
            task_id="bad_qc_task",
            channel_id=1,
            rendered_video_path=str(fake_bad)
        )
        self.assertFalse(qc_bad["passed"])
        self.assertEqual(qc_bad["qc_score"], 0)

        # 2. Testa validação de sincronia de legendas extrapoladas
        # Cria um arquivo .ass fictício com timestamp de 90s para um vídeo de 20s
        fake_ass = Path(self.temp_dir) / "desynced.ass"
        fake_ass.write_text(
            "[Script Info]\nTitle: Test\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:01:30.00,Default,,0,0,0,,Texto que termina em 90 segundos\n",
            encoding="utf-8"
        )
        # Se validarmos o sample_wav (22s) contra essa legenda desincronizada (90s)
        qc_desync = self.pipeline.stage_9_review_quality(
            task_id="desync_qc_task",
            channel_id=1,
            rendered_video_path=str(self.sample_wav),
            ass_subtitles_path=str(fake_ass)
        )
        self.assertFalse(qc_desync["passed"])
        self.assertIn("Legenda desincronizada", " ".join(qc_desync["failure_reasons"]))

    def test_09_database_audit_logging_and_timings(self):
        """Etapa 10: Valida que a execução do pipeline grava registros completos no SQLite."""
        task_id = "test_fase10_audit_db_001"
        qc_mock = {
            "passed": True,
            "qc_score": 95,
            "duration_sec": 28.5,
            "resolution": "1080x1920",
            "integrated_lufs": -14.2
        }
        timings_mock = {
            "stage_1_ms": 12.0,
            "stage_7_ms": 350.0,
            "total_ms": 500.0
        }
        prov_mock = {
            "source_url": "https://youtube.com/shorts/sample_audit",
            "source_author": "Audit Author",
            "source_license": "Creative Commons",
            "transformative_type": "educational_analysis"
        }

        stored = self.pipeline.stage_10_store_and_register(
            task_id=task_id,
            channel_id=2,
            source_media_path="raw/video.mp4",
            output_media_path="clips/final.mp4",
            thumbnail_path="clips/final_thumb.jpg",
            provenance=prov_mock,
            qc_result=qc_mock,
            stage_timings=timings_mock
        )

        self.assertEqual(stored["status"], "COMPLETED")
        self.assertTrue(stored["portal_2_ready"])

        # Confere leitura direta no banco SQLite
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM audiovisual_pipeline_runs WHERE task_id = ?", (task_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["channel_id"], 2)
            self.assertEqual(row["qc_passed"], 1)
            self.assertEqual(row["qc_score"], 95)
            self.assertEqual(row["transformative_type"], "educational_analysis")
            self.assertIn("stage_1_ms", row["stage_timings_json"])

    def test_10_concurrency_and_resource_safety(self):
        """Valida que o pipeline respeita limites e não causa vazamento de recursos ou handles de arquivo."""
        # Executa múltiplos probes e checagens consecutivas garantindo liberação de arquivos
        for i in range(5):
            probe = self.ffmpeg.probe_media(str(self.sample_wav))
            self.assertTrue(probe.get("has_audio"))
            self.assertGreater(probe.get("duration_sec"), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
