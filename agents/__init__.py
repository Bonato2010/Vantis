# VANTIS Multi-Agent Architecture
# Backward-compatible exports for legacy roundtable deliberation
from .base_agent import BaseSpecialistAgent, AgentEvaluationResult
from .specialists import (
    SportsAgent, PodcastAgent, ComedyAgent, StorytellingAgent,
    RetentionAgent, EditingAgent, AudienceAgent, TrendsAgent,
    OriginalityAgent, ContentDirectorAgent
)
from .company import ContentCompany

# VANTIS 10 Autonomous Operational Agents Architecture
from .base_vantis_agent import (
    AgentState, AgentTaskContext, AgentExecutionResult, VantisBaseAgent
)
from .opportunity_research_agent import OpportunityResearchAgent
from .trend_analysis_agent import TrendAnalysisAgent
from .editorial_planning_agent import EditorialPlanningAgent
from .scriptwriting_agent import ScriptwritingAgent
from .audiovisual_analysis_agent import AudiovisualAnalysisAgent
from .transcription_agent import TranscriptionAgent
from .media_prep_editing_agent import MediaPrepEditingAgent
from .quality_review_agent import QualityReviewAgent
from .performance_analytics_agent import PerformanceAnalyticsAgent
from .task_coordinator_agent import TaskCoordinatorAgent
from .agent_registry import AgentRegistry

__all__ = [
    # Legacy
    "BaseSpecialistAgent", "AgentEvaluationResult",
    "SportsAgent", "PodcastAgent", "ComedyAgent", "StorytellingAgent",
    "RetentionAgent", "EditingAgent", "AudienceAgent", "TrendsAgent",
    "OriginalityAgent", "ContentDirectorAgent", "ContentCompany",
    # VANTIS
    "AgentState", "AgentTaskContext", "AgentExecutionResult", "VantisBaseAgent",
    "OpportunityResearchAgent", "TrendAnalysisAgent", "EditorialPlanningAgent",
    "ScriptwritingAgent", "AudiovisualAnalysisAgent", "TranscriptionAgent",
    "MediaPrepEditingAgent", "QualityReviewAgent", "PerformanceAnalyticsAgent",
    "TaskCoordinatorAgent", "AgentRegistry"
]
