"""
VANTIS — Motor de Memória Editorial Evolutiva e Aprendizado Real (Fase 18)
Executa split estratificado 70/15/15 sem vazamento, normaliza desempenho por canal,
avalia hipóteses anteriores, descobre novos padrões a partir de características reais
e compara a utilidade editorial antes e depois no conjunto de teste disjunto.
"""

import json
import math
import sqlite3
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.discovery.scale_selector import ScaleSelectionPlanner
from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.learning.editorial_feature_extractor import (
    EditorialFeatureExtractor,
    NOT_AVAILABLE,
)


def _median(vals: List[float]) -> float:
    return round(float(statistics.median(vals)), 4) if vals else 0.0


def _iqr(vals: List[float]) -> float:
    if len(vals) < 4:
        return round(float(max(vals) - min(vals)), 4) if vals else 0.0
    s = sorted(vals)
    q1 = s[len(s) // 4]
    q3 = s[(3 * len(s)) // 4]
    return round(float(q3 - q1), 4)


def _parse_json(raw: Any, default: Any) -> Any:
    if isinstance(raw, type(default)):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default
    return default


class EditorialMemoryEngine:
    """Memória editorial evolutiva com split anti-vazamento e aprendizado baseado em evidências."""

    def __init__(self, db_path: Optional[Path] = None):
        self.als = AudiovisualLearningSystem(db_path=db_path)
        self.db_path = Path(self.als.db_path)
        self.extractor = EditorialFeatureExtractor()
        self.planner = ScaleSelectionPlanner()

    def build_leak_free_splits(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Divide vídeos elegíveis por canal em 70% train / 15% validation / 15% test,
        verificando ausência de sobreposição por ID, SHA256 e fingerprint título+duração.
        """
        by_channel: Dict[int, List[Dict[str, Any]]] = {}
        seen_ids = set()
        seen_hashes = set()
        seen_fps = set()
        duplicates_removed: List[Dict[str, Any]] = []

        for v in videos:
            vid = str(v.get("source_id") or v.get("id") or "")
            raw_meta = _parse_json(v.get("raw_metadata"), {})
            sha = str(v.get("sha256") or raw_meta.get("sha256") or "").strip()
            norm_title = " ".join(str(v.get("title") or "").lower().split())
            dur = round(float(v.get("duration_seconds") or 0.0), 1)
            fp = f"{norm_title}|{dur}" if norm_title else ""

            if not vid or vid in seen_ids:
                duplicates_removed.append({"id": vid, "reason": "duplicate_id"})
                continue
            if sha and sha in seen_hashes:
                duplicates_removed.append({"id": vid, "reason": "duplicate_sha256"})
                continue
            if fp and fp in seen_fps:
                duplicates_removed.append({"id": vid, "reason": "duplicate_title_duration"})
                continue

            seen_ids.add(vid)
            if sha:
                seen_hashes.add(sha)
            if fp:
                seen_fps.add(fp)

            ch_id = int(v.get("channel_id") or raw_meta.get("target_channel_id") or 0)
            by_channel.setdefault(ch_id, []).append(v)

        train, validation, test = [], [], []
        per_channel_counts: Dict[int, Dict[str, int]] = {}

        for ch_id, ch_videos in sorted(by_channel.items()):
            # Ordenação estratificada por views para distribuir popularidade entre os 3 splits
            ordered = sorted(
                ch_videos,
                key=lambda x: (int(x.get("views_count") or x.get("views") or 0), str(x.get("source_id") or x.get("id"))),
            )
            ch_train, ch_val, ch_test = [], [], []
            for idx, item in enumerate(ordered):
                mod = idx % 20
                if mod in (2, 9, 16):  # 15%
                    item_copy = dict(item, split="validation")
                    ch_val.append(item_copy)
                elif mod in (5, 12, 19):  # 15%
                    item_copy = dict(item, split="test")
                    ch_test.append(item_copy)
                else:  # 70%
                    item_copy = dict(item, split="train")
                    ch_train.append(item_copy)

            train.extend(ch_train)
            validation.extend(ch_val)
            test.extend(ch_test)
            per_channel_counts[ch_id] = {
                "total": len(ordered),
                "train": len(ch_train),
                "validation": len(ch_val),
                "test": len(ch_test),
            }

        train_ids = {str(v.get("source_id") or v.get("id")) for v in train}
        val_ids = {str(v.get("source_id") or v.get("id")) for v in validation}
        test_ids = {str(v.get("source_id") or v.get("id")) for v in test}

        return {
            "train": train,
            "validation": validation,
            "test": test,
            "per_channel_counts": per_channel_counts,
            "duplicates_removed": duplicates_removed,
            "leakage_checks": {
                "train_test_id_overlap": len(train_ids & test_ids),
                "val_test_id_overlap": len(val_ids & test_ids),
                "train_val_id_overlap": len(train_ids & val_ids),
                "leak_free": len(train_ids & test_ids) == 0 and len(val_ids & test_ids) == 0,
            },
        }

    def compute_channel_normalized_metrics(self, videos: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """Calcula mediana de views, mediana e IQR de engajamento por canal (nunca compara views brutas entre canais)."""
        by_ch: Dict[int, List[Dict[str, Any]]] = {}
        for v in videos:
            raw_meta = _parse_json(v.get("raw_metadata"), {})
            ch_id = int(v.get("channel_id") or raw_meta.get("target_channel_id") or 0)
            by_ch.setdefault(ch_id, []).append(v)

        stats: Dict[int, Dict[str, Any]] = {}
        for ch_id, vids in by_ch.items():
            views_list = [float(v.get("views_count") or v.get("views") or 0) for v in vids]
            eng_list = [float(v.get("engagement_ratio") or 0.0) for v in vids]
            med_views = max(1.0, _median(views_list))
            med_eng = _median(eng_list)
            iqr_eng = _iqr(eng_list)

            for v in vids:
                v_views = float(v.get("views_count") or v.get("views") or 0)
                v["relative_views_to_channel_median"] = round(v_views / med_views, 3)

            stats[ch_id] = {
                "count": len(vids),
                "median_views": round(med_views, 1),
                "median_engagement_pct": med_eng,
                "iqr_engagement_pct": iqr_eng,
            }
        return stats

    def _evaluate_feature_predicate(
        self,
        channel_id: int,
        niche: str,
        feature_name: str,
        hypothesis_text: str,
        train_val_videos: List[Dict[str, Any]],
        predicate,
        min_validated_favorable: int = 5,
        min_validated_counter: int = 3,
    ) -> Dict[str, Any]:
        """Avalia uma característica no conjunto train+val do canal e decide classificação honesta."""
        favorable_good: List[str] = []
        favorable_weak: List[str] = []
        control_good: List[str] = []
        control_weak: List[str] = []
        fav_engs: List[float] = []
        ctrl_engs: List[float] = []
        fav_rel_views: List[float] = []
        ctrl_rel_views: List[float] = []

        engs = [float(v.get("engagement_ratio") or 0.0) for v in train_val_videos]
        ch_med_eng = _median(engs)

        for v in train_val_videos:
            vid = str(v.get("source_id") or v.get("id"))
            feats = v.get("editorial_features") or self.extractor.extract(v)
            v["editorial_features"] = feats
            eng = float(v.get("engagement_ratio") or 0.0)
            rel_v = float(v.get("relative_views_to_channel_median") or 0.0)
            matched = predicate(feats, v)
            if matched is None:
                continue
            is_above_med = (eng > ch_med_eng and eng > 0.0) or rel_v >= 1.0
            if matched:
                fav_engs.append(eng)
                fav_rel_views.append(rel_v)
                if is_above_med:
                    favorable_good.append(vid)
                else:
                    favorable_weak.append(vid)
            else:
                ctrl_engs.append(eng)
                ctrl_rel_views.append(rel_v)
                if is_above_med:
                    control_good.append(vid)
                else:
                    control_weak.append(vid)

        # Filtra ruído de denominador minúsculo (ex: 1 view + 1 like = 100% engajamento) ao calcular medianas
        fav_engs_reliable = [
            float(v.get("engagement_ratio") or 0.0)
            for v in train_val_videos
            if predicate(v.get("editorial_features") or self.extractor.extract(v), v) is True
            and int(v.get("views_count") or v.get("views") or 0) >= 30
        ]
        ctrl_engs_reliable = [
            float(v.get("engagement_ratio") or 0.0)
            for v in train_val_videos
            if predicate(v.get("editorial_features") or self.extractor.extract(v), v) is False
            and int(v.get("views_count") or v.get("views") or 0) >= 30
        ]
        med_fav_eng = _median(fav_engs_reliable) if len(fav_engs_reliable) >= 3 else _median(fav_engs)
        med_ctrl_eng = _median(ctrl_engs_reliable) if len(ctrl_engs_reliable) >= 3 else _median(ctrl_engs)
        med_fav_rel = _median(fav_rel_views)
        med_ctrl_rel = _median(ctrl_rel_views)

        total_fav = len(fav_engs)
        total_ctrl = len(ctrl_engs)
        # Exige lift positivo real em engajamento (e sem colapso em views relativas) para evitar correlações fracas
        positive_lift = (med_fav_eng > med_ctrl_eng) and (med_fav_rel >= med_ctrl_rel * 0.9)
        # Evidências favoráveis = vídeos com a característica e bom desempenho;
        # Contraexemplos = vídeos com a característica mas desempenho fraco, ou controle com bom desempenho.
        counterexamples = (favorable_weak + control_good)[:15]
        ev_ids = (favorable_good if favorable_good else (favorable_good + favorable_weak))[:15]

        if (
            len(favorable_good) >= min_validated_favorable
            and len(counterexamples) >= min_validated_counter
            and total_ctrl >= min_validated_counter
            and positive_lift
        ):
            classification = "APRENDIZADO_VALIDADO"
            confidence = round(min(0.92, 0.72 + 0.02 * len(favorable_good)), 2)
        elif total_fav >= 3 and total_ctrl >= 2 and not positive_lift and med_fav_eng < med_ctrl_eng:
            classification = "HIPÓTESE"
            confidence = 0.45
        elif total_fav >= 2:
            classification = "HIPÓTESE"
            confidence = round(min(0.68, 0.50 + 0.03 * len(favorable_good)), 2)
        else:
            classification = "OBSERVAÇÃO"
            confidence = 0.52

        return {
            "channel_id": channel_id,
            "niche": niche,
            "feature_name": feature_name,
            "hypothesis": hypothesis_text,
            "classification": classification,
            "confidence": confidence,
            "evidence_video_ids": ev_ids,
            "counterexamples": counterexamples,
            "videos_analyzed": len(train_val_videos),
            "metrics_source": "youtube_public_metadata + ffmpeg_ebur128 + pyscenedetect + faster_whisper",
            "calculation_method": (
                f"train+val canal {channel_id}: med_eng(fav)={med_fav_eng}% vs med_eng(ctrl)={med_ctrl_eng}%, "
                f"med_rel_views(fav)={med_fav_rel}x vs ctrl={med_ctrl_rel}x "
                f"(n_fav_good={len(favorable_good)}, n_fav_total={total_fav}, n_ctrl={total_ctrl})"
            ),
            "positive_lift": positive_lift,
            "med_fav_eng": med_fav_eng,
            "med_ctrl_eng": med_ctrl_eng,
        }

    def run_evolutionary_learning(
        self,
        train_val_videos: List[Dict[str, Any]],
        channel_names: Optional[Dict[int, Tuple[str, str]]] = None,
        pilot_phase: int = 18,
    ) -> Dict[str, Any]:
        """
        Executa aprendizado editorial real usando SOMENTE train+validation,
        atualiza memória evolutiva (preservando histórico) e detecta contradições/duplicatas.
        """
        ch_meta = channel_names or {
            1: ("Canal 01 - Futebol em 60 Segundos", "futebol_outros"),
            2: ("Canal 02 - Arquivo Sombrio (Casos Reais)", "casos_policiais"),
            3: ("Canal 03 - Rir para Não Chorar", "humor"),
            4: ("Canal 04 - Mente Curiosa & Ciência", "curiosidades"),
            5: ("Canal 05 - Mente Focada & Produtividade", "desenvolvimento_pessoal"),
        }

        norm_stats = self.compute_channel_normalized_metrics(train_val_videos)
        by_ch: Dict[int, List[Dict[str, Any]]] = {}
        for v in train_val_videos:
            raw_meta = _parse_json(v.get("raw_metadata"), {})
            ch_id = int(v.get("channel_id") or raw_meta.get("target_channel_id") or 0)
            by_ch.setdefault(ch_id, []).append(v)

        feature_specs = [
            (
                "ritmo_de_cortes_dinamico",
                "Cortes dinâmicos (>= 4 cortes) melhoram retenção inicial e desempenho no canal.",
                lambda f, v: None if f["cuts_count"] == NOT_AVAILABLE else int(f["cuts_count"]) >= 4,
            ),
            (
                "estrutura_narrativa_real",
                "Presença de narração falada estruturada eleva engajamento relativo frente a clipes sem fala.",
                lambda f, v: None if f["has_narration"] == NOT_AVAILABLE else bool(f["has_narration"]),
            ),
            (
                "gancho_inicial_forte",
                "Gancho de pergunta ou curiosidade nos primeiros segundos aumenta tração editorial.",
                lambda f, v: None if f["hook_type"] == NOT_AVAILABLE else f["hook_type"] in ("question", "curiosity_or_fact", "direct_command"),
            ),
            (
                "progressao_narrativa_completa",
                "Estrutura completa (abertura, desenvolvimento e conclusão) sustenta melhor desempenho.",
                lambda f, v: None if f["narrative_progression"] == NOT_AVAILABLE else f["narrative_progression"] == "complete_3_acts",
            ),
            (
                "texto_na_tela_suporte",
                "Presença de texto na tela reforça compreensão visual e engajamento.",
                lambda f, v: None if f["text_on_screen_detected"] == NOT_AVAILABLE else bool(f["text_on_screen_detected"]),
            ),
        ]

        recorded: List[Dict[str, Any]] = []
        prior_updates: List[Dict[str, Any]] = []
        contradictions: List[Dict[str, Any]] = []

        for ch_id, vids in sorted(by_ch.items()):
            ch_name, niche = ch_meta.get(ch_id, (f"Canal {ch_id}", "outros"))
            for topic, hyp_text, pred in feature_specs:
                res = self._evaluate_feature_predicate(ch_id, niche, topic, hyp_text, vids, pred)
                if not res["evidence_video_ids"]:
                    continue
                rec = self.als.record_knowledge(
                    niche=niche,
                    topic=topic,
                    title=f"[Fase {pilot_phase}] {topic} em {ch_name}",
                    summary=f"{hyp_text} Evidência ({res['calculation_method']}).",
                    classification=res["classification"],
                    confidence_score=res["confidence"],
                    evidence_video_ids=res["evidence_video_ids"],
                    counterexamples=res["counterexamples"],
                    actionable_recommendation=(
                        f"Aplicar '{topic}' em {ch_name} quando validado; monitorar contraexemplos."
                        if res["classification"] == "APRENDIZADO_VALIDADO"
                        else f"Testar '{topic}' em {ch_name} como hipótese controlada."
                    ),
                    anti_pattern_warning="Evitar aplicar sem narração/áudio válido ou em vídeos silenciosos (-70 LUFS).",
                    target_channel_id=ch_id,
                    pilot_phase=pilot_phase,
                    require_counterexamples=(res["classification"] == "APRENDIZADO_VALIDADO"),
                )
                # Enriquecer metadata com os campos obrigatórios da Seção 5
                with self.als._get_conn() as conn:
                    row = conn.execute(
                        "SELECT metadata FROM editorial_knowledge_library WHERE id = ?",
                        (rec["id"],),
                    ).fetchone()
                    meta = _parse_json(row[0] if row else "{}", {})
                    meta.update({
                        "observed_feature": topic,
                        "editorial_hypothesis": hyp_text,
                        "videos_analyzed_count": res["videos_analyzed"],
                        "metrics_source": res["metrics_source"],
                        "calculation_method": res["calculation_method"],
                        "positive_lift": res["positive_lift"],
                        "channel_normalized_stats": norm_stats.get(ch_id, {}),
                    })
                    conn.execute(
                        "UPDATE editorial_knowledge_library SET metadata = ? WHERE id = ?",
                        (json.dumps(meta, ensure_ascii=False), rec["id"]),
                    )
                    conn.commit()
                recorded.append({**res, "knowledge_id": rec["id"], "final_classification": rec["classification"]})

        # Evoluir hipóteses da Fase 16/17.1 (IDs 104..126) com base no novo ciclo
        with self.als._get_conn() as conn:
            old_rows = conn.execute(
                "SELECT id, target_channel_id, knowledge_type, classification, metadata FROM editorial_knowledge_library WHERE id BETWEEN 104 AND 126 ORDER BY id"
            ).fetchall()
            new_by_key = {(r["channel_id"], r["feature_name"]): r for r in recorded}
            for old_id, old_ch, old_type, old_cls, old_meta_raw in old_rows:
                matched_new = new_by_key.get((old_ch, old_type))
                if not matched_new:
                    continue
                old_meta = _parse_json(old_meta_raw, {})
                hist = old_meta.get("classification_history", [])
                new_cls = matched_new["final_classification"]
                if old_cls in ("HIPÓTESE", "PENDENTE_DE_VALIDACAO"):
                    if new_cls == "APRENDIZADO_VALIDADO":
                        target_cls = "APRENDIZADO_VALIDADO"
                        note = f"Promovido na Fase {pilot_phase} após confirmação em train+val (n={matched_new['videos_analyzed']})."
                    elif not matched_new["positive_lift"] and matched_new["med_fav_eng"] < matched_new["med_ctrl_eng"]:
                        target_cls = "HIPÓTESE"
                        note = f"Mantido como HIPÓTESE / sem lift positivo na Fase {pilot_phase} ({matched_new['calculation_method']})."
                        contradictions.append({"prior_id": old_id, "new_id": matched_new["knowledge_id"], "channel_id": old_ch, "feature": old_type, "reason": note})
                    else:
                        target_cls = old_cls
                        note = f"Mantido em {old_cls} na Fase {pilot_phase}: amostra ainda requer confirmação adicional."

                    hist.append({
                        "previous_classification": old_cls,
                        "new_classification": target_cls,
                        "reason": note,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    old_meta["classification_history"] = hist
                    old_meta["phase18_followup_knowledge_id"] = matched_new["knowledge_id"]
                    conn.execute(
                        "UPDATE editorial_knowledge_library SET classification = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (target_cls, json.dumps(old_meta, ensure_ascii=False), old_id),
                    )
                    prior_updates.append({"id": old_id, "channel_id": old_ch, "feature": old_type, "from": old_cls, "to": target_cls, "note": note})
            conn.commit()

        return {
            "channel_normalized_stats": norm_stats,
            "recorded_knowledge": recorded,
            "prior_hypothesis_updates": prior_updates,
            "contradictions_detected": contradictions,
        }

    def evaluate_utility_before_after(
        self,
        test_videos: List[Dict[str, Any]],
        train_ids: set,
    ) -> Dict[str, Any]:
        """
        Compara Baseline (sem memória da Fase 18) vs Sistema Atualizado (com memória da Fase 18)
        sobre o conjunto de teste independente (15% disjunto).
        """
        test_ids = {str(v.get("source_id") or v.get("id")) for v in test_videos}
        overlap = len(test_ids & train_ids)

        # Carrega apenas regras validadas da Fase 18+ (evita vazamento de regras legadas pré-calibração)
        validated_by_ch: Dict[int, List[str]] = {}
        with self.als._get_conn() as conn:
            rows = conn.execute(
                "SELECT target_channel_id, knowledge_type FROM editorial_knowledge_library WHERE classification = 'APRENDIZADO_VALIDADO' AND (metadata LIKE '%\"pilot_phase\": 18%' OR metadata NOT LIKE '%\"pilot_phase\": 15%') AND target_channel_id IS NOT NULL"
            ).fetchall()
            for ch_id, ktype in rows:
                validated_by_ch.setdefault(int(ch_id), []).append(ktype)

        base_tp = base_fp = base_fn = 0
        upd_tp = upd_fp = upd_fn = 0
        upd_recs = 0
        upd_anti = 0
        upd_explained = 0

        # Mediana por canal no próprio test set para definir alvo de desempenho acima da mediana
        by_ch_eng: Dict[int, List[float]] = {}
        for v in test_videos:
            ch = int(v.get("channel_id") or 0)
            by_ch_eng.setdefault(ch, []).append(float(v.get("engagement_ratio") or 0.0))
        ch_med = {ch: _median(vals) for ch, vals in by_ch_eng.items()}

        for v in test_videos:
            ch = int(v.get("channel_id") or 0)
            eng = float(v.get("engagement_ratio") or 0.0)
            actual_good = eng > ch_med.get(ch, 0.0) and eng > 0.0
            feats = v.get("editorial_features") or self.extractor.extract(v)
            is_silent = feats["audio_visual_relation"] == "silent_or_unusable_audio"
            is_rejected = v.get("processing_state") == "editorially_rejected"

            # Baseline ingênuo: apenas ter > 0 cortes
            base_pred = feats["cuts_count"] != NOT_AVAILABLE and int(feats["cuts_count"]) >= 1
            if base_pred and actual_good:
                base_tp += 1
            elif base_pred and not actual_good:
                base_fp += 1
            elif not base_pred and actual_good:
                base_fn += 1

            # Atualizado: bloqueia silenciosos/rejeitados e usa regras validadas do canal (ou fallback seguro de qualidade)
            if is_silent or is_rejected:
                upd_anti += 1
                upd_pred = False
            else:
                ch_rules = validated_by_ch.get(ch, [])
                if ch_rules:
                    upd_recs += 1
                    score = 0
                    if "ritmo_de_cortes_dinamico" in ch_rules and feats["cuts_count"] != NOT_AVAILABLE and int(feats["cuts_count"]) >= 4:
                        score += 1
                    if "estrutura_narrativa_real" in ch_rules and feats["has_narration"] is True:
                        score += 1
                    if "gancho_inicial_forte" in ch_rules and feats["hook_type"] in ("question", "curiosity_or_fact", "direct_command"):
                        score += 1
                    if "progressao_narrativa_completa" in ch_rules and feats["narrative_progression"] == "complete_3_acts":
                        score += 1
                    if "texto_na_tela_suporte" in ch_rules and feats["text_on_screen_detected"] is True:
                        score += 1
                    upd_pred = score >= 1
                    upd_explained += 1
                else:
                    upd_explained += 1
                    upd_pred = bool(
                        (feats["cuts_count"] != NOT_AVAILABLE and int(feats["cuts_count"]) >= 1)
                        or feats["has_narration"] is True
                    )

            if upd_pred and actual_good:
                upd_tp += 1
            elif upd_pred and not actual_good:
                upd_fp += 1
            elif not upd_pred and actual_good:
                upd_fn += 1

        base_prec = round((base_tp / max(1, base_tp + base_fp)) * 100.0, 1)
        upd_prec = round((upd_tp / max(1, upd_tp + upd_fp)) * 100.0, 1)

        return {
            "sample_size": len(test_videos),
            "overlap_with_training": overlap,
            "is_causal_experiment": False,
            "note": "Avaliação observacional retrospectiva em split de teste disjunto (15%); não equivale a experimento causal randomizado no YouTube.",
            "baseline": {
                "tp": base_tp,
                "fp": base_fp,
                "fn": base_fn,
                "precision_pct": base_prec,
                "anti_patterns_blocked": 0,
                "channel_specific_recommendations": 0,
            },
            "updated_with_phase18": {
                "tp": upd_tp,
                "fp": upd_fp,
                "fn": upd_fn,
                "precision_pct": upd_prec,
                "anti_patterns_blocked": upd_anti,
                "channel_specific_recommendations": upd_recs,
                "decisions_explained": upd_explained,
            },
        }
