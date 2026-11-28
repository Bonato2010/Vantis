"""
VANTIS — Engine de Execução do Benchmark Controlado de 250 Vídeos (Fase 18)
Auditoria Física Multimodal | Extração de Características | Trava Custo Zero ($0.00) | Checkpointing + Task Queue
"""

import ctypes
import ctypes.wintypes
import hashlib
import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.learning.editorial_feature_extractor import EditorialFeatureExtractor
from services.media_processing.ffmpeg_engine import FFmpegEngine
from services.media_processing.media_downloader import MediaDownloader
from services.model_gateway.gateway import ModelGatewayService
from services.orchestration.central_controller import CentralOperationsController
from services.transcription.whisper_service import WhisperTranscriptionService
from services.video_analysis.scene_detector import SceneDetectorService
from services.video_analysis.visual_analyzer import OpenCVVisualAnalyzer

MANIFEST_JSON = BASE_DIR / "docs" / "audits" / "phase18_selected_candidates.json"
EXECUTION_DATA_JSON = BASE_DIR / "docs" / "audits" / "phase18_benchmark_execution_data.json"
DOWNLOADS_ROOT = BASE_DIR / "workspace" / "downloads" / "benchmark250"
BATCH_ID = "benchmark_250_fase18"


class CircuitBreakerException(Exception):
    """Exceção levantada quando um critério de proteção do sistema é violado."""


def get_process_memory_mb() -> float:
    """Mede RSS real do processo no Windows via ctypes (zero dependência externa)."""
    try:
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.wintypes.DWORD),
                ("PageFaultCount", ctypes.wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.kernel32.K32GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return round(counters.WorkingSetSize / (1024 * 1024), 2)
    except Exception:
        pass
    return 0.0


def fetch_subtitles_for_short(youtube_url: str, video_id: str, local_video_path: Optional[str] = None) -> str:
    """Extrai legendas locais (.vtt/.srt) sem fallback sintético."""
    if local_video_path:
        for sub_file in Path(local_video_path).parent.glob(f"{video_id}.*"):
            if sub_file.suffix.lower() in [".vtt", ".srt"]:
                try:
                    content = sub_file.read_text(encoding="utf-8", errors="ignore")
                    lines = [
                        l.strip()
                        for l in content.split("\n")
                        if l.strip() and not l.startswith("WEBVTT") and "-->" not in l and not l.isdigit()
                    ]
                    if lines:
                        return " ".join(lines[:60])
                except Exception:
                    pass
    return ""


def compute_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_video_file(file_path: str) -> Dict[str, Any]:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=20)
    if res.returncode != 0 or not res.stdout.strip():
        return {"ok": False, "error": "ffprobe_failed"}
    try:
        data = json.loads(res.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        return {
            "ok": True,
            "duration": float(fmt.get("duration") or 0.0),
            "size_bytes": int(fmt.get("size") or 0),
            "streams_count": len(streams),
            "video_codec": v_stream.get("codec_name") if v_stream else None,
            "width": int(v_stream.get("width") or 0) if v_stream else 0,
            "height": int(v_stream.get("height") or 0) if v_stream else 0,
            "audio_codec": a_stream.get("codec_name") if a_stream else None,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def verify_ffmpeg_decode(file_path: str) -> bool:
    cmd = ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=45)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def init_checkpoint(conn: sqlite3.Connection, total_target: int):
    conn.execute(
        """
        INSERT INTO learning_batch_checkpoints (
            batch_id, target_goal, processed_count, success_count, rejected_count,
            error_count, status, updated_at
        ) VALUES (?, ?, 0, 0, 0, 0, 'RUNNING', CURRENT_TIMESTAMP)
        ON CONFLICT(batch_id) DO UPDATE SET status='RUNNING', updated_at=CURRENT_TIMESTAMP
        """,
        (BATCH_ID, total_target),
    )
    conn.commit()


def update_checkpoint(
    conn: sqlite3.Connection,
    processed: int,
    success: int,
    rejected: int,
    consec_err: int,
    last_vid: str,
    status: str = "RUNNING",
):
    conn.execute(
        """
        UPDATE learning_batch_checkpoints
        SET processed_count = ?, success_count = ?, rejected_count = ?,
            error_count = ?, last_processed_source_id = ?,
            status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE batch_id = ?
        """,
        (processed, success, rejected, consec_err, last_vid, status, BATCH_ID),
    )
    conn.commit()


def run_benchmark_250(limit: Optional[int] = None):
    if not MANIFEST_JSON.exists():
        raise FileNotFoundError(f"Manifesto não encontrado: {MANIFEST_JSON}")

    with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    candidates: List[Dict[str, Any]] = manifest.get("candidates", [])
    if limit is not None:
        candidates = candidates[:limit]

    print(f"=== FASE 18: INICIANDO BENCHMARK DE {len(candidates)} VÍDEOS ===", flush=True)
    start_wall = time.time()
    start_cpu = time.process_time()

    learning_sys = AudiovisualLearningSystem(target_goal=7000)
    ctrl = CentralOperationsController(db_path=str(learning_sys.db_path))
    downloader = MediaDownloader()
    scene_detector = SceneDetectorService()
    visual_analyzer = OpenCVVisualAnalyzer()
    whisper_svc = WhisperTranscriptionService(model_size="tiny")
    feature_extractor = EditorialFeatureExtractor()
    model_gateway = ModelGatewayService(enforce_free_tier=True)

    with learning_sys._get_conn() as conn:
        init_checkpoint(conn, len(candidates))

    processed_records: List[Dict[str, Any]] = []
    if EXECUTION_DATA_JSON.exists():
        try:
            with open(EXECUTION_DATA_JSON, "r", encoding="utf-8") as f:
                prev_data = json.load(f)
                processed_records = prev_data.get("records", [])
        except Exception:
            processed_records = []

    already_done_ids = {r["video_id"] for r in processed_records}
    seen_hashes = {r["sha256"] for r in processed_records if r.get("sha256")}
    resumed_count = len(already_done_ids)

    processed_count = len(processed_records)
    success_count = sum(1 for r in processed_records if r.get("state") == "learning_candidate")
    rejected_count = sum(1 for r in processed_records if r.get("state") == "editorially_rejected")
    failed_count = sum(1 for r in processed_records if r.get("state") == "failed")
    corrupted_count = 0
    silent_audio_count = sum(1 for r in processed_records if r.get("acoustic_classification") == "SILENT_AUDIO_TRACK")
    duplicates_skipped = 0
    consecutive_dl_errors = 0
    ram_samples: List[float] = []

    for idx, cand in enumerate(candidates, 1):
        v_id = str(cand["id"])
        if v_id in already_done_ids:
            continue

        ch_id = int(cand["channel_id"])
        ch_name = cand["channel_name"]
        niche = cand["niche"]
        url = cand["url"]
        title = cand["title"]
        task_id = f"fase18_vid_{v_id}"

        ctrl.submit_task(task_id, "BENCHMARK_250_ANALYZE", {"source_id": v_id, "channel_id": ch_id}, channel_id=ch_id)
        ctrl.claim_next_task(worker_agent="benchmark_250_worker", channel_id=ch_id)

        ch_dir = DOWNLOADS_ROOT / f"ch_{ch_id}"
        ch_dir.mkdir(parents=True, exist_ok=True)
        local_video_path: Optional[str] = None
        for ext in [".mp4", ".webm", ".mkv"]:
            p = ch_dir / f"{v_id}{ext}"
            if p.exists() and p.stat().st_size > 1000:
                local_video_path = str(p)
                break

        if not local_video_path:
            time.sleep(random.uniform(0.6, 1.4))
            dl_res = downloader.download_short(url, output_dir=ch_dir)
            if not dl_res.get("success"):
                consecutive_dl_errors += 1
                failed_count += 1
                err_msg = dl_res.get("error") or "download_failed"
                ctrl.fail_task_with_retry(task_id, err_msg, permanent=True)
                learning_sys.discover_video(
                    source_id=v_id, original_url=url, title=title, niche=niche,
                    duration_seconds=float(cand.get("duration_seconds") or 0.0),
                    views_count=int(cand.get("views") or 0),
                    likes_count=int(cand.get("likes") or 0),
                    comment_count=int(cand.get("comments") or 0),
                    target_channel_id=ch_id, pilot_phase=18,
                )
                learning_sys._set_state(v_id, "failed", error_msg=err_msg)
                processed_records.append({
                    "channel_id": ch_id, "channel_name": ch_name, "niche": niche,
                    "video_id": v_id, "url": url, "title": title,
                    "state": "failed", "error_message": err_msg,
                })
                processed_count += 1
                if consecutive_dl_errors >= 12:
                    raise CircuitBreakerException("Muitas falhas consecutivas de download (>=12).")
                continue
            local_video_path = dl_res["file_path"]
            consecutive_dl_errors = 0

        file_size = os.path.getsize(local_video_path)
        sha256 = compute_sha256(local_video_path)
        if sha256 in seen_hashes:
            duplicates_skipped += 1
            ctrl.complete_task(task_id, {"skipped": "duplicate_sha256"})
            continue
        seen_hashes.add(sha256)

        probe = probe_video_file(local_video_path)
        decode_ok = verify_ffmpeg_decode(local_video_path) if probe.get("ok") else False
        verified_dur = float(probe.get("duration") or cand.get("duration_seconds") or 0.0)

        if not probe.get("ok") or not decode_ok or file_size <= 0 or verified_dur <= 0.0 or verified_dur > 60.5:
            corrupted_count += 1
            failed_count += 1
            err_msg = f"integrity_or_duration_invalid (decode={decode_ok}, dur={verified_dur})"
            ctrl.fail_task_with_retry(task_id, err_msg, permanent=True)
            learning_sys.discover_video(
                source_id=v_id, original_url=url, title=title, niche=niche,
                duration_seconds=verified_dur, views_count=int(cand.get("views") or 0),
                likes_count=int(cand.get("likes") or 0), comment_count=int(cand.get("comments") or 0),
                target_channel_id=ch_id, pilot_phase=18,
            )
            learning_sys._set_state(v_id, "failed", error_msg=err_msg)
            processed_records.append({
                "channel_id": ch_id, "channel_name": ch_name, "niche": niche,
                "video_id": v_id, "url": url, "title": title,
                "file_size_bytes": file_size, "sha256": sha256,
                "state": "failed", "error_message": err_msg,
            })
            processed_count += 1
            continue

        # Registra vídeo e estado downloaded
        learning_sys.discover_video(
            source_id=v_id, original_url=url, title=title,
            creator=cand.get("creator") or "Desconhecido",
            channel_id_source=cand.get("channel_id_source") or "",
            duration_seconds=verified_dur, niche=niche,
            views_count=int(cand.get("views") or 0),
            likes_count=int(cand.get("likes") or 0),
            comment_count=int(cand.get("comments") or 0),
            target_channel_id=ch_id, pilot_phase=18,
            metadata_payload={
                "sha256": sha256, "file_size_bytes": file_size,
                "local_path": local_video_path, "target_channel_id": ch_id,
                "pilot_phase": 18, "metadata_origin": cand.get("metadata_origin"),
                "collected_at": cand.get("collected_at"),
                "popularity_tier": cand.get("popularity_tier"),
            },
        )
        learning_sys._set_state(v_id, "downloaded")

        # 1. Visual (PySceneDetect + OpenCV)
        scenes_res = scene_detector.detect_scenes(local_video_path)
        cuts_count = max(0, int(scenes_res.get("total_scenes", 1)) - 1)
        cut_intervals = scenes_res.get("cut_intervals_sec", [])
        avg_cut_interval = scenes_res.get("avg_cut_interval_sec", verified_dur)
        first_cut_ts = scenes_res["scenes"][0].get("end_sec") if scenes_res.get("scenes") else None

        motion_info = visual_analyzer.analyze_framing_and_motion(local_video_path)
        opencv_ok = bool(motion_info.get("opencv_frames_read_ok", False))
        sampled_cnt = int(motion_info.get("sampled_frames_count", 0))
        shot_type = motion_info.get("estimated_shot_type", "")
        dominant_comp = "close_up_narrador" if "Close-Up" in shot_type else ("dynamic_action" if "Dynamic" in shot_type else "standard")
        w = probe.get("width") or 0
        h = probe.get("height") or 0
        aspect_ratio = f"{w}:{h}" if w and h else "unknown"
        is_vert = (h > w) if (w and h) else False

        learning_sys.register_physical_media(
            source_id=v_id,
            local_path=local_video_path,
            file_size_bytes=file_size,
            sha256_hash=sha256,
            verified_duration=verified_dur,
            video_codec=probe.get("video_codec"),
            audio_codec=probe.get("audio_codec"),
            streams_count=probe.get("streams_count"),
            ffmpeg_decode_ok=decode_ok,
            opencv_frames_read_ok=opencv_ok,
            opencv_sampled_frames=sampled_cnt,
            resolution=f"{w}x{h}" if w and h else None,
        )
        learning_sys._set_state(v_id, "downloaded")

        learning_sys.process_visual(
            source_id=v_id,
            cuts_count=cuts_count,
            aspect_ratio=aspect_ratio,
            has_subtitles_on_screen=bool(motion_info.get("text_on_screen_detected", False)),
            framing_changes=int(motion_info.get("framing_changes_detected", 0)),
            broll_presence_ratio=0.0,
            dominant_composition=dominant_comp,
            cut_intervals_sec=cut_intervals,
            avg_cut_interval_sec=avg_cut_interval,
            representative_frames=motion_info.get("representative_frames", []),
            average_motion_score=motion_info.get("average_motion_score"),
            text_detection_evidence={
                "method": motion_info.get("text_detection_method"),
                "text_edge_density_avg": motion_info.get("text_edge_density_avg"),
                "first_cut_timestamp_sec": first_cut_ts,
            },
            opencv_frames_read_ok=opencv_ok,
        )

        # 2. Acústica (FFmpeg EBU R128 com -vn)
        audio_metrics = learning_sys._analyze_audio_file(local_video_path)
        measured_lufs = float(audio_metrics["integrated_lufs"])
        acoustic_class = audio_metrics["classification"]
        if acoustic_class == "SILENT_AUDIO_TRACK":
            silent_audio_count += 1

        learning_sys.process_audio(
            source_id=v_id,
            speech_clarity_score=audio_metrics["speech_clarity_score"],
            estimated_lufs=measured_lufs,
            pauses_ratio=audio_metrics["pauses_ratio"],
            audio_classification=acoustic_class,
            is_usable=audio_metrics["is_usable"],
            diagnostic_message=audio_metrics["diagnostic_message"],
            clipping_detected=audio_metrics.get("clipping_detected", False),
            true_peak_db=audio_metrics.get("true_peak_db"),
            lra=audio_metrics.get("lra"),
        )

        # 3. Narrativa REAL (Legendas locais ou Faster-Whisper CPU)
        real_transcript = fetch_subtitles_for_short(url, v_id, local_video_path=local_video_path)
        trans_engine = "youtube_subtitles"
        if not real_transcript and audio_metrics["is_usable"]:
            try:
                lang_hint = "en" if any(w_en in title.lower() for w_en in ["the ", "how ", "why ", "stoic"]) else "pt"
                w_res = whisper_svc.transcribe_audio(local_video_path, language=lang_hint)
                real_transcript = (w_res.get("full_transcript") or "").strip()
                trans_engine = f"faster_whisper_{whisper_svc.model_size}"
            except Exception as e:
                print(f"  [Aviso Whisper {v_id}]: {e}", flush=True)
                real_transcript = ""

        narr_res = learning_sys.process_transcript(
            v_id, real_transcript, allow_insufficient_speech=True, transcription_engine=trans_engine
        )
        narr_metrics = narr_res.get("metrics", {})
        learning_sys._set_state(v_id, "technical_analysis_complete")

        # 4. Avaliação Editorial Contextual
        ed_res = learning_sys.evaluate_editorial_adherence(source_id=v_id, target_channel_id=ch_id)
        if ed_res["processing_state"] == "editorially_rejected":
            rejected_count += 1
            record_state = "editorially_rejected"
        else:
            prom_res = learning_sys.promote_to_learning_candidate(v_id)
            success_count += 1
            record_state = prom_res["processing_state"]

        # 5. Extração Estruturada de 15 Características Editoriais Reais
        with learning_sys._get_conn() as conn:
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
            features = feature_extractor.extract(vid_dict)
            payload_obj = json.loads(row[8] or "{}")
            payload_obj["editorial_features"] = features
            conn.execute(
                "UPDATE audiovisual_library SET analysis_payload = ? WHERE source_id = ?",
                (json.dumps(payload_obj, ensure_ascii=False), v_id),
            )
            conn.commit()

        ctrl.complete_task(task_id, {"state": record_state, "sha256": sha256})
        processed_count += 1
        ram_mb = get_process_memory_mb()
        if ram_mb > 0:
            ram_samples.append(ram_mb)

        processed_records.append({
            "channel_id": ch_id,
            "channel_name": ch_name,
            "niche": niche,
            "video_id": v_id,
            "url": url,
            "title": title,
            "duration_seconds": verified_dur,
            "views_count": int(cand.get("views") or 0),
            "likes_count": int(cand.get("likes") or 0),
            "comment_count": int(cand.get("comments") or 0),
            "engagement_ratio": float(cand.get("engagement_ratio") or 0.0),
            "file_size_bytes": file_size,
            "sha256": sha256,
            "video_codec": probe.get("video_codec"),
            "audio_codec": probe.get("audio_codec"),
            "ffmpeg_decode_ok": True,
            "opencv_frames_read_ok": opencv_ok,
            "cuts_count": cuts_count,
            "aspect_ratio": aspect_ratio,
            "is_vertical_9_16": is_vert,
            "integrated_lufs": measured_lufs,
            "acoustic_classification": acoustic_class,
            "speech_detected": bool(narr_metrics.get("speech_detected", False)),
            "word_count": narr_metrics.get("word_count", 0),
            "editorial_features": features,
            "state": record_state,
            "editorial_verdict": ed_res.get("editorial_verdict"),
            "rejection_reason": ed_res.get("rejection_reason"),
        })

        if processed_count % 5 == 0 or idx == len(candidates):
            with learning_sys._get_conn() as conn:
                update_checkpoint(conn, processed_count, success_count, rejected_count, consecutive_dl_errors, v_id)
            EXECUTION_DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
            with open(EXECUTION_DATA_JSON, "w", encoding="utf-8") as f:
                json.dump({"records": processed_records}, f, indent=2, ensure_ascii=False)
            elapsed_now = time.time() - start_wall
            print(
                f"  [{processed_count}/{len(candidates)}] Ch{ch_id} {v_id} -> {record_state} | "
                f"LUFS={measured_lufs:.1f} | cuts={cuts_count} | words={narr_metrics.get('word_count', 0)} | "
                f"RAM={ram_mb:.1f}MB | {elapsed_now:.0f}s",
                flush=True,
            )

    with learning_sys._get_conn() as conn:
        update_checkpoint(conn, processed_count, success_count, rejected_count, 0, candidates[-1]["id"], status="COMPLETED")

    elapsed_wall = round(time.time() - start_wall, 2)
    elapsed_cpu = round(time.process_time() - start_cpu, 2)
    final_cost = float(model_gateway.get_usage_metrics().get("total_cost_usd", 0.0))
    db_size_mb = round(os.path.getsize(learning_sys.db_path) / (1024 * 1024), 2)
    storage_bytes = sum(r.get("file_size_bytes", 0) for r in processed_records)

    summary = {
        "benchmark_name": "FASE18_BENCHMARK_250_SHORTS",
        "elapsed_wall_seconds": elapsed_wall,
        "elapsed_cpu_seconds": elapsed_cpu,
        "avg_seconds_per_video": round(elapsed_wall / max(1, processed_count - resumed_count), 2),
        "throughput_videos_per_min": round(((processed_count - resumed_count) / max(1.0, elapsed_wall)) * 60.0, 2),
        "ram_peak_mb": max(ram_samples) if ram_samples else get_process_memory_mb(),
        "ram_avg_mb": round(sum(ram_samples) / len(ram_samples), 2) if ram_samples else get_process_memory_mb(),
        "sqlite_db_size_mb": db_size_mb,
        "total_target": len(candidates),
        "processed_count": processed_count,
        "resumed_from_checkpoint_count": resumed_count,
        "duplicates_skipped": duplicates_skipped,
        "editorially_approved_count": success_count,
        "editorially_rejected_count": rejected_count,
        "failed_count": failed_count,
        "corrupted_count": corrupted_count,
        "silent_audio_count": silent_audio_count,
        "speech_transcribed_count": sum(1 for r in processed_records if r.get("speech_detected")),
        "total_storage_bytes": storage_bytes,
        "total_storage_mb": round(storage_bytes / (1024 * 1024), 2),
        "cost_usd": final_cost,
        "records": processed_records,
    }
    with open(EXECUTION_DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n=== BENCHMARK 250 CONCLUÍDO: {processed_count}/{len(candidates)} | {elapsed_wall}s | Custo ${final_cost:.2f} ===", flush=True)


if __name__ == "__main__":
    lim = None
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        lim = int(sys.argv[i + 1])
    run_benchmark_250(limit=lim)
