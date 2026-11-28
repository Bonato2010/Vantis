"""
VANTIS — Motor de Renderização Audiovisual de Pacotes Editoriais (Fase 22)
Transforma pacotes aprovados (APPROVED_FOR_PRODUCTION) com ativos verificados em
vídeos MP4 9:16 reais usando Edge-TTS, legendas ASS, FFmpeg EBU R128 (-14 LUFS),
verificação física via FFprobe/FFmpeg decode e SHA256.
"""

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.media_processing.ffmpeg_engine import FFmpegEngine
from services.media_processing.subtitle_generator import SubtitleGenerator
from services.media_processing.tts_engine import TTSNarrationService
from services.production.editorial_production_engine import EditorialProductionEngine

RENDER_STATES = (
    "QUEUED",
    "VALIDATING",
    "PREPARING_ASSETS",
    "GENERATING_AUDIO",
    "ASSEMBLING",
    "RENDERING",
    "VERIFYING",
    "READY_FOR_REVIEW",
    "BLOCKED",
    "FAILED",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class PackageRendererService:
    """Renderizador audiovisual real com aprovação obrigatória, verificação de ativos e checkpoints."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        tts_service: Optional[TTSNarrationService] = None,
        subtitle_generator: Optional[SubtitleGenerator] = None,
        ffmpeg_engine: Optional[FFmpegEngine] = None,
    ):
        self.prod_engine = EditorialProductionEngine(db_path=db_path)
        self.db_path = Path(self.prod_engine.db_path)
        self.output_dir = Path(output_dir) if output_dir else (BASE_DIR / "workspace" / "renders")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tts = tts_service or TTSNarrationService(output_dir=self.output_dir / "audio")
        self.subs = subtitle_generator or SubtitleGenerator(output_dir=self.output_dir / "subs")
        self.ffmpeg = ffmpeg_engine or FFmpegEngine()
        self._ensure_table()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self):
        with self._get_conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS render_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'QUEUED',
                    checkpoint_stage TEXT DEFAULT 'QUEUED',
                    output_mp4_path TEXT,
                    file_size_bytes INTEGER DEFAULT 0,
                    duration_sec REAL DEFAULT 0.0,
                    resolution TEXT,
                    video_codec TEXT,
                    audio_codec TEXT,
                    sha256 TEXT,
                    measured_lufs REAL,
                    scenes_count INTEGER DEFAULT 0,
                    subtitles_count INTEGER DEFAULT 0,
                    pending_assets_json TEXT DEFAULT '[]',
                    assets_used_json TEXT DEFAULT '[]',
                    error_message TEXT,
                    review_decision TEXT,
                    review_notes TEXT,
                    review_defects_json TEXT DEFAULT '[]',
                    reviewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(render_jobs)").fetchall()}
            for col_name, col_def in (
                ("review_decision", "TEXT"),
                ("review_notes", "TEXT"),
                ("review_defects_json", "TEXT DEFAULT '[]'"),
                ("reviewed_at", "TIMESTAMP"),
            ):
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE render_jobs ADD COLUMN {col_name} {col_def}")
            conn.commit()

    def _create_job(self, package_id: int, channel_id: int) -> int:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO render_jobs (package_id, channel_id, status, checkpoint_stage) VALUES (?, ?, 'QUEUED', 'QUEUED')",
                (package_id, channel_id),
            )
            conn.commit()
            return int(cur.lastrowid)

    def _update_job(self, job_id: int, **fields):
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields.keys())
        vals = list(fields.values()) + [job_id]
        with self._get_conn() as conn:
            conn.execute(f"UPDATE render_jobs SET {cols}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", vals)
            conn.commit()

    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            r = conn.execute("SELECT * FROM render_jobs WHERE id = ?", (job_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["pending_assets"] = json.loads(d.pop("pending_assets_json") or "[]")
        d["assets_used"] = json.loads(d.pop("assets_used_json") or "[]")
        d["review_defects"] = json.loads(d.pop("review_defects_json", "[]") or "[]")
        return d

    def list_jobs(self, channel_id: Optional[int] = None, limit: int = 30) -> List[Dict[str, Any]]:
        q = "SELECT * FROM render_jobs"
        params: List[Any] = []
        if channel_id is not None:
            q += " WHERE channel_id = ?"
            params.append(int(channel_id))
        q += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._get_conn() as conn:
            rows = conn.execute(q, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["pending_assets"] = json.loads(d.pop("pending_assets_json") or "[]")
            d["assets_used"] = json.loads(d.pop("assets_used_json") or "[]")
            d["review_defects"] = json.loads(d.pop("review_defects_json", "[]") or "[]")
            out.append(d)
        return out

    def submit_human_review(
        self,
        job_id: int,
        decision: str,
        notes: str = "",
        defects: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Registra a revisão humana final de um vídeo renderizado sem auto-aprovar."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job de renderização {job_id} não encontrado.")
        if job["status"] not in ("READY_FOR_REVIEW", "CHANGES_REQUESTED"):
            raise ValueError(f"Job #{job_id} em estado '{job['status']}' não está aguardando revisão final.")

        allowed = {
            "APPROVE_AFTER_REVIEW": "APPROVED_AFTER_REVIEW",
            "APPROVE_FINAL": "COMPLETED",
            "REQUEST_CHANGES": "CHANGES_REQUESTED",
            "REJECT": "REJECTED",
        }
        if decision not in allowed:
            raise ValueError(f"Decisão inválida '{decision}'. Permitidas: {tuple(allowed.keys())}")

        new_status = allowed[decision]
        defects_list = [str(x).strip() for x in (defects or []) if str(x).strip()]
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE render_jobs
                SET status = ?,
                    checkpoint_stage = ?,
                    review_decision = ?,
                    review_notes = ?,
                    review_defects_json = ?,
                    reviewed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_status, new_status, decision, notes, json.dumps(defects_list, ensure_ascii=False), job_id),
            )
            conn.commit()
        return self.get_job(job_id)

    def _measure_lufs(self, media_path: str) -> Optional[float]:
        cmd = [
            self.ffmpeg.binary_path or "ffmpeg",
            "-vn", "-i", media_path,
            "-af", "ebur128=framelog=quiet",
            "-f", "null", "-",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding="utf-8", errors="replace", timeout=45)
        m = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", res.stderr or "")
        return float(m[-1]) if m else None

    def render_package(
        self,
        package_id: int,
        available_assets: Optional[Dict[int, str]] = None,
        resume_job_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Executa a renderização real de um pacote editorial aprovado."""
        pkg = self.prod_engine.get_package(package_id)
        if not pkg:
            raise ValueError(f"Pacote editorial {package_id} não encontrado.")

        ch_id = int(pkg["channel_id"])
        job_id = resume_job_id or self._create_job(package_id, ch_id)

        # 1. VALIDATING — exige aprovação humana explícita
        self._update_job(job_id, status="VALIDATING", checkpoint_stage="VALIDATING")
        if pkg["status"] not in ("APPROVED_FOR_PRODUCTION", "PRODUCTION_IN_PROGRESS"):
            err = f"Renderização bloqueada: pacote #{package_id} está em '{pkg['status']}' (exige APPROVED_FOR_PRODUCTION)."
            self._update_job(job_id, status="BLOCKED", error_message=err)
            return self.get_job(job_id)

        # 2. PREPARING_ASSETS — valida todos os ativos das cenas sem inventar mídia
        self._update_job(job_id, status="PREPARING_ASSETS", checkpoint_stage="PREPARING_ASSETS")
        content = pkg["package"]
        scenes = content.get("audiovisual_plan", {}).get("scenes", [])
        assets_map = available_assets or {}
        pending_assets: List[Dict[str, Any]] = []
        assets_used: List[Dict[str, Any]] = []

        for sc in scenes:
            idx = int(sc["scene_index"])
            candidate_path = assets_map.get(idx) or assets_map.get(str(idx)) or sc.get("asset_path")
            if not candidate_path or not Path(candidate_path).is_file() or Path(candidate_path).stat().st_size <= 0:
                pending_assets.append({
                    "scene_index": idx,
                    "stage": sc.get("stage"),
                    "reason": "ASSET_NEEDED_OR_MISSING",
                })
            else:
                assets_used.append({
                    "scene_index": idx,
                    "path": str(Path(candidate_path).resolve()),
                    "origin": "verified_local_asset",
                })

        if pending_assets or not scenes:
            err = f"{len(pending_assets)} cena(s) sem ativo físico verificado (ASSET_NEEDED)."
            self._update_job(
                job_id,
                status="BLOCKED",
                scenes_count=len(scenes),
                pending_assets_json=json.dumps(pending_assets, ensure_ascii=False),
                assets_used_json=json.dumps(assets_used, ensure_ascii=False),
                error_message=err,
            )
            return self.get_job(job_id)

        self._update_job(
            job_id,
            scenes_count=len(scenes),
            assets_used_json=json.dumps(assets_used, ensure_ascii=False),
            pending_assets_json="[]",
        )

        # 3. GENERATING_AUDIO — Edge-TTS real obrigatório (rejeita mock_fallback!)
        self._update_job(job_id, status="GENERATING_AUDIO", checkpoint_stage="GENERATING_AUDIO")
        narration_text = (content.get("audio_plan", {}).get("narration_text") or "").strip()
        if not narration_text:
            self._update_job(job_id, status="FAILED", error_message="Texto de narração vazio no pacote.")
            return self.get_job(job_id)

        tts_res = self.tts.generate_narration(
            text=narration_text,
            channel_id=ch_id,
            task_id=f"pkg{package_id}_job{job_id}",
            force_offline=False,
        )
        if not tts_res.get("success") or tts_res.get("mode") != "real_neural" or not Path(tts_res.get("audio_path", "")).is_file():
            err = f"TTS neural indisponível ou falhou (mode={tts_res.get('mode')}); simulação bloqueada."
            self._update_job(job_id, status="FAILED", error_message=err)
            return self.get_job(job_id)

        audio_path = Path(tts_res["audio_path"])
        audio_dur = float(tts_res.get("duration_sec") or 0.0)
        if audio_dur <= 0.0:
            aprobe = self.ffmpeg.probe_media(str(audio_path))
            audio_dur = float(aprobe.get("duration_sec") or 0.0)
        if audio_dur <= 0.0:
            self._update_job(job_id, status="FAILED", error_message="Áudio TTS gerado com duração zero.")
            return self.get_job(job_id)

        # 4. ASSEMBLING — Legendas ASS reais sincronizadas + segmentos de cena 9:16
        self._update_job(job_id, status="ASSEMBLING", checkpoint_stage="ASSEMBLING")
        cues = tts_res.get("boundaries") or [{"text": narration_text, "start": 0.0, "end": audio_dur}]
        sub_res = self.subs.generate_ass(
            cues=cues,
            channel_id=ch_id,
            task_id=f"pkg{package_id}_job{job_id}",
        )
        ass_path = Path(sub_res["ass_path"])
        sub_count = int(sub_res.get("total_cues") or 0)

        # 5. RENDERING — FFmpeg real (1080x1920 9:16, concat de cenas, ASS, EBU R128 -14 LUFS)
        self._update_job(job_id, status="RENDERING", checkpoint_stage="RENDERING", subtitles_count=sub_count)
        ffmpeg_bin = self.ffmpeg.binary_path or "ffmpeg"
        out_mp4 = self.output_dir / f"vantis_ch{ch_id}_pkg{package_id}_job{job_id}.mp4"
        seg_dir = self.output_dir / f"_segs_job{job_id}"
        seg_dir.mkdir(parents=True, exist_ok=True)
        seg_dur = round(audio_dur / max(1, len(assets_used)), 3)

        try:
            seg_paths: List[Path] = []
            for asset in assets_used:
                ap = Path(asset["path"])
                seg_out = seg_dir / f"seg_{asset['scene_index']}.mp4"
                is_img = ap.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                cmd_seg = [ffmpeg_bin, "-y"]
                if is_img:
                    cmd_seg.extend(["-loop", "1", "-t", str(seg_dur), "-i", str(ap)])
                else:
                    cmd_seg.extend(["-stream_loop", "-1", "-t", str(seg_dur), "-i", str(ap)])
                cmd_seg.extend([
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
                    "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    str(seg_out),
                ])
                r_seg = subprocess.run(cmd_seg, capture_output=True, text=True, check=False, timeout=60)
                if r_seg.returncode != 0 or not seg_out.is_file():
                    self._update_job(job_id, status="FAILED", error_message=f"FFmpeg falhou na cena {asset['scene_index']}: {r_seg.stderr[-250:]}")
                    return self.get_job(job_id)
                seg_paths.append(seg_out)

            concat_file = seg_dir / "concat.txt"
            concat_file.write_text("\n".join(f"file '{sp.as_posix()}'" for sp in seg_paths), encoding="utf-8")
            # Escapa ':' e '\' para o filtro ass= no Windows
            ass_escaped = ass_path.as_posix().replace(":", "\\:")
            cmd_final = [
                ffmpeg_bin, "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_file),
                "-i", str(audio_path),
                "-vf", f"ass='{ass_escaped}'",
                "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-shortest",
                str(out_mp4),
            ]
            r_fin = subprocess.run(cmd_final, capture_output=True, text=True, check=False, timeout=120)
            if r_fin.returncode != 0 or not out_mp4.is_file():
                self._update_job(job_id, status="FAILED", error_message=f"FFmpeg falhou na renderização final: {r_fin.stderr[-300:]}")
                return self.get_job(job_id)
        except Exception as e:
            self._update_job(job_id, status="FAILED", error_message=f"Erro durante renderização FFmpeg: {e}")
            return self.get_job(job_id)
        finally:
            import shutil
            shutil.rmtree(seg_dir, ignore_errors=True)

        # 6. VERIFYING — FFprobe + decodificação FFmpeg + SHA256 + medição real de LUFS
        self._update_job(job_id, status="VERIFYING", checkpoint_stage="VERIFYING")
        dec = subprocess.run([ffmpeg_bin, "-v", "error", "-i", str(out_mp4), "-f", "null", "-"], capture_output=True, text=True, check=False, timeout=45)
        probe = self.ffmpeg.probe_media(str(out_mp4))
        measured_lufs = self._measure_lufs(str(out_mp4))
        size_bytes = out_mp4.stat().st_size if out_mp4.is_file() else 0
        if dec.returncode != 0 or size_bytes <= 0 or float(probe.get("duration_sec") or 0.0) <= 0.0:
            self._update_job(job_id, status="FAILED", error_message="Arquivo MP4 renderizado falhou na verificação de integridade.")
            return self.get_job(job_id)

        sha256 = _sha256_file(out_mp4)
        res_str = f"{probe.get('width')}x{probe.get('height')}"
        self._update_job(
            job_id,
            status="READY_FOR_REVIEW",
            checkpoint_stage="READY_FOR_REVIEW",
            output_mp4_path=str(out_mp4.resolve()),
            file_size_bytes=size_bytes,
            duration_sec=round(float(probe["duration_sec"]), 2),
            resolution=res_str,
            video_codec=probe.get("video_codec"),
            audio_codec=probe.get("audio_codec"),
            sha256=sha256,
            measured_lufs=measured_lufs,
            error_message=None,
        )
        return self.get_job(job_id)
