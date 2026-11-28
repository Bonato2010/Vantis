"""
VANTIS — Fase 20: Execução Real End-to-End em Amostra de 5 Shorts (1 por Canal)
Valida o fluxo completo de 16 etapas com arquivos reais já disponíveis no disco,
sem iniciar novos lotes de 250, 500 ou 7.000 vídeos.
"""

import json
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.orchestration.vantis_core_pipeline import VantisCorePipeline

BENCH_JSON = BASE_DIR / "docs" / "audits" / "phase18_benchmark_execution_data.json"
OUT_JSON = BASE_DIR / "docs" / "audits" / "phase20_e2e_sample_5.json"


def main():
    recs = json.loads(BENCH_JSON.read_text(encoding="utf-8")).get("records", [])
    # Seleciona 1 vídeo real válido por canal (canais 1 a 5)
    sample_5 = []
    seen_ch = set()
    for r in recs:
        ch = int(r["channel_id"])
        if ch in seen_ch or r.get("state") != "learning_candidate":
            continue
        p = BASE_DIR / "workspace" / "downloads" / "benchmark250" / f"ch_{ch}" / f"{r['video_id']}.mp4"
        if not p.is_file():
            for ext in (".webm", ".mkv"):
                alt = p.with_suffix(ext)
                if alt.is_file():
                    p = alt
                    break
        if p.is_file():
            seen_ch.add(ch)
            sample_5.append((r, p))
        if len(sample_5) == 5:
            break

    pipe = VantisCorePipeline()
    results = []
    for r, local_p in sample_5:
        spec = {
            "id": r["video_id"],
            "channel_id": r["channel_id"],
            "niche": r["niche"],
            "title": r["title"],
            "url": r["url"],
            "views": r.get("views_count", 0),
            "likes": r.get("likes_count", 0),
            "comments": r.get("comment_count", 0),
        }
        out = pipe.process_video_end_to_end(spec, local_file_override=local_p)
        results.append(out)
        print(
            f"[Ch{out['channel_id']}] {out['video_id']} -> {out['final_state']} ({out['db_processing_state']}) | "
            f"{out['duration_seconds']}s | LUFS={out['integrated_lufs']} | cuts={out['cuts_count']} | "
            f"words={out['transcript_word_count']} | recs={len(out['editorial_recommendations'])} | {out['elapsed_seconds']}s",
            flush=True,
        )

    OUT_JSON.write_text(json.dumps({"sample_count": len(results), "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"=== FASE 20 E2E CONCLUÍDO: {len(results)}/5 VÍDEOS ===")


if __name__ == "__main__":
    main()
