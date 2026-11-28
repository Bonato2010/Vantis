import json
import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Users\jcvse\OneDrive\Desktop\Daniel\CENTRAL SHORTS")
sys.path.insert(0, str(BASE_DIR))

from services.production.editorial_production_engine import EditorialProductionEngine
from services.production.package_renderer import PackageRendererService

eng = EditorialProductionEngine()
renderer = PackageRendererService()
pkgs = eng.list_packages(limit=20)
approved = [p for p in pkgs if p["status"] == "APPROVED_FOR_PRODUCTION"]
gate_report = {
    "total_packages": len(pkgs),
    "approved_for_production_count": len(approved),
    "ready_for_review_count": sum(1 for p in pkgs if p["status"] == "READY_FOR_REVIEW"),
    "pilot_rendered_count": 0,
    "gate_status": "AWAITING_HUMAN_APPROVAL_AND_ASSETS",
    "note": "Nenhum pacote alterado automaticamente para APPROVED_FOR_PRODUCTION; renderização de produção aguarda aprovação humana no dashboard e seleção de ativos para cenas ASSET_NEEDED.",
}
out = BASE_DIR / "docs" / "audits" / "phase22_pilot_gate_status.json"
out.write_text(json.dumps(gate_report, indent=2, ensure_ascii=False), encoding="utf-8")
print("PILOT GATE:", json.dumps(gate_report, ensure_ascii=False))
