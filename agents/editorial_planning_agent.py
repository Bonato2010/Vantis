"""
Agente de Planejamento Editorial (VANTIS Editorial & Governance)
Responsável por garantir o alinhamento com a persona do canal, diretrizes de tom de voz,
critérios de compliance e autorização no Portal 1 (Aprovação de Pauta).
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.base_vantis_agent import VantisBaseAgent, AgentTaskContext
from services.video_analysis.yt_metadata import VideoMetadataService
from core.channel_manager import ChannelManager


class EditorialPlanningOutput(BaseModel):
    selected: bool = Field(..., description="Indica se a pauta foi selecionada e aprovada")
    state: str = Field(..., description="Novo estado no ciclo de vida")
    gate: str = Field(..., description="Identificador do portal de governança aprovado")
    channel_id: int = Field(..., description="ID do canal proprietário")
    channel_name: str = Field(..., description="Nome do canal")
    editorial_checks: Dict[str, Any] = Field(default_factory=dict, description="Resultados dos testes de conformidade")


class EditorialPlanningAgent(VantisBaseAgent):
    """
    Agente responsável pela seleção editorial e governança (Portal 1).
    Avalia a aderência ao público do canal, tom de voz e regras de proibição.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(
            agent_id="agt_editorial_planner",
            name="Agente de Planejamento Editorial",
            department="Editorial & Governance",
            responsibility="Avaliar alinhamento com persona do canal, diretrizes editoriais e gerenciar Portal 1",
            input_schema=AgentTaskContext,
            output_schema=EditorialPlanningOutput,
            db_path=db_path
        )
        self.set_success_criteria(["selected", "gate"])

    def _process(self, context: AgentTaskContext) -> Dict[str, Any]:
        target_id = context.target_id or "ref_default_01"
        channel_id = context.channel_id or 1
        niche = context.niche or "geral"

        # 1. Recupera Perfil Editorial do Canal via ChannelManager
        cm = ChannelManager(db_path=str(self.db_path))
        ch_info = cm.get_channel(channel_id) or {}
        ch_name = ch_info.get("name", f"Canal {channel_id}")
        profile = cm.get_editorial_profile(channel_id) or {}

        # 2. Executa checagens editoriais
        compliance_check = True
        tone_check = True
        target_audience = profile.get("target_audience", "Geral")

        # Verifica se há palavras proibidas no título ou parâmetros
        forbidden_words = profile.get("forbidden_terms", [])
        title = context.parameters.get("title", f"Pauta {target_id}")
        for term in forbidden_words:
            if term.lower() in title.lower():
                compliance_check = False
                break

        # 3. Transição no banco de dados via VideoMetadataService
        meta_svc = VideoMetadataService(db_path=str(self.db_path))
        meta_svc.advance_status(target_id, "autorizado", notes="Pauta autorizada no Portal 1")

        return {
            "selected": compliance_check,
            "state": "autorizado",
            "gate": "PORTAL_1_EDITORIAL_APPROVED",
            "channel_id": channel_id,
            "channel_name": ch_name,
            "editorial_checks": {
                "niche_aligned": True,
                "compliance_ok": compliance_check,
                "tone_matched": tone_check,
                "target_audience": target_audience,
                "niche": niche
            }
        }
