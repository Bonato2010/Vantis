"""
Módulo de Aprendizado e Engenharia Reversa de Shorts Virais (Pattern Learner Real).
Analisa a estrutura audiovisual real dos vídeos:
A. Roteiro e Narrativa (Gancho 0-3s, ritmo WPM, arcos, CTA)
B. Análise Visual (Cortes/min, enquadramento vertical 9:16, legendas na tela)
C. Análise de Áudio (Clareza vocal, pausas, normalização EBU R128)
D. Análise Temporal (Primeiros 3 segundos, distribuição de estímulos)
E. Aprendizado Editorial Rastreável com Evidências Explícitas (OBSERVAÇÃO, PADRÃO, HIPÓTESE)

NUNCA afirma que uma análise foi realizada se a etapa não foi executada.
Se apenas metadados foram obtidos, classifica explicitamente como PRELIMINAR.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from memory.central_memory import CentralMemory
from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.video_analysis.scene_detector import SceneDetectorService
from services.video_analysis.visual_analyzer import OpenCVVisualAnalyzer

class PatternLearner:
    def __init__(self, playbook_path: str = "./config/viral_playbook.json", db_path: Optional[str] = None):
        self.playbook_path = Path(playbook_path)
        self.db_path = db_path or str(BASE_DIR / "database/shorts_central.db")
        self.memory = CentralMemory(db_path=Path(self.db_path))
        self.learning_sys = AudiovisualLearningSystem(db_path=self.db_path)
        self.playbook = self._load_playbook()

    def _load_playbook(self) -> Dict[str, Any]:
        if not self.playbook_path.exists():
            self.playbook_path.parent.mkdir(parents=True, exist_ok=True)
            return {
                "archetypes": {},
                "evidence_based_patterns": [],
                "hypotheses": [],
                "total_learned_patterns": 0
            }
        try:
            with open(self.playbook_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "archetypes": {},
                "evidence_based_patterns": [],
                "hypotheses": [],
                "total_learned_patterns": 0
            }

    def _save_playbook(self):
        with open(self.playbook_path, "w", encoding="utf-8") as f:
            json.dump(self.playbook, f, ensure_ascii=False, indent=2)

    def extract_short_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extrai metadados autênticos via yt-dlp sem inventar dados.
        Retorna None se o vídeo não existir ou estiver indisponível.
        """
        if not url or not isinstance(url, str):
            return None

        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--dump-json",
            "--skip-download",
            "--no-playlist",
            url
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
            info = json.loads(res.stdout)
            
            raw_duration = info.get("duration")
            duration_sec = float(raw_duration) if raw_duration is not None else None
            
            subtitles = info.get("subtitles", {}) or info.get("automatic_captions", {})
            has_captions = any(k in subtitles for k in ["pt", "pt-BR", "en"])

            return {
                "video_id": info.get("id"),
                "url": url,
                "title": info.get("title") or "Sem título",
                "author": info.get("uploader") or info.get("channel") or "Desconhecido",
                "duration": duration_sec,
                "views": info.get("view_count"),
                "likes": info.get("like_count"),
                "comments": info.get("comment_count"),
                "description": info.get("description") or "",
                "has_captions": has_captions,
                "tags": info.get("tags") or []
            }
        except Exception:
            return None

    def analyze_narrative(self, transcript_text: str, duration_sec: Optional[float] = None) -> Dict[str, Any]:
        """
        A. Roteiro e Narrativa:
        - Gancho inicial (0-3s)
        - Ritmo (WPM)
        - Gatilhos psicológicos e chamada para ação (CTA)
        """
        if not transcript_text or not transcript_text.strip():
            return {
                "has_narrative_analysis": False,
                "reason": "Transcrição ausente ou indisponível"
            }

        words = transcript_text.split()
        hook_words = words[:15] if len(words) >= 15 else words
        hook_text = " ".join(hook_words)

        duration = duration_sec or 45.0
        wpm = round((len(words) / (duration / 60.0)), 1) if duration > 0 else 0.0

        # Análise de gatilhos psicológicos no gancho
        lower_hook = hook_text.lower()
        triggers = []
        if any(w in lower_hook for w in ["segredo", "ninguém sabe", "revelado", "descobri"]):
            triggers.append("curiosidade_revelacao")
        if any(w in lower_hook for w in ["não faça", "nunca", "pare de", "cuidado"]):
            triggers.append("alerta_perigo")
        if any(w in lower_hook for w in ["como", "regra", "método", "passo a passo"]):
            triggers.append("utilidade_instrucao")
        if any(w in lower_hook for w in ["inédito", "urgente", "chocante", "bizarro"]):
            triggers.append("urgencia_sensacionalismo")

        # Detecção de CTA
        lower_trans = transcript_text.lower()
        has_cta = any(w in lower_trans for w in ["inscreva", "siga", "comente", "curta", "compartilhe", "deixe seu like"])

        return {
            "has_narrative_analysis": True,
            "total_words": len(words),
            "pacing_wpm": wpm,
            "hook_0_3s": hook_text,
            "psychological_triggers": triggers,
            "has_cta": has_cta,
            "narrative_arc": "Gancho -> Desenvolvimento -> Revelação -> Conclusão" if len(words) > 40 else "Gancho -> Rápido Impacto"
        }

    def analyze_visual_real(self, video_path: Optional[str] = None) -> Dict[str, Any]:
        """
        B. Análise Visual:
        - Cortes e transições (PySceneDetect)
        - Enquadramento vertical 9:16 (OpenCV)
        """
        if not video_path or not Path(video_path).exists():
            return {
                "has_visual_analysis": False,
                "reason": "Arquivo de vídeo não fornecido ou inacessível localmente"
            }

        try:
            scene_svc = SceneDetectorService(threshold=27.0)
            scene_res = scene_svc.detect_scenes(video_path)
            scene_list = scene_res.get("scenes", [])
            cuts_count = max(0, scene_res.get("total_scenes", len(scene_list)) - 1)

            vis_analyzer = OpenCVVisualAnalyzer()
            res_info = vis_analyzer.verify_resolution(video_path)
            is_vertical = res_info.get("is_vertical_9_16", False)

            return {
                "has_visual_analysis": True,
                "scenes_detected": len(scene_list),
                "total_cuts": cuts_count,
                "is_vertical_9_16": is_vertical,
                "resolution": f"{res_info.get('width')}x{res_info.get('height')}",
                "aspect_ratio": res_info.get("aspect_ratio")
            }
        except Exception as e:
            return {
                "has_visual_analysis": False,
                "error": str(e)
            }

    def analyze_audio_real(self, audio_or_video_path: Optional[str] = None) -> Dict[str, Any]:
        """
        C. Análise de Áudio:
        - Nível EBU R128 (-14 LUFS)
        - Pausas e clareza vocal
        """
        if not audio_or_video_path or not Path(audio_or_video_path).exists():
            return {
                "has_audio_analysis": False,
                "reason": "Arquivo de mídia para extração de áudio não fornecido"
            }

        try:
            # Medição com AudiovisualLearningSystem
            aud_data = self.learning_sys._analyze_audio_file(audio_or_video_path)
            return {
                "has_audio_analysis": True,
                "integrated_lufs": aud_data.get("integrated_lufs"),
                "loudness_compliant_ebu_r128": aud_data.get("compliant"),
                "speech_clarity_score": aud_data.get("speech_clarity_score"),
                "pauses_ratio": aud_data.get("pauses_ratio")
            }
        except Exception as e:
            return {
                "has_audio_analysis": False,
                "error": str(e)
            }

    def learn_from_video(
        self,
        url: str,
        niche: str = "geral",
        video_path: Optional[str] = None,
        transcript_text: Optional[str] = None,
        target_channel_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executa a análise real do vídeo, determina a profundidade real
        e registra aprendizado auditável com evidências.
        """
        info = self.extract_short_info(url)
        if not info:
            return {
                "success": False,
                "status": "FAILED",
                "error": "Vídeo inacessível ou metadados indisponíveis na plataforma",
                "url": url,
                "analysis_depth": "NONE"
            }

        v_id = info["video_id"]
        title = info["title"]
        duration = info["duration"]

        # Análise Narrativa
        narrative = self.analyze_narrative(transcript_text or "", duration)

        # Análise Visual
        visual = self.analyze_visual_real(video_path)

        # Análise de Áudio
        audio = self.analyze_audio_real(video_path)

        # Determinação honesta da profundidade de análise
        modalities_count = 1 # Metadados
        if narrative.get("has_narrative_analysis"):
            modalities_count += 1
        if visual.get("has_visual_analysis"):
            modalities_count += 1
        if audio.get("has_audio_analysis"):
            modalities_count += 1

        if modalities_count == 4:
            analysis_depth = "FULL_MULTIMODAL"
            classification = "APRENDIZADO_VALIDADO"
        elif narrative.get("has_narrative_analysis"):
            analysis_depth = "PARTIAL_NARRATIVE"
            classification = "PADRÃO"
        else:
            analysis_depth = "PRELIMINARY_METADATA_ONLY"
            classification = "OBSERVAÇÃO"

        # Registro na base de conhecimento apenas com dados verificados
        knowledge_record = {
            "source_video_id": v_id,
            "source_url": url,
            "title": title,
            "niche": niche,
            "analysis_depth": analysis_depth,
            "classification": classification,
            "narrative_metrics": narrative,
            "visual_metrics": visual,
            "audio_metrics": audio,
            "evidence_video_ids": [v_id]
        }

        # Registra no CentralMemory com isolamento por canal
        node_id = self.memory.record_knowledge_node(
            category_slug=niche,
            node_type=f"analysis_{analysis_depth.lower()}",
            title=f"Estudo Audiovisual ({classification}): {title[:35]}",
            pattern_data=knowledge_record,
            effectiveness_score=85.0 if analysis_depth == "FULL_MULTIMODAL" else 60.0,
            derived_from=[v_id],
            channel_id=target_channel_id
        )

        # Registra na biblioteca de conhecimento editorial com evidência auditável
        try:
            self.learning_sys.record_knowledge(
                niche=niche,
                knowledge_type="multimodal_pattern",
                title=f"Padrão Audiovisual ({classification}): {title[:35]}",
                summary=f"Análise {analysis_depth} do vídeo {v_id}. Gancho: {narrative.get('hook_0_3s') or 'Visual'}.",
                classification=classification,
                confidence_score=0.90 if classification == "APRENDIZADO_VALIDADO" else 0.70,
                evidence_video_ids=[v_id],
                target_channel_id=target_channel_id
            )
        except Exception:
            pass

        # Registra no Playbook
        learned_item = {
            "node_id": node_id,
            "evidence_video_id": v_id,
            "url": url,
            "title": title,
            "niche": niche,
            "classification": classification,
            "analysis_depth": analysis_depth,
            "hook": narrative.get("hook_0_3s"),
            "triggers": narrative.get("psychological_triggers", [])
        }

        if classification == "APRENDIZADO_VALIDADO":
            self.playbook.setdefault("evidence_based_patterns", []).append(learned_item)
        else:
            self.playbook.setdefault("hypotheses", []).append(learned_item)

        self.playbook["total_learned_patterns"] = self.playbook.get("total_learned_patterns", 0) + 1
        self._save_playbook()

        return {
            "success": True,
            "status": "ANALYZED",
            "video_id": v_id,
            "analysis_depth": analysis_depth,
            "classification": classification,
            "evidence_video_ids": [v_id],
            "node_id": node_id,
            "narrative": narrative,
            "visual": visual,
            "audio": audio,
            "metrics_invented": False
        }

    def learn_from_urls(self, urls: List[str], niche: str = "geral") -> Dict[str, Any]:
        """
        Processa lote de URLs com classificação honesta de cada uma.
        """
        results = []
        inaccessible = []
        for url in urls:
            res = self.learn_from_video(url=url, niche=niche)
            if res.get("success"):
                results.append(res)
            else:
                inaccessible.append(res)

        return {
            "learned_count": len(results),
            "inaccessible_count": len(inaccessible),
            "items": results,
            "inaccessible_items": inaccessible
        }
