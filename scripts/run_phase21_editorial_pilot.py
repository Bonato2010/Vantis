"""
VANTIS — Fase 21: Piloto Editorial Controlado de 10 Pacotes (2 por Canal)
Usa referências reais de audiovisual_library e memória isolada de cada canal.
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.production.editorial_production_engine import EditorialProductionEngine

OUT_JSON = BASE_DIR / "docs" / "audits" / "phase21_pilot_10_packages.json"

PILOT_THEMES = {
    1: [
        "A regra esquecida do impedimento que decidiu uma semifinal",
        "Por que goleiros mudaram o posicionamento nos pênaltis modernos",
    ],
    2: [
        "O detalhe cronológico que revelou a contradição de um álibi real",
        "Como a perícia de vestígios resolveu um caso arquivado há décadas",
    ],
    3: [
        "Quando a reunião online de segunda-feira dura mais que o projeto",
        "A diferença entre o que você planejou no domingo e a realidade da terça",
    ],
    4: [
        "Por que o céu noturno é escuro mesmo com bilhões de estrelas",
        "Como o cérebro preenche pontos cegos sem você perceber",
    ],
    5: [
        "A armadilha dos micro-objetivos que destrói seu bloco de foco",
        "Como usar blocos de 25 minutos sem cair em fadiga decisória",
    ],
}


def main():
    engine = EditorialProductionEngine()
    generated = []
    for ch_id in range(1, 6):
        refs = engine.list_eligible_references(ch_id, limit=5)
        for idx, theme in enumerate(PILOT_THEMES[ch_id]):
            ref_id = refs[idx]["source_id"] if idx < len(refs) else None
            pkg = engine.generate_package(
                channel_id=ch_id,
                theme=theme,
                reference_source_id=ref_id,
                target_duration_sec=36.0,
            )
            p_obj = pkg["package"]
            generated.append({
                "id": pkg["id"],
                "package_uid": pkg["package_uid"],
                "channel_id": ch_id,
                "channel_name": pkg["channel_name"],
                "theme": theme,
                "reference_source_id": ref_id,
                "status": pkg["status"],
                "scenes_count": p_obj["audiovisual_plan"]["total_scenes"],
                "applied_memories_count": len(p_obj["applied_memories"]),
                "validated_used": p_obj["memory_summary"]["validated_used"],
                "hypotheses_used": p_obj["memory_summary"]["hypotheses_used"],
                "insufficient_evidence_warning": p_obj["memory_summary"]["insufficient_evidence_warning"],
                "hook_preview": p_obj["script"]["hook"],
            })
            print(
                f"[Ch{ch_id}] Pkg #{pkg['id']} ({pkg['status']}) | ref={ref_id} | "
                f"scenes={p_obj['audiovisual_plan']['total_scenes']} | "
                f"val={p_obj['memory_summary']['validated_used']} hyp={p_obj['memory_summary']['hypotheses_used']}",
                flush=True,
            )

    OUT_JSON.write_text(json.dumps({"total_generated": len(generated), "packages": generated}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"=== PILOTO FASE 21 CONCLUÍDO: {len(generated)}/10 PACOTES ===")


if __name__ == "__main__":
    main()
