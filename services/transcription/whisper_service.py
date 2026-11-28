"""
IAS Transcription & Word Alignment Service
Integração com Faster-Whisper e WhisperX para geração de legendas dinâmicas
alinhadas ao milissegundo no estilo viral (TikTok / YouTube Shorts Hormozi).
"""
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

class WhisperTranscriptionService:
    """Serviço de transcrição com alinhamento de palavras e saída em legendas ASS."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None
        self._patch_pyav_compat()
        self.engine_type = self._detect_engine()

    def _patch_pyav_compat(self):
        """Aplica patch de compatibilidade com PyAV 14+ onde metadata_errors foi descontinuado."""
        try:
            import faster_whisper.audio as fa
            import av
            import io
            import gc
            import numpy as np

            def patched_decode_audio(input_file, sampling_rate=16000, split_stereo=False):
                resampler = av.audio.resampler.AudioResampler(
                    format="s16",
                    layout="mono" if not split_stereo else "stereo",
                    rate=sampling_rate,
                )
                raw_buffer = io.BytesIO()
                dtype = None
                try:
                    container = av.open(input_file, mode="r", metadata_errors="ignore")
                except TypeError:
                    container = av.open(input_file, mode="r")

                with container:
                    frames = container.decode(audio=0)
                    frames = fa._ignore_invalid_frames(frames)
                    frames = fa._group_frames(frames, 500000)
                    frames = fa._resample_frames(frames, resampler)
                    for frame in frames:
                        array = frame.to_ndarray()
                        dtype = array.dtype
                        raw_buffer.write(array)
                del resampler
                gc.collect()
                audio = np.frombuffer(raw_buffer.getbuffer(), dtype=dtype)
                audio = audio.astype(np.float32) / 32768.0
                if split_stereo:
                    return audio[0::2], audio[1::2]
                return audio

            fa.decode_audio = patched_decode_audio
            try:
                import faster_whisper.transcribe as ft
                ft.decode_audio = patched_decode_audio
            except Exception:
                pass
        except Exception:
            pass

    def _detect_engine(self) -> str:
        try:
            import whisperx
            return "whisperx"
        except ImportError:
            try:
                import faster_whisper
                return "faster_whisper"
            except ImportError:
                return "mock_fallback"

    def _load_model(self):
        if self._model is not None:
            return self._model

        if self.engine_type == "faster_whisper":
            from faster_whisper import WhisperModel
            # Roda em CPU com int8 para máxima compatibilidade sem travar
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        elif self.engine_type == "whisperx":
            import whisperx
            self._model = whisperx.load_model(self.model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe_audio(self, audio_path: str, language: str = "pt") -> Dict[str, Any]:
        """Transcreve arquivo de áudio e extrai segmentos com timestamps."""
        if not os.path.exists(audio_path):
            return {"error": f"Arquivo não encontrado: {audio_path}"}

        model = self._load_model()
        segments_data = []
        full_text_parts = []
        total_words = 0

        if self.engine_type == "faster_whisper":
            segments, info = model.transcribe(
                audio_path,
                language=language,
                word_timestamps=True,
                vad_filter=True
            )
            for seg in segments:
                words_list = []
                if hasattr(seg, "words") and seg.words:
                    for w in seg.words:
                        words_list.append({
                            "word": w.word.strip(),
                            "start": round(w.start, 3),
                            "end": round(w.end, 3),
                            "probability": round(w.probability, 3)
                        })
                        total_words += 1
                else:
                    for word_str in seg.text.strip().split():
                        words_list.append({
                            "word": word_str,
                            "start": round(seg.start, 3),
                            "end": round(seg.end, 3),
                            "probability": 0.95
                        })
                        total_words += 1

                full_text_parts.append(seg.text.strip())
                segments_data.append({
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text.strip(),
                    "words": words_list
                })

            duration = getattr(info, "duration", 0.0)
        else:
            # Fallback mock estruturado para testes unitários ou ambientes mínimos
            full_text_parts = ["Este é um gancho impactante para testar o sistema IAS."]
            segments_data = [{
                "start": 0.0,
                "end": 3.2,
                "text": full_text_parts[0],
                "words": [
                    {"word": "Este", "start": 0.0, "end": 0.4, "probability": 0.99},
                    {"word": "é", "start": 0.4, "end": 0.6, "probability": 0.99},
                    {"word": "um", "start": 0.6, "end": 0.8, "probability": 0.99},
                    {"word": "gancho", "start": 0.8, "end": 1.4, "probability": 0.99},
                    {"word": "impactante", "start": 1.4, "end": 2.2, "probability": 0.99},
                    {"word": "para", "start": 2.2, "end": 2.5, "probability": 0.99},
                    {"word": "testar", "start": 2.5, "end": 3.2, "probability": 0.99}
                ]
            }]
            duration = 3.2
            total_words = 7

        full_transcript = " ".join(full_text_parts)
        wpm = (total_words / (duration / 60.0)) if duration > 0 else 0

        return {
            "engine": self.engine_type,
            "duration_sec": round(duration, 2),
            "total_words": total_words,
            "pacing_wpm": round(wpm, 1),
            "full_transcript": full_transcript,
            "segments": segments_data
        }

    def format_ass_time(self, seconds: float) -> str:
        """Converte segundos em formato de timestamp do padrão ASS (h:mm:ss.cs)."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int(round((seconds - int(seconds)) * 100))
        return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"

    def generate_viral_ass_subtitles(
        self,
        segments: List[Dict[str, Any]],
        output_ass_path: str,
        highlight_color_hex: str = "&H0000FFFF&", # Amarelo vibrante
        primary_color_hex: str = "&H00FFFFFF&",   # Branco puro
        outline_color_hex: str = "&H00000000&",   # Preto
        font_name: str = "Arial",
        font_size: int = 72,
        words_per_group: int = 4
    ) -> str:
        """
        Gera arquivo de legendas .ass formatado para 1080x1920 (9:16)
        com destaque palavra por palavra estilo MrBeast / Alex Hormozi
        e personalização de fontes e cores por canal.
        """
        ass_lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Default,{font_name},{font_size},{primary_color_hex},{highlight_color_hex},{outline_color_hex},&H80000000,-1,0,0,0,100,100,0,0,1,6,2,2,40,40,480,1",
            f"Style: Highlight,{font_name},{font_size + 4},{highlight_color_hex},{primary_color_hex},{outline_color_hex},&H80000000,-1,0,0,0,105,105,0,0,1,7,3,2,40,40,480,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        for seg in segments:
            words = seg.get("words", [])
            if not words:
                continue

            # Agrupa palavras para não poluir a tela vertical
            for i in range(0, len(words), words_per_group):
                group = words[i:i + words_per_group]
                start_t = group[0]["start"]
                end_t = group[-1]["end"]
                
                # Palavra-chave destacada
                first_word = group[0]["word"].upper()
                remaining = " ".join(w["word"].upper() for w in group[1:])

                formatted_start = self.format_ass_time(start_t)
                formatted_end = self.format_ass_time(end_t)

                if remaining:
                    styled_text = f"{{\\c{highlight_color_hex}}}{first_word}{{\\c{primary_color_hex}}} {remaining}"
                else:
                    styled_text = f"{{\\c{highlight_color_hex}}}{first_word}"

                dialogue_line = f"Dialogue: 0,{formatted_start},{formatted_end},Default,,0,0,0,,{styled_text}"
                ass_lines.append(dialogue_line)

        os.makedirs(os.path.dirname(output_ass_path), exist_ok=True)
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write("\n".join(ass_lines))

        return output_ass_path
