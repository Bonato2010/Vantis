"""
VANTIS — Suíte de Testes da Fase 15
Validação Real de Shorts, Download Físico, Análise Multimodal e Integridade Operacional
Garante conformidade com as 12 regras obrigatórias da Fase 15.
"""

import os
import sys
import json
import tempfile
import sqlite3
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from core.pattern_learner import PatternLearner
from services.media_processing.media_downloader import MediaDownloader


class TestFase15RealShortsPhysicalPilot(unittest.TestCase):
    """Testes formais da Fase 15 — Rigor, Integridade e Zero Simulação."""

    def setUp(self):
        # Utiliza banco de dados temporário para isolamento absoluto dos testes
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()
        
        self.system = AudiovisualLearningSystem(db_path=self.temp_db_path)
        self.downloader = MediaDownloader(download_dir=Path(tempfile.gettempdir()) / "vantis_test_media")

    def tearDown(self):
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def test_rule_1_reject_videos_over_60s(self):
        """Regra 1: Vídeos com duração > 60s são terminantemente rejeitados para análise de Shorts."""
        with self.assertRaises(ValueError) as ctx:
            self.system.discover_video(
                source_id="long_vid_999",
                original_url="https://youtube.com/watch?v=long_vid_999",
                title="Vídeo Longo",
                creator="Canal Longo",
                niche="futebol",
                duration_seconds=60.1
            )
        self.assertIn("excede o limite de Shorts (60s)", str(ctx.exception))

    def test_rule_2_reject_videos_without_verifiable_duration(self):
        """Regra 2: Vídeos sem duração verificável (<=0 ou None) devem ser rejeitados."""
        with self.assertRaises(ValueError) as ctx1:
            self.system.discover_video(
                source_id="no_dur_001",
                original_url="https://youtube.com/watch?v=no_dur_001",
                title="Sem Duração",
                creator="Canal X",
                niche="curiosidades",
                duration_seconds=0.0
            )
        self.assertIn("Duração inválida", str(ctx1.exception))

        with self.assertRaises(ValueError) as ctx2:
            self.system.discover_video(
                source_id="no_dur_002",
                original_url="https://youtube.com/watch?v=no_dur_002",
                title="Sem Duração",
                creator="Canal X",
                niche="curiosidades",
                duration_seconds=-5.0
            )
        self.assertIn("Duração inválida", str(ctx2.exception))

    def test_rule_3_duplicate_ids_do_not_increment_valid_count(self):
        """Regra 3: Tentativas de reingerir vídeos com o mesmo source_id não duplicam contagens."""
        res1 = self.system.discover_video(
            source_id="unique_short_123",
            original_url="https://youtube.com/shorts/unique_short_123",
            title="Short Único",
            creator="Criador",
            niche="humor",
            duration_seconds=30.0
        )
        self.assertIn(res1.get("status"), ["SUCCESS", "discovered"])

        # Segunda tentativa com o mesmo source_id
        res2 = self.system.discover_video(
            source_id="unique_short_123",
            original_url="https://youtube.com/shorts/unique_short_123",
            title="Short Duplicado",
            creator="Criador",
            niche="humor",
            duration_seconds=30.0
        )
        self.assertEqual(res2.get("status"), "ALREADY_CATALOGED")

        # Verifica total no banco
        conn = sqlite3.connect(self.temp_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM audiovisual_library WHERE source_id = ?", ("unique_short_123",))
        count = cur.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_rule_4_incompatible_arguments_raise_visible_error(self):
        """Regra 4: Parâmetros incompatíveis devem disparar erro explícito (sem tolerância a kwargs arbitrários)."""
        self.system.discover_video(
            source_id="arg_check_short",
            original_url="https://youtube.com/shorts/arg_check_short",
            title="Short de Teste",
            creator="Criador",
            niche="curiosidades",
            duration_seconds=15.0
        )

        # 1. Composição dominante inválida
        with self.assertRaises(ValueError) as ctx:
            self.system.process_visual(
                source_id="arg_check_short",
                cuts_count=4,
                aspect_ratio="9:16",
                dominant_composition="composicao_inexistente_xyz"
            )
        self.assertIn("Composição dominante inválida", str(ctx.exception))

        # 2. Número negativo de cortes
        with self.assertRaises(ValueError) as ctx:
            self.system.process_visual(
                source_id="arg_check_short",
                cuts_count=-1,
                aspect_ratio="9:16"
            )
        self.assertIn("cuts_count deve ser um inteiro não-negativo", str(ctx.exception))

        # 3. LUFS fora do intervalo físico aceitável (-70 a +5)
        with self.assertRaises(ValueError) as ctx:
            self.system.process_audio(
                source_id="arg_check_short",
                estimated_lufs=10.5
            )
        self.assertIn("estimated_lufs fora dos limites", str(ctx.exception))

        # 4. Proporção de pausas fora de [0.0, 1.0]
        with self.assertRaises(ValueError) as ctx:
            self.system.process_audio(
                source_id="arg_check_short",
                pauses_ratio=1.5
            )
        self.assertIn("pauses_ratio deve estar entre 0.0 e 1.0", str(ctx.exception))

    def test_rule_5_critical_exceptions_not_silenced_by_try_except(self):
        """Regra 5: Métodos do pipeline propagam exceções e registram estado de erro em falha crítica."""
        with self.assertRaises(ValueError):
            self.system.process_visual(
                source_id="non_existent_vid_404",
                cuts_count=5,
                aspect_ratio="9:16"
            )

    def test_rule_6_videos_without_local_files_reject_physical_analysis(self):
        """Regra 6: Chamadas para análise física de mídia sem arquivo local existente devem falhar."""
        self.system.discover_video(
            source_id="no_file_short",
            original_url="https://youtube.com/shorts/no_file_short",
            title="Short Sem Arquivo",
            creator="Criador",
            niche="desenvolvimento_pessoal",
            duration_seconds=25.0
        )

        with self.assertRaises(FileNotFoundError) as ctx:
            self.system.register_physical_media(
                source_id="no_file_short",
                local_path="C:/caminho/completamente/inexistente/video.mp4"
            )
        self.assertIn("Arquivo físico de mídia não existe", str(ctx.exception))

    def test_rule_7_wpm_not_fabricated_without_transcript(self):
        """Regra 7: WPM não pode ser fabricado se não houver transcrição física ou legendas extraídas."""
        self.system.discover_video(
            source_id="empty_transcript_short",
            original_url="https://youtube.com/shorts/empty_transcript_short",
            title="Short Sem Transcrição",
            creator="Criador",
            niche="humor",
            duration_seconds=20.0
        )
        
        # Processa transcrição vazia (rejeita por falta de texto)
        res = self.system.process_transcript(
            source_id="empty_transcript_short",
            transcript_text=""
        )
        self.assertEqual(res.get("state"), "rejected")

        conn = sqlite3.connect(self.temp_db_path)
        cur = conn.cursor()
        cur.execute("SELECT processing_state, analysis_payload FROM audiovisual_library WHERE source_id = ?", ("empty_transcript_short",))
        row = cur.fetchone()
        conn.close()

        st = row[0]
        payload = json.loads(row[1] or "{}")
        narrative = payload.get("narrative_and_script", {})
        self.assertNotIn("speaking_pace_wpm", narrative, "WPM jamais deve ser inventado sem transcrição válida!")

    def test_rule_8_loudness_not_fabricated_without_media(self):
        """Regra 8: Medição acústica (LUFS) requer mídia física real e falha na ausência do arquivo."""
        with self.assertRaises(FileNotFoundError):
            self.system._analyze_audio_file("C:/arquivos_inexistentes/audio_fantasma.mp4")

    def test_rule_9_partial_analysis_does_not_become_fully_analyzed(self):
        """Regra 9: Análise parcial (somente metadados ou visual) não pode transitar para 'fully_analyzed'."""
        self.system.discover_video(
            source_id="partial_short_1",
            original_url="https://youtube.com/shorts/partial_short_1",
            title="Short Parcial",
            creator="Criador",
            niche="futebol_outros",
            duration_seconds=45.0
        )
        
        # Apenas metadados
        self.system.process_metadata("partial_short_1")

        conn = sqlite3.connect(self.temp_db_path)
        cur = conn.cursor()
        cur.execute("SELECT processing_state FROM audiovisual_library WHERE source_id = ?", ("partial_short_1",))
        st = cur.fetchone()[0]
        conn.close()

        self.assertEqual(st, "metadata_processed")
        self.assertNotEqual(st, "fully_analyzed")

    def test_rule_10_editorial_patterns_have_traceable_evidence(self):
        """Regra 10: Padrões editoriais gravados devem conter IDs de evidência válidos e rastreáveis."""
        with self.assertRaises(ValueError) as ctx:
            self.system.record_knowledge(
                category="humor",
                topic="timing_comico",
                pattern_description="Padrão sem evidência",
                confidence_score=0.9,
                evidence_video_ids=[]  # Evidência vazia deve disparar erro
            )
        self.assertIn("evidence_video_ids não pode estar vazio", str(ctx.exception))

    def test_rule_11_dashboard_reflects_real_states(self):
        """Regra 11: Telemetria de visão geral reflete com precisão os estados reais armazenados."""
        # Registra 2 vídeos em estados diferentes
        self.system.discover_video(
            source_id="dash_vid_1",
            original_url="https://youtube.com/shorts/dash_vid_1",
            title="Dash Vid 1",
            creator="Criador",
            niche="curiosidades",
            duration_seconds=30.0
        )
        self.system.discover_video(
            source_id="dash_vid_2",
            original_url="https://youtube.com/shorts/dash_vid_2",
            title="Dash Vid 2",
            creator="Criador",
            niche="curiosidades",
            duration_seconds=20.0
        )
        self.system.process_metadata("dash_vid_2")

        stats = self.system.get_overview_statistics()
        self.assertEqual(stats.get("total_cataloged"), 2)
        # 1 em discovered, 1 em metadata_processed
        breakdown = stats.get("status_breakdown", {})
        self.assertEqual(breakdown.get("discovered"), 1)
        self.assertEqual(breakdown.get("metadata_processed"), 1)
        self.assertEqual(breakdown.get("fully_analyzed", 0), 0)

    def test_rule_12_batch_resumption_without_duplicate_ingestion(self):
        """Regra 12: Retomada de lote ignora itens já cadastrados sem corromper integridade."""
        temp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_video.write(b"SIMULATED_MEDIA_FOR_TEST_ONLY_1234567890")
        temp_video.close()

        try:
            # Primeiro ciclo
            self.system.discover_video(
                source_id="batch_vid_resume",
                original_url="https://youtube.com/shorts/batch_vid_resume",
                title="Batch Resume",
                creator="Criador",
                niche="futebol",
                duration_seconds=15.0
            )

            # Segundo ciclo (retomada): deve detectar que já existe
            res = self.system.discover_video(
                source_id="batch_vid_resume",
                original_url="https://youtube.com/shorts/batch_vid_resume",
                title="Batch Resume",
                creator="Criador",
                niche="futebol",
                duration_seconds=15.0
            )
            self.assertEqual(res.get("status"), "ALREADY_CATALOGED")
        finally:
            if os.path.exists(temp_video.name):
                try:
                    os.remove(temp_video.name)
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()
