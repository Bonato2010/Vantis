"""
IAS Media Downloader Service (services/media_processing/media_downloader.py)
Gerencia o download autêntico e seguro de YouTube Shorts para análise audiovisual física.
Utiliza yt-dlp e FFmpeg, calculando SHA256 e extraindo metadados técnicos reais.
"""

import os
import sys
import json
import time
import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.media_processing.ffmpeg_engine import FFmpegEngine

logger = logging.getLogger("Vantis.MediaDownloader")

class MediaDownloader:
    """Download controlado de mídias para análise física sem simulações."""

    def __init__(self, download_dir: Optional[Union[str, Path]] = None):
        if download_dir:
            self.download_dir = Path(download_dir)
        else:
            self.download_dir = BASE_DIR / "workspace" / "downloads" / "shorts_pilot_fase15"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg = FFmpegEngine()

    def download_short(
        self,
        youtube_url: str,
        timeout_seconds: int = 45,
        output_dir: Optional[Union[str, Path]] = None,
        max_retries: int = 2,
        backoff_base_sec: float = 4.0
    ) -> Dict[str, Any]:
        """
        Executa download com restrições rígidas:
        - Duração estrita de Shorts (<= 60s)
        - Tamanho máximo 100MB
        - Rejeição de lives ou streams infinitos
        - Backoff exponencial em falhas transitórias
        - Cálculo de SHA256 do arquivo baixado
        - Probing via FFprobe e decodificação FFmpeg
        """
        if not youtube_url or not isinstance(youtube_url, str):
            return {
                "success": False,
                "error": "URL inválida fornecida",
                "reason": "invalid_url"
            }

        target_dir = Path(output_dir) if output_dir else self.download_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        ffmpeg_dir = Path(self.ffmpeg.binary_path).parent if self.ffmpeg.binary_path else None
        output_template = str(target_dir / "%(id)s.%(ext)s")

        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--js-runtimes", "node",
            "--no-playlist",
            "--max-filesize", "100M",
            "--match-filter", "duration <= 60 & !is_live",
            "-f", "bv*+ba/b",
            "-o", output_template
        ]

        if ffmpeg_dir and ffmpeg_dir.exists():
            cmd.extend(["--ffmpeg-location", str(ffmpeg_dir)])

        cmd.append(youtube_url)

        last_err = None
        res = None
        for attempt in range(max_retries + 1):
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    encoding="utf-8",
                    errors="replace"
                )
                if res.returncode == 0:
                    break
                stderr = res.stderr or ""
                if "does not pass filter duration <= 60" in stderr or "did not match filter" in stderr:
                    logger.warning(f"Vídeo {youtube_url} rejeitado por exceder 60s.")
                    return {
                        "success": False,
                        "error": "Vídeo rejeitado: duração excede 60s (não é um Short)",
                        "reason": "duration_exceeds_60s"
                    }
                last_err = stderr[-200:].strip()
            except subprocess.TimeoutExpired:
                last_err = f"Timeout de {timeout_seconds}s excedido durante download"
            except Exception as e:
                last_err = str(e)

            if attempt < max_retries:
                wait_sec = backoff_base_sec * (2 ** attempt)
                logger.warning(f"Download falhou ({last_err}). Backoff exponencial: aguardando {wait_sec:.1f}s antes de tentar novamente...")
                time.sleep(wait_sec)

        if res is None or res.returncode != 0:
            reason = "download_timeout" if last_err and "Timeout" in last_err else "yt_dlp_error"
            return {
                "success": False,
                "error": f"Falha no download via yt-dlp após {max_retries + 1} tentativa(s): {last_err}",
                "reason": reason
            }

        try:
            # Localiza o arquivo baixado
            # Extrai o ID da URL (suporta /shorts/ID, /watch?v=ID e youtu.be/ID)
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(youtube_url.strip())
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                raw_id = qs["v"][0]
            else:
                raw_id = parsed.path.rstrip("/").split("/")[-1]

            # Busca o arquivo pelo ID no diretório de download
            candidates = list(target_dir.glob(f"{raw_id}.*"))
            media_candidates = [c for c in candidates if c.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov")] or candidates
            if not media_candidates:
                return {
                    "success": False,
                    "error": f"Arquivo não encontrado no diretório de destino após download: {raw_id}",
                    "reason": "file_not_found_post_download"
                }

            target_file = media_candidates[0]
            file_size = target_file.stat().st_size
            if file_size <= 0:
                target_file.unlink(missing_ok=True)
                return {
                    "success": False,
                    "error": "Arquivo baixado possui 0 bytes (vazio/corrompido)",
                    "reason": "zero_byte_file"
                }

            # 1. Calcula hash SHA256 do arquivo real
            hasher = hashlib.sha256()
            with open(target_file, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            sha256_hash = hasher.hexdigest()

            # 2. Probe FFprobe para verificar duração exata, codecs e streams
            probe = self.ffmpeg.probe_media(str(target_file))
            verified_duration = probe.get("duration_sec", 0.0)

            # Revalidação estrita: se a duração medida pelo FFprobe for > 60s, rejeita e deleta
            if verified_duration > 61.0:
                target_file.unlink(missing_ok=True)
                return {
                    "success": False,
                    "error": f"Duração física verificada ({verified_duration}s) excede 60s.",
                    "reason": "physical_duration_exceeds_60s"
                }

            # 3. Validação física de decodificação via FFmpeg
            decode_res = self.ffmpeg.verify_decode_integrity(str(target_file))
            if not decode_res.get("decodable", False):
                return {
                    "success": False,
                    "error": f"Arquivo falhou na decodificação FFmpeg: {decode_res.get('stderr')}",
                    "reason": "ffmpeg_decode_failed"
                }

            return {
                "success": True,
                "local_path": str(target_file.resolve()),
                "file_path": str(target_file.resolve()),
                "file_size_bytes": file_size,
                "sha256": sha256_hash,
                "verified_duration": verified_duration,
                "duration_seconds": verified_duration,
                "video_codec": probe.get("video_codec"),
                "audio_codec": probe.get("audio_codec"),
                "streams_count": probe.get("streams_count", 0),
                "ffmpeg_decode_ok": True,
                "probe": probe,
                "source_id": raw_id,
                "source_url": youtube_url
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "reason": "unexpected_exception"
            }
