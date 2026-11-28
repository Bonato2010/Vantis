"""
VANTIS — Planejador de Seleção Estratificada e Auditoria de Capacidade para 7.000 Vídeos (Fase 17 Seções 5 & 7)
IMPORTANTE: Este módulo apenas modela capacidade e planeja/valida critérios de seleção e divisão
(train/validation/test) — NÃO executa downloads em massa de 7.000 vídeos.
"""

import math
from typing import Dict, Any, List, Optional


class ScaleSelectionPlanner:
    """
    Planejamento de seleção estratificada anti-viés de popularidade e auditoria de capacidade
    para a futura biblioteca de 7.000+ Shorts.
    """

    POPULARITY_TIERS = {
        "emerging": (0, 10_000),
        "mid_tier": (10_000, 500_000),
        "viral": (500_000, float("inf")),
    }

    DEFAULT_TIER_QUOTAS = {
        "emerging": 0.30,   # 30% vídeos menores para evitar viés de celebridade/mega-viral
        "mid_tier": 0.40,   # 40% vídeos intermediários consistentes
        "viral": 0.30,      # 30% vídeos virais de alto alcance
    }

    SPLIT_RATIOS = {
        "train": 0.70,
        "validation": 0.15,
        "test": 0.15,
    }

    def estimate_capacity_scenarios(
        self,
        target_videos: int = 7000,
        pilot_videos: int = 100,
        pilot_storage_bytes: int = 840_630_006,
        pilot_elapsed_sec: float = 3349.7,
        pilot_db_delta_bytes: int = 2_097_152,
    ) -> Dict[str, Any]:
        """
        Projeta 3 cenários (Conservador, Realista, Pessimista) para 7.000 vídeos com base
        nas medições reais do piloto de 100 vídeos.
        Deixa explícitas todas as premissas, fórmulas e margens de segurança.
        """
        avg_mb_per_video = (pilot_storage_bytes / (1024 * 1024)) / max(1, pilot_videos)
        avg_sec_per_video = pilot_elapsed_sec / max(1, pilot_videos)  # ~33.5s/vídeo sequencial (Whisper+FFmpeg+PySceneDetect)
        avg_db_kb_per_video = (pilot_db_delta_bytes / 1024) / max(1, pilot_videos)

        scale_factor = target_videos / max(1, pilot_videos)

        # Premissas por cenário:
        # 1. Conservador (4 workers paralelos eficientes, jitter médio 4.5s, margem 1.15x, retenção de arquivos pós-análise ou limpeza parcial)
        # 2. Realista (3 workers efetivos considerando throttling YouTube e picos 4K AV1, margem 1.30x)
        # 3. Pessimista (1-2 workers devido a rate limit/retries YouTube, vídeos maiores, margem 1.60x)
        scenarios = {}
        configs = [
            ("conservador", 4.0, 1.15, 0.05),
            ("realista", 2.8, 1.30, 0.12),
            ("pessimista", 1.5, 1.60, 0.25),
        ]

        for name, eff_workers, safety_margin, retry_overhead in configs:
            raw_storage_gb = (target_videos * avg_mb_per_video) / 1024.0
            storage_with_margin_gb = round(raw_storage_gb * safety_margin, 2)

            # Tempo inclui download (~5s jitter) + análise física (~33.5s sequencial) dividido por workers efetivos
            sec_per_vid_total = (avg_sec_per_video + 5.0) * (1.0 + retry_overhead) / eff_workers
            total_hours = round((target_videos * sec_per_vid_total) / 3600.0, 2)

            sqlite_mb = round(((target_videos * avg_db_kb_per_video) / 1024.0) * safety_margin, 2)

            scenarios[name] = {
                "is_estimate": True,
                "effective_workers": eff_workers,
                "safety_margin": safety_margin,
                "retry_overhead_ratio": retry_overhead,
                "estimated_media_storage_gb": storage_with_margin_gb,
                "estimated_sqlite_growth_mb": sqlite_mb,
                "estimated_wall_clock_hours": total_hours,
                "estimated_cost_usd": 0.0,
                "ram_peak_estimate_gb": round(0.8 * eff_workers + 0.6, 2),
                "cpu_utilization_estimate": f"{min(95, int(eff_workers * 25))}%",
            }

        return {
            "target_videos": target_videos,
            "baseline_measurements_from_pilot_100": {
                "avg_mb_per_video": round(avg_mb_per_video, 2),
                "avg_analysis_sec_per_video_seq": round(avg_sec_per_video, 2),
                "scale_factor": scale_factor,
            },
            "formulas": {
                "storage_gb": "target_videos * avg_mb_per_video / 1024 * safety_margin",
                "wall_clock_hours": "target_videos * ((avg_analysis_sec + 5.0) * (1 + retry_overhead) / effective_workers) / 3600",
                "ram_peak_gb": "0.8 * effective_workers + 0.6 (modelo Whisper tiny + OpenCV/PyAV)",
            },
            "scenarios": scenarios,
            "recommendation": "Executar em sublotes de 250-500 vídeos com expurgo controlado de mídia bruta após extração de evidências ou offload para Google Drive (5 TB) para manter disco local < 15 GB.",
        }

    def classify_popularity_tier(self, views: int) -> str:
        v = max(0, int(views or 0))
        if v < 10_000:
            return "emerging"
        if v < 500_000:
            return "mid_tier"
        return "viral"

    def plan_stratified_selection(
        self,
        pool: List[Dict[str, Any]],
        target_per_channel: int = 1400,
        existing_ids: Optional[set] = None,
    ) -> Dict[str, Any]:
        """
        Seleciona candidatos com estratificação anti-viés de popularidade, diversidade de formato/fala/nicho,
        deduplicação estrita e atribuição determinística de split train/validation/test (70/15/15).
        """
        seen = set(existing_ids or set())
        seen_fingerprints = set()
        selected: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []

        # Agrupa por canal
        by_channel: Dict[int, List[Dict[str, Any]]] = {}
        for item in pool:
            vid = item.get("id") or item.get("source_id")
            dur = float(item.get("duration_seconds") or item.get("metadata_duration") or 0.0)
            url = item.get("url") or item.get("original_url") or ""
            is_available = item.get("is_available", True)
            norm_title = " ".join(str(item.get("title") or "").lower().split())
            fp = f"{norm_title}|{round(dur, 1)}" if norm_title else None

            if not vid or vid in seen:
                rejected.append({"id": vid, "reason": "duplicate_or_missing_id"})
                continue
            if fp and fp in seen_fingerprints:
                rejected.append({"id": vid, "reason": "duplicate_title_duration_fingerprint"})
                continue
            if not url.startswith("http"):
                rejected.append({"id": vid, "reason": "invalid_url"})
                continue
            if not is_available:
                rejected.append({"id": vid, "reason": "unavailable_video"})
                continue
            if dur <= 0.0 or dur > 60.0:
                rejected.append({"id": vid, "reason": "duration_out_of_shorts_bounds"})
                continue

            seen.add(vid)
            if fp:
                seen_fingerprints.add(fp)
            ch_id = int(item.get("channel_id") or 1)
            tier = self.classify_popularity_tier(item.get("views", 0))
            enriched = {**item, "id": vid, "popularity_tier": tier}
            by_channel.setdefault(ch_id, []).append(enriched)

        tier_counts = {"emerging": 0, "mid_tier": 0, "viral": 0}
        split_counts = {"train": 0, "validation": 0, "test": 0}

        for ch_id, items in sorted(by_channel.items()):
            # Distribui por quotas de popularidade para evitar apenas mega-virais
            buckets = {"emerging": [], "mid_tier": [], "viral": []}
            for it in items:
                buckets[it["popularity_tier"]].append(it)

            ch_selected: List[Dict[str, Any]] = []
            for tier, ratio in self.DEFAULT_TIER_QUOTAS.items():
                quota = int(round(target_per_channel * ratio))
                ch_selected.extend(buckets[tier][:quota])

            # Completa até target_per_channel apenas com itens válidos restantes se algum tier tiver menos
            if len(ch_selected) < target_per_channel:
                used_ids = {x["id"] for x in ch_selected}
                for it in items:
                    if it["id"] not in used_ids:
                        ch_selected.append(it)
                        used_ids.add(it["id"])
                    if len(ch_selected) >= target_per_channel:
                        break

            ch_selected = ch_selected[:target_per_channel]

            # Atribuição determinística de split (70% train / 15% validation / 15% test)
            n_ch = len(ch_selected)
            n_train = int(round(n_ch * self.SPLIT_RATIOS["train"]))
            n_val = int(round(n_ch * self.SPLIT_RATIOS["validation"]))

            for idx, it in enumerate(ch_selected):
                if idx < n_train:
                    split = "train"
                elif idx < n_train + n_val:
                    split = "validation"
                else:
                    split = "test"
                it["dataset_split"] = split
                it["inclusion_rationale"] = (
                    f"channel={ch_id}, tier={it['popularity_tier']}, split={split}, "
                    f"duration={float(it.get('duration_seconds') or it.get('metadata_duration') or 0):.1f}s"
                )
                tier_counts[it["popularity_tier"]] += 1
                split_counts[split] += 1
                selected.append(it)

        return {
            "selected_count": len(selected),
            "rejected_count": len(rejected),
            "tier_distribution": tier_counts,
            "split_distribution": split_counts,
            "selected": selected,
            "rejected": rejected,
        }
