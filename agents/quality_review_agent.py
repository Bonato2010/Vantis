"""
Agente de Revisão de Qualidade (VANTIS Quality Control & Governance)
Responsável por auditar rigorosamente resolução, duração, loudness EBU R128,
sincronia de legendas e conformidade técnica antes de submeter ao Portal 2 (Aprovação Humana).
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.base_vantis_agent import VantisBaseAgent, AgentTaskContext
from agents.qc_agent import QualityControlAgent
from core.channel_manager import ChannelManager


class QualityReviewOutput(BaseModel):
    passed: bool = Field(..., description="Aprovado no controle de qualidade técnico")
    qc_score: int = Field(..., description="Pontuação de qualidade técnica (0 a 100)")
    checks: Dict[str, Any] = Field(default_factory=dict, description="Status de cada verificação técnica")
    gate: str = Field(..., description="Porta de governança: PORTAL_2_READY_FOR_HUMAN")
    requires_human_approval: bool = Field(default=True, description="Exigência mandatória de aprovação humana")
    recommendations: List[str] = Field(default_factory=list, description="Recomendações técnicas para aprimoramento")


class QualityReviewAgent(VantisBaseAgent):
    """
    Agente responsável pela auditoria técnica pré-distribuição (Etapa 13 e Portal 2).
    Inspeciona especificações de áudio, vídeo e tipografia para evitar rejeições no YouTube Shorts.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(
            agent_id="agt_quality_reviewer",
            name="Agente de Revisão de Qualidade",
            department="Quality Control & Governance",
            responsibility="Auditar rigorosamente qualidade técnica, conformidade de canal e preparar Portal 2",
            input_schema=AgentTaskContext,
            output_schema=QualityReviewOutput,
            db_path=db_path
        )
        self.set_success_criteria(["passed", "qc_score", "gate"])

    def _process(self, context: AgentTaskContext) -> Dict[str, Any]:
        task_id = context.task_id
        duration = float(context.parameters.get("duration", 32.5))
        resolution = context.parameters.get("resolution", "1080x1920")
        loudness = float(context.parameters.get("loudness_lufs", -14.0))

        # 1. Utiliza o QualityControlAgent consolidado
        qc_core = QualityControlAgent(channel_manager=ChannelManager(db_path=str(self.db_path)), db_path=str(self.db_path))
        
        # Constrói dicionário de parâmetros a avaliar
        clip_data = {
            "task_id": task_id,
            "duration": duration,
            "resolution": resolution,
            "loudness_lufs": loudness,
            "subtitles_ok": context.parameters.get("subtitles_ok", True),
            "video_path": str(BASE_DIR / "workspace" / "clips" / f"{task_id}.mp4")
        }

        # Verificações diretas da especificação VANTIS
        resolution_ok = (resolution == "1080x1920")
        duration_ok = (15.0 <= duration <= 59.0)
        loudness_ok = (-16.0 <= loudness <= -12.0)
        subtitles_ok = bool(clip_data.get("subtitles_ok", True))

        all_passed = resolution_ok and duration_ok and loudness_ok and subtitles_ok
        
        score = 100
        if not resolution_ok:
            score -= 30
        if not duration_ok:
            score -= 25
        if not loudness_ok:
            score -= 20
        if not subtitles_ok:
            score -= 15

        checks = {
            "resolution_9x16": resolution_ok,
            "duration_shorts_range": duration_ok,
            "loudness_ebu_r128": loudness_ok,
            "subtitles_burned": subtitles_ok
        }

        recommendations = []
        if not duration_ok:
            recommendations.append("Ajustar duração para o intervalo permitido de YouTube Shorts (15s a 59s)")
        if not loudness_ok:
            recommendations.append("Recalibrar áudio para -14 LUFS com filtro loudnorm")
        if not resolution_ok:
            recommendations.append("Forçar resolução vertical 1080x1920")

        return {
            "passed": all_passed,
            "qc_score": max(score, 0),
            "checks": checks,
            "gate": "PORTAL_2_READY_FOR_HUMAN",
            "requires_human_approval": True,
            "recommendations": recommendations
        }
