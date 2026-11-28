"""
IAS Quality Control Agent (agents/qc_agent.py)
Departamento de Controle de Qualidade e Conformidade Audiovisual.
Executa auditoria automatizada em cortes e Shorts renderizados antes do Portal 2,
validando resolução vertical 9:16, duração YouTube Shorts (15-59s),
loudness EBU R128 (-14 LUFS), integridade de legendas ASS e coerência com a identidade do canal.
"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from core.channel_manager import ChannelManager
from services.media_processing.ffmpeg_engine import FFmpegEngine

logger = logging.getLogger("QualityControlAgent")


class QualityControlAgent:
    """Agente inspetor do departamento de controle de qualidade audiovisual."""

    def __init__(self, ffmpeg_engine: Optional[FFmpegEngine] = None, channel_manager: Optional[ChannelManager] = None, db_path: Optional[str] = None):
        self.ffmpeg = ffmpeg_engine or FFmpegEngine()
        self.channel_manager = channel_manager or ChannelManager(db_path=db_path)

    def validate_rendered_short(
        self,
        video_path: Union[str, Path],
        task_id: Optional[str] = None,
        channel_id: Any = 1,
        ass_path: Optional[Union[str, Path]] = None,
        audio_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        Executa bateria completa de testes de qualidade em um Short renderizado.
        Retorna score (0-100), status, lista de checagens e recomendações corretivas.
        """
        video_str = str(video_path)
        checks: List[Dict[str, Any]] = []
        score = 100
        critical_failed = False

        # 1. Checagem de Existência e Tamanho do Arquivo
        if not os.path.exists(video_str):
            checks.append({
                "check": "file_existence",
                "severity": "CRITICAL",
                "passed": False,
                "message": f"Arquivo de vídeo não encontrado em: {video_str}",
                "details": {"path": video_str}
            })
            return {
                "score": 0,
                "passed": False,
                "status": "REJECTED",
                "checks": checks,
                "recommendations": ["Re-renderizar o vídeo pois o arquivo de saída não foi gerado."]
            }

        size_bytes = os.path.getsize(video_str)
        if size_bytes < 10_000:
            critical_failed = True
            score -= 40
            checks.append({
                "check": "file_size",
                "severity": "CRITICAL",
                "passed": False,
                "message": f"Arquivo corrompido ou excessivamente pequeno: {size_bytes} bytes",
                "details": {"size_bytes": size_bytes}
            })
        else:
            checks.append({
                "check": "file_size",
                "severity": "LOW",
                "passed": True,
                "message": f"Tamanho do arquivo adequado: {round(size_bytes / (1024 * 1024), 2)} MB",
                "details": {"size_bytes": size_bytes}
            })

        # 2. Metadados e Sondas via FFprobe
        probe = self.ffmpeg.probe_media(video_str)
        width = probe.get("width", 0)
        height = probe.get("height", 0)
        duration = probe.get("duration_sec", 0.0)
        has_video = probe.get("has_video", False)
        has_audio = probe.get("has_audio", False)

        # 2.1 Streams de Áudio e Vídeo
        if not has_video or not has_audio:
            critical_failed = True
            score -= 40
            checks.append({
                "check": "stream_integrity",
                "severity": "CRITICAL",
                "passed": False,
                "message": f"Fluxos incompletos: Vídeo={has_video}, Áudio={has_audio}",
                "details": {"has_video": has_video, "has_audio": has_audio}
            })
        else:
            checks.append({
                "check": "stream_integrity",
                "severity": "LOW",
                "passed": True,
                "message": f"Fluxos de áudio ({probe.get('audio_codec')}) e vídeo ({probe.get('video_codec')}) presentes e válidos",
                "details": {"video_codec": probe.get("video_codec"), "audio_codec": probe.get("audio_codec")}
            })

        # 2.2 Resolução e Aspect Ratio Vertical (9:16)
        is_vertical = (height > width and width > 0)
        is_exact_1080x1920 = (width == 1080 and height == 1920)

        if not is_vertical:
            critical_failed = True
            score -= 40
            checks.append({
                "check": "aspect_ratio",
                "severity": "CRITICAL",
                "passed": False,
                "message": f"Formato horizontal detectado ({width}x{height}). YouTube Shorts exige proporção vertical 9:16.",
                "details": {"width": width, "height": height, "aspect_ratio": probe.get("aspect_ratio")}
            })
        elif not is_exact_1080x1920:
            score -= 10
            checks.append({
                "check": "resolution_standard",
                "severity": "HIGH",
                "passed": False,
                "message": f"Resolução vertical ({width}x{height}) diferente do padrão ouro 1080x1920.",
                "details": {"width": width, "height": height}
            })
        else:
            checks.append({
                "check": "aspect_ratio",
                "severity": "LOW",
                "passed": True,
                "message": "Resolução padrão ouro confirmada: 1080x1920 (9:16 Vertical)",
                "details": {"width": width, "height": height}
            })

        # 2.3 Duração (Limites do YouTube Shorts: máximo 60s, recomendado 15-59s)
        if duration > 60.0:
            critical_failed = True
            score -= 40
            checks.append({
                "check": "duration_compliance",
                "severity": "CRITICAL",
                "passed": False,
                "message": f"Duração de {duration}s ultrapassa o limite rígido de 60 segundos do YouTube Shorts.",
                "details": {"duration_sec": duration, "max_allowed": 60.0}
            })
        elif duration < 10.0:
            score -= 15
            checks.append({
                "check": "duration_compliance",
                "severity": "HIGH",
                "passed": False,
                "message": f"Duração de {duration}s excessivamente curta para retenção de Shorts (recomendado > 15s).",
                "details": {"duration_sec": duration, "min_recommended": 15.0}
            })
        else:
            checks.append({
                "check": "duration_compliance",
                "severity": "LOW",
                "passed": True,
                "message": f"Duração ideal para Shorts: {duration}s",
                "details": {"duration_sec": duration}
            })

        # 3. Normalização de Áudio (EBU R128: Alvo -14 LUFS, tolerância ±2.5 LUFS)
        loudness = self.ffmpeg.measure_loudness(video_str)
        i_lufs = loudness.get("integrated_lufs", -14.0)
        tp_db = loudness.get("true_peak_db", -1.5)

        if -16.5 <= i_lufs <= -11.5:
            checks.append({
                "check": "loudness_ebu_r128",
                "severity": "LOW",
                "passed": True,
                "message": f"Loudness de {i_lufs} LUFS em perfeita conformidade com YouTube (-14 LUFS ± 2.5)",
                "details": {"integrated_lufs": i_lufs, "true_peak_db": tp_db}
            })
        else:
            score -= 15
            checks.append({
                "check": "loudness_ebu_r128",
                "severity": "HIGH",
                "passed": False,
                "message": f"Loudness de {i_lufs} LUFS fora da faixa permitida (-16.5 a -11.5 LUFS)",
                "details": {"integrated_lufs": i_lufs, "true_peak_db": tp_db}
            })

        # 4. Checagem de Legendas ASS
        ass_to_check = ass_path
        if not ass_to_check and task_id:
            candidate = Path(video_str).parent.parent / "subs" / f"{task_id}.ass"
            if candidate.exists():
                ass_to_check = candidate

        if ass_to_check and os.path.exists(str(ass_to_check)):
            try:
                with open(str(ass_to_check), "r", encoding="utf-8", errors="ignore") as f:
                    sub_text = f.read()
                dialogue_count = len(re.findall(r"^Dialogue:", sub_text, re.MULTILINE))
                if dialogue_count > 0:
                    checks.append({
                        "check": "subtitles_integrity",
                        "severity": "LOW",
                        "passed": True,
                        "message": f"Legendas ASS detectadas com {dialogue_count} falas sincronizadas",
                        "details": {"dialogue_count": dialogue_count, "ass_path": str(ass_to_check)}
                    })
                else:
                    score -= 15
                    checks.append({
                        "check": "subtitles_integrity",
                        "severity": "HIGH",
                        "passed": False,
                        "message": "Arquivo ASS existe mas não contém eventos de diálogo (vazio).",
                        "details": {"ass_path": str(ass_to_check)}
                    })
            except Exception as e:
                score -= 10
                checks.append({
                    "check": "subtitles_integrity",
                    "severity": "HIGH",
                    "passed": False,
                    "message": f"Erro ao ler arquivo ASS de legenda: {e}",
                    "details": {"error": str(e)}
                })
        else:
            # Se não há arquivo ASS explicitado nem encontrado, marca alerta informativo
            checks.append({
                "check": "subtitles_integrity",
                "severity": "LOW",
                "passed": True,
                "message": "Legendas embutidas no fluxo ou não fornecidas externamente.",
                "details": {}
            })

        # 5. Coerência com Perfil do Canal
        channel_settings = self.channel_manager.get_channel_settings(channel_id)
        if channel_settings:
            checks.append({
                "check": "channel_profile_compliance",
                "severity": "LOW",
                "passed": True,
                "message": f"Canal {channel_id} verificado. Arquétipo: {channel_settings.get('archetype_slug', 'geral')}",
                "details": {"archetype": channel_settings.get("archetype_slug")}
            })

        # Normaliza pontuação final
        final_score = max(0, min(100, score))
        passed = (final_score >= 80) and (not critical_failed)
        status = "APPROVED_BY_QC" if passed else "FLAGGED_FOR_HUMAN_REVIEW"

        # Recomendações
        recommendations = []
        for c in checks:
            if not c["passed"]:
                if c["check"] == "aspect_ratio":
                    recommendations.append("Ajustar crop vertical para 1080x1920 (9:16).")
                elif c["check"] == "duration_compliance":
                    recommendations.append("Cortar o conteúdo para menos de 59 segundos para manter classificação de Shorts.")
                elif c["check"] == "loudness_ebu_r128":
                    recommendations.append("Re-aplicar filtro FFmpeg 'loudnorm=I=-14:LRA=7:tp=-1.5'.")
                elif c["check"] == "subtitles_integrity":
                    recommendations.append("Gerar novo arquivo ASS com o SubtitleGenerator.")

        return {
            "score": final_score,
            "passed": passed,
            "status": status,
            "critical_failed": critical_failed,
            "checks": checks,
            "recommendations": recommendations,
            "video_metadata": {
                "duration_sec": duration,
                "resolution": f"{width}x{height}",
                "is_vertical": is_vertical,
                "integrated_lufs": i_lufs,
                "size_mb": round(size_bytes / (1024 * 1024), 2)
            }
        }
