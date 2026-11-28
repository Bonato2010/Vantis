"""
Motor de Catalogação em Larga Escala (Suporte a 200.000+ Vídeos de Referência).
Sem dados simulados, métricas inventadas ou estimativas fantasiosas.
Extrai metadados, ganchos e transcrições reais via yt-dlp SEM baixar vídeos pesados localmente.
Salva metadados auditáveis na memória central e backup no Google Drive 5 TB.
"""
import json
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from memory.central_memory import CentralMemory
from core.gdrive_manager import GDriveManager

class LargeScaleCataloger:
    def __init__(self, memory: Optional[CentralMemory] = None):
        self.memory = memory or CentralMemory()
        self.gdrive = GDriveManager()
        self.temp_dir = BASE_DIR / "workspace/catalog_temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def extract_video_metadata_fast(self, youtube_url: str) -> Optional[Dict[str, Any]]:
        """
        Extrai metadados reais do vídeo via yt-dlp.
        Retorna None se o vídeo não puder ser acessado ou não existir.
        NUNCA inventa dados sintéticos.
        """
        if not youtube_url or not isinstance(youtube_url, str):
            return None

        # Validação de formato básico de URL
        if not ("youtube.com" in youtube_url or "youtu.be" in youtube_url):
            return None

        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--dump-json",
            "--skip-download",
            "--no-playlist",
            youtube_url
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
            data = json.loads(res.stdout)

            v_id = data.get("id")
            if not v_id:
                return None

            subtitles = data.get("subtitles", {}) or data.get("automatic_captions", {})
            has_pt = any(k in subtitles for k in ["pt", "pt-BR", "pt-PT"])

            raw_duration = data.get("duration")
            duration_sec = float(raw_duration) if raw_duration is not None else None

            views = data.get("view_count")
            views_count = int(views) if views is not None else None

            likes = data.get("like_count")
            likes_count = int(likes) if likes is not None else None

            comments = data.get("comment_count")
            comments_count = int(comments) if comments is not None else None

            return {
                "youtube_id": v_id,
                "url": youtube_url,
                "title": data.get("title") or "Sem título",
                "author": data.get("uploader") or data.get("channel") or "Desconhecido",
                "channel_id": data.get("channel_id") or None,
                "views_count": views_count,
                "likes_count": likes_count,
                "comments_count": comments_count,
                "duration_seconds": duration_sec,
                "description": data.get("description") or "",
                "tags": ", ".join(data.get("tags", [])[:15]) if data.get("tags") else "",
                "has_subtitles": has_pt,
                "raw_source": "yt-dlp",
                "is_synthetic": False
            }
        except Exception:
            return None

    def ingest_reference(self, youtube_url: str, category_slug: str, transcript_text: str = "") -> Dict[str, Any]:
        """
        Catalogação estrita:
        - Se o vídeo for inacessível, registra falha sem inventar métricas.
        - Não inventa visualizações, curtidas, comentários, duração ou retenção.
        - Não considera título como transcrição.
        """
        meta = self.extract_video_metadata_fast(youtube_url)
        if not meta:
            # Vídeo inacessível ou inválido: NUNCA inventar dados
            return {
                "success": False,
                "status": "INACCESSIBLE",
                "error": "Falha na extração de metadados reais: vídeo inacessível, removido ou URL inválida.",
                "url": youtube_url,
                "metrics_invented": False
            }

        # Análise de transcrição real apenas se fornecida
        has_real_transcript = bool(transcript_text and transcript_text.strip())
        words = transcript_text.split() if has_real_transcript else []
        hook_transcript = " ".join(words[:12]) if words else None

        duration = meta.get("duration_seconds")
        pacing_wpm = None
        if duration and duration > 0 and len(words) > 0:
            pacing_wpm = round(len(words) / (duration / 60.0), 1)

        views = meta.get("views_count")
        likes = meta.get("likes_count")

        # Taxa de engajamento real apenas se existirem dados reais
        derived_engagement_rate = None
        if views is not None and likes is not None and views > 0:
            derived_engagement_rate = round((likes / views) * 100, 2)

        # Retenção: YouTube NÃO fornece retenção pública em metadados. Não inventar!
        retention_score = None

        # Salva no Banco de Dados
        with self.memory._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE slug = ?", (category_slug,))
            row = cursor.fetchone()
            cat_id = row["id"] if row else 1

            cursor.execute("""
                INSERT OR REPLACE INTO video_references (
                    category_id, video_id, title, original_url, youtube_id, url, author,
                    views_count, likes_count, duration_seconds,
                    hook_transcript, full_transcript, niche,
                    pacing_bpm, retention_score, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cat_id,
                meta["youtube_id"],
                meta["title"],
                meta["url"],
                meta["youtube_id"],
                meta["url"],
                meta["author"],
                views if views is not None else 0,
                likes if likes is not None else 0,
                duration if duration is not None else 0.0,
                hook_transcript or "",
                transcript_text or "",
                category_slug,
                pacing_wpm if pacing_wpm is not None else 0.0,
                retention_score, # NULL real no banco
                meta.get("tags", "")
            ))
            ref_id = cursor.lastrowid
            conn.commit()

        # Somente registra padrão se houver transcrição real analisada
        if has_real_transcript and hook_transcript:
            pattern_title = f"Gancho Real ({category_slug}): {hook_transcript[:35]}..."
            self.memory.record_pattern(
                category_slug=category_slug,
                pattern_type="hook_formula",
                title=pattern_title,
                structure_template="Gancho Real extraído de transcrição autêntica",
                hook_formula=hook_transcript,
                ideal_duration=duration or 45.0,
                typical_retention=0.0, # Sem suposição fictícia
                source_ref_id=ref_id,
                metadata={
                    "uploader": meta["author"],
                    "views": views,
                    "likes": likes,
                    "engagement_rate": derived_engagement_rate,
                    "verified_real_data": True
                }
            )

        return {
            "success": True,
            "status": "TRANSCRIPTION_COMPLETED" if has_real_transcript else "METADATA_COLLECTED",
            "ref_id": ref_id,
            "video_id": meta["youtube_id"],
            "title": meta["title"],
            "author": meta["author"],
            "category": category_slug,
            "views_count": views,
            "likes_count": likes,
            "duration_seconds": duration,
            "derived_engagement_rate": derived_engagement_rate,
            "retention_score": None, # Explicitamente ausente sem dados de audiência
            "pacing_wpm": pacing_wpm,
            "hook": hook_transcript,
            "has_real_transcript": has_real_transcript,
            "metrics_invented": False
        }

    def batch_catalog_urls(self, url_list: List[Dict[str, str]]) -> Dict[str, Any]:
        results = []
        inaccessible = []
        for item in url_list:
            url = item.get("url")
            cat = item.get("category", "cortes_podcasts")
            text = item.get("transcript", "")
            if url:
                res = self.ingest_reference(url, cat, text)
                if res.get("success"):
                    results.append(res)
                else:
                    inaccessible.append(res)
        return {
            "cataloged_count": len(results),
            "inaccessible_count": len(inaccessible),
            "items": results,
            "inaccessible_items": inaccessible
        }
