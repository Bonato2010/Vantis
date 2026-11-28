"""
VANTIS — Seleção Auditada de Candidatos para o Benchmark de 250 Vídeos (Fase 18)
Critérios Rigorosos:
- Exatamente 250 candidatos únicos (50 por canal para os 5 canais).
- Duração estrita: 0 < duração <= 60.0s.
- Exclusão total de IDs históricos já presentes em shorts_central.db (143 IDs).
- Deduplicação por ID e por fingerprint (título normalizado + duração) entre todos os canais.
- Diversidade de popularidade (emerging, mid_tier, viral) e duração.
- Persistência incremental em docs/audits/phase18_selected_candidates.json.
"""
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.discovery.scale_selector import ScaleSelectionPlanner

DB_PATH = BASE_DIR / "database" / "shorts_central.db"
OUTPUT_JSON = BASE_DIR / "docs" / "audits" / "phase18_selected_candidates.json"

CHANNELS_CONFIG = [
    {
        "channel_id": 1,
        "name": "Canal 01 - Futebol em 60 Segundos",
        "niche": "futebol_outros",
        "target_count": 50,
        "queries": [
            "shorts futebol gols lances incriveis brasil",
            "futebol lances inacreditaveis shorts brasil",
            "dribles incriveis futebol shorts brasil",
            "polemicas arbitragem lances futebol shorts",
            "momentos historicos futebol shorts brasil",
            "curiosidades futebol lances rapidos shorts",
            "shorts futebol brasileiro golaco",
            "shorts melhores momentos futebol brasil",
            "shorts copa do brasil lances",
            "shorts brasileirao gols hoje",
            "shorts futebol analise tatica rapida",
            "shorts historia do futebol curiosidades",
            "shorts goleiros defesas impossiveis",
            "shorts futebol selecao brasileira",
            "shorts futebol var decisao polemica",
        ],
        "negative_keywords": ["moda", "jeans", "cintura", "vestido", "bermuda", "tigrinho", "cassino", "gameplay", "fifa", "efootball", "pes"],
    },
    {
        "channel_id": 2,
        "name": "Canal 02 - Arquivo Sombrio (Casos Reais)",
        "niche": "casos_policiais",
        "target_count": 50,
        "queries": [
            "policia #shorts",
            "crime real #shorts",
            "true crime #shorts",
            "casos criminais #shorts",
            "investigacao criminal #shorts",
            "abordagem policial #shorts",
            "rotam bope #shorts",
            "policia militar #shorts",
            "policia civil #shorts",
            "misterio real #shorts",
            "desaparecimento #shorts",
            "pericia criminal #shorts",
            "seguranca publica #shorts",
            "ocorrencia policial #shorts",
            "justica crime #shorts",
            "historia sombria #shorts",
            "casos bizarros reais #shorts",
            "sobrevivencia crime #shorts",
            "prisao #shorts",
            "delegacia #shorts",
            "true crime story #shorts",
            "cold case #shorts",
        ],
        "negative_keywords": ["costura", "maquina", "gameplay", "gta", "free fire", "jeans", "cintura", "moda", "tigrinho", "cassino", "maquiagem", "humor", "unhas", "look"],
    },
    {
        "channel_id": 3,
        "name": "Canal 03 - Rir para Não Chorar",
        "niche": "humor",
        "target_count": 50,
        "queries": [
            "comedia #shorts",
            "humor #shorts",
            "stand up #shorts",
            "memes #shorts",
            "engracado #shorts",
            "pegadinha #shorts",
            "piada #shorts",
            "humor brasil #shorts",
            "comedia brasil #shorts",
            "trolagem #shorts",
            "esquete comedia #shorts",
            "dublagem engracada #shorts",
            "imitacao comedia #shorts",
            "risada #shorts",
            "casal comedia #shorts",
            "trabalho humor #shorts",
            "familia humor #shorts",
            "funny #shorts",
        ],
        "negative_keywords": ["triste", "morte", "crime", "policia", "jeans", "cintura", "moda", "tigrinho", "cassino", "politica", "sfx", "sound effect"],
    },
    {
        "channel_id": 4,
        "name": "Canal 04 - Mente Curiosa & Ciência",
        "niche": "curiosidades",
        "target_count": 50,
        "queries": [
            "ciencia #shorts",
            "curiosidades #shorts",
            "astronomia #shorts",
            "fisica #shorts",
            "biologia #shorts",
            "quimica #shorts",
            "universo #shorts",
            "corpo humano #shorts",
            "experimento #shorts",
            "fatos curiosos #shorts",
            "voce sabia #shorts",
            "tecnologia #shorts",
            "neurociencia #shorts",
            "historia ciencia #shorts",
            "animais curiosidades #shorts",
            "science facts #shorts",
            "space #shorts",
        ],
        "negative_keywords": ["fofoca", "celebridades", "jeans", "cintura", "moda", "tigrinho", "cassino", "maquiagem"],
    },
    {
        "channel_id": 5,
        "name": "Canal 05 - Mente Focada & Produtividade",
        "niche": "desenvolvimento_pessoal",
        "target_count": 50,
        "queries": [
            "produtividade #shorts",
            "disciplina #shorts",
            "habitos #shorts",
            "foco #shorts",
            "estoicismo #shorts",
            "procrastinacao #shorts",
            "motivacao #shorts",
            "desenvolvimento pessoal #shorts",
            "estudos foco #shorts",
            "rotina matinal #shorts",
            "mentalidade #shorts",
            "gestao de tempo #shorts",
            "dopamina foco #shorts",
            "alta performance #shorts",
            "psicologia habitos #shorts",
            "self improvement #shorts",
            "productivity tips #shorts",
        ],
        "negative_keywords": ["jeans", "cintura", "moda", "tigrinho", "cassino", "renda extra facil", "fique rico rapido"],
    },
]


def load_excluded_state() -> tuple[Set[str], Set[str]]:
    excluded_ids: Set[str] = set()
    excluded_fps: Set[str] = set()
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            for sid, title, dur in conn.execute("SELECT source_id, title, duration_seconds FROM audiovisual_library"):
                if sid:
                    excluded_ids.add(str(sid))
                if title and dur:
                    norm_t = " ".join(str(title).lower().split())
                    excluded_fps.add(f"{norm_t}|{round(float(dur), 1)}")
    print(f"[Deduplicação] {len(excluded_ids)} IDs históricos e {len(excluded_fps)} fingerprints excluídos.", flush=True)
    return excluded_ids, excluded_fps


def load_existing_manifest() -> Dict[str, Any]:
    if OUTPUT_JSON.exists():
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"candidates": []}


def save_manifest(candidates: List[Dict[str, Any]]):
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "pilot_name": "FASE18_BENCHMARK_250_SHORTS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(candidates),
        "target_channels_count": 5,
        "candidates_per_channel": 50,
        "zero_cost_enforced": True,
        "candidates": candidates,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f" -> [Manifesto Atualizado] {len(candidates)} candidatos salvos em {OUTPUT_JSON.name}", flush=True)


def search_candidates_for_channel(
    config: Dict[str, Any],
    seen_ids: Set[str],
    seen_fps: Set[str],
    existing_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    channel_id = config["channel_id"]
    ch_name = config["name"]
    niche = config["niche"]
    target = config["target_count"]
    queries = config["queries"]
    neg_kw = config["negative_keywords"]

    current = [c for c in existing_candidates if c["channel_id"] == channel_id]
    if len(current) >= target:
        print(f"\n[Canal {channel_id}] Já possui {len(current)}/{target} candidatos. Preservado.", flush=True)
        return current[:target]

    print(f"\n=== Buscando Candidatos: {ch_name} ({niche}) [{len(current)}/{target}] ===", flush=True)
    pool: List[Dict[str, Any]] = []

    for q in queries:
        if len(current) + len(pool) >= target * 2:
            break
        print(f"  -> Query: '{q}'...", flush=True)
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--match-filter", "duration <= 60 & !is_live",
            "--dump-json",
            "--no-playlist",
            f"ytsearch50:{q}",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding="utf-8", timeout=70)
            if res.stdout:
                for line in res.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    try:
                        info = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    vid = str(info.get("id") or "").strip()
                    dur = info.get("duration")
                    title = str(info.get("title") or "").strip()
                    if not vid or not dur or float(dur) <= 0.0 or float(dur) > 60.0:
                        continue
                    norm_t = " ".join(title.lower().split())
                    fp = f"{norm_t}|{round(float(dur), 1)}"
                    if vid in seen_ids or fp in seen_fps:
                        continue
                    if any(nk in norm_t for nk in neg_kw):
                        continue

                    seen_ids.add(vid)
                    seen_fps.add(fp)
                    views = int(info.get("view_count") or 0)
                    likes = int(info.get("like_count") or 0)
                    comments = int(info.get("comment_count") or 0)
                    eng = round(((likes + comments) / views) * 100.0, 2) if views > 0 else 0.0

                    pool.append({
                        "id": vid,
                        "url": info.get("webpage_url") or f"https://www.youtube.com/shorts/{vid}",
                        "title": title,
                        "creator": info.get("uploader") or info.get("channel") or "Desconhecido",
                        "channel_id_source": info.get("channel_id") or "",
                        "duration_seconds": float(dur),
                        "views": views,
                        "likes": likes,
                        "comments": comments,
                        "engagement_ratio": eng,
                        "channel_id": channel_id,
                        "channel_name": ch_name,
                        "niche": niche,
                        "query_source": q,
                        "metadata_origin": "yt-dlp --dump-json",
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                        "is_available": True,
                    })
        except Exception as e:
            print(f"    [Aviso yt-dlp]: {e}", flush=True)

    needed = target - len(current)
    planner = ScaleSelectionPlanner()
    plan = planner.plan_stratified_selection(pool, target_per_channel=needed)
    selected = plan["selected"]
    # Se estratificação não preencheu tudo por falta de um tier, completa com restantes do pool
    if len(selected) < needed:
        sel_ids = {s["id"] for s in selected}
        for p in pool:
            if p["id"] not in sel_ids:
                p["popularity_tier"] = planner.classify_popularity_tier(p["views"])
                p["inclusion_rationale"] = "Complemento de pool real após estratificação por tier"
                selected.append(p)
                if len(selected) >= needed:
                    break

    combined = (current + selected)[:target]
    print(f" -> [Canal {channel_id}] Selecionados: {len(combined)}/{target} | Tiers: {plan['tier_distribution']}", flush=True)
    return combined


def main():
    excluded_ids, excluded_fps = load_excluded_state()
    manifest = load_existing_manifest()
    existing = manifest.get("candidates", [])

    seen_ids = set(excluded_ids)
    seen_fps = set(excluded_fps)
    for c in existing:
        seen_ids.add(str(c["id"]))
        norm_t = " ".join(str(c.get("title") or "").lower().split())
        seen_fps.add(f"{norm_t}|{round(float(c.get('duration_seconds') or 0.0), 1)}")

    all_selected: List[Dict[str, Any]] = []
    for cfg in CHANNELS_CONFIG:
        ch_cands = search_candidates_for_channel(cfg, seen_ids, seen_fps, existing)
        all_selected.extend(ch_cands)
        save_manifest(all_selected)

    print(f"\n=== SELEÇÃO FASE 18 CONCLUÍDA: {len(all_selected)}/250 CANDIDATOS ===", flush=True)


if __name__ == "__main__":
    main()
