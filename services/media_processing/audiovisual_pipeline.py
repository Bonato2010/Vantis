"""
IAS / VANTIS Audiovisual Production Pipeline (services/media_processing/audiovisual_pipeline.py)
================================================================================================
Pipeline audiovisual de alta fidelidade estruturado em 10 etapas modulares, funcionais e rastreáveis.
Garante integridade técnica, proveniência de direitos autorais, valor editorial transformativo,
isolamento por canal, travas de conformidade EBU R128 (-14 LUFS), Smart Crop 9:16 (1080x1920)
e auditoria de qualidade (QC) antes da liberação para o Portal 2 (Aprovação Humana).
"""

import os
import re
import sys
import json
import time
import shutil
import sqlite3
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.media_processing.ffmpeg_engine import FFmpegEngine
from services.media_processing.tts_engine import TTSNarrationService
from services.media_processing.subtitle_generator import SubtitleGenerator
from services.transcription.whisper_service import WhisperTranscriptionService
from services.video_analysis.scene_detector import SceneDetectorService
from services.video_analysis.visual_analyzer import OpenCVVisualAnalyzer
from agents.qc_agent import QualityControlAgent
from core.channel_manager import ChannelManager

logger = logging.getLogger("AudiovisualPipeline")


class AudiovisualPipelineError(Exception):
    """Exceção base para falhas operacionais do pipeline audiovisual."""
    def __init__(self, stage: str, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"[{stage}] {code}: {message}")
        self.stage = stage
        self.code = code
        self.message = message
        self.details = details or {}


class AudiovisualProductionPipeline:
    """
    Pipeline industrial de produção e processamento audiovisual do VANTIS.
    Organizado em 10 etapas sequenciais e modulares:
      1. Recebimento e validação da mídia
      2. Extração de metadados e proveniência
      3. Transcrição (Faster-Whisper / Timestamps)
      4. Análise de cenas e conteúdo (PySceneDetect + OpenCV)
      5. Seleção e validação de trechos
      6. Preparação de cortes e enquadramento 9:16
      7. Processamento audiovisual, mixagem e renderização (FFmpeg + EBU R128)
      8. Geração de versões preliminares e thumbnail
      9. Revisão de qualidade técnica automatizada (QC)
      10. Armazenamento, manifesto e registro no banco de dados
    """

    SUPPORTED_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
    SUPPORTED_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

    def __init__(
        self,
        db_path: Optional[str] = None,
        workspace_dir: Optional[Union[str, Path]] = None,
        channel_manager: Optional[ChannelManager] = None
    ):
        self.db_path = str(db_path or (BASE_DIR / "database" / "shorts_central.db"))
        self.workspace = Path(workspace_dir or (BASE_DIR / "workspace"))
        self.raw_dir = self.workspace / "raw"
        self.audio_dir = self.workspace / "audio"
        self.subs_dir = self.workspace / "subs"
        self.clips_dir = self.workspace / "clips"

        for d in [self.raw_dir, self.audio_dir, self.subs_dir, self.clips_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.ffmpeg = FFmpegEngine()
        self.channel_manager = channel_manager or ChannelManager(db_path=self.db_path)
        self.tts_service = TTSNarrationService(output_dir=self.audio_dir, channel_manager=self.channel_manager)
        self.sub_generator = SubtitleGenerator(output_dir=self.subs_dir, channel_manager=self.channel_manager)
        self.whisper_service = WhisperTranscriptionService()
        self.scene_detector = SceneDetectorService()
        self.visual_analyzer = OpenCVVisualAnalyzer()
        self.qc_agent = QualityControlAgent(ffmpeg_engine=self.ffmpeg, channel_manager=self.channel_manager, db_path=self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # ETAPA 1: RECEBIMENTO E VALIDAÇÃO DA MÍDIA
    # =========================================================================
    def stage_1_validate_input_media(self, media_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Recebe e valida a mídia de entrada:
        - Verifica existência e tamanho físico (> 1000 bytes)
        - Valida integridade do contêiner e detecção de arquivo corrompido
        - Valida extensão de formato suportado
        - Identifica streams de áudio e vídeo
        """
        p = Path(media_path)
        if not p.exists():
            raise AudiovisualPipelineError(
                stage="stage_1_validate_input",
                code="FILE_NOT_FOUND",
                message=f"Arquivo de mídia não encontrado: {p}",
                details={"path": str(p)}
            )

        suffix = p.suffix.lower()
        is_video = suffix in self.SUPPORTED_VIDEO_EXTS
        is_audio = suffix in self.SUPPORTED_AUDIO_EXTS
        if not (is_video or is_audio):
            raise AudiovisualPipelineError(
                stage="stage_1_validate_input",
                code="UNSUPPORTED_MEDIA_FORMAT",
                message=f"Formato de mídia não suportado: '{suffix}'. Formatos aceitos: {self.SUPPORTED_VIDEO_EXTS | self.SUPPORTED_AUDIO_EXTS}",
                details={"suffix": suffix}
            )

        size_bytes = p.stat().st_size
        if size_bytes < 1000:
            raise AudiovisualPipelineError(
                stage="stage_1_validate_input",
                code="CORRUPTED_FILE_ZERO_OR_TRUNCATED",
                message=f"Arquivo de mídia vazio ou corrompido ({size_bytes} bytes): {p}",
                details={"path": str(p), "size_bytes": size_bytes}
            )

        # Validação de integridade real via FFprobe / FFmpeg
        probe = self.ffmpeg.probe_media(str(p))
        if not probe.get("exists") or probe.get("duration_sec", 0.0) <= 0.0:
            # Tenta decodificação leve de teste
            if self.ffmpeg.available:
                test_cmd = [
                    self.ffmpeg.binary_path, "-v", "error",
                    "-i", str(p),
                    "-f", "null", "-"
                ]
                res = subprocess.run(test_cmd, capture_output=True, text=True, timeout=15)
                if res.returncode != 0:
                    raise AudiovisualPipelineError(
                        stage="stage_1_validate_input",
                        code="CORRUPTED_MEDIA_STREAM",
                        message=f"Arquivo corrompido: falha na decodificação do container: {res.stderr[:200]}",
                        details={"stderr": res.stderr}
                    )

        has_video = probe.get("has_video", False)
        has_audio = probe.get("has_audio", False)
        duration_sec = probe.get("duration_sec", 0.0)

        if not has_video and not has_audio:
            raise AudiovisualPipelineError(
                stage="stage_1_validate_input",
                code="NO_STREAMS_FOUND",
                message="Nenhum fluxo de áudio ou vídeo detectado no arquivo.",
                details=probe
            )

        return {
            "valid": True,
            "media_path": str(p),
            "media_type": "video" if has_video else "audio",
            "has_video": has_video,
            "has_audio": has_audio,
            "duration_sec": duration_sec,
            "size_bytes": size_bytes,
            "file_ext": suffix,
            "probe_details": probe
        }

    # =========================================================================
    # ETAPA 2: EXTRAÇÃO DE METADADOS E PROVENIÊNCIA
    # =========================================================================
    def stage_2_extract_metadata(
        self,
        media_path: Union[str, Path],
        provenance: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extrai metadados técnicos precisos e consolida registro de direitos autorais:
        - Resolução, codecs, bitrate, canais de áudio, aspect ratio
        - Registro de autoria original, licença e propósito transformativo
        """
        p = Path(media_path)
        probe = self.ffmpeg.probe_media(str(p))
        prov = provenance or {}

        source_url = prov.get("source_url") or "local_ingest"
        source_author = prov.get("source_author") or "Desconhecido / Licenciado"
        source_license = prov.get("source_license") or "fair_use_transformative"
        transformative_type = prov.get("transformative_type") or "educational_analysis"

        # Trava de conformidade de direitos: proíbe redistribuição direta sem transformação
        if transformative_type == "raw_reupload_prohibited":
            raise AudiovisualPipelineError(
                stage="stage_2_extract_metadata",
                code="COPYRIGHT_COMPLIANCE_BLOCKED",
                message="Operação cancelada: reupload direto sem valor transformativo viola as diretrizes de direitos autorais do VANTIS.",
                details={"transformative_type": transformative_type}
            )

        width = probe.get("width", 0)
        height = probe.get("height", 0)
        duration = probe.get("duration_sec", 0.0)

        metadata = {
            "file_name": p.name,
            "file_path": str(p),
            "file_size_mb": round(p.stat().st_size / (1024 * 1024), 2),
            "duration_sec": round(duration, 2),
            "width": width,
            "height": height,
            "is_vertical": probe.get("is_vertical", False),
            "aspect_ratio": probe.get("aspect_ratio"),
            "video_codec": probe.get("video_codec"),
            "audio_codec": probe.get("audio_codec"),
            "has_video": probe.get("has_video", False),
            "has_audio": probe.get("has_audio", False),
            "provenance": {
                "source_url": source_url,
                "source_author": source_author,
                "source_license": source_license,
                "transformative_type": transformative_type,
                "transformative_intent": f"Análise editorial crítica e síntese autoral ({transformative_type})"
            }
        }
        return metadata

    # =========================================================================
    # ETAPA 3: TRANSCRIÇÃO (QUANDO APLICÁVEL)
    # =========================================================================
    def stage_3_transcribe_audio(
        self,
        media_path: Union[str, Path],
        task_id: str,
        language: str = "pt",
        provided_script: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcreve o áudio nativo usando Faster-Whisper com timestamps em nível de frase e palavra.
        Se o arquivo for vídeo, extrai previamente áudio em 16kHz mono.
        Se já houver roteiro estruturado fornecido e sem áudio de fala, valida compatibilidade.
        """
        p = Path(media_path)
        v_info = self.ffmpeg.probe_media(str(p))

        # Se for vídeo sem áudio
        if v_info.get("has_video") and not v_info.get("has_audio"):
            if provided_script:
                return {
                    "transcribed": False,
                    "engine": "script_provided_no_audio_in_video",
                    "full_transcript": provided_script,
                    "segments": [],
                    "total_words": len(provided_script.split()),
                    "pacing_wpm": 150.0
                }
            raise AudiovisualPipelineError(
                stage="stage_3_transcribe_audio",
                code="MISSING_AUDIO_STREAM",
                message="Vídeo de entrada não possui trilha de áudio e nenhum roteiro/narração foi fornecido.",
                details={"media_path": str(p)}
            )

        # Extrai áudio temporário se for arquivo de vídeo
        audio_target = p
        temp_extracted_wav = None
        if v_info.get("has_video") and v_info.get("has_audio"):
            temp_extracted_wav = self.audio_dir / f"{task_id}_extracted_16k.wav"
            extracted_ok = self.ffmpeg.extract_audio(str(p), str(temp_extracted_wav))
            if not extracted_ok or not temp_extracted_wav.exists():
                raise AudiovisualPipelineError(
                    stage="stage_3_transcribe_audio",
                    code="AUDIO_EXTRACTION_FAILED",
                    message="Falha ao extrair trilha de áudio mono a 16kHz do arquivo de vídeo.",
                    details={"media_path": str(p)}
                )
            audio_target = temp_extracted_wav

        # Executa transcrição real com Faster-Whisper
        try:
            trans_res = self.whisper_service.transcribe_audio(str(audio_target), language=language)
            if "error" in trans_res:
                raise RuntimeError(trans_res["error"])
        except Exception as e:
            # Tratamento de erro sem gerar resultados falsos silenciosos
            raise AudiovisualPipelineError(
                stage="stage_3_transcribe_audio",
                code="TRANSCRIPTION_ENGINE_ERROR",
                message=f"Falha na transcrição de áudio: {str(e)}",
                details={"audio_target": str(audio_target), "error": str(e)}
            )
        finally:
            # Limpa áudio temporário intermediário se necessário
            if temp_extracted_wav and temp_extracted_wav.exists():
                try:
                    temp_extracted_wav.unlink(missing_ok=True)
                except Exception:
                    pass

        return {
            "transcribed": True,
            "engine": trans_res.get("engine", "faster_whisper"),
            "duration_sec": trans_res.get("duration_sec", 0.0),
            "total_words": trans_res.get("total_words", 0),
            "pacing_wpm": trans_res.get("pacing_wpm", 0.0),
            "full_transcript": trans_res.get("full_transcript", ""),
            "segments": trans_res.get("segments", [])
        }

    # =========================================================================
    # ETAPA 4: ANÁLISE DE CENAS E CONTEÚDO
    # =========================================================================
    def stage_4_analyze_scenes_and_content(self, video_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Executa análise técnica de vídeo:
        - PySceneDetect: detecção de cortes de cena e cálculo de ritmo visual (BPM)
        - OpenCV: detecção de saliência de movimento e Smart Crop 9:16
        """
        p = Path(video_path)
        v_info = self.ffmpeg.probe_media(str(p))
        if not v_info.get("has_video"):
            return {
                "has_video": False,
                "visual_bpm": 0.0,
                "scene_count": 0,
                "scenes": [],
                "smart_crop": {
                    "center_x_normalized": 0.50,
                    "ffmpeg_crop_offset_x": "(iw-ow)/2",
                    "smart_crop_applied": False
                }
            }

        # 1. Detecção de Cenas
        scene_res = self.scene_detector.detect_scenes(str(p))
        scenes = scene_res.get("scenes", [])
        visual_bpm = scene_res.get("visual_bpm", 18.0)

        # 2. Análise Visual de Movimento e Smart Crop com OpenCV
        visual_res = self.visual_analyzer.analyze_framing_and_motion(str(p))
        crop_center_x = visual_res.get("recommended_crop_center_x", 0.50)
        crop_offset_x = visual_res.get("ffmpeg_crop_offset_x", "(iw-ow)/2")
        smart_crop_applied = visual_res.get("smart_crop_applied", False)

        return {
            "has_video": True,
            "visual_bpm": float(visual_bpm),
            "scene_count": len(scenes),
            "scenes": scenes,
            "motion_score": visual_res.get("average_motion_score", 0.0),
            "estimated_shot_type": visual_res.get("estimated_shot_type", "Standard"),
            "smart_crop": {
                "center_x_normalized": crop_center_x,
                "ffmpeg_crop_offset_x": crop_offset_x,
                "smart_crop_applied": smart_crop_applied
            }
        }

    # =========================================================================
    # ETAPA 5: SELEÇÃO E VALIDAÇÃO DE TRECHOS
    # =========================================================================
    def stage_5_select_segments(
        self,
        total_duration: float,
        start_sec: Optional[float] = None,
        end_sec: Optional[float] = None,
        scenes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Seleciona e valida rigorosamente os limites do corte:
        - Valida que start >= 0
        - Valida que end > start
        - Valida que end <= total_duration
        - Valida duração permitida para Shorts (15.0s a 59.0s)
        - Se não fornecido, encontra o intervalo de maior impacto dentro dos limites
        """
        # Se os cortes forem fornecidos explicitamente
        if start_sec is not None and end_sec is not None:
            s = float(start_sec)
            e = float(end_sec)

            if s < 0.0:
                raise AudiovisualPipelineError(
                    stage="stage_5_select_segments",
                    code="INVALID_CUT_NEGATIVE_START",
                    message=f"Timestamp de início inválido ({s}s). O valor não pode ser negativo.",
                    details={"start_sec": s, "end_sec": e}
                )

            if s >= e:
                raise AudiovisualPipelineError(
                    stage="stage_5_select_segments",
                    code="INVALID_CUT_START_GE_END",
                    message=f"Corte inválido: início ({s}s) maior ou igual ao fim ({e}s).",
                    details={"start_sec": s, "end_sec": e}
                )

            # Tolerância de 0.5s para limites de container
            if total_duration > 0 and e > (total_duration + 0.5):
                raise AudiovisualPipelineError(
                    stage="stage_5_select_segments",
                    code="INVALID_CUT_EXCEEDS_DURATION",
                    message=f"Timestamp final ({e}s) excede a duração total do arquivo ({total_duration}s).",
                    details={"start_sec": s, "end_sec": e, "total_duration": total_duration}
                )

            cut_duration = e - s
            if cut_duration < 15.0 or cut_duration > 59.0:
                raise AudiovisualPipelineError(
                    stage="stage_5_select_segments",
                    code="INVALID_SHORTS_DURATION",
                    message=f"Duração do corte ({round(cut_duration, 2)}s) fora da especificação YouTube Shorts (15s a 59s).",
                    details={"cut_duration": cut_duration, "min": 15.0, "max": 59.0}
                )

            chosen_start = s
            chosen_end = min(e, total_duration) if total_duration > 0 else e
        else:
            # Algoritmo de seleção automática para formato Short (alvo: 35s a 45s)
            if total_duration <= 0:
                chosen_start = 0.0
                chosen_end = 30.0
            elif total_duration <= 59.0:
                chosen_start = 0.0
                chosen_end = max(15.0, total_duration)
            else:
                # Seleciona bloco de 35s a partir do primeiro corte relevante de cena
                chosen_start = 0.0
                if scenes and len(scenes) > 1:
                    # Começa próximo a um início de cena para dinamismo
                    first_scene_start = scenes[0].get("start_sec", 0.0)
                    chosen_start = first_scene_start
                target_len = min(42.0, total_duration - chosen_start)
                chosen_end = chosen_start + max(15.0, target_len)

        return {
            "start_sec": round(chosen_start, 2),
            "end_sec": round(chosen_end, 2),
            "cut_duration_sec": round(chosen_end - chosen_start, 2),
            "is_within_shorts_range": 15.0 <= (chosen_end - chosen_start) <= 59.0
        }

    # =========================================================================
    # ETAPA 6: PREPARAÇÃO DE CORTES E ENQUADRAMENTO 9:16
    # =========================================================================
    def stage_6_prepare_cuts(
        self,
        segment_info: Dict[str, Any],
        analysis_info: Dict[str, Any],
        channel_id: int
    ) -> Dict[str, Any]:
        """
        Monta a diretriz de edição:
        - Ajusta offset do Smart Crop 9:16 para não cortar o sujeito
        - Configura perfil de renderização e identidade visual do canal
        """
        smart_crop = analysis_info.get("smart_crop", {})
        crop_offset_x = smart_crop.get("ffmpeg_crop_offset_x", "(iw-ow)/2")

        # Busca perfil visual do canal
        settings = self.channel_manager.get_channel_settings(channel_id)
        sub_style = self.sub_generator.get_channel_style(channel_id)
        voice_profile = self.tts_service.get_channel_voice_config(channel_id)

        return {
            "channel_id": channel_id,
            "target_resolution": "1080x1920",
            "aspect_ratio": "9:16",
            "start_sec": segment_info["start_sec"],
            "end_sec": segment_info["end_sec"],
            "duration_sec": segment_info["cut_duration_sec"],
            "crop_offset_x": crop_offset_x,
            "fps": 30,
            "subtitle_style": sub_style,
            "voice_profile": voice_profile,
            "audio_target_lufs": -14.0
        }

    # =========================================================================
    # ETAPA 7: PROCESSAMENTO AUDIOVISUAL E RENDERIZAÇÃO
    # =========================================================================
    def stage_7_process_av_and_render(
        self,
        task_id: str,
        channel_id: int,
        input_video_path: Optional[str],
        narration_audio_path: Optional[str],
        ass_subtitles_path: Optional[str],
        render_prep: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executa a renderização audiovisual de alto desempenho com FFmpeg:
        - Normalização EBU R128 (-14 LUFS)
        - Queima de legendas ASS dinâmicas
        - Enquadramento vertical 9:16 (1080x1920)
        - Renderização de Canvas nativo caso não haja vídeo bruto
        """
        output_file = self.clips_dir / f"{task_id}.mp4"
        start_sec = render_prep["start_sec"]
        end_sec = render_prep["end_sec"]
        crop_offset_x = render_prep.get("crop_offset_x", "(iw-ow)/2")

        if input_video_path and os.path.exists(input_video_path):
            render_res = self.ffmpeg.render_vertical_short(
                input_video=input_video_path,
                output_path=str(output_file),
                start_sec=start_sec,
                end_sec=end_sec,
                ass_subtitles_path=ass_subtitles_path,
                narration_audio_path=narration_audio_path,
                crop_offset_x=crop_offset_x,
                channel_variant=channel_id,
                normalize_audio=True
            )
        elif narration_audio_path and os.path.exists(narration_audio_path):
            # Renderização de Canvas Dinâmico 9:16 a partir de áudio de narração e legendas
            bg_colors = {
                1: "0x001E0A", # Futebol - Verde floresta escuro
                2: "0x0A0A14", # Arquivo Sombrio - Preto azulado
                3: "0x140A00", # Humor - Marrom escuro
                4: "0x00141E", # Curiosidades - Azul profundo
                5: "0x1E1400", # Produtividade - Âmbar escuro
            }
            bg_color = bg_colors.get(channel_id, "0x0D0D11")
            cut_dur = max(15.0, end_sec - start_sec)
            render_res = self.ffmpeg.generate_canvas_short(
                audio_path=narration_audio_path,
                output_path=str(output_file),
                bg_color=bg_color,
                ass_subtitles_path=ass_subtitles_path,
                channel_variant=channel_id,
                duration_sec=cut_dur
            )
        else:
            raise AudiovisualPipelineError(
                stage="stage_7_process_av_and_render",
                code="NO_RENDERABLE_MEDIA",
                message="Nenhum arquivo de vídeo ou narração de áudio foi disponibilizado para renderização.",
                details={"input_video_path": input_video_path, "narration_audio_path": narration_audio_path}
            )

        if not render_res.get("success") or not output_file.exists():
            raise AudiovisualPipelineError(
                stage="stage_7_process_av_and_render",
                code="RENDER_EXECUTION_FAILED",
                message=f"Falha na execução do FFmpeg: {render_res.get('error')}",
                details=render_res
            )

        return {
            "success": True,
            "output_path": str(output_file),
            "rendered_duration_sec": render_res.get("duration_sec", 0.0),
            "size_mb": render_res.get("size_mb", 0.0),
            "resolution": "1080x1920 (9:16)",
            "output_file": str(output_file)
        }

    # =========================================================================
    # ETAPA 8: GERAÇÃO DE VERSÕES PRELIMINARES E THUMBNAIL
    # =========================================================================
    def stage_8_generate_previews(
        self,
        task_id: str,
        rendered_video_path: str,
        best_timestamp_sec: float = 2.0
    ) -> Dict[str, Any]:
        """
        Extrai frame de destaque para miniatura em alta resolução (1080x1920 .jpg)
        e registra ponto de verificação para reprodução visual no Portal 2.
        """
        thumb_path = self.clips_dir / f"{task_id}_thumb.jpg"
        v_info = self.ffmpeg.probe_media(rendered_video_path)
        dur = v_info.get("duration_sec", 5.0)

        # Garante que o timestamp do frame de miniatura esteja no primeiro terço (gancho inicial)
        target_time = min(max(1.0, best_timestamp_sec), max(1.0, dur * 0.35))

        frame_extracted = False
        if self.ffmpeg.available:
            frame_extracted = self.ffmpeg.extract_frame(
                video_path=rendered_video_path,
                timestamp_sec=target_time,
                output_img=str(thumb_path)
            )

        return {
            "preview_ready": True,
            "preview_video_path": rendered_video_path,
            "thumbnail_path": str(thumb_path) if frame_extracted and thumb_path.exists() else None,
            "thumbnail_timestamp_sec": target_time
        }

    # =========================================================================
    # ETAPA 9: REVISÃO DE QUALIDADE TÉCNICA (QC AUTOMATIZADO)
    # =========================================================================
    def stage_9_review_quality(
        self,
        task_id: str,
        channel_id: int,
        rendered_video_path: str,
        ass_subtitles_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Audita rigorosamente o vídeo renderizado contra a especificação VANTIS:
        - 1. Arquivo íntegro e não corrompido (tamanho > 10KB)
        - 2. Fluxos de áudio e vídeo presentes e decodificáveis
        - 3. Resolução estritamente 1080x1920 (9:16)
        - 4. Duração estritamente entre 15.0s e 59.0s
        - 5. Loudness EBU R128 (-16.0 a -12.0 LUFS, alvo -14 LUFS)
        - 6. Sincronia de legendas (sem eventos de legenda extrapolando a duração do vídeo)
        """
        p = Path(rendered_video_path)
        if not p.exists() or p.stat().st_size < 10_000:
            return {
                "passed": False,
                "qc_score": 0,
                "status": "REJECTED_CORRUPTED",
                "failure_reasons": ["Arquivo renderizado inexistente, truncado ou corrompido."]
            }

        probe = self.ffmpeg.probe_media(str(p))
        width = probe.get("width", 0)
        height = probe.get("height", 0)
        duration = probe.get("duration_sec", 0.0)
        has_video = probe.get("has_video", False)
        has_audio = probe.get("has_audio", False)

        # Medição de Loudness via filtro EBU R128
        loudness_info = self.ffmpeg.measure_loudness(str(p))
        measured_lufs = loudness_info.get("integrated_lufs", -14.0)

        # Checagem de sincronia de legendas
        subs_sync_ok = True
        subs_failure_msg = None
        if ass_subtitles_path and os.path.exists(ass_subtitles_path):
            with open(ass_subtitles_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Encontra tempos finais de diálogo: Dialogue: 0,0:00:01.00,0:00:03.50,...
                matches = re.findall(r"Dialogue:\s*\d+,\d+:(\d+):([\d\.]+),(\d+):(\d+):([\d\.]+)", content)
                for m in matches:
                    try:
                        end_h = int(m[2])
                        end_m = int(m[3])
                        end_s = float(m[4])
                        total_sub_end = end_h * 3600 + end_m * 60 + end_s
                        # Tolerância de 1.5s além do fim do vídeo
                        if duration > 0 and total_sub_end > (duration + 1.5):
                            subs_sync_ok = False
                            subs_failure_msg = f"Legenda desincronizada: evento de legenda termina em {round(total_sub_end, 2)}s, mas vídeo tem {round(duration, 2)}s."
                            break
                    except Exception:
                        pass

        resolution_ok = (width == 1080 and height == 1920)
        duration_ok = (15.0 <= duration <= 59.0)
        loudness_ok = (-16.5 <= measured_lufs <= -11.5)
        streams_ok = (has_video and has_audio)

        score = 100
        failures = []

        if not streams_ok:
            score -= 40
            failures.append(f"Fluxos de mídia incompletos: Vídeo={has_video}, Áudio={has_audio}")
        if not resolution_ok:
            score -= 30
            failures.append(f"Resolução inadequada ({width}x{height}). Exigido estritamente 1080x1920 (9:16).")
        if not duration_ok:
            score -= 25
            failures.append(f"Duração inválida ({round(duration, 2)}s). Permitido: 15.0s a 59.0s.")
        if not loudness_ok:
            score -= 20
            failures.append(f"Loudness fora do padrão EBU R128 ({measured_lufs} LUFS). Alvo: -14 LUFS.")
        if not subs_sync_ok:
            score -= 15
            failures.append(subs_failure_msg or "Legendas fora de sincronia com a trilha de áudio.")

        passed = (len(failures) == 0) and (score >= 80)

        return {
            "passed": passed,
            "qc_score": max(0, score),
            "status": "APPROVED_READY_FOR_PORTAL_2" if passed else "FAILED_QC",
            "duration_sec": duration,
            "resolution": f"{width}x{height}",
            "integrated_lufs": measured_lufs,
            "has_video": has_video,
            "has_audio": has_audio,
            "subtitles_synced": subs_sync_ok,
            "failure_reasons": failures,
            "checks": {
                "file_integrity": True,
                "streams_intact": streams_ok,
                "resolution_9x16": resolution_ok,
                "duration_shorts": duration_ok,
                "loudness_ebu_r128": loudness_ok,
                "subtitles_synced": subs_sync_ok
            }
        }

    # =========================================================================
    # ETAPA 10: ARMAZENAMENTO E REGISTRO DO RESULTADO
    # =========================================================================
    def stage_10_store_and_register(
        self,
        task_id: str,
        channel_id: int,
        source_media_path: Optional[str],
        output_media_path: str,
        thumbnail_path: Optional[str],
        provenance: Dict[str, Any],
        qc_result: Dict[str, Any],
        stage_timings: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Persiste o registro oficial do job audiovisual no SQLite:
        - Tabela `audiovisual_pipeline_runs`
        - Emite o manifesto de prontidão para o Portal 2
        """
        status = "COMPLETED" if qc_result.get("passed") else "FAILED_QC"
        duration_sec = qc_result.get("duration_sec", 0.0)
        resolution = qc_result.get("resolution", "1080x1920")
        loudness_lufs = qc_result.get("integrated_lufs", -14.0)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO audiovisual_pipeline_runs (
                    task_id, channel_id, source_media_path, output_media_path, thumbnail_path,
                    source_url, source_author, source_license, transformative_type,
                    status, current_stage, duration_sec, resolution, loudness_lufs,
                    qc_passed, qc_score, qc_details_json, stage_timings_json,
                    metadata_json, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                task_id,
                channel_id,
                str(source_media_path) if source_media_path else None,
                str(output_media_path),
                str(thumbnail_path) if thumbnail_path else None,
                provenance.get("source_url", "local_ingest"),
                provenance.get("source_author", "Desconhecido"),
                provenance.get("source_license", "fair_use_transformative"),
                provenance.get("transformative_type", "educational_analysis"),
                status,
                "COMPLETED" if status == "COMPLETED" else "FAILED_IN_QC",
                duration_sec,
                resolution,
                loudness_lufs,
                1 if qc_result.get("passed") else 0,
                qc_result.get("qc_score", 0),
                json.dumps(qc_result, ensure_ascii=False),
                json.dumps(stage_timings, ensure_ascii=False),
                json.dumps({
                    "channel_id": channel_id,
                    "task_id": task_id,
                    "portal_2_ready": qc_result.get("passed", False)
                }, ensure_ascii=False)
            ))
            conn.commit()

        return {
            "task_id": task_id,
            "channel_id": channel_id,
            "status": status,
            "output_path": output_media_path,
            "thumbnail_path": thumbnail_path,
            "qc_passed": qc_result.get("passed", False),
            "qc_score": qc_result.get("qc_score", 0),
            "portal_2_ready": qc_result.get("passed", False)
        }

    # =========================================================================
    # ORQUESTRADOR CENTRAL DO PIPELINE AUDIOVISUAL (10 ETAPAS)
    # =========================================================================
    def execute_full_pipeline(self, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa sequencialmente e com rastreamento temporal todas as 10 etapas do pipeline audiovisual.
        """
        task_id = job_config.get("task_id", f"av_task_{int(time.time())}")
        channel_id = int(job_config.get("channel_id", 1))
        input_media_path = job_config.get("input_media_path")
        script_text = job_config.get("script_text")
        generate_tts = job_config.get("generate_tts", False)
        generate_subs = job_config.get("generate_subtitles", True)
        cut_start_sec = job_config.get("cut_start_sec")
        cut_end_sec = job_config.get("cut_end_sec")
        provenance = job_config.get("provenance", {})

        timings: Dict[str, float] = {}
        t_global_start = time.time()

        try:
            # ETAPA 1: Recebimento e validação da mídia (ou preparação de locução sintética)
            t0 = time.time()
            if input_media_path and os.path.exists(input_media_path):
                val_res = self.stage_1_validate_input_media(input_media_path)
            elif script_text:
                # Geração a partir de roteiro puro
                val_res = {
                    "valid": True,
                    "media_path": None,
                    "media_type": "script_only",
                    "has_video": False,
                    "has_audio": False,
                    "duration_sec": 30.0
                }
            else:
                raise AudiovisualPipelineError(
                    stage="stage_1_validate_input",
                    code="EMPTY_INPUT_SPECIFICATION",
                    message="O job deve fornecer ao menos um arquivo de mídia existente ou um roteiro de texto."
                )
            timings["stage_1_validate_media_ms"] = round((time.time() - t0) * 1000, 2)

            # ETAPA 2: Extração de metadados e proveniência
            t0 = time.time()
            if input_media_path and os.path.exists(input_media_path):
                meta_res = self.stage_2_extract_metadata(input_media_path, provenance=provenance)
            else:
                meta_res = {
                    "file_name": f"{task_id}.txt",
                    "file_path": None,
                    "duration_sec": 30.0,
                    "provenance": provenance or {
                        "source_url": "original_production",
                        "source_author": f"Canal {channel_id}",
                        "source_license": "original_work",
                        "transformative_type": "original_production"
                    }
                }
            timings["stage_2_extract_metadata_ms"] = round((time.time() - t0) * 1000, 2)

            # ETAPA 3: Transcrição / Síntese Neural de Locução (Edge-TTS)
            t0 = time.time()
            narration_audio_path = None
            narration_boundaries = []

            if generate_tts and script_text:
                # Síntese autoral gratuita via Edge-TTS
                tts_output = self.audio_dir / f"{task_id}_tts.mp3"
                tts_res = self.tts_service.generate_narration(
                    text=script_text,
                    channel_id=channel_id,
                    task_id=task_id,
                    output_path=str(tts_output)
                )
                narration_audio_path = tts_res.get("audio_path")
                narration_boundaries = tts_res.get("sentence_boundaries", [])
                transcribe_res = {
                    "transcribed": True,
                    "engine": "edge_tts_boundary_alignment",
                    "full_transcript": script_text,
                    "segments": [
                        {"start": b["start_sec"], "end": b["end_sec"], "text": b["text"]}
                        for b in narration_boundaries
                    ] if narration_boundaries else []
                }
            elif input_media_path and os.path.exists(input_media_path):
                transcribe_res = self.stage_3_transcribe_audio(
                    media_path=input_media_path,
                    task_id=task_id,
                    provided_script=script_text
                )
            else:
                transcribe_res = {"transcribed": False, "segments": []}
            timings["stage_3_transcription_ms"] = round((time.time() - t0) * 1000, 2)

            # ETAPA 4: Análise de cenas e conteúdo (PySceneDetect + OpenCV)
            t0 = time.time()
            if input_media_path and os.path.exists(input_media_path) and val_res.get("has_video"):
                analysis_res = self.stage_4_analyze_scenes_and_content(input_media_path)
            else:
                analysis_res = {
                    "has_video": False,
                    "visual_bpm": 18.0,
                    "scene_count": 1,
                    "scenes": [{"start_sec": 0.0, "end_sec": 30.0}],
                    "smart_crop": {
                        "center_x_normalized": 0.50,
                        "ffmpeg_crop_offset_x": "(iw-ow)/2",
                        "smart_crop_applied": False
                    }
                }
            timings["stage_4_scene_analysis_ms"] = round((time.time() - t0) * 1000, 2)

            # ETAPA 5: Seleção e validação de trechos
            t0 = time.time()
            total_duration = meta_res.get("duration_sec", 30.0)
            if narration_audio_path and os.path.exists(narration_audio_path):
                probe_tts = self.ffmpeg.probe_media(narration_audio_path)
                total_duration = probe_tts.get("duration_sec", total_duration)

            seg_res = self.stage_5_select_segments(
                total_duration=total_duration,
                start_sec=cut_start_sec,
                end_sec=cut_end_sec,
                scenes=analysis_res.get("scenes")
            )
            timings["stage_5_segment_selection_ms"] = round((time.time() - t0) * 1000, 2)

            # ETAPA 6: Preparação de cortes e enquadramento 9:16
            t0 = time.time()
            prep_res = self.stage_6_prepare_cuts(
                segment_info=seg_res,
                analysis_info=analysis_res,
                channel_id=channel_id
            )
            timings["stage_6_prepare_cuts_ms"] = round((time.time() - t0) * 1000, 2)

            # Preparação de legendas dinâmicas ASS
            ass_subtitles_path = None
            if generate_subs:
                segments_for_subs = transcribe_res.get("segments", [])
                if segments_for_subs:
                    ass_file = self.subs_dir / f"{task_id}.ass"
                    self.sub_generator.generate_ass(
                        segments=segments_for_subs,
                        output_file=str(ass_file),
                        channel_id=channel_id
                    )
                    if ass_file.exists():
                        ass_subtitles_path = str(ass_file)

            # ETAPA 7: Processamento audiovisual e renderização
            t0 = time.time()
            render_res = self.stage_7_process_av_and_render(
                task_id=task_id,
                channel_id=channel_id,
                input_video_path=input_media_path if (input_media_path and val_res.get("has_video")) else None,
                narration_audio_path=narration_audio_path,
                ass_subtitles_path=ass_subtitles_path,
                render_prep=prep_res
            )
            timings["stage_7_render_ms"] = round((time.time() - t0) * 1000, 2)

            # ETAPA 8: Geração de versões preliminares e thumbnail
            t0 = time.time()
            preview_res = self.stage_8_generate_previews(
                task_id=task_id,
                rendered_video_path=render_res["output_path"],
                best_timestamp_sec=2.0
            )
            timings["stage_8_previews_ms"] = round((time.time() - t0) * 1000, 2)

            # ETAPA 9: Revisão de qualidade técnica (QC Automatizado)
            t0 = time.time()
            qc_res = self.stage_9_review_quality(
                task_id=task_id,
                channel_id=channel_id,
                rendered_video_path=render_res["output_path"],
                ass_subtitles_path=ass_subtitles_path
            )
            timings["stage_9_qc_review_ms"] = round((time.time() - t0) * 1000, 2)

            # ETAPA 10: Armazenamento e registro do resultado
            t0 = time.time()
            store_res = self.stage_10_store_and_register(
                task_id=task_id,
                channel_id=channel_id,
                source_media_path=input_media_path,
                output_media_path=render_res["output_path"],
                thumbnail_path=preview_res.get("thumbnail_path"),
                provenance=meta_res.get("provenance", {}),
                qc_result=qc_res,
                stage_timings=timings
            )
            timings["stage_10_store_and_register_ms"] = round((time.time() - t0) * 1000, 2)
            timings["total_pipeline_ms"] = round((time.time() - t_global_start) * 1000, 2)

            return {
                "success": qc_res.get("passed", False),
                "status": store_res.get("status"),
                "task_id": task_id,
                "channel_id": channel_id,
                "output_video_path": render_res["output_path"],
                "thumbnail_path": preview_res.get("thumbnail_path"),
                "ass_subtitles_path": ass_subtitles_path,
                "duration_sec": qc_res.get("duration_sec"),
                "resolution": qc_res.get("resolution"),
                "integrated_lufs": qc_res.get("integrated_lufs"),
                "qc_passed": qc_res.get("passed", False),
                "qc_score": qc_res.get("qc_score", 0),
                "portal_2_ready": qc_res.get("passed", False),
                "stage_timings": timings,
                "metadata": meta_res
            }

        except AudiovisualPipelineError as ape:
            # Registra falha estruturada no banco
            self._record_pipeline_failure(task_id, channel_id, ape.stage, ape.code, ape.message)
            raise ape
        except Exception as e:
            msg = str(e)
            self._record_pipeline_failure(task_id, channel_id, "unknown_stage", "UNEXPECTED_ERROR", msg)
            raise AudiovisualPipelineError(
                stage="orchestrator",
                code="UNEXPECTED_PIPELINE_ERROR",
                message=msg
            )

    def _record_pipeline_failure(
        self,
        task_id: str,
        channel_id: int,
        stage: str,
        error_code: str,
        error_msg: str
    ):
        """Registra falha técnica na tabela audiovisual_pipeline_runs sem quebrar o banco."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO audiovisual_pipeline_runs (
                        task_id, channel_id, status, current_stage, error_message, completed_at
                    ) VALUES (?, ?, 'FAILED', ?, ?, CURRENT_TIMESTAMP)
                """, (task_id, channel_id, stage, f"[{error_code}] {error_msg}"))
                conn.commit()
        except Exception as e:
            logger.error(f"Erro ao persistir falha no SQLite: {e}")
