"""
IAS Subtitle Generator (services/media_processing/subtitle_generator.py)
Gerador de legendas avançadas em formato ASS (Advanced SubStation Alpha)
otimizadas para YouTube Shorts (1080x1920, 9:16) com tipografia, cores e ritmo dinâmico por canal.
"""
import os
import re
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from core.channel_manager import ChannelManager

logger = logging.getLogger("SubtitleGenerator")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WORKSPACE_SUBS = BASE_DIR / "workspace" / "subs"

# Estilos padrão de legenda por canal caso não haja override no banco
DEFAULT_CHANNEL_SUB_STYLES = {
    1: {"font": "Arial Black", "fontsize": 76, "primary_colour": "&H0000FFFF&", "outline_colour": "&H00000000&", "bold": 1, "outline": 4, "margin_v": 380},
    2: {"font": "Consolas", "fontsize": 70, "primary_colour": "&H00FFFF00&", "outline_colour": "&H00000000&", "bold": 1, "outline": 3, "margin_v": 400},
    3: {"font": "Impact", "fontsize": 80, "primary_colour": "&H0000FF00&", "outline_colour": "&H00000000&", "bold": 1, "outline": 4, "margin_v": 380},
    4: {"font": "Trebuchet MS", "fontsize": 72, "primary_colour": "&H00FFFFFF&", "outline_colour": "&H00000000&", "bold": 1, "outline": 3, "margin_v": 400},
    5: {"font": "Montserrat", "fontsize": 74, "primary_colour": "&H00E0E0E0&", "outline_colour": "&H00000000&", "bold": 1, "outline": 3, "margin_v": 420},
}
FALLBACK_STYLE = {"font": "Arial Black", "fontsize": 76, "primary_colour": "&H0000FFFF&", "outline_colour": "&H00000000&", "bold": 1, "outline": 4, "margin_v": 380}


class SubtitleGenerator:
    """Gerador e estilizador de legendas ASS dinâmicas para Shorts verticais."""

    def __init__(self, output_dir: Optional[Union[str, Path]] = None, channel_manager: Optional[ChannelManager] = None):
        self.output_dir = Path(output_dir or WORKSPACE_SUBS)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.channel_manager = channel_manager or ChannelManager()

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """Converte segundos para formato de timestamp ASS: H:MM:SS.cc"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"

    def get_channel_style(self, channel_id: Any) -> Dict[str, Any]:
        """Obtém configuração visual de legenda do canal."""
        try:
            settings = self.channel_manager.get_channel_settings(channel_id)
            if settings and "subtitle_style" in settings:
                st = settings["subtitle_style"]
                return {
                    "font": st.get("font", FALLBACK_STYLE["font"]),
                    "fontsize": st.get("fontsize", FALLBACK_STYLE["fontsize"]),
                    "primary_colour": st.get("primary_colour", FALLBACK_STYLE["primary_colour"]),
                    "outline_colour": st.get("outline_colour", FALLBACK_STYLE["outline_colour"]),
                    "bold": st.get("bold", 1),
                    "outline": st.get("outline", 4),
                    "margin_v": st.get("margin_v", 380)
                }
        except Exception as e:
            logger.warning(f"Erro ao obter estilo de legenda do canal {channel_id}: {e}")

        ch_num = 1
        if isinstance(channel_id, int):
            ch_num = channel_id
        elif isinstance(channel_id, str):
            m = re.search(r'\d+', channel_id)
            if m:
                ch_num = int(m.group(0))

        return DEFAULT_CHANNEL_SUB_STYLES.get(ch_num, FALLBACK_STYLE)

    def _split_into_phrases(self, text: str, start_sec: float, end_sec: float, max_words: int = 4) -> List[Dict[str, Any]]:
        """Divide uma sentença em blocos curtos (2-4 palavras) de alto dinamismo para Shorts."""
        words = text.strip().split()
        if not words:
            return []
        if len(words) <= max_words:
            return [{"text": text.strip().upper(), "start": start_sec, "end": end_sec}]

        total_duration = max(0.2, end_sec - start_sec)
        time_per_word = total_duration / len(words)
        phrases = []
        cur_start = start_sec

        for i in range(0, len(words), max_words):
            chunk = words[i:i + max_words]
            chunk_dur = len(chunk) * time_per_word
            chunk_end = min(end_sec, cur_start + chunk_dur)
            phrases.append({
                "text": " ".join(chunk).upper(),
                "start": round(cur_start, 2),
                "end": round(chunk_end, 2)
            })
            cur_start = chunk_end

        return phrases

    def generate_ass(
        self,
        cues: Optional[List[Dict[str, Any]]] = None,
        channel_id: Any = 1,
        task_id: Optional[str] = None,
        max_words_per_cue: int = 4,
        segments: Optional[List[Dict[str, Any]]] = None,
        output_file: Optional[Union[str, Path]] = None,
        font_name: Optional[str] = None,
        font_size: Optional[int] = None,
        primary_color: Optional[str] = None,
        highlight_color: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera arquivo de legenda .ass com PlayResX=1080 e PlayResY=1920 (9:16).
        Cada cue/segment deve conter 'text', 'start'/'start_sec', 'end'/'end_sec'.
        """
        raw_cues = cues or segments or []
        task_id = task_id or f"sub_{uuid.uuid4().hex[:10]}"
        final_output_file = Path(output_file) if output_file else self.output_dir / f"{task_id}.ass"
        style = dict(self.get_channel_style(channel_id))

        if font_name:
            style["font"] = font_name
        if font_size:
            style["fontsize"] = font_size
        if primary_color:
            style["primary_colour"] = primary_color

        # Cabeçalho ASS para resolução vertical Shorts 1080x1920
        header = f"""[Script Info]
; IAS Automated Content Engine - Styled Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['font']},{style['fontsize']},{style['primary_colour']},&H000000FF,{style['outline_colour']},&H80000000,{style['bold']},0,0,0,100,100,0,0,1,{style['outline']},2,2,40,40,{style['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        dialogue_lines = []
        total_cues_generated = 0

        for cue in raw_cues:
            text = cue.get("text", "").strip()
            if not text:
                continue
            start_s = float(cue.get("start", cue.get("start_sec", 0.0)))
            end_s = float(cue.get("end", cue.get("end_sec", start_s + 2.0)))

            # Quebra em frases dinâmicas para Shorts
            sub_chunks = self._split_into_phrases(text, start_s, end_s, max_words=max_words_per_cue)
            for sc in sub_chunks:
                t_start = self.format_timestamp(sc["start"])
                t_end = self.format_timestamp(sc["end"])
                # Escapa chaves e barras do formato ASS
                safe_text = sc["text"].replace("{", "\\{").replace("}", "\\}")
                dialogue_lines.append(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{safe_text}")
                total_cues_generated += 1

        full_content = header + "\n".join(dialogue_lines) + "\n"
        with open(final_output_file, "w", encoding="utf-8") as f:
            f.write(full_content)

        return {
            "success": True,
            "ass_path": str(final_output_file.resolve()),
            "task_id": task_id,
            "channel_id": channel_id,
            "style_applied": style,
            "total_cues": total_cues_generated
        }
