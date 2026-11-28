"""
VANTIS — Fase 18: Aprendizado Editorial Evolutivo, Split 70/15/15 e Avaliação Antes/Depois
Consome os vídeos reais analisados do benchmark de 250 vídeos, aplica split estratificado
anti-vazamento, atualiza a memória editorial apenas com train+val e avalia no split test disjunto.
"""

import json
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.learning.editorial_memory_engine import EditorialMemoryEngine

EXECUTION_DATA_JSON = BASE_DIR / "docs" / "audits" / "phase18_benchmark_execution_data.json"
OUTPUT_JSON = BASE_DIR / "docs" / "audits" / "phase18_learning_and_eval.json"


def main():
    if not EXECUTION_DATA_JSON.exists():
        raise FileNotFoundError(f"Arquivo de execução não encontrado: {EXECUTION_DATA_JSON}")

    with open(EXECUTION_DATA_JSON, "r", encoding="utf-8") as f:
        bench = json.load(f)

    records = bench.get("records", [])
    # Carrega payload completo do SQLite para cada vídeo válido do benchmark
    engine = EditorialMemoryEngine()
    eligible_videos = []
    with engine.als._get_conn() as conn:
        conn.row_factory = sqlite3.Row
        for r in records:
            if r.get("state") == "failed":
                continue
            row = conn.execute(
                "SELECT * FROM audiovisual_library WHERE source_id = ?",
                (r["video_id"],),
            ).fetchone()
            if not row:
                continue
            d = dict(row)
            d["channel_id"] = r["channel_id"]
            d["sha256"] = r.get("sha256")
            d["editorial_features"] = r.get("editorial_features")
            eligible_videos.append(d)

    splits = engine.build_leak_free_splits(eligible_videos)
    train_val = splits["train"] + splits["validation"]
    train_val_ids = {str(v.get("source_id") or v.get("id")) for v in train_val}

    learning_res = engine.run_evolutionary_learning(train_val, pilot_phase=18)
    eval_res = engine.evaluate_utility_before_after(splits["test"], train_ids=train_val_ids)

    # Verifica isolamento entre canais após gravação
    isolation_checks = {}
    for ch_id in range(1, 6):
        mem = engine.als.get_channel_editorial_memory(ch_id)
        recs = mem.get("channel_specific_rules") or mem.get("records") or mem.get("knowledge_records") or []
        isolation_checks[str(ch_id)] = {
            "channel_records": len(recs),
            "other_channel_leaks": len(mem.get("other_channel_leaks", [])),
        }

    result = {
        "eligible_videos_count": len(eligible_videos),
        "splits": {
            "train_count": len(splits["train"]),
            "validation_count": len(splits["validation"]),
            "test_count": len(splits["test"]),
            "per_channel_counts": splits["per_channel_counts"],
            "duplicates_removed": splits["duplicates_removed"],
            "leakage_checks": splits["leakage_checks"],
        },
        "learning": learning_res,
        "utility_before_after": eval_res,
        "isolation_checks": isolation_checks,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("=== FASE 18 LEARNING & EVAL CONCLUÍDO ===", flush=True)
    print(f"Elegíveis: {len(eligible_videos)} | Train: {len(splits['train'])} | Val: {len(splits['validation'])} | Test: {len(splits['test'])}", flush=True)
    print(f"Leak-free: {splits['leakage_checks']['leak_free']}", flush=True)
    print(f"Conhecimentos gerados: {len(learning_res['recorded_knowledge'])}", flush=True)
    print(f"Atualizações de hipóteses anteriores: {len(learning_res['prior_hypothesis_updates'])}", flush=True)
    print(f"Baseline prec: {eval_res['baseline']['precision_pct']}% -> Atualizado prec: {eval_res['updated_with_phase18']['precision_pct']}%", flush=True)


if __name__ == "__main__":
    main()
