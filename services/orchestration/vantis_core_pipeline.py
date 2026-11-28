"""
VANTIS — Pipeline Operacional Integrado End-to-End (Fase 20)
Conecta os módulos existentes (Descoberta/Importação, Deduplicação, Download/Cache,
Integridade FFmpeg/SHA256, Áudio EBU R128, Whisper, PySceneDetect/OpenCV,
Extrator de 15 Recursos, Memória Evolutiva e Recomendações por Canal) em uma
máquina de estados explícita sem dados simulados nem sucesso falso.
"""

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.learning.editorial_feature_extractor import EditorialFeatureExtractor, NOT_AVAILABLE
from services.learning.editorial_memory_engine import EditorialMemoryEngine
from services.media_processing.media_downloader import MediaDownloader
from services.model_gateway.gateway import ModelGatewayService
from services.orchestration.central_controller import CentralOperationsController
from services.transcription.whisper_service import WhisperTranscriptionService
from services.video_analysis.scene_detector import SceneDetectorService
from services.video_analysis.visual_analyzer import OpenCVVisualAnalyzer

PIPELINE_STATES = (
    "QUEUED",
    "DOWNLOADING",
    "DOWNLOAD_FAILED",
    "MEDIA_VERIFIED",
    "AUDIO_PROCESSING",
    "TRANSCRIBING",
    "VISUAL_ANALYSIS",
    "EDITORIAL_ANALYSIS",
    "LEARNING_CANDIDATE",
    "EDITORIAL_REJECTED",
    "COMPLETED",
    "RETRY_PENDING",
    "FAILED",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _probe_and_decode(file_path: str) -> Dict[str, Any]:
    probe_cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
    try:
        p_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=False, timeout=20)
        if p_res.returncode != 0 or not p_res.stdout.strip():
            return {"ok": False, "error": "ffprobe_failed"}
        data = json.loads(p_res.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        v_s = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_s = next((s for s in streams if s.get("codec_type") == "audio"), None)
        dec_cmd = ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"]
        d_res = subprocess.run(dec_cmd, capture_output=True, text=True, check=False, timeout=45)
        return {
            "ok": d_res.returncode == 0,
            "error": None if d_res.returncode == 0 else "ffmpeg_decode_failed",
            "duration": float(fmt.get("duration") or 0.0),
            "size_bytes": int(fmt.get("size") or 0),
            "streams_count": len(streams),
            "video_codec": v_s.get("codec_name") if v_s else None,
            "width": int(v_s.get("width") or 0) if v_s else 0,
            "height": int(v_s.get("height") or 0) if v_s else 0,
            "audio_codec": a_s.get("codec_name") if a_s else None,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "ffprobe_or_ffmpeg_timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class VantisCorePipeline:
    """Orquestrador End-to-End real conectando todos os módulos do núcleo do VANTIS."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        downloads_dir: Optional[Path] = None,
        whisper_model: str = "tiny",
    ):
        self.als = AudiovisualLearningSystem(db_path=db_path)
        self.db_path = Path(self.als.db_path)
        self.downloads_dir = Path(downloads_dir) if downloads_dir else (BASE_DIR / "workspace" / "downloads")
        self.ctrl = CentralOperationsController(db_path=str(self.db_path))
        self.downloader = MediaDownloader(download_dir=self.downloads_dir)
        self.scene_detector = SceneDetectorService()
        self.visual_analyzer = OpenCVVisualAnalyzer()
        self.whisper_svc = WhisperTranscriptionService(model_size=whisper_model)
        self.extractor = EditorialFeatureExtractor()
        self.memory_engine = EditorialMemoryEngine(db_path=self.db_path)
        self.gateway = ModelGatewayService(enforce_free_tier=True)

    def generate_recommendations_from_memory(
        self,
        channel_id: int,
        features: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Gera recomendações editoriais rastreáveis usando a memória persistente do canal."""
        mem = self.als.get_channel_editorial_memory(channel_id)
        items = mem.get("knowledge_items", [])
        recs: List[Dict[str, Any]] = []

        for item in items:
            cls = item.get("classification")
            if cls not in ("APRENDIZADO_VALIDADO", "ANTI_PATTERN", "HIPÓTESE"):
                continue
            ktype = item.get("knowledge_type") or ""
            meta = item.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except json.JSONDecodeError:
                    meta = {}
            ev_count = int(item.get("evidence_count") or len(item.get("evidence_video_ids") or []))
            cnt_count = len(meta.get("counterexamples") or [])

            applies_msg = None
            if cls == "ANTI_PATTERN" and features.get("audio_visual_relation") == "silent_or_unusable_audio":
                applies_msg = f"ALERTA ANTI-PATTERN (ID {item['id']}): Faixa silenciosa ou inutilizável detectada."
            elif ktype == "ritmo_de_cortes_dinamico" and cls == "APRENDIZADO_VALIDADO":
                cuts = features.get("cuts_count")
                if cuts != NOT_AVAILABLE and int(cuts) < 4:
                    applies_msg = f"Aumentar cortes dinâmicos (>=4; atual={cuts}) conforme regra validada ID {item['id']}."
                elif cuts != NOT_AVAILABLE:
                    applies_msg = f"Ritmo de cortes ({cuts}) alinhado à regra validada ID {item['id']}."
            elif ktype == "estrutura_narrativa_real" and cls == "APRENDIZADO_VALIDADO":
                if features.get("has_narration") is False:
                    applies_msg = f"Adicionar narração falada estruturada conforme regra validada ID {item['id']}."
                elif features.get("has_narration") is True:
                    applies_msg = f"Narração presente, alinhada à regra validada ID {item['id']}."
            elif ktype == "gancho_inicial_forte" and cls == "APRENDIZADO_VALIDADO":
                if features.get("hook_type") not in ("question", "curiosity_or_fact", "direct_command"):
                    applies_msg = f"Reforçar gancho inicial (pergunta/curiosidade) conforme regra validada ID {item['id']}."
            elif ktype == "progressao_narrativa_completa" and cls == "APRENDIZADO_VALIDADO":
                if features.get("narrative_progression") != "complete_3_acts":
                    applies_msg = f"Completar progressão em 3 atos (abertura, desenvolvimento, conclusão) conforme ID {item['id']}."

            if applies_msg:
                recs.append({
                    "knowledge_id": item["id"],
                    "channel_id": channel_id,
                    "classification": cls,
                    "knowledge_type": ktype,
                    "recommendation": applies_msg,
                    "evidence_count": ev_count,
                    "counterexamples_count": cnt_count,
                })

        if not recs:
            recs.append({
                "knowledge_id": None,
                "channel_id": channel_id,
                "classification": "HIPÓTESE",
                "knowledge_type": "baseline_observacional",
                "recommendation": f"Canal {channel_id} sem regra validada acionada; manter monitoramento em hipótese.",
                "evidence_count": 0,
                "counterexamples_count": 0,
            })
        return recs

    def process_video_end_to_end(
        self,
        video_spec: Dict[str, Any],
        local_file_override: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Executa o fluxo completo de 16 etapas para um vídeo real com máquina de estados."""
        t0 = time.time()
        v_id = str(video_spec["id"])
        ch_id = int(video_spec.get("channel_id") or 1)
        niche = video_spec.get("niche") or "outros"
        title = video_spec.get("title") or v_id
        url = video_spec.get("url") or f"https://www.youtube.com/shorts/{v_id}"
        task_id = f"e2e_core_{v_id}_{int(t0)}"

        steps_executed: List[str] = []
        state = "QUEUED"
        self.ctrl.submit_task(task_id, "E2E_CORE_PIPELINE", {"source_id": v_id, "channel_id": ch_id}, channel_id=ch_id)
        self.ctrl.claim_next_task(worker_agent="vantis_core_pipeline", channel_id=ch_id)

        # 1-4. Origem / Download ou Arquivo Local Real
        state = "DOWNLOADING"
        local_path: Optional[Path] = Path(local_file_override) if local_file_override else None
        if not local_path or not local_path.is_file():
            dl = self.downloader.download_short(url, output_dir=self.downloads_dir / f"ch_{ch_id}")
            if not dl.get("success"):
                state = "DOWNLOAD_FAILED"
                err = dl.get("error") or "download_failed"
                self.ctrl.fail_task_with_retry(task_id, err, permanent=True)
                return {"video_id": v_id, "final_state": state, "steps_executed": steps_executed, "error": err}
            local_path = Path(dl["file_path"])
        steps_executed.append("media_acquired")

        # 5. Verificação de integridade física (SHA256 + FFprobe + FFmpeg decode)
        sha256 = _sha256_file(local_path)
        file_size = local_path.stat().st_size
        probe = _probe_and_decode(str(local_path))
        if not probe.get("ok") or file_size <= 0 or probe.get("duration", 0.0) <= 0.0:
            state = "FAILED"
            err = probe.get("error") or "integrity_check_failed"
            self.ctrl.fail_task_with_retry(task_id, err, permanent=True)
            return {"video_id": v_id, "final_state": state, "steps_executed": steps_executed, "error": err}

        state = "MEDIA_VERIFIED"
        verified_dur = float(probe["duration"])
        steps_executed.append("integrity_verified")

        # Registro de descoberta / metadados reais (idempotente)
        self.als.discover_video(
            source_id=v_id,
            original_url=url,
            title=title,
            creator=video_spec.get("creator") or "Desconhecido",
            duration_seconds=verified_dur,
            niche=niche,
            views_count=int(video_spec.get("views") or 0),
            likes_count=int(video_spec.get("likes") or 0),
            comment_count=int(video_spec.get("comments") or 0),
            target_channel_id=ch_id,
            pilot_phase=20,
            metadata_payload={"sha256": sha256, "local_path": str(local_path), "target_channel_id": ch_id},
        )
        self.als.register_physical_media(
            source_id=v_id,
            local_path=str(local_path),
            file_size_bytes=file_size,
            sha256_hash=sha256,
            verified_duration=verified_dur,
            video_codec=probe.get("video_codec"),
            audio_codec=probe.get("audio_codec"),
            streams_count=probe.get("streams_count"),
            ffmpeg_decode_ok=True,
        )
        self.als._set_state(v_id, "downloaded")
        steps_executed.append("metadata_registered")

        # 6. Extração e análise de áudio (FFmpeg EBU R128)
        state = "AUDIO_PROCESSING"
        audio_metrics = self.als._analyze_audio_file(str(local_path))
        self.als.process_audio(
            source_id=v_id,
            speech_clarity_score=audio_metrics["speech_clarity_score"],
            estimated_lufs=float(audio_metrics["integrated_lufs"]),
            pauses_ratio=audio_metrics["pauses_ratio"],
            audio_classification=audio_metrics["classification"],
            is_usable=audio_metrics["is_usable"],
            diagnostic_message=audio_metrics["diagnostic_message"],
            clipping_detected=audio_metrics.get("clipping_detected", False),
            true_peak_db=audio_metrics.get("true_peak_db"),
            lra=audio_metrics.get("lra"),
        )
        steps_executed.append("audio_analyzed")

        # 7. Transcrição real (Faster-Whisper CPU)
        state = "TRANSCRIBING"
        transcript_text = ""
        trans_engine = "none"
        if audio_metrics["is_usable"]:
            w_res = self.whisper_svc.transcribe_audio(str(local_path), language="pt")
            transcript_text = (w_res.get("full_transcript") or "").strip()
            trans_engine = f"faster_whisper_{self.whisper_svc.model_size}"
        narr_res = self.als.process_transcript(
            v_id, transcript_text, allow_insufficient_speech=True, transcription_engine=trans_engine
        )
        steps_executed.append("transcribed")

        # 8-9. Análise visual (OpenCV) e detecção de cenas/cortes (PySceneDetect)
        state = "VISUAL_ANALYSIS"
        scenes_res = self.scene_detector.detect_scenes(str(local_path))
        cuts_count = max(0, int(scenes_res.get("total_scenes", 1)) - 1)
        motion_info = self.visual_analyzer.analyze_framing_and_motion(str(local_path))
        w, h = probe.get("width") or 0, probe.get("height") or 0
        self.als.process_visual(
            source_id=v_id,
            cuts_count=cuts_count,
            aspect_ratio=f"{w}:{h}" if w and h else "unknown",
            has_subtitles_on_screen=bool(motion_info.get("text_on_screen_detected", False)),
            framing_changes=int(motion_info.get("framing_changes_detected", 0)),
            broll_presence_ratio=0.0,
            dominant_composition="standard",
            cut_intervals_sec=scenes_res.get("cut_intervals_sec", []),
            avg_cut_interval_sec=scenes_res.get("avg_cut_interval_sec", verified_dur),
            representative_frames=motion_info.get("representative_frames", []),
            average_motion_score=motion_info.get("average_motion_score"),
            opencv_frames_read_ok=bool(motion_info.get("opencv_frames_read_ok", False)),
        )
        self.als._set_state(v_id, "technical_analysis_complete")
        steps_executed.append("visual_and_scenes_analyzed")

        # 10-12. Análise editorial, classificação e extração dos 15 recursos reais
        state = "EDITORIAL_ANALYSIS"
        ed_res = self.als.evaluate_editorial_adherence(source_id=v_id, target_channel_id=ch_id)
        if ed_res["processing_state"] == "editorially_rejected":
            state = "EDITORIAL_REJECTED"
        else:
            self.als.promote_to_learning_candidate(v_id)
            state = "LEARNING_CANDIDATE"
        steps_executed.append("editorial_classified")

        with self.als._get_conn() as conn:
            row = conn.execute(
                "SELECT source_id, title, duration_seconds, views_count, likes_count, comment_count, engagement_ratio, processing_state, analysis_payload FROM audiovisual_library WHERE source_id = ?",
                (v_id,),
            ).fetchone()
            vid_dict = {
                "source_id": row[0], "title": row[1], "duration_seconds": row[2],
                "views_count": row[3], "likes_count": row[4], "comment_count": row[5],
                "engagement_ratio": row[6], "processing_state": row[7], "analysis_payload": row[8],
                "channel_id": ch_id,
            }
            features = self.extractor.extract(vid_dict)
            steps_executed.append("features_extracted")

            # 13-15. Recomendações usando memória persistente do canal + persistência
            recommendations = self.generate_recommendations_from_memory(ch_id, features)
            pay = json.loads(row[8] or "{}")
            pay["editorial_features"] = features
            pay["editorial_recommendations"] = recommendations
            conn.execute(
                "UPDATE audiovisual_library SET analysis_payload = ? WHERE source_id = ?",
                (json.dumps(pay, ensure_ascii=False), v_id),
            )
            conn.commit()
        steps_executed.append("recommendations_persisted")

        self.ctrl.complete_task(task_id, {"final_state": "COMPLETED", "db_state": ed_res["processing_state"]})
        steps_executed.append("completed")
        return {
            "video_id": v_id,
            "channel_id": ch_id,
            "origin": str(local_path),
            "initial_state": "QUEUED",
            "db_processing_state": ed_res["processing_state"],
            "final_state": "COMPLETED",
            "steps_executed": steps_executed,
            "duration_seconds": round(verified_dur, 2),
            "elapsed_seconds": round(time.time() - t0, 2),
            "sha256": sha256,
            "integrated_lufs": audio_metrics["integrated_lufs"],
            "cuts_count": cuts_count,
            "transcript_word_count": narr_res.get("metrics", {}).get("word_count", 0),
            "transcript_preview": transcript_text[:120],
            "editorial_features": features,
            "editorial_recommendations": recommendations,
            "errors": [],
        }
