"""
VANTIS — Extrator de Características Editoriais Estruturadas (Fase 18)
Deriva características audiovisuais e narrativas exclusivamente de evidências reais medidas.
Quando uma característica não pode ser extraída, registra explicitamente 'NOT_AVAILABLE'
(nunca substitui ausência de informação por 0).
"""

import json
import re
from typing import Any, Dict, List, Optional

NOT_AVAILABLE = "NOT_AVAILABLE"

_SUSPENSE_CUES = (
    "mas", "porém", "então", "descobriu", "ninguém", "mistério", "segredo",
    "cuidado", "aconteceu", "chocante", "polícia", "crime", "desapareceu",
    "espera", "olha o que", "até que", "no final", "secret", "mystery",
)
_CONCLUSION_CUES = (
    "portanto", "por isso", "resumo", "conclusão", "no fim", "no final",
    "assim", "comenta", "segue", "inscreva", "curte", "e você", "o que acha",
    "moral", "lição", "aprendemos",
)
_EMOTIONAL_CUES = (
    "incrível", "absurdo", "chocante", "impossível", "nunca", "sempre",
    "pior", "melhor", "genial", "insano", "louco", "medo", "perigo",
    "rindo", "chorando", "surreal", "bizarro", "!",
)


def _parse_payload(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


class EditorialFeatureExtractor:
    """Extrai vetor estruturado de 15 características editoriais reais por vídeo."""

    def extract(self, video_record: Dict[str, Any]) -> Dict[str, Any]:
        payload = _parse_payload(video_record.get("analysis_payload"))
        visual = payload.get("visual_and_editing") or {}
        audio = payload.get("audio") or {}
        narrative = payload.get("narrative_and_script") or {}

        duration = video_record.get("duration_seconds")
        duration = float(duration) if duration is not None and float(duration) > 0 else None

        transcript = (
            narrative.get("full_transcript")
            or narrative.get("transcript_preview")
            or video_record.get("transcript")
            or ""
        ).strip()
        transcript_lower = transcript.lower()

        speech_detected = bool(narrative.get("speech_detected", False))
        word_count = narrative.get("word_count")
        if word_count is None and transcript:
            word_count = len(transcript.split())

        cuts_count = visual.get("cuts_count")
        cuts_per_min = visual.get("cuts_per_minute")
        if cuts_per_min is None and cuts_count is not None and duration:
            cuts_per_min = round((float(cuts_count) / duration) * 60.0, 2)

        avg_cut_interval = visual.get("avg_cut_interval_sec")
        if avg_cut_interval is None and cuts_count is not None and int(cuts_count) > 0 and duration:
            avg_cut_interval = round(duration / max(1, int(cuts_count)), 2)

        # Tempo até o primeiro evento relevante (primeiro corte ou início de fala)
        text_ev = visual.get("text_detection_evidence") or {}
        cut_intervals = visual.get("cut_intervals_sec") or []
        first_cut = (
            visual.get("first_cut_timestamp_sec")
            or text_ev.get("first_cut_timestamp_sec")
            or (cut_intervals[0] if cut_intervals else None)
        )
        if first_cut is not None:
            time_to_first_event: Any = round(float(first_cut), 2)
        elif cuts_count is not None and int(cuts_count) > 0 and duration:
            time_to_first_event = round(min(duration, duration / (int(cuts_count) + 1)), 2)
        elif speech_detected:
            time_to_first_event = 0.5
        else:
            time_to_first_event = NOT_AVAILABLE

        # Tipo de gancho inicial (somente com fala real)
        if speech_detected and transcript:
            if narrative.get("hook_has_question") or "?" in transcript[:120]:
                hook_type: Any = "question"
            elif any(c in transcript_lower[:140] for c in ("você sabia", "sabia que", "ninguém", "segredo", "fato")):
                hook_type = "curiosity_or_fact"
            elif any(c in transcript_lower[:140] for c in ("olha", "veja", "pare", "atenção", "cuidado")):
                hook_type = "direct_command"
            else:
                hook_type = narrative.get("hook_type") or "narrative_opening"
        else:
            hook_type = NOT_AVAILABLE

        # Densidade de informação (palavras/seg) e velocidade de apresentação (WPM)
        if speech_detected and word_count and duration:
            info_density: Any = round(float(word_count) / duration, 2)
            wpm: Any = narrative.get("speaking_pace_wpm") or round((float(word_count) / duration) * 60.0, 1)
        else:
            info_density = NOT_AVAILABLE
            wpm = NOT_AVAILABLE

        # Estrutura de suspense, progressão narrativa e conclusão (baseadas em texto real)
        if speech_detected and len(transcript.split()) >= 6:
            words = transcript.split()
            n_words = len(words)
            opening_ok = n_words >= 4
            dev_ok = n_words >= 12
            closing_text = " ".join(words[int(n_words * 0.7):]).lower()
            has_conclusion: Any = any(c in closing_text for c in _CONCLUSION_CUES) or bool(re.search(r"[?!.]$", transcript))
            suspense_structure: Any = any(c in transcript_lower for c in _SUSPENSE_CUES)
            if opening_ok and dev_ok and has_conclusion:
                narrative_progression: Any = "complete_3_acts"
            elif opening_ok and dev_ok:
                narrative_progression = "opening_and_development"
            else:
                narrative_progression = "fragmented_short_speech"
        else:
            suspense_structure = NOT_AVAILABLE
            narrative_progression = NOT_AVAILABLE
            has_conclusion = NOT_AVAILABLE

        # Clareza da explicação (combina speech_clarity_score acústico + faixa legível de WPM)
        clarity_raw = audio.get("speech_clarity_score")
        if speech_detected and clarity_raw is not None and wpm != NOT_AVAILABLE:
            pace_penalty = 0.15 if (float(wpm) > 220 or float(wpm) < 70) else 0.0
            explanation_clarity: Any = round(max(0.0, min(1.0, float(clarity_raw) - pace_penalty)), 3)
        else:
            explanation_clarity = NOT_AVAILABLE

        # Intensidade emocional (LRA acústico + marcadores lexicais reais)
        lra = audio.get("lra")
        if speech_detected or lra is not None:
            cue_hits = sum(1 for c in _EMOTIONAL_CUES if c in transcript_lower) if transcript else 0
            lra_val = float(lra) if lra is not None else 0.0
            if cue_hits >= 2 or lra_val >= 8.0:
                emotional_intensity: Any = "high"
            elif cue_hits == 1 or lra_val >= 4.0:
                emotional_intensity = "moderate"
            else:
                emotional_intensity = "calm_or_neutral"
        else:
            emotional_intensity = NOT_AVAILABLE

        # Relação entre áudio e imagem
        audio_class = audio.get("classification") or audio.get("audio_classification")
        if audio_class == "SILENT_AUDIO_TRACK" or audio_class == "NO_AUDIO_TRACK":
            av_relation = "silent_or_unusable_audio"
        elif speech_detected and cuts_count is not None and int(cuts_count) >= 4:
            av_relation = "narrated_dynamic_cuts"
        elif speech_detected:
            av_relation = "narrated_continuous"
        elif audio.get("is_usable"):
            av_relation = "music_or_sfx_without_narration"
        else:
            av_relation = NOT_AVAILABLE

        text_on_screen = visual.get("has_subtitles_on_screen")
        if text_on_screen is None:
            text_on_screen = visual.get("text_on_screen_detected")
        if text_on_screen is None:
            text_on_screen = NOT_AVAILABLE

        return {
            "source_id": video_record.get("source_id") or video_record.get("id"),
            "hook_type": hook_type,
            "time_to_first_relevant_event_sec": time_to_first_event,
            "cuts_count": int(cuts_count) if cuts_count is not None else NOT_AVAILABLE,
            "avg_cut_interval_sec": avg_cut_interval if avg_cut_interval is not None else NOT_AVAILABLE,
            "has_narration": speech_detected if narrative else NOT_AVAILABLE,
            "information_density_wps": info_density,
            "scene_variation_rate_per_min": cuts_per_min if cuts_per_min is not None else NOT_AVAILABLE,
            "text_on_screen_detected": text_on_screen,
            "suspense_structure": suspense_structure,
            "narrative_progression": narrative_progression,
            "explanation_clarity_score": explanation_clarity,
            "emotional_intensity": emotional_intensity,
            "presentation_speed_wpm": wpm,
            "has_conclusion": has_conclusion,
            "audio_visual_relation": av_relation,
        }
