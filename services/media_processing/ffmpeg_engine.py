"""
IAS Media Processing Engine (services/media_processing/ffmpeg_engine.py)
Renderização audiovisual de alto desempenho para YouTube Shorts (9:16 vertical),
normalização de áudio (EBU R128), queima de legendas ASS estilizadas,
sintetização de telas dinâmicas e conformidade com perfis anti-duplicação.
"""
import os
import re
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Union


class FFmpegEngine:
    """Motor de processamento audiovisual baseado em FFmpeg e FFprobe."""

    def __init__(self, ffmpeg_bin: Optional[str] = None, ffprobe_bin: Optional[str] = None):
        self.binary_path = ffmpeg_bin or self._find_ffmpeg()
        self.probe_path = ffprobe_bin or self._find_ffprobe()
        self.available = bool(self.binary_path and os.path.exists(self.binary_path))

    def _find_ffmpeg(self) -> Optional[str]:
        # 1. Checa PATH do sistema
        in_path = shutil.which("ffmpeg")
        if in_path:
            return in_path

        # 2. Checa caminho conhecido do WinGet
        winget_path = Path(r"C:\Users\jcvse\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.1-full_build\bin\ffmpeg.exe")
        if winget_path.exists():
            return str(winget_path)

        # 3. Busca recursiva no AppData
        appdata_local = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\jcvse\AppData\Local"))
        matches = list(appdata_local.glob("**/ffmpeg.exe"))
        if matches:
            return str(matches[0])

        return None

    def _find_ffprobe(self) -> Optional[str]:
        if self.binary_path:
            sibling = Path(self.binary_path).parent / "ffprobe.exe"
            if sibling.exists():
                return str(sibling)
        in_path = shutil.which("ffprobe")
        if in_path:
            return in_path
        return None

    def get_status(self) -> Dict[str, Any]:
        if not self.available:
            return {"available": False, "version": None, "binary_path": None, "probe_path": None}
        try:
            res = subprocess.run([self.binary_path, "-version"], capture_output=True, text=True, timeout=5)
            version_line = res.stdout.splitlines()[0] if res.stdout else "FFmpeg detectado"
            return {
                "available": True,
                "version": version_line,
                "binary_path": self.binary_path,
                "probe_path": self.probe_path
            }
        except Exception as e:
            return {"available": False, "version": None, "error": str(e), "binary_path": self.binary_path}

    def probe_media(self, file_path: str) -> Dict[str, Any]:
        """Extrai metadados estruturados de áudio/vídeo via FFprobe."""
        if not self.probe_path or not os.path.exists(self.probe_path):
            # Fallback básico via os.path
            return {
                "exists": os.path.exists(file_path),
                "duration_sec": 0.0,
                "width": 0,
                "height": 0,
                "is_vertical": False,
                "has_audio": False,
                "has_video": False,
                "size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }

        cmd = [
            self.probe_path, "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height",
            "-of", "json",
            str(file_path)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                streams = data.get("streams", [])
                fmt = data.get("format", {})
                duration = float(fmt.get("duration", 0.0))
                size_bytes = int(fmt.get("size", 0))

                v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
                a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

                width = int(v_stream.get("width", 0)) if v_stream else 0
                height = int(v_stream.get("height", 0)) if v_stream else 0
                is_vertical = (height > width and width > 0)

                return {
                    "exists": True,
                    "duration_sec": round(duration, 2),
                    "size_bytes": size_bytes,
                    "width": width,
                    "height": height,
                    "is_vertical": is_vertical,
                    "aspect_ratio": f"{width}:{height}" if width and height else None,
                    "streams_count": len(streams),
                    "has_video": v_stream is not None,
                    "has_audio": a_stream is not None,
                    "video_codec": v_stream.get("codec_name") if v_stream else None,
                    "audio_codec": a_stream.get("codec_name") if a_stream else None
                }
        except Exception as e:
            return {"exists": os.path.exists(file_path), "error": str(e), "duration_sec": 0.0}

        return {"exists": os.path.exists(file_path), "duration_sec": 0.0}

    def verify_decode_integrity(self, file_path: str, timeout_seconds: int = 60) -> Dict[str, Any]:
        """Valida integridade física decodificando o arquivo via FFmpeg para saída nula."""
        if not self.available:
            return {"decodable": False, "returncode": -1, "stderr": "FFmpeg binary unavailable"}
        if not os.path.exists(file_path):
            return {"decodable": False, "returncode": -1, "stderr": f"File not found: {file_path}"}

        cmd = [
            self.binary_path, "-v", "error",
            "-i", str(file_path),
            "-f", "null", "-"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
            err_text = (res.stderr or "").strip()
            return {
                "decodable": res.returncode == 0,
                "returncode": res.returncode,
                "stderr": err_text[-300:] if err_text else ""
            }
        except subprocess.TimeoutExpired:
            return {"decodable": False, "returncode": -2, "stderr": f"Decode timeout after {timeout_seconds}s"}
        except Exception as e:
            return {"decodable": False, "returncode": -3, "stderr": str(e)}

    def measure_loudness(self, media_path: str) -> Dict[str, Any]:
        """Mede o Integrated Loudness em LUFS via filtro EBU R128 do FFmpeg (com -vn para evitar timeout em 4K)."""
        if not self.available:
            return {"integrated_lufs": -70.0, "true_peak_db": -1.5, "measured": False, "measurement_failure": True, "clipping_detected": False}

        cmd = [
            self.binary_path, "-y",
            "-i", str(media_path),
            "-vn",
            "-af", "ebur128=framelog=verbose",
            "-f", "null", "-"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            output = res.stderr or ""
            # Procura por: Integrated loudness:\n    I:         -14.2 LUFS
            match_i = re.search(r"Integrated loudness:\s+I:\s+([-\d\.]+)\s+LUFS", output)
            match_tp = re.search(r"True peak:\s+Peak:\s+([-\d\.]+)\s+dBFS", output)
            match_lra = re.search(r"LRA:\s+([-\d\.]+)\s+LU", output)

            if not match_i:
                return {
                    "integrated_lufs": -70.0,
                    "true_peak_db": -1.5,
                    "measured": False,
                    "measurement_failure": True,
                    "clipping_detected": False,
                    "error": output[-200:].strip()
                }

            i_lufs = float(match_i.group(1))
            tp_db = float(match_tp.group(1)) if match_tp else -1.5
            lra = float(match_lra.group(1)) if match_lra else 0.0

            return {
                "integrated_lufs": i_lufs,
                "true_peak_db": tp_db,
                "lra": lra,
                "measured": True,
                "measurement_failure": False,
                "clipping_detected": tp_db >= -0.3 or i_lufs > -6.0
            }
        except Exception as e:
            return {
                "integrated_lufs": -70.0,
                "true_peak_db": -1.5,
                "measured": False,
                "measurement_failure": True,
                "clipping_detected": False,
                "error": str(e)
            }

    def extract_audio(self, video_path: str, output_wav: str) -> bool:
        """Extrai áudio mono a 16kHz ideal para transcrição com Whisper."""
        if not self.available:
            raise RuntimeError("FFmpeg não está disponível no sistema.")
        
        cmd = [
            self.binary_path, "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(output_wav)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0

    def extract_frame(self, video_path: str, timestamp_sec: float, output_img: str) -> bool:
        """Extrai um frame estático no timestamp indicado para análise de cena ou thumbnail."""
        if not self.available:
            raise RuntimeError("FFmpeg não está disponível no sistema.")
        
        cmd = [
            self.binary_path, "-y",
            "-ss", str(timestamp_sec),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_img)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0

    def generate_canvas_short(
        self,
        audio_path: str,
        output_path: str,
        bg_color: str = "0x001E0A",
        ass_subtitles_path: Optional[str] = None,
        channel_variant: int = 1,
        duration_sec: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Gera um vídeo vertical 9:16 (1080x1920) a 30fps a partir de áudio de narração e legendas,
        utilizando cor de fundo da marca do canal e normalização de áudio EBU R128.
        """
        if not self.available:
            return {"success": False, "error": "FFmpeg não disponível"}

        audio_info = self.probe_media(audio_path)
        total_audio_dur = audio_info.get("duration_sec", 10.0)
        duration = duration_sec or total_audio_dur
        if duration <= 0:
            duration = 10.0

        # Normaliza formato da cor para o filtro lavfi (ex: #001E0A -> 0x001E0A)
        clean_color = bg_color.replace("#", "0x")
        if not clean_color.startswith("0x"):
            clean_color = f"0x{clean_color}"

        v_filters = []
        if channel_variant > 1:
            v_filters.append("noise=alls=5:allf=t+u")

        if ass_subtitles_path and os.path.exists(ass_subtitles_path):
            escaped_sub = str(ass_subtitles_path).replace("\\", "/").replace(":", "\\:")
            v_filters.append(f"subtitles='{escaped_sub}'")

        if v_filters:
            filter_chain = f"[0:v]{','.join(v_filters)}[v]"
        else:
            filter_chain = "[0:v]null[v]"

        a_filter = "loudnorm=I=-14:LRA=7:tp=-1.5"
        if channel_variant > 1:
            a_filter += ",atempo=1.008"

        cmd = [
            self.binary_path, "-y",
            "-f", "lavfi", "-i", f"color=c={clean_color}:s=1080x1920:r=30:d={duration}",
            "-i", str(audio_path),
            "-filter_complex", filter_chain,
            "-map", "[v]",
            "-map", "1:a",
            "-filter:a", a_filter,
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path)
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                return {
                    "success": True,
                    "output_path": str(output_path),
                    "duration_sec": duration,
                    "size_mb": round(size_mb, 2),
                    "resolution": "1080x1920 (9:16)",
                    "variant": channel_variant
                }
            else:
                return {
                    "success": False,
                    "error": res.stderr[-500:] if res.stderr else "Erro desconhecido na renderização"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def render_vertical_short(
        self,
        input_video: str,
        output_path: str,
        start_sec: float = 0.0,
        end_sec: Optional[float] = None,
        ass_subtitles_path: Optional[str] = None,
        narration_audio_path: Optional[str] = None,
        crop_offset_x: Optional[str] = None,
        channel_variant: int = 1,
        normalize_audio: bool = True
    ) -> Dict[str, Any]:
        """
        Renderiza corte ou short vertical (1080x1920, 9:16),
        queima legendas ASS e aplica normalização EBU R128 (-14 LUFS).
        Se narration_audio_path for fornecido, utiliza a locução gerada.
        """
        if not self.available:
            return {"success": False, "error": "FFmpeg não disponível"}

        if not os.path.exists(input_video):
            # Se não há vídeo de entrada, mas há narração de áudio, renderiza canvas nativo
            if narration_audio_path and os.path.exists(narration_audio_path):
                return self.generate_canvas_short(
                    audio_path=narration_audio_path,
                    output_path=output_path,
                    ass_subtitles_path=ass_subtitles_path,
                    channel_variant=channel_variant
                )
            return {"success": False, "error": f"Arquivo de vídeo de entrada não encontrado: {input_video}"}

        v_info = self.probe_media(input_video)
        total_vid_dur = v_info.get("duration_sec", 60.0)
        end_sec = end_sec or total_vid_dur
        duration = max(1.0, end_sec - start_sec)
        offset_x = crop_offset_x or "(iw-ow)/2"

        # Constrói o filter_complex de vídeo
        filters = [
            f"[0:v]crop=ih*(9/16):ih:{offset_x}:0,scale=1080:1920"
        ]

        # Variante de canal (anti-duplicação)
        if channel_variant > 1:
            filters.append("eq=contrast=1.03:saturation=1.04:brightness=0.01")

        # Queima de legenda ASS
        if ass_subtitles_path and os.path.exists(ass_subtitles_path):
            escaped_sub = str(ass_subtitles_path).replace("\\", "/").replace(":", "\\:")
            filters.append(f"subtitles='{escaped_sub}'")

        v_filter_chain = ",".join(filters) + "[v]"

        # Áudio: normalização de loudness broadcast (-14 LUFS)
        a_filter = "loudnorm=I=-14:LRA=7:tp=-1.5"
        if channel_variant > 1:
            a_filter += ",atempo=1.008"

        inputs = [
            "-ss", str(start_sec),
            "-to", str(end_sec),
            "-i", str(input_video)
        ]

        if narration_audio_path and os.path.exists(narration_audio_path):
            inputs.extend(["-i", str(narration_audio_path)])
            audio_map = "1:a"
        else:
            audio_map = "0:a"

        cmd = [
            self.binary_path, "-y",
            *inputs,
            "-filter_complex", v_filter_chain,
            "-map", "[v]",
            "-map", audio_map,
            "-filter:a", a_filter,
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path)
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                return {
                    "success": True,
                    "output_path": str(output_path),
                    "duration_sec": duration,
                    "size_mb": round(size_mb, 2),
                    "resolution": "1080x1920 (9:16)",
                    "variant": channel_variant
                }
            else:
                return {
                    "success": False,
                    "error": res.stderr[-500:] if res.stderr else "Erro desconhecido na renderização"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def render_short(
        self,
        input_video: str,
        output_video: str,
        subtitles_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        start_sec: float = 0.0,
        end_sec: Optional[float] = None,
        target_resolution: str = "1080x1920",
        fps: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """Alias de compatibilidade para render_vertical_short."""
        return self.render_vertical_short(
            input_video=input_video,
            output_path=output_video,
            start_sec=start_sec,
            end_sec=end_sec,
            ass_subtitles_path=subtitles_path,
            narration_audio_path=audio_path,
            **kwargs
        )
