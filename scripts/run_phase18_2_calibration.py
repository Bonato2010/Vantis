"""
VANTIS — Fase 18.2: Calibração Editorial (Parte 9 da Fase 19)
Investiga a queda de precisão (42.3% -> 40.0%) usando train+validation,
calibra a lógica de decisão sem tocar no conjunto de teste e avalia uma única vez no teste.
"""

import json
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.learning.editorial_feature_extractor import NOT_AVAILABLE
from services.learning.editorial_memory_engine import EditorialMemoryEngine, _median

DB_PATH = BASE_DIR / "database" / "shorts_central.db"
EXEC_JSON = BASE_DIR / "docs" / "audits" / "phase18_benchmark_execution_data.json"
OUT_JSON = BASE_DIR / "docs" / "audits" / "phase18_2_calibration_results.json"


def evaluate_calibrated_policy(
    videos: list,
    validated_by_ch: dict,
    policy: str,
) -> dict:
    by_ch_eng = {}
    for v in videos:
        ch = int(v["channel_id"])
        by_ch_eng.setdefault(ch, []).append(float(v.get("engagement_ratio") or 0.0))
    ch_med = {ch: _median(vals) for ch, vals in by_ch_eng.items()}

    tp = fp = fn = tn = anti = recs = explained = 0
    per_channel = {}
    for v in videos:
        ch = int(v["channel_id"])
        eng = float(v.get("engagement_ratio") or 0.0)
        actual_good = eng > ch_med.get(ch, 0.0) and eng > 0.0
        feats = v["editorial_features"]
        is_silent = feats["audio_visual_relation"] == "silent_or_unusable_audio"
        is_rejected = v.get("processing_state") == "editorially_rejected"

        if policy == "baseline":
            pred = feats["cuts_count"] != NOT_AVAILABLE and int(feats["cuts_count"]) >= 1
        elif policy == "pre_calibration":
            if is_silent or is_rejected:
                anti += 1
                pred = False
            else:
                ch_rules = validated_by_ch.get(ch, [])
                if ch_rules:
                    recs += 1
                    explained += 1
                    score = 0
                    if "ritmo_de_cortes_dinamico" in ch_rules and feats["cuts_count"] != NOT_AVAILABLE and int(feats["cuts_count"]) >= 4:
                        score += 1
                    if "estrutura_narrativa_real" in ch_rules and feats["has_narration"] is True:
                        score += 1
                    if "gancho_inicial_forte" in ch_rules and feats["hook_type"] in ("question", "curiosity_or_fact", "direct_command"):
                        score += 1
                    if "progressao_narrativa_completa" in ch_rules and feats["narrative_progression"] == "complete_3_acts":
                        score += 1
                    pred = score >= 1
                else:
                    pred = bool(feats["has_narration"] is True and feats["cuts_count"] != NOT_AVAILABLE and int(feats["cuts_count"]) >= 4)
        else:  # calibrated: usa regras validadas quando existem no canal; nos canais sem regra validada, usa critério base não-restritivo (cuts>=1 ou narração) bloqueando apenas silenciosos/rejeitados
            if is_silent or is_rejected:
                anti += 1
                pred = False
            else:
                ch_rules = validated_by_ch.get(ch, [])
                if ch_rules:
                    recs += 1
                    explained += 1
                    score = 0
                    if "ritmo_de_cortes_dinamico" in ch_rules and feats["cuts_count"] != NOT_AVAILABLE and int(feats["cuts_count"]) >= 4:
                        score += 1
                    if "estrutura_narrativa_real" in ch_rules and feats["has_narration"] is True:
                        score += 1
                    if "gancho_inicial_forte" in ch_rules and feats["hook_type"] in ("question", "curiosity_or_fact", "direct_command"):
                        score += 1
                    if "progressao_narrativa_completa" in ch_rules and feats["narrative_progression"] == "complete_3_acts":
                        score += 1
                    pred = score >= 1
                else:
                    explained += 1
                    pred = bool(
                        (feats["cuts_count"] != NOT_AVAILABLE and int(feats["cuts_count"]) >= 1)
                        or feats["has_narration"] is True
                    )

        d = per_channel.setdefault(ch, {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
        if pred and actual_good:
            tp += 1
            d["tp"] += 1
        elif pred and not actual_good:
            fp += 1
            d["fp"] += 1
        elif not pred and actual_good:
            fn += 1
            d["fn"] += 1
        else:
            tn += 1
            d["tn"] += 1

    prec = round((tp / max(1, tp + fp)) * 100.0, 1)
    recall = round((tp / max(1, tp + fn)) * 100.0, 1)
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision_pct": prec, "recall_pct": recall,
        "anti_patterns_blocked": anti,
        "channel_specific_recommendations": recs,
        "decisions_explained": explained,
        "per_channel": per_channel,
    }


def main():
    engine = EditorialMemoryEngine(db_path=DB_PATH)
    recs = json.loads(EXEC_JSON.read_text(encoding="utf-8"))["records"]
    eligible = []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        for r in recs:
            if r.get("state") == "failed":
                continue
            row = conn.execute("SELECT * FROM audiovisual_library WHERE source_id = ?", (r["video_id"],)).fetchone()
            d = dict(row)
            d["channel_id"] = r["channel_id"]
            d["sha256"] = r.get("sha256")
            d["editorial_features"] = engine.extractor.extract(d)
            eligible.append(d)

        validated_by_ch = {}
        for ch_id, ktype in conn.execute(
            "SELECT target_channel_id, knowledge_type FROM editorial_knowledge_library WHERE classification = 'APRENDIZADO_VALIDADO' AND metadata LIKE '%\"pilot_phase\": 18%' AND target_channel_id IS NOT NULL"
        ).fetchall():
            validated_by_ch.setdefault(int(ch_id), []).append(ktype)

    splits = engine.build_leak_free_splits(eligible)
    val_set = splits["validation"]
    test_set = splits["test"]

    res = {
        "leak_free": splits["leakage_checks"]["leak_free"],
        "validated_rules_by_channel": validated_by_ch,
        "validation_split": {
            "n": len(val_set),
            "baseline": evaluate_calibrated_policy(val_set, validated_by_ch, "baseline"),
            "pre_calibration": evaluate_calibrated_policy(val_set, validated_by_ch, "pre_calibration"),
            "calibrated": evaluate_calibrated_policy(val_set, validated_by_ch, "calibrated"),
        },
        "test_split": {
            "n": len(test_set),
            "baseline": evaluate_calibrated_policy(test_set, validated_by_ch, "baseline"),
            "pre_calibration": evaluate_calibrated_policy(test_set, validated_by_ch, "pre_calibration"),
            "calibrated": evaluate_calibrated_policy(test_set, validated_by_ch, "calibrated"),
        },
    }
    OUT_JSON.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print("VAL:", json.dumps(res["validation_split"], indent=2))
    print("TEST:", json.dumps(res["test_split"], indent=2))


if __name__ == "__main__":
    main()
