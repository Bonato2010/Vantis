"""
VANTIS Agent Registry & Directory Service
Gerencia a descoberta, inicialização, injeção de dependências e diagnóstico
de todos os 10 agentes operacionais autônomos da plataforma.
"""
from typing import Dict, Any, List, Optional, Type
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.base_vantis_agent import VantisBaseAgent, AgentState
from agents.opportunity_research_agent import OpportunityResearchAgent
from agents.trend_analysis_agent import TrendAnalysisAgent
from agents.editorial_planning_agent import EditorialPlanningAgent
from agents.scriptwriting_agent import ScriptwritingAgent
from agents.audiovisual_analysis_agent import AudiovisualAnalysisAgent
from agents.transcription_agent import TranscriptionAgent
from agents.media_prep_editing_agent import MediaPrepEditingAgent
from agents.quality_review_agent import QualityReviewAgent
from agents.performance_analytics_agent import PerformanceAnalyticsAgent
from agents.task_coordinator_agent import TaskCoordinatorAgent


class AgentRegistry:
    """
    Catálogo Central e Gerenciador de Ciclo de Vida dos Agentes VANTIS.
    Permite busca por ID, listagem de capacidades e telemetria unificada.
    """

    _instance: Optional["AgentRegistry"] = None

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(BASE_DIR / "database" / "shorts_central.db")
        self._agents: Dict[str, VantisBaseAgent] = {}
        self._register_default_agents()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> "AgentRegistry":
        if cls._instance is None or (db_path and cls._instance.db_path != str(db_path)):
            cls._instance = cls(db_path=db_path)
        return cls._instance

    def _register_default_agents(self):
        """Instancia e registra os 10 agentes operacionais oficiais."""
        agent_classes: List[Type[VantisBaseAgent]] = [
            OpportunityResearchAgent,
            TrendAnalysisAgent,
            EditorialPlanningAgent,
            ScriptwritingAgent,
            AudiovisualAnalysisAgent,
            TranscriptionAgent,
            MediaPrepEditingAgent,
            QualityReviewAgent,
            PerformanceAnalyticsAgent,
            TaskCoordinatorAgent
        ]

        for cls in agent_classes:
            agent = cls(db_path=self.db_path)
            self._agents[agent.agent_id] = agent

    def register_agent(self, agent: VantisBaseAgent):
        """Registra um novo agente dinâmico no catálogo."""
        self._agents[agent.agent_id] = agent

    def get_agent(self, agent_id_or_name: str) -> Optional[VantisBaseAgent]:
        """Recupera um agente por seu ID ou nome aproximado."""
        if agent_id_or_name in self._agents:
            return self._agents[agent_id_or_name]
        
        # Busca por nome
        for agent in self._agents.values():
            if agent.name.lower() == agent_id_or_name.lower():
                return agent
        return None

    def list_all_agents(self) -> List[Dict[str, Any]]:
        """Retorna metadados e inventário de todos os agentes registrados."""
        return [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "department": a.department,
                "responsibility": a.responsibility,
                "state": a.state.value,
                "success_criteria": a.success_criteria,
                "has_input_schema": a.input_schema is not None,
                "has_output_schema": a.output_schema is not None
            }
            for a in self._agents.values()
        ]

    def health_check_all(self) -> Dict[str, Any]:
        """Executa verificação de integridade operacional de todos os agentes."""
        total = len(self._agents)
        healthy = 0
        details = {}

        for aid, agent in self._agents.items():
            is_healthy = agent.state != AgentState.ERROR
            if is_healthy:
                healthy += 1
            details[aid] = {
                "name": agent.name,
                "department": agent.department,
                "state": agent.state.value,
                "status": "ONLINE" if is_healthy else "DEGRADED"
            }

        return {
            "total_agents": total,
            "healthy_agents": healthy,
            "system_health_pct": round((healthy / total) * 100, 1) if total > 0 else 0,
            "agents": details
        }
