"""
IAS TTS Narration Engine (services/media_processing/tts_engine.py)
Motor de síntese de voz neural gratuita (Edge-TTS) integrado aos perfis dos 20 canais.
Gera arquivos de áudio em formato MP3/WAV com mapeamento temporal de sentenças/palavras
para sincronização de legendas dinâmicas.
"""
import os
import sys
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from core.channel_manager import ChannelManager

logger = logging.getLogger("TTSNarrationEngine")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WORKSPACE_AUDIO = BASE_DIR / "workspace" / "audio"

# Vozes padrão mapeadas por canal piloto (somente vozes pt-BR ativas no Edge-TTS)
DEFAULT_CHANNEL_VOICES = {
    1: {"voice": "pt-BR-AntonioNeural", "rate": "+12%", "pitch": "+0Hz"},
    2: {"voice": "pt-BR-AntonioNeural", "rate": "-6%", "pitch": "-4Hz"},
    3: {"voice": "pt-BR-ThalitaMultilingualNeural", "rate": "+8%", "pitch": "+2Hz"},
    4: {"voice": "pt-BR-FranciscaNeural", "rate": "-2%", "pitch": "+0Hz"},
    5: {"voice": "pt-BR-AntonioNeural", "rate": "+4%", "pitch": "-2Hz"},
}
ACTIVE_PT_BR_VOICES = {
    "pt-BR-AntonioNeural",
    "pt-BR-FranciscaNeural",
    "pt-BR-ThalitaMultilingualNeural",
}
FALLBACK_VOICE = "pt-BR-AntonioNeural"


class TTSNarrationService:
    """Serviço de geração de locução neural de alta fidelidade e custo zero."""

    def __init__(self, output_dir: Optional[Union[str, Path]] = None, channel_manager: Optional[ChannelManager] = None):
        self.output_dir = Path(output_dir or WORKSPACE_AUDIO)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.channel_manager = channel_manager or ChannelManager()

    def get_channel_voice_config(self, channel_id: Any) -> Dict[str, str]:
        """Obtém configurações de voz a partir do ChannelManager ou fallback."""
        try:
            settings = self.channel_manager.get_channel_settings(channel_id)
            if settings and "voice_profile" in settings:
                vp = settings["voice_profile"]
                voice_id = vp.get("voice_id", FALLBACK_VOICE)
                if voice_id not in ACTIVE_PT_BR_VOICES:
                    voice_id = FALLBACK_VOICE
                return {
                    "voice": voice_id,
                    "rate": vp.get("rate", "+0%"),
                    "pitch": vp.get("pitch", "+0Hz")
                }
        except Exception as e:
            logger.warning(f"Erro ao buscar configurações do canal {channel_id}: {e}")

        # Fallback por número do canal se channel_id for numérico ou string 'canal_XX'
        ch_num = 1
        if isinstance(channel_id, int):
            ch_num = channel_id
        elif isinstance(channel_id, str):
            import re
            m = re.search(r'\d+', channel_id)
            if m:
                ch_num = int(m.group(0))

        return DEFAULT_CHANNEL_VOICES.get(ch_num, {"voice": FALLBACK_VOICE, "rate": "+0%", "pitch": "+0Hz"})

    async def _generate_edge_tts(
        self,
        text: str,
        voice: str,
        rate: str,
        pitch: str,
        output_file: Path
    ) -> List[Dict[str, Any]]:
        """Invoca edge-tts e captura áudio + SentenceBoundaries."""
        import edge_tts
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        boundaries = []

        with open(output_file, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    # offset e duration estão em unidades de 100ns (1s = 10,000,000 unidades)
                    start_sec = chunk["offset"] / 10_000_000.0
                    dur_sec = chunk["duration"] / 10_000_000.0
                    boundaries.append({
                        "text": chunk.get("text", "").strip(),
                        "start_sec": round(start_sec, 3),
                        "end_sec": round(start_sec + dur_sec, 3),
                        "duration_sec": round(dur_sec, 3)
                    })

        return boundaries

    def _generate_mock_audio(self, output_file: Path, text: str) -> List[Dict[str, Any]]:
        """Gera um arquivo de áudio WAV sintético quando offline para testes e resiliência."""
        import wave
        import math
        import struct

        words = text.split()
        estimated_duration = max(1.5, len(words) * 0.4)
        sample_rate = 16000
        num_samples = int(estimated_duration * sample_rate)

        # Gera tom suave de 440Hz com decaimento
        with wave.open(str(output_file), "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            raw_data = bytearray()
            for i in range(num_samples):
                val = int(3000 * math.sin(2 * math.pi * 440 * (i / sample_rate)))
                raw_data.extend(struct.pack("<h", val))
            wav.writeframes(raw_data)

        # Monta boundaries estimadas
        boundaries = []
        cur_time = 0.0
        chunk_size = 5
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            dur = max(0.6, len(chunk_words) * 0.35)
            boundaries.append({
                "text": chunk_text,
                "start_sec": round(cur_time, 3),
                "end_sec": round(cur_time + dur, 3),
                "duration_sec": round(dur, 3)
            })
            cur_time += dur

        return boundaries

    def generate_narration(
        self,
        text: str,
        channel_id: Any = 1,
        task_id: Optional[str] = None,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        force_offline: bool = False,
        output_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera a narração em áudio MP3 para o roteiro informado.
        Aplica a voz e entonação configuradas para o canal.
        """
        if not text or not text.strip():
            return {"success": False, "error": "Texto da narração não pode ser vazio"}

        task_id = task_id or f"tts_{uuid.uuid4().hex[:10]}"
        voice_cfg = self.get_channel_voice_config(channel_id)
        selected_voice = voice or voice_cfg.get("voice", FALLBACK_VOICE)
        selected_rate = rate or voice_cfg.get("rate", "+0%")
        selected_pitch = pitch or voice_cfg.get("pitch", "+0Hz")

        final_out_path = Path(output_path) if output_path else self.output_dir / f"{task_id}.mp3"
        output_path = final_out_path
        boundaries = []
        mode = "real_neural"

        if not force_offline:
            import time as _time
            last_err = None
            attempts = [
                (selected_voice, selected_rate, selected_pitch),
                (selected_voice, selected_rate, selected_pitch),
                (FALLBACK_VOICE, "+0%", "+0Hz"),
            ]
            for idx_att, (v_try, r_try, p_try) in enumerate(attempts):
                try:
                    boundaries = asyncio.run(self._generate_edge_tts(
                        text=text,
                        voice=v_try,
                        rate=r_try,
                        pitch=p_try,
                        output_file=output_path
                    ))
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    if idx_att < len(attempts) - 1:
                        _time.sleep(0.8)
            if last_err is not None:
                logger.warning(f"Edge-TTS falhou ({last_err}). Recorrendo ao gerador sintético de resiliência.")
                mode = "mock_fallback"
                wav_path = self.output_dir / f"{task_id}.wav"
                boundaries = self._generate_mock_audio(wav_path, text)
                output_path = wav_path
        else:
            mode = "mock_fallback"
            wav_path = self.output_dir / f"{task_id}.wav"
            boundaries = self._generate_mock_audio(wav_path, text)
            output_path = wav_path

        # Mede duração e tamanho
        size_bytes = os.path.getsize(output_path) if output_path.exists() else 0
        total_duration = boundaries[-1]["end_sec"] if boundaries else 0.0

        return {
            "success": True,
            "audio_path": str(output_path.resolve()),
            "task_id": task_id,
            "channel_id": channel_id,
            "voice_id": selected_voice,
            "rate": selected_rate,
            "pitch": selected_pitch,
            "duration_sec": total_duration,
            "size_bytes": size_bytes,
            "boundaries": boundaries,
            "mode": mode
        }

    async def list_available_voices(self, language_prefix: str = "pt-BR") -> List[Dict[str, str]]:
        """Lista todas as vozes neurais disponíveis para o idioma selecionado."""
        try:
            import edge_tts
            all_voices = await edge_tts.list_voices()
            filtered = [
                {
                    "name": v["ShortName"],
                    "gender": v["Gender"],
                    "locale": v["Locale"],
                    "friendly_name": v.get("FriendlyName", v["ShortName"])
                }
                for v in all_voices
                if v.get("Locale", "").startswith(language_prefix)
            ]
            return filtered
        except Exception as e:
            logger.error(f"Erro ao listar vozes: {e}")
            return [
                {"name": "pt-BR-AntonioNeural", "gender": "Male", "locale": "pt-BR", "friendly_name": "Antonio (Dinâmico)"},
                {"name": "pt-BR-JulioNeural", "gender": "Male", "locale": "pt-BR", "friendly_name": "Julio (Investigativo)"},
                {"name": "pt-BR-FabioNeural", "gender": "Male", "locale": "pt-BR", "friendly_name": "Fabio (Expressivo)"},
                {"name": "pt-BR-FranciscaNeural", "gender": "Female", "locale": "pt-BR", "friendly_name": "Francisca (Didática)"},
                {"name": "pt-BR-ValerioNeural", "gender": "Male", "locale": "pt-BR", "friendly_name": "Valerio (Autoritário)"},
            ]
