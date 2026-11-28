"""
IAS Test Suite - Fase 5: Produção Audiovisual & Edição Avançada
Testa:
1. Síntese de voz neural (Edge-TTS) e mapeamento por perfil de canal
2. Resiliência e fallback offline da narração
3. Geração de legendas ASS dinâmicas e estilização por canal (1080x1920)
4. Renderização vertical FFmpeg (9:16, 1080x1920) e inspeção FFprobe
5. Normalização de áudio broadcast EBU R128 (-14 LUFS)
6. Auditoria do Departamento de Controle de Qualidade (QC Agent)
7. Integração ponta-a-ponta no LangGraph (Etapas 9, 10 e 11)
"""
import os
import sys
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
from services.media_processing.tts_engine import TTSNarrationService, DEFAULT_CHANNEL_VOICES
from services.media_processing.subtitle_generator import SubtitleGenerator
from services.media_processing.ffmpeg_engine import FFmpegEngine
from agents.qc_agent import QualityControlAgent
from services.orchestration.langgraph_engine import IASOrchestrationEngine
from database.migrate import run_migrations


class TestFase5Audiovisual(unittest.TestCase):
    """Bateria de testes da infraestrutura audiovisual, legendas e controle de qualidade."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="test_audiovisual_")
        cls.db_path = Path(cls.temp_dir) / "test_audiovisual.db"
        run_migrations(db_path=cls.db_path)
        cls.channel_manager = ChannelManager(db_path=str(cls.db_path))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        self.tts_out = Path(self.temp_dir) / "audio"
        self.subs_out = Path(self.temp_dir) / "subs"
        self.clips_out = Path(self.temp_dir) / "clips"
        self.tts_out.mkdir(exist_ok=True)
        self.subs_out.mkdir(exist_ok=True)
        self.clips_out.mkdir(exist_ok=True)

        self.tts = TTSNarrationService(output_dir=self.tts_out, channel_manager=self.channel_manager)
        self.sub_gen = SubtitleGenerator(output_dir=self.subs_out, channel_manager=self.channel_manager)
        self.ffmpeg = FFmpegEngine()
        self.qc = QualityControlAgent(ffmpeg_engine=self.ffmpeg, channel_manager=self.channel_manager)

    def test_01_tts_channel_voice_mapping_and_generation(self):
        """Verifica o mapeamento de vozes dos 5 canais piloto e geração de áudio."""
        v1 = self.tts.get_channel_voice_config(1)
        v2 = self.tts.get_channel_voice_config(2)
        v3 = self.tts.get_channel_voice_config(3)
        v4 = self.tts.get_channel_voice_config(4)
        v5 = self.tts.get_channel_voice_config(5)

        from services.media_processing.tts_engine import ACTIVE_PT_BR_VOICES
        self.assertEqual(v1["voice"], "pt-BR-AntonioNeural")
        self.assertIn(v2["voice"], ACTIVE_PT_BR_VOICES)
        self.assertIn(v3["voice"], ACTIVE_PT_BR_VOICES)
        self.assertEqual(v4["voice"], "pt-BR-FranciscaNeural")
        self.assertIn(v5["voice"], ACTIVE_PT_BR_VOICES)

        # Geração de áudio para o Canal 1 (Futebol)
        text = "O drible desconcertante que mudou a final do campeonato!"
        res = self.tts.generate_narration(
            text=text,
            channel_id=1,
            task_id="test_tts_ch1"
        )

        self.assertTrue(res["success"])
        self.assertTrue(os.path.exists(res["audio_path"]))
        self.assertGreater(res["size_bytes"], 1000)
        self.assertGreater(res["duration_sec"], 1.0)
        self.assertGreaterEqual(len(res["boundaries"]), 1)
        self.assertEqual(res["voice_id"], "pt-BR-AntonioNeural")

    def test_02_tts_offline_resilience(self):
        """Testa o gerador de resiliência e fallback offline caso a rede falhe."""
        text = "Este é um teste de fallback sintético do motor de narração."
        res = self.tts.generate_narration(
            text=text,
            channel_id=2,
            task_id="test_tts_offline",
            force_offline=True
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "mock_fallback")
        self.assertTrue(os.path.exists(res["audio_path"]))
        self.assertGreater(res["size_bytes"], 1000)
        self.assertGreater(len(res["boundaries"]), 1)

    def test_03_subtitle_generator_ass_styling(self):
        """Valida que o SubtitleGenerator cria cabeçalhos 1080x1920 e estilos corretos por canal."""
        cues = [
            {"start": 0.0, "end": 2.5, "text": "ISSO AQUI É UMA REVELAÇÃO EXCLUSIVA"},
            {"start": 2.5, "end": 5.0, "text": "NINGUÉM ESPERAVA POR ESSE RESULTADO"}
        ]

        # Canal 1 - Futebol (Arial Black, Amarelo)
        res_ch1 = self.sub_gen.generate_ass(cues=cues, channel_id=1, task_id="sub_test_ch1")
        self.assertTrue(res_ch1["success"])
        self.assertTrue(os.path.exists(res_ch1["ass_path"]))
        self.assertGreaterEqual(res_ch1["total_cues"], 2)

        with open(res_ch1["ass_path"], "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("PlayResX: 1080", content)
        self.assertIn("PlayResY: 1920", content)
        self.assertIn("Arial Black", content)
        self.assertIn("&H0000FFFF&", content) # Amarelo BGR
        self.assertIn("Dialogue:", content)

        # Canal 2 - Casos Reais (Consolas, Ciano)
        res_ch2 = self.sub_gen.generate_ass(cues=cues, channel_id=2, task_id="sub_test_ch2")
        with open(res_ch2["ass_path"], "r", encoding="utf-8") as f:
            content2 = f.read()

        self.assertIn("Consolas", content2)
        self.assertIn("&H00FFFF00&", content2) # Ciano BGR

    def test_04_ffmpeg_vertical_render_and_probe(self):
        """Renderiza um Short vertical real (1080x1920) e valida metadados com FFprobe."""
        # 1. Gera áudio
        audio_res = self.tts.generate_narration("Momento decisivo que parou a internet inteira!", channel_id=1, task_id="render_audio")
        # 2. Gera legenda
        sub_res = self.sub_gen.generate_ass(
            cues=[{"start": 0.0, "end": audio_res["duration_sec"], "text": "MOMENTO DECISIVO QUE PAROU A INTERNET"}],
            channel_id=1,
            task_id="render_sub"
        )

        output_mp4 = self.clips_out / "short_render_test.mp4"

        # 3. Renderiza vertical 9:16
        render_res = self.ffmpeg.generate_canvas_short(
            audio_path=audio_res["audio_path"],
            output_path=str(output_mp4),
            bg_color="#001E0A",
            ass_subtitles_path=sub_res["ass_path"],
            channel_variant=1
        )

        self.assertTrue(render_res["success"], f"Falha na renderização: {render_res.get('error')}")
        self.assertTrue(output_mp4.exists())
        self.assertGreater(output_mp4.stat().st_size, 10_000)

        # 4. Sonda com FFprobe
        probe = self.ffmpeg.probe_media(str(output_mp4))
        self.assertTrue(probe["exists"])
        self.assertEqual(probe["width"], 1080)
        self.assertEqual(probe["height"], 1920)
        self.assertTrue(probe["is_vertical"])
        self.assertTrue(probe["has_video"])
        self.assertTrue(probe["has_audio"])
        self.assertEqual(probe["video_codec"], "h264")
        self.assertEqual(probe["audio_codec"], "aac")

    def test_05_audio_loudness_ebu_r128(self):
        """Verifica se a normalização de áudio atinge o padrão broadcast -14 LUFS."""
        output_mp4 = self.clips_out / "short_render_test.mp4"
        if not output_mp4.exists():
            self.test_04_ffmpeg_vertical_render_and_probe()

        loudness = self.ffmpeg.measure_loudness(str(output_mp4))
        self.assertTrue(loudness["measured"])
        i_lufs = loudness["integrated_lufs"]
        # Tolerância broadcast permitida: -16.5 a -11.5 LUFS
        self.assertGreaterEqual(i_lufs, -17.0)
        self.assertLessEqual(i_lufs, -11.0)

    def test_06_quality_control_agent_validation(self):
        """Testa o agente de QC em vídeos válidos, limites de Shorts e arquivos corrompidos."""
        output_mp4 = self.clips_out / "short_render_test.mp4"
        if not output_mp4.exists():
            self.test_04_ffmpeg_vertical_render_and_probe()

        sub_path = self.subs_out / "render_sub.ass"

        # Validação do vídeo correto
        report = self.qc.validate_rendered_short(
            video_path=output_mp4,
            task_id="render_sub",
            channel_id=1,
            ass_path=sub_path
        )

        self.assertFalse(report["critical_failed"])
        self.assertGreaterEqual(report["score"], 80)
        self.assertEqual(report["status"], "APPROVED_BY_QC")

        # Validação em arquivo inexistente
        bad_report = self.qc.validate_rendered_short(
            video_path=self.clips_out / "non_existent.mp4",
            task_id="ghost_task",
            channel_id=1
        )
        self.assertFalse(bad_report["passed"])
        self.assertEqual(bad_report["score"], 0)
        self.assertEqual(bad_report["status"], "REJECTED")

    def test_07_langgraph_step10_step11_pipeline_integration(self):
        """Testa a esteira integrada executando até as etapas 9, 10 e 11."""
        engine = IASOrchestrationEngine(db_path=str(self.db_path))

        final_state = engine.start_workflow(
            task_id="task_fase5_full_run",
            target_id="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            niche="futebol",
            channel_id=1
        )

        # O pipeline deve pausar na Etapa 11 (Portal 2) para aprovação humana
        self.assertEqual(final_state["status"], "PAUSED_FOR_REVIEW")
        self.assertEqual(final_state["current_step"], "11_revisao_humana")
        self.assertIn("9_preparacao_materiais", final_state["completed_steps"])
        self.assertIn("10_edicao_audiovisual", final_state["completed_steps"])

        # Verifica resultados da etapa 9 (TTS + Subtitles)
        step9 = final_state["step_results"]["9_preparacao_materiais"]
        self.assertTrue(step9["audio_generated"])
        self.assertTrue(step9["ass_file_generated"])
        self.assertTrue(os.path.exists(step9["audio_path"]))
        self.assertTrue(os.path.exists(step9["ass_path"]))

        # Verifica resultados da etapa 10 (Edição FFmpeg)
        step10 = final_state["step_results"]["10_edicao_audiovisual"]
        self.assertTrue(step10["rendered_successfully"])
        self.assertEqual(step10["resolution"], "1080x1920")
        self.assertTrue(os.path.exists(step10["output_clip_path"]))

        # Verifica resultados da etapa 11 (QC Agent + Portal 2)
        step11 = final_state["step_results"]["11_revisao_humana"]
        self.assertTrue(step11["waiting_approval"])
        self.assertIn("qc_report", step11)
        self.assertGreaterEqual(step11["qc_score"], 80)
        self.assertEqual(step11["approval_gate"], "PORTAL_2_EDITORIAL_DIRECTOR")


if __name__ == "__main__":
    unittest.main()
