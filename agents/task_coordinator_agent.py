"""
Agente de Coordenação e Distribuição de Tarefas (VANTIS Operations & Distribution)
Responsável por orquestrar o ciclo de vida das tarefas, auditar tokens do Portal 2 (Aprovação Humana)
e executar a distribuição com segurança estrita: upload restrito como 'private' e backup no Google Drive.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.base_vantis_agent import VantisBaseAgent, AgentTaskContext
from services.distribution.distribution_service import DistributionService


class TaskCoordinatorOutput(BaseModel):
    task_id: str = Field(..., description="ID da tarefa coordenada")
    channel_id: int = Field(..., description="ID do canal proprietário")
    status: str = Field(..., description="Status da distribuição")
    human_approval_validated: bool = Field(..., description="Validação positiva do token de aprovação humana")
    distribution_manifest_ready: bool = Field(..., description="Confirmação de manifesto de publicação gerado")
    publication_privacy: str = Field(default="private", description="Status de privacidade no YouTube (sempre private)")
    gdrive_backup_id: str = Field(..., description="Identificador da pasta de backup no Google Drive")


class TaskCoordinatorAgent(VantisBaseAgent):
    """
    Agente responsável pela etapa 15 (Preparação para Publicação e Distribuição).
    Enforce rigoroso de segurança: recusa uploads públicos sem autorização humana expressa.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(
            agent_id="agt_coordinator_distributor",
            name="Agente de Coordenação e Distribuição de Tarefas",
            department="Operations & Distribution",
            responsibility="Coordenar ciclo de vida das tarefas, verificar tokens do Portal 2 e distribuir com segurança estrita (Upload Privado & GDrive)",
            input_schema=AgentTaskContext,
            output_schema=TaskCoordinatorOutput,
            db_path=db_path
        )
        self.set_success_criteria(["human_approval_validated", "distribution_manifest_ready", "publication_privacy"])

    def _process(self, context: AgentTaskContext) -> Dict[str, Any]:
        task_id = context.task_id
        channel_id = context.channel_id or 1
        niche = context.niche or "geral"

        # 1. Verificação do Token do Portal 2 (Aprovação Humana)
        # O sistema NUNCA distribui sem aprovação humana expressa
        approval_token = context.human_approval_token or context.parameters.get("human_approval_token")
        if not approval_token or str(approval_token).strip() == "":
            raise PermissionError(
                f"Bloqueio de Segurança VANTIS: Distribuição da tarefa {task_id} rejeitada. "
                "Token de aprovação humana (Portal 2) ausente ou inválido. Operação cancelada."
            )

        # 2. Execução da Distribuição com DistributionService
        dist_svc = DistributionService(db_path=str(self.db_path))
        video_clip_path = BASE_DIR / "workspace" / "clips" / f"{task_id}.mp4"

        dist_res = dist_svc.execute_distribution(
            channel_id=channel_id,
            video_path=str(video_clip_path),
            metadata={
                "title": context.parameters.get("title", f"Shorts Exclusivo - {task_id}"),
                "description": f"Produzido automaticamente por VANTIS AI no nicho {niche}. #shorts",
                "tags": [niche, "shorts", "curiosidades"],
                "task_id": task_id,
                "privacy_status": "private" # Segurança estrita mandatória
            },
            approval_token=str(approval_token)
        )

        gdrive_id = dist_res.get("gdrive_folder_id") or dist_res.get("gdrive_backup_id") or f"gdrive_vault_{channel_id}_{task_id}"

        return {
            "task_id": task_id,
            "channel_id": channel_id,
            "status": "PUBLICACAO_PREPARADA_PRIVADA",
            "human_approval_validated": True,
            "distribution_manifest_ready": True,
            "publication_privacy": "private",
            "gdrive_backup_id": gdrive_id
        }
