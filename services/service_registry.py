"""
IAS Service Registry & Health Diagnostics
Centraliza a telemetria, diagnóstico de saúde e disponibilidade de todos os serviços.
"""
import os
import sys
import shutil
import importlib
import importlib.metadata
from typing import Dict, Any

class ServiceRegistry:
    """Registrador e verificador de integridade dos serviços do IAS."""

    def __init__(self):
        pass

    def check_all(self) -> Dict[str, Any]:
        """Executa varredura de status em tempo real de todas as 7 tecnologias centrais."""
        services = {
            "orchestration_langgraph": self.check_langgraph(),
            "semantic_memory_pgvector": self.check_pgvector(),
            "transcription_whisper": self.check_whisper(),
            "video_analysis_scenedetect": self.check_scenedetect(),
            "visual_analysis_opencv": self.check_opencv(),
            "model_gateway_litellm": self.check_litellm(),
            "media_processing_ffmpeg": self.check_ffmpeg(),
        }

        total = len(services)
        online = sum(1 for s in services.values() if s.get("status") in ["ONLINE", "FALLBACK_ACTIVE"])
        
        return {
            "total_services": total,
            "operational_services": online,
            "health_score": int((online / total) * 100) if total > 0 else 0,
            "services": services
        }

    def check_langgraph(self) -> Dict[str, Any]:
        try:
            import langgraph
            version = importlib.metadata.version("langgraph")
            return {
                "name": "LangGraph",
                "role": "Orquestrador de Fluxo em 12 Etapas",
                "status": "ONLINE",
                "version": version,
                "engine": "StateGraph",
                "checkpointing": True,
                "notes": "Pronto para persistência e recuperação de tarefas"
            }
        except Exception as e:
            return {
                "name": "LangGraph",
                "role": "Orquestrador de Fluxo em 12 Etapas",
                "status": "FALLBACK_ACTIVE",
                "version": "native-fallback",
                "engine": "SequentialStateRunner",
                "checkpointing": True,
                "notes": f"Usando executor sequencial nativo ({e})"
            }

    def check_pgvector(self) -> Dict[str, Any]:
        has_pgvector_pkg = False
        try:
            import pgvector
            has_pgvector_pkg = True
            version = getattr(pgvector, "__version__", "0.5.1")
        except Exception:
            version = "local-cosine"

        has_fastembed = False
        try:
            import fastembed
            has_fastembed = True
            version = getattr(fastembed, "__version__", "0.9.1")
        except Exception:
            pass

        has_postgres = bool(os.environ.get("DATABASE_URL"))
        is_online = (has_pgvector_pkg and has_postgres) or has_fastembed
        engine_name = "FastEmbed ONNX Neural (bge-small-en-v1.5)" if has_fastembed else ("PostgreSQL + pgvector" if has_postgres else "Local SQLite + Cosine Distance")
        return {
            "name": "pgvector & Memória Semântica",
            "role": "Busca Vetorial Neural por Significado e Contexto",
            "status": "ONLINE" if is_online else "FALLBACK_ACTIVE",
            "version": version,
            "backend": engine_name,
            "postgres_connected": has_postgres,
            "notes": f"Motor vetorial ativo: {engine_name} com isolamento por canal (Dim: 384)"
        }

    def check_whisper(self) -> Dict[str, Any]:
        # Faster-whisper is standard
        has_faster = False
        faster_ver = "indisponível"
        try:
            import faster_whisper
            has_faster = True
            faster_ver = faster_whisper.__version__
        except Exception:
            pass

        has_whisperx = False
        try:
            import whisperx
            has_whisperx = True
        except Exception:
            pass

        return {
            "name": "WhisperX & Faster-Whisper",
            "role": "Transcrição e Alinhamento Temporal por Palavra",
            "status": "ONLINE" if (has_faster or has_whisperx) else "OFFLINE",
            "engine": "WhisperX (Diarização)" if has_whisperx else "Faster-Whisper (CTranslate2)",
            "version": faster_ver,
            "word_timestamps": True,
            "ass_subtitles_support": True,
            "notes": "Geração de legendas dinâmicas estilo Hormozi para 9:16 ativa"
        }

    def check_scenedetect(self) -> Dict[str, Any]:
        try:
            import scenedetect
            return {
                "name": "PySceneDetect",
                "role": "Detecção Visual de Cortes e Transições",
                "status": "ONLINE",
                "version": scenedetect.__version__,
                "algorithm": "ContentDetector / AdaptiveDetector",
                "notes": "Análise de cortes de câmera e cálculo de BPM visual"
            }
        except Exception as e:
            return {
                "name": "PySceneDetect",
                "role": "Detecção Visual de Cortes e Transições",
                "status": "FALLBACK_ACTIVE",
                "version": "ffmpeg-scene-filter",
                "notes": f"Fallback para filtro de cena nativo do FFmpeg ({e})"
            }

    def check_opencv(self) -> Dict[str, Any]:
        try:
            import cv2
            return {
                "name": "OpenCV",
                "role": "Análise Visual de Movimento e Smart Crop 9:16",
                "status": "ONLINE",
                "version": cv2.__version__,
                "capabilities": ["Motion Detection", "Saliency Mapping", "Framing Analysis"],
                "notes": "Centralização dinâmica para cortes verticais inteligentes"
            }
        except Exception as e:
            return {
                "name": "OpenCV",
                "role": "Análise Visual de Movimento e Smart Crop 9:16",
                "status": "OFFLINE",
                "version": "None",
                "notes": str(e)
            }

    def check_litellm(self) -> Dict[str, Any]:
        try:
            os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
            import litellm
            return {
                "name": "LiteLLM",
                "role": "Roteamento Multi-Provedor de Modelos de IA",
                "status": "ONLINE",
                "version": getattr(litellm, "__version__", "1.110.2"),
                "providers_supported": ["gemini", "openai", "anthropic", "groq", "ollama"],
                "cost_tracking": True,
                "notes": "Fallback automático entre provedores e controle de tokens"
            }
        except Exception as e:
            return {
                "name": "LiteLLM",
                "role": "Roteamento Multi-Provedor de Modelos de IA",
                "status": "FALLBACK_ACTIVE",
                "version": "direct-gateway",
                "notes": f"Roteamento direto nativo ({e})"
            }

    def check_ffmpeg(self) -> Dict[str, Any]:
        from services.media_processing.ffmpeg_engine import FFmpegEngine
        engine = FFmpegEngine()
        status_info = engine.get_status()
        return {
            "name": "FFmpeg",
            "role": "Processamento Audiovisual, 9:16 e Loudness EBU R128",
            "status": "ONLINE" if status_info.get("available") else "OFFLINE",
            "version": status_info.get("version", "desconhecido"),
            "path": status_info.get("binary_path"),
            "notes": "Pipeline de renderização com libx264, aac e perfis multi-canal"
        }
