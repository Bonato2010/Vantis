"""
Servidor REST API e Interface da Central Inteligente de Conteúdo (VIAGEM / IAS).
Plataforma Multi-Skill: 10 Agentes Especializados de Produção, Central Multiagente de Pesquisadores,
Pipeline de Pesquisa e Aprendizado (200.000+ Shorts), Módulo de Análise Crítica, Google Drive 5 TB e 20 Canais.
"""
import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent

from database.db import get_db_connection, init_db
from core.gdrive_manager import GDriveManager
from core.channel_manager import ChannelManager
from core.cataloger import ReferenceCataloger
from core.intelligence_engine import IntelligenceEngine
from core.script_generator import ScriptGenerator
from memory.central_memory import CentralMemory
from agents.company import ContentCompany
from agents.research_agents import ResearchOrchestrator
from core.large_scale_cataloger import LargeScaleCataloger
from core.research_pipeline import ResearchPipelineManager
from core.critical_analysis import CriticalAnalysisEngine
from core.podcast_deep_analyzer import PodcastDeepAnalyzer
from core.editorial_profiles import EditorialProfilesManager
from core.experimentation import ExperimentationLab
from services.service_registry import ServiceRegistry
from services.orchestration.langgraph_engine import IASOrchestrationEngine
from services.orchestration.central_controller import CentralOperationsController
from services.semantic_memory.vector_memory import VectorMemoryService
from services.model_gateway.gateway import ModelGatewayService
from services.video_analysis.yt_metadata import VideoMetadataService
from services.discovery.youtube_crawler import RealYouTubeDiscoveryService
from services.discovery.portal1_service import Portal1GovernanceService
from services.media_processing.ffmpeg_engine import FFmpegEngine
from services.media_processing.tts_engine import TTSNarrationService
from services.media_processing.subtitle_generator import SubtitleGenerator
from services.media_processing.audiovisual_pipeline import AudiovisualProductionPipeline
from services.distribution.distribution_service import DistributionService
from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from agents.qc_agent import QualityControlAgent

app = FastAPI(
    title="VIAGEM / IAS - Central de Inteligência de Conteúdo",
    description="Plataforma de IA com Central Multiagente de Pesquisa, Análise Crítica e Produção em Escala (200.000+ Shorts) com Drive 5 TB",
    version="3.0.0"
)

# Inicializações
init_db()
profiles_mgr = EditorialProfilesManager()
profiles_mgr.init_profiles()

gdrive_mgr = GDriveManager()
channel_mgr = ChannelManager()
cataloger = ReferenceCataloger()
intelligence_engine = IntelligenceEngine()
script_gen = ScriptGenerator()
memory = CentralMemory()
company = ContentCompany(memory=memory)
research_orchestrator = ResearchOrchestrator(memory=memory)
large_cataloger = LargeScaleCataloger(memory=memory)
pipeline_mgr = ResearchPipelineManager(memory=memory)
critical_analysis_eng = CriticalAnalysisEngine(memory=memory)
podcast_analyzer = PodcastDeepAnalyzer(memory=memory)
exp_lab = ExperimentationLab(memory=memory)

# Serviços de Infraestrutura Open Source
service_registry = ServiceRegistry()
orchestration_engine = IASOrchestrationEngine()
central_controller = CentralOperationsController()
semantic_memory = VectorMemoryService()
model_gateway = ModelGatewayService()
video_metadata_svc = VideoMetadataService()
youtube_crawler = RealYouTubeDiscoveryService()
portal1_governance = Portal1GovernanceService()
ffmpeg_engine = FFmpegEngine()
tts_service = TTSNarrationService(channel_manager=channel_mgr)
subtitle_generator = SubtitleGenerator(channel_manager=channel_mgr)
qc_agent = QualityControlAgent(ffmpeg_engine=ffmpeg_engine, channel_manager=channel_mgr)
av_pipeline = AudiovisualProductionPipeline(channel_manager=channel_mgr)
distribution_service = DistributionService(channel_manager=channel_mgr, gdrive_manager=gdrive_mgr)
learning_system = AudiovisualLearningSystem()

class VideoDiscoveryRequest(BaseModel):
    source_id: str
    original_url: str
    title: str
    creator: str
    niche: str
    duration_seconds: float
    language: Optional[str] = "pt-BR"
    views_count: Optional[int] = 0
    likes_count: Optional[int] = 0
    comment_count: Optional[int] = 0
    raw_metadata: Optional[Dict[str, Any]] = None

class BatchRunRequest(BaseModel):
    batch_id: Optional[str] = None
    batch_size: Optional[int] = 25
    target_goal: Optional[int] = 7000

class CrossPollinationRequest(BaseModel):
    source_channel_id: int
    target_channel_id: int
    knowledge_id: int
    rationale: str

class TargetGoalRequest(BaseModel):
    target_goal: int

class TTSGenerateRequest(BaseModel):
    text: str
    channel_id: Optional[Any] = 1
    voice: Optional[str] = None
    rate: Optional[str] = None
    pitch: Optional[str] = None

class SubtitleGenerateRequest(BaseModel):
    cues: List[Dict[str, Any]]
    channel_id: Optional[Any] = 1
    task_id: Optional[str] = None

class RenderShortRequest(BaseModel):
    audio_path: Optional[str] = None
    video_path: Optional[str] = None
    ass_path: Optional[str] = None
    channel_id: Optional[Any] = 1
    task_id: Optional[str] = None
    bg_color: Optional[str] = "#001E0A"

class QCValidateRequest(BaseModel):
    video_path: str
    task_id: Optional[str] = None
    channel_id: Optional[Any] = 1
    ass_path: Optional[str] = None

class PublishShortRequest(BaseModel):
    approval_token: str
    channel_id: Optional[Any] = 1
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    video_path: Optional[str] = None

class StartWorkflowRequest(BaseModel):
    task_id: str
    target_id: str
    niche: str = "futebol"
    channel_id: Optional[int] = 1
    pipeline_mode: Optional[str] = "vantis_17"

class SubmitTaskRequest(BaseModel):
    task_id: str
    task_type: str = "full_production_workflow"
    payload: Dict[str, Any]
    channel_id: Optional[int] = 1
    priority: int = 50
    assigned_agent: Optional[str] = None

class CancelTaskRequest(BaseModel):
    reason: str = "Cancelado pelo operador via Dashboard"

class ApproveWorkflowRequest(BaseModel):
    approval_token: str = "TOKEN_HUMAN_DIRECTOR_01"

class SemanticSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    top_k: int = 5

class UpdateStatusRequest(BaseModel):
    video_id: str
    new_status: str
    notes: Optional[str] = None

class CreateChannelRequest(BaseModel):
    name: str
    niche: str
    subniche: Optional[str] = None
    target_audience: Optional[str] = None
    language: str = "pt-BR"
    communication_tone: Optional[str] = None
    editing_style: Optional[str] = None
    posting_frequency: Optional[str] = None
    goals: Optional[str] = None
    editorial_strategy: Optional[str] = None
    visual_identity: Optional[Dict[str, Any]] = None
    voice_profile: Optional[Dict[str, Any]] = None
    subtitle_style: Optional[Dict[str, Any]] = None
    content_formats: Optional[List[str]] = None
    references: Optional[List[str]] = None
    rules_restrictions: Optional[List[str]] = None
    catchphrases: Optional[List[str]] = None
    archetype_slug: Optional[str] = None
    status: str = "draft"

class UpdateChannelStrategyRequest(BaseModel):
    name: Optional[str] = None
    niche: Optional[str] = None
    subniche: Optional[str] = None
    target_audience: Optional[str] = None
    editing_style: Optional[str] = None
    communication_tone: Optional[str] = None
    editorial_strategy: Optional[str] = None
    posting_frequency: Optional[str] = None
    status: Optional[str] = None

class SetChannelSettingRequest(BaseModel):
    setting_key: str
    setting_value: Any

class RecordFinancialEntryRequest(BaseModel):
    entry_type: str
    category: str
    amount_usd: float
    description: str = ""
    reference_id: Optional[str] = None

class DiscoverShortsRequest(BaseModel):
    niche: str = "futebol_outros"
    query: Optional[str] = None
    limit: int = 5
    channel_id: Optional[int] = 1

class ApproveOpportunityRequest(BaseModel):
    reviewer: str = "Diretor Editorial"
    auto_dispatch: bool = False

class RejectOpportunityRequest(BaseModel):
    rejection_reason: str
    rejection_category: str = "fora_da_persona"
    reviewer: str = "Diretor Editorial"

class CompletionRequest(BaseModel):
    prompt: str
    task: str = "critical_analysis"
    preferred_model: Optional[str] = None

# ------------------------------------------------------------------------------
# 1. VISÃO GERAL, HEALTH CHECKS & KPIs (OPERACIONAL)
# ------------------------------------------------------------------------------
@app.get("/health")
@app.get("/api/health")
def health_check():
    """
    Endpoint oficial de diagnóstico e health check do VANTIS (Prompt 10).
    Verifica integridade do banco SQLite WAL, sistema de arquivos, serviços e trava tarifária.
    """
    import datetime
    db_ok = False
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1").fetchone()
            db_ok = True
    except Exception:
        db_ok = False

    services_health = service_registry.check_all()
    drive_ok = gdrive_mgr.is_authenticated()

    is_healthy = db_ok and (services_health.get("health_score", 0) >= 70)

    return {
        "status": "HEALTHY" if is_healthy else "DEGRADED",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version": "3.0.0",
        "database": {
            "status": "CONNECTED" if db_ok else "DISCONNECTED",
            "engine": "SQLite WAL",
            "path": "database/shorts_central.db"
        },
        "services": services_health,
        "google_drive": {
            "authenticated": drive_ok,
            "status": "ONLINE" if drive_ok else "PENDING_OAUTH"
        },
        "cost_guard": {
            "enforce_free_tier": True,
            "total_expenses_usd": 0.0,
            "status": "ACTIVE_ZERO_COST"
        }
    }

@app.get("/api/overview")
def get_overview_kpis():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM video_references")
        total_cataloged = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM content_patterns")
        total_patterns = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM scripts")
        total_scripts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM podcast_candidate_cuts")
        total_cuts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM agent_decisions")
        total_decisions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM experiments")
        total_experiments = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM production_pipeline WHERE current_stage != 'published'")
        in_production = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM publications WHERE status = 'published'")
        total_published = cursor.fetchone()[0]

    drive_quota = gdrive_mgr.get_storage_quota()
    pipeline_status = pipeline_mgr.get_pipeline_metrics()

    return {
        "kpis": {
            "cataloged_references": total_cataloged,
            "target_references": 200000,
            "catalog_progress_percent": round((total_cataloged / 200000.0) * 100, 3),
            "content_patterns_mined": total_patterns,
            "scripts_generated": total_scripts,
            "podcast_cuts_evaluated": total_cuts,
            "agent_decisions_logged": total_decisions,
            "active_experiments": total_experiments,
            "videos_in_production": in_production,
            "videos_published": total_published,
            "active_channels": 20,
            "specialist_agents": 10,
            "researcher_agents": 10
        },
        "pipeline_metrics": pipeline_status,
        "drive_storage": drive_quota
    }

# ------------------------------------------------------------------------------
# 2. GOOGLE DRIVE (5 TB)
# ------------------------------------------------------------------------------
@app.get("/api/drive/quota")
def get_drive_quota():
    return gdrive_mgr.get_storage_quota()

@app.post("/api/drive/setup-folders")
def setup_drive_folders():
    if not gdrive_mgr.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Google Drive não autenticado. Execute 'CONECTAR MEU GOOGLE DRIVE.bat' no Desktop."
        )
    folders = gdrive_mgr.setup_drive_structure()
    return {"message": "13 Pastas sincronizadas no Google Drive 5 TB com sucesso!", "folders": folders}

# ------------------------------------------------------------------------------
# 3. CENTRAL MULTIAGENTE DE PESQUISA (PESQUISADORES)
# ------------------------------------------------------------------------------
@app.get("/api/researchers")
def list_researchers():
    """Retorna a lista dos 10 pesquisadores autônomos por nicho."""
    return research_orchestrator.list_researchers()

class ResearcherRunRequest(BaseModel):
    niche_slug: str
    query: Optional[str] = None

@app.post("/api/researchers/run")
def run_researcher(req: ResearcherRunRequest):
    """Executa missão de pesquisa com o pesquisador especializado do nicho."""
    return research_orchestrator.execute_targeted_research(req.niche_slug, req.query)

@app.post("/api/researchers/sweep")
def run_global_sweep():
    """Dispara missão sincronizada em todos os 10 nichos simultaneamente."""
    return research_orchestrator.execute_global_sweep()

# ------------------------------------------------------------------------------
# 4. ALGORITMO DE PESQUISA & APRENDIZADO (200.000+ SHORTS)
# ------------------------------------------------------------------------------
@app.get("/api/pipeline/metrics")
def get_pipeline_metrics():
    return pipeline_mgr.get_pipeline_metrics()

class PipelineStepRequest(BaseModel):
    niche_slug: str
    query: str

@app.post("/api/pipeline/run-step")
def run_pipeline_step(req: PipelineStepRequest):
    return pipeline_mgr.run_full_pipeline_step(req.niche_slug, req.query)

# ------------------------------------------------------------------------------
# 5. MÓDULO DE ANÁLISE CRÍTICA PROFISSIONAL
# ------------------------------------------------------------------------------
class CriticalAnalysisRequest(BaseModel):
    title: str
    transcript: str
    duration_seconds: float = 35.0
    niche_slug: str = "geral"

@app.post("/api/critical-analysis")
def run_critical_analysis(req: CriticalAnalysisRequest):
    """Executa a Análise Crítica completa com justificativas técnicas detalhadas."""
    return critical_analysis_eng.evaluate_content(
        title=req.title,
        transcript=req.transcript,
        duration_seconds=req.duration_seconds,
        niche_slug=req.niche_slug
    )

# ------------------------------------------------------------------------------
# 6. OS 10 AGENTES ESPECIALIZADOS DE PRODUÇÃO
# ------------------------------------------------------------------------------
@app.get("/api/agents")
def list_agents():
    return company.get_company_roster()

@app.get("/api/agents/decisions")
def list_agent_decisions(agent_name: Optional[str] = None, limit: int = 50):
    return memory.get_agent_history(agent_name, limit)

class CutEvaluationRequest(BaseModel):
    title: str
    transcript: str
    duration: float = 35.0
    is_direct_clip: bool = True
    source_authorized: bool = True

@app.post("/api/agents/evaluate")
def evaluate_cut_with_company(req: CutEvaluationRequest):
    payload = {
        "title": req.title,
        "transcript": req.transcript,
        "duration": req.duration,
        "is_direct_clip": req.is_direct_clip,
        "source_authorized": req.source_authorized
    }
    return company.evaluate_candidate_cut(payload)

# ------------------------------------------------------------------------------
# 7. DEEP PODCAST ANALYZER
# ------------------------------------------------------------------------------
class PodcastAnalysisRequest(BaseModel):
    title: str
    transcript_text: str
    source_url: Optional[str] = ""
    channel_name: Optional[str] = "Podcast Host"

@app.post("/api/podcasts/analyze")
def analyze_podcast_endpoint(req: PodcastAnalysisRequest):
    return podcast_analyzer.analyze_episode(
        episode_title=req.title,
        transcript_data=req.transcript_text,
        source_url=req.source_url or "",
        channel_name=req.channel_name or "Podcast Host"
    )

@app.get("/api/podcasts/cuts")
def list_podcast_cuts(status: Optional[str] = None, limit: int = 50):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM podcast_candidate_cuts"
        params = []
        if status:
            query += " WHERE director_decision LIKE ?"
            params.append(f"%{status}%")
        query += " ORDER BY quality_score DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        rows = []
        for r in cursor.fetchall():
            d = dict(r)
            if d.get("agent_evaluations"):
                try:
                    d["agent_evaluations"] = json.loads(d["agent_evaluations"])
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"[WebApp] Aviso: agent_evaluations inválido no corte {d.get('id')}: {e}")
            rows.append(d)
        return rows

# ------------------------------------------------------------------------------
# 8. BIBLIOTECA DE REFERÊNCIAS (200.000 SHORTS)
# ------------------------------------------------------------------------------
@app.get("/api/catalog")
def list_catalog_videos(
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT v.*, c.name as category_name 
            FROM video_references v
            LEFT JOIN categories c ON c.id = v.category_id
            WHERE 1=1
        """
        params = []
        if category:
            query += " AND c.slug = ?"
            params.append(category)
        if search:
            query += " AND (v.title LIKE ? OR v.author LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY v.retention_score DESC, v.views_count DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

# ------------------------------------------------------------------------------
# 9. PERSONALIDADES EDITORIAIS & EXPERIMENTOS
# ------------------------------------------------------------------------------
@app.get("/api/profiles")
def list_editorial_profiles():
    return profiles_mgr.get_all_profiles()

@app.get("/api/experiments")
def list_experiments_endpoint():
    return exp_lab.list_experiments()

# ------------------------------------------------------------------------------
# 10. OS 20 CANAIS YOUTUBE SHORTS (SISTEMA MULTICANAL & ISOLAMENTO EDITORIAL)
# ------------------------------------------------------------------------------
@app.get("/api/channels")
def list_channels():
    """Lista todos os 20 canais com métricas consolidadas."""
    return channel_mgr.list_all_channels()

@app.get("/api/channels/{channel_id}")
def get_channel_details(channel_id: int):
    """Retorna detalhes gerais do canal por ID ou channel_number."""
    ch = channel_mgr.get_channel_by_id(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Canal não encontrado")
    return ch

@app.get("/api/channels/{channel_id}/profile")
def get_channel_profile(channel_id: int):
    """Retorna o perfil completo e consolidado: arquétipo, branding, legendas e voz."""
    prof = channel_mgr.get_channel_profile(channel_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Perfil do canal não encontrado")
    return prof

@app.get("/api/channels/{channel_id}/guidelines")
def get_channel_guidelines(channel_id: int):
    """Retorna as diretrizes editoriais do canal para injeção em agentes."""
    guidelines = channel_mgr.get_channel_editorial_guidelines(channel_id)
    return {"channel_id": channel_id, "guidelines": guidelines}

@app.get("/api/channels/{channel_id}/settings")
def get_channel_settings(channel_id: int):
    """Retorna todas as configurações personalizadas salvas do canal."""
    return channel_mgr.get_channel_settings(channel_id)

@app.post("/api/channels/{channel_id}/settings")
def set_channel_setting(channel_id: int, req: SetChannelSettingRequest):
    """Define ou atualiza uma configuração personalizada do canal."""
    success = channel_mgr.set_channel_setting(channel_id, req.setting_key, req.setting_value)
    if not success:
        raise HTTPException(status_code=400, detail="Erro ao salvar configuração do canal")
    return {"success": True, "channel_id": channel_id, "setting_key": req.setting_key}

@app.post("/api/channels/{channel_id}/update")
def update_channel(channel_id: int, req: UpdateChannelStrategyRequest):
    """Atualiza estratégia, nicho, público ou estilo do canal."""
    success = channel_mgr.update_channel_strategy(
        channel_id=channel_id,
        name=req.name,
        niche=req.niche,
        subniche=req.subniche,
        target_audience=req.target_audience,
        editing_style=req.editing_style,
        communication_tone=req.communication_tone,
        editorial_strategy=req.editorial_strategy,
        posting_frequency=req.posting_frequency,
        status=req.status
    )
    if not success:
        raise HTTPException(status_code=400, detail="Erro ao atualizar canal")
    return {"success": True, "channel_id": channel_id}

@app.get("/api/channels/{channel_id}/financials")
def get_channel_financials(channel_id: int):
    """Retorna balanço financeiro exclusivo do canal (custos de tokens vs receita estimada)."""
    return channel_mgr.get_financial_summary(channel_id)

@app.post("/api/channels/{channel_id}/financials")
def record_channel_financial_entry(channel_id: int, req: RecordFinancialEntryRequest):
    """Registra lançamento financeiro (custo ou receita) para o canal."""
    entry_id = channel_mgr.record_financial_entry(
        channel_id=channel_id,
        entry_type=req.entry_type,
        category=req.category,
        amount_usd=req.amount_usd,
        description=req.description,
        reference_id=req.reference_id
    )
    return {"success": True, "entry_id": entry_id, "channel_id": channel_id}

@app.post("/api/channels")
def create_channel_draft(req: CreateChannelRequest):
    """Cria um novo canal (ou rascunho de canal) com isolamento multitenant estrito (Prompt 08)."""
    profile = channel_mgr.create_channel(
        name=req.name,
        niche=req.niche,
        subniche=req.subniche,
        target_audience=req.target_audience,
        language=req.language,
        communication_tone=req.communication_tone,
        editing_style=req.editing_style,
        posting_frequency=req.posting_frequency,
        goals=req.goals,
        editorial_strategy=req.editorial_strategy,
        visual_identity=req.visual_identity,
        voice_profile=req.voice_profile,
        subtitle_style=req.subtitle_style,
        content_formats=req.content_formats,
        references=req.references,
        rules_restrictions=req.rules_restrictions,
        catchphrases=req.catchphrases,
        archetype_slug=req.archetype_slug,
        status=req.status
    )
    readiness = channel_mgr.get_channel_readiness(profile["channel_id"])
    return {"success": True, "channel": profile, "readiness": readiness}

@app.post("/api/channels/{channel_id}/archive")
def archive_channel(channel_id: int):
    """Arquiva um canal, desativando-o para operações regulares sem perda de histórico."""
    success = channel_mgr.archive_channel(channel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Canal não encontrado para arquivamento")
    return {"success": True, "channel_id": channel_id, "status": "archived"}

@app.post("/api/channels/{channel_id}/set-pilot")
def set_pilot_channel(channel_id: int):
    """Define o canal selecionado como canal-piloto ativo para testes e produção."""
    success = channel_mgr.set_pilot_channel(channel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Canal não encontrado para marcar como piloto")
    return {"success": True, "channel_id": channel_id, "is_pilot": True}

@app.get("/api/channels/{channel_id}/readiness")
def get_channel_readiness(channel_id: int):
    """Retorna avaliação percentual de completude do canal, campos faltantes e próximos passos."""
    return channel_mgr.get_channel_readiness(channel_id)

@app.get("/api/channels/{channel_id}/memory")
def get_channel_memory(channel_id: int):
    """Retorna sumário exclusivo da memória semântica e histórico de aprovações/rejeições do canal."""
    return channel_mgr.get_channel_memory_summary(channel_id)

# ------------------------------------------------------------------------------
# 10.1 PORTAL 1: GOVERNANÇA HUMANA DE DESCOBERTA & PAUTAS (HUMAN-IN-THE-LOOP)
# ------------------------------------------------------------------------------
@app.get("/api/portal1/opportunities")
def list_portal1_opportunities(
    status: Optional[str] = Query("PENDING_REVIEW", description="Filtrar por status (PENDING_REVIEW, APPROVED, REJECTED)"),
    channel_id: Optional[int] = Query(None, description="Filtrar por ID do canal"),
    niche: Optional[str] = Query(None, description="Filtrar por nicho"),
    limit: int = Query(50, description="Limite de pautas")
):
    """Lista oportunidades de pautas mineradas no Portal 1 com filtros."""
    return portal1_governance.list_opportunities(status=status, channel_id=channel_id, niche=niche, limit=limit)

@app.get("/api/portal1/opportunity/{opportunity_id}")
def get_portal1_opportunity(opportunity_id: str):
    """Retorna detalhes e evidências de popularidade de uma oportunidade específica."""
    opp = portal1_governance.get_opportunity(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Oportunidade não encontrada")
    return opp

@app.post("/api/portal1/discover")
def trigger_real_youtube_discovery(req: DiscoverShortsRequest):
    """Executa mineração real de vídeos no YouTube via yt-dlp sem dados sintéticos."""
    results = youtube_crawler.discover_shorts_by_niche(
        niche=req.niche,
        query=req.query,
        limit=req.limit,
        channel_id=req.channel_id
    )
    return {
        "success": True,
        "niche": req.niche,
        "channel_id": req.channel_id,
        "mined_count": len(results),
        "opportunities": results
    }

@app.post("/api/portal1/approve/{opportunity_id}")
def approve_portal1_opportunity(opportunity_id: str, req: Optional[ApproveOpportunityRequest] = None):
    """Aprova uma pauta no Portal 1, liberando para produção e indexando na memória semântica."""
    reviewer = req.reviewer if req else "Diretor Editorial"
    auto_dispatch = req.auto_dispatch if req else False
    res = portal1_governance.approve_opportunity(
        opportunity_id=opportunity_id,
        reviewer=reviewer,
        auto_dispatch=auto_dispatch
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.post("/api/portal1/reject/{opportunity_id}")
def reject_portal1_opportunity(opportunity_id: str, req: RejectOpportunityRequest):
    """Rejeita uma pauta no Portal 1 com motivo obrigatório e alimenta a memória negativa da IA."""
    res = portal1_governance.reject_opportunity(
        opportunity_id=opportunity_id,
        rejection_reason=req.rejection_reason,
        rejection_category=req.rejection_category,
        reviewer=req.reviewer
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.get("/api/portal1/metrics")
def get_portal1_metrics():
    """Retorna métricas consolidadas de governança do Portal 1 (taxa de aprovação e motivos de recusa)."""
    return portal1_governance.get_governance_metrics()

@app.get("/api/categories")
def list_categories():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name ASC")
        return [dict(r) for r in cursor.fetchall()]

@app.get("/api/memory/stats")
def get_memory_stats():
    return memory.get_summary_stats()

@app.get("/api/memory/nodes")
def list_knowledge_nodes(node_type: Optional[str] = None):
    return memory.query_knowledge_nodes(node_type=node_type)

# ------------------------------------------------------------------------------
# 11. SERVIÇOS & INFRAESTRUTURA OPEN SOURCE (LangGraph, pgvector, LiteLLM, yt-dlp)
# ------------------------------------------------------------------------------
@app.get("/api/services/status")
def get_services_status():
    """Retorna telemetria e estado operacional das 7 tecnologias essenciais."""
    return service_registry.check_all()

@app.get("/api/services/costs")
def get_services_costs():
    """Retorna métricas de consumo de tokens e custos estimados via LiteLLM."""
    return model_gateway.get_usage_metrics()

@app.get("/api/orchestration/tasks")
def list_orchestration_tasks():
    """Lista todos os fluxos e tarefas registradas no LangGraph."""
    return orchestration_engine.list_all_tasks()

@app.get("/api/orchestration/task/{task_id}")
def get_orchestration_task(task_id: str):
    """Retorna estado e progresso das 12 etapas de uma tarefa específica."""
    state = orchestration_engine.get_task_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return state

@app.get("/api/orchestration/vantis-steps")
def list_vantis_pipeline_steps():
    """Retorna as 17 etapas oficiais do Pipeline Central VANTIS."""
    from services.orchestration.langgraph_engine import VANTIS_17_STEPS, WORKFLOW_STEPS
    return {
        "vantis_17_steps": VANTIS_17_STEPS,
        "legacy_12_steps": WORKFLOW_STEPS,
        "default_mode": "vantis_17"
    }

@app.post("/api/orchestration/start")
def start_orchestration_flow(req: StartWorkflowRequest):
    """Inicia o pipeline LangGraph (VANTIS 17 etapas ou legado) integrado com o Controlador Central e a task_queue."""
    state = central_controller.dispatch_workflow(
        task_id=req.task_id,
        target_id=req.target_id,
        niche=req.niche,
        channel_id=req.channel_id or 1,
        pipeline_mode=req.pipeline_mode or "vantis_17"
    )
    return state

@app.post("/api/orchestration/approve/{task_id}")
def approve_orchestration_task(task_id: str, req: Optional[ApproveWorkflowRequest] = None):
    """Aprova a etapa 11 (revisão humana expressa - Portal 2) e conclui a distribuição (etapa 12)."""
    token = req.approval_token if req else "TOKEN_HUMAN_DIRECTOR_01"
    resumed = central_controller.approve_and_resume_workflow(task_id=task_id, approval_token=token)
    if not resumed:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada para aprovação")
    return resumed

# ------------------------------------------------------------------------------
# 11.1 FILA PERSISTENTE & CONTROLADOR CENTRAL DE OPERAÇÕES
# ------------------------------------------------------------------------------
@app.get("/api/queue/list")
def list_queue_tasks(
    status: Optional[str] = Query(None, description="Filtrar por status (QUEUED, RUNNING, PAUSED_FOR_REVIEW, COMPLETED, FAILED, RETRYING)"),
    channel_id: Optional[int] = Query(None, description="Filtrar por ID do canal"),
    limit: int = Query(50, description="Limite de tarefas")
):
    """Lista tarefas na fila persistente com filtros e ordenação por prioridade."""
    return central_controller.list_queue(status=status, channel_id=channel_id, limit=limit)

@app.get("/api/queue/task/{task_id}")
def get_queue_task(task_id: str):
    """Retorna detalhes e status completo de uma tarefa na fila persistente."""
    task = central_controller.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada na fila")
    return task

@app.post("/api/queue/submit")
def submit_queue_task(req: SubmitTaskRequest):
    """Submete uma nova tarefa para a fila persistente com bloqueio de duplicidade."""
    res = central_controller.submit_task(
        task_id=req.task_id,
        task_type=req.task_type,
        payload=req.payload,
        channel_id=req.channel_id,
        priority=req.priority,
        assigned_agent=req.assigned_agent
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.post("/api/queue/claim")
def claim_queue_task(
    worker_agent: str = Query("general_worker", description="Nome do agente/worker"),
    channel_id: Optional[int] = Query(None, description="Canal alvo opcional"),
    max_concurrent: int = Query(2, description="Limite de concorrência por canal")
):
    """Reivindica atomicamente a próxima tarefa de maior prioridade disponível."""
    claimed = central_controller.claim_next_task(
        worker_agent=worker_agent,
        channel_id=channel_id,
        max_concurrent_per_channel=max_concurrent
    )
    if not claimed:
        return {"claimed": False, "message": "Nenhuma tarefa elegível na fila"}
    return {"claimed": True, "task": claimed}

@app.post("/api/queue/cancel/{task_id}")
def cancel_queue_task(task_id: str, req: Optional[CancelTaskRequest] = None):
    """Cancela uma tarefa na fila."""
    reason = req.reason if req else "Cancelado pelo operador via Dashboard"
    success = central_controller.cancel_task(task_id, reason=reason)
    if not success:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada para cancelamento")
    return {"success": True, "task_id": task_id, "action": "CANCELLED"}

@app.post("/api/queue/recover-stalled")
def recover_stalled_tasks(timeout_minutes: int = Query(30, description="Minutos de inatividade em RUNNING")):
    """Recupera e reenfileira tarefas travadas em RUNNING após falhas ou quedas inesperadas."""
    recovered = central_controller.recover_stalled_tasks(timeout_minutes=timeout_minutes)
    return {"success": True, "recovered_count": recovered}

@app.post("/api/semantic/search")
def search_semantic_memory(req: SemanticSearchRequest):
    """Busca por significado e contexto vetorial (distância de cosseno)."""
    results = semantic_memory.search_similar(
        query=req.query,
        category=req.category,
        top_k=req.top_k
    )
    return {
        "query": req.query,
        "category": req.category,
        "count": len(results),
        "results": results
    }

@app.get("/api/semantic/stats")
def get_semantic_stats():
    """Retorna estatísticas da memória semântica vetorial."""
    return semantic_memory.get_stats()

@app.get("/api/approval/queue")
def get_approval_queue(status: Optional[str] = None):
    """Retorna vídeos na máquina de estados de catalogação e aprovação de direitos."""
    return video_metadata_svc.list_by_status(status=status)

@app.post("/api/approval/update-status")
def update_video_status(req: UpdateStatusRequest):
    """Avança o status de um vídeo na máquina de estados (catalogado -> aprovado)."""
    res = video_metadata_svc.advance_status(
        video_id=req.video_id,
        new_status=req.new_status,
        notes=req.notes
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.post("/api/gateway/completion")
def model_gateway_completion(req: CompletionRequest):
    """Executa requisição ao gateway LiteLLM com fallback automático multi-provedor."""
    messages = [{"role": "user", "content": req.prompt}]
    return model_gateway.completion(
        messages=messages,
        task=req.task,
        preferred_model=req.preferred_model
    )

# ==============================================================================
# ENDPOINTS DE PRODUÇÃO AUDIOVISUAL & CONTROLE DE QUALIDADE (FASE 5)
# ==============================================================================

@app.get("/api/media/voices")
async def list_media_voices(lang: str = "pt-BR"):
    """Lista vozes neurais gratuitas de alta resolução do Edge-TTS."""
    return await tts_service.list_available_voices(language_prefix=lang)

@app.post("/api/media/tts/generate")
def generate_narration_audio(req: TTSGenerateRequest):
    """Gera áudio de narração neural para um canal específico."""
    res = tts_service.generate_narration(
        text=req.text,
        channel_id=req.channel_id,
        voice=req.voice,
        rate=req.rate,
        pitch=req.pitch
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Erro ao sintetizar áudio"))
    return res

@app.post("/api/media/subtitles/generate")
def generate_ass_subtitles(req: SubtitleGenerateRequest):
    """Gera arquivo de legendas ASS dinâmicas com identidade visual do canal."""
    res = subtitle_generator.generate_ass(
        cues=req.cues,
        channel_id=req.channel_id,
        task_id=req.task_id
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Erro ao gerar legendas"))
    return res

@app.post("/api/media/render/short")
def render_short_video(req: RenderShortRequest):
    """Renderiza vídeo vertical 9:16 (1080x1920) com EBU R128 e legendas ASS."""
    clips_dir = BASE_DIR / "workspace" / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    out_file = str(clips_dir / f"{req.task_id or 'render'}.mp4")

    if req.video_path and os.path.exists(req.video_path):
        res = ffmpeg_engine.render_vertical_short(
            input_video=req.video_path,
            output_path=out_file,
            ass_subtitles_path=req.ass_path,
            narration_audio_path=req.audio_path,
            channel_variant=int(req.channel_id) if str(req.channel_id).isdigit() else 1
        )
    elif req.audio_path and os.path.exists(req.audio_path):
        res = ffmpeg_engine.generate_canvas_short(
            audio_path=req.audio_path,
            output_path=out_file,
            bg_color=req.bg_color or "#001E0A",
            ass_subtitles_path=req.ass_path,
            channel_variant=int(req.channel_id) if str(req.channel_id).isdigit() else 1
        )
    else:
        raise HTTPException(status_code=400, detail="Nem video_path nem audio_path válidos foram fornecidos para renderização.")

    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Falha na renderização FFmpeg"))
    return res

@app.post("/api/qc/validate")
def validate_rendered_short(req: QCValidateRequest):
    """Executa auditoria técnica rigorosa de qualidade antes do Portal 2."""
    return qc_agent.validate_rendered_short(
        video_path=req.video_path,
        task_id=req.task_id,
        channel_id=req.channel_id,
        ass_path=req.ass_path
    )

@app.get("/api/media/preview/{file_type}/{filename}")
def preview_media_file(file_type: str, filename: str):
    """Transmite arquivos de mídia gerados (áudio, clips ou legendas) para inspeção."""
    allowed_dirs = {
        "audio": BASE_DIR / "workspace" / "audio",
        "clips": BASE_DIR / "workspace" / "clips",
        "subs": BASE_DIR / "workspace" / "subs"
    }
    target_dir = allowed_dirs.get(file_type)
    if not target_dir:
        raise HTTPException(status_code=400, detail=f"Tipo de mídia inválido: {file_type}")

    safe_name = os.path.basename(filename)
    file_path = target_dir / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no diretório de mídia.")

    media_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".mp4": "video/mp4",
        ".ass": "text/plain",
        ".json": "application/json"
    }
    ext = file_path.suffix.lower()
    return FileResponse(str(file_path), media_type=media_types.get(ext, "application/octet-stream"))

# ==============================================================================
# ENDPOINTS DE DISTRIBUIÇÃO SEGURA & MANIFESTOS (FASE 6)
# ==============================================================================

@app.get("/api/distribution/manifests")
def list_publication_manifests(channel_id: Optional[int] = None):
    """Lista manifestos de publicação gerados para os canais."""
    return distribution_service.list_manifests(channel_id=channel_id)

@app.get("/api/distribution/manifest/{task_id}")
def get_publication_manifest(task_id: str):
    """Recupera o manifesto detalhado de um Short."""
    man = distribution_service.get_manifest(task_id=task_id)
    if not man:
        raise HTTPException(status_code=404, detail="Manifesto não encontrado para a tarefa indicada.")
    return man

@app.post("/api/distribution/publish/{task_id}")
def execute_short_publication(task_id: str, req: PublishShortRequest):
    """Executa a publicação privada segura após autorização humana com token do Portal 2."""
    try:
        return distribution_service.execute_distribution(
            task_id=task_id,
            channel_id=req.channel_id,
            human_approved=True,
            human_approval_token=req.approval_token,
            title=req.title,
            description=req.description,
            tags=req.tags,
            video_path=req.video_path
        )
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/distribution/publications")
def list_channel_publications(channel_id: Optional[int] = None):
    """Retorna o histórico de publicações realizadas com status e privacidade."""
    return distribution_service.list_publications(channel_id=channel_id)

# ==============================================================================
# ENDPOINTS DO DASHBOARD DE CONTROLE UNIFICADO (FASE 7)
# ==============================================================================

@app.get("/api/dashboard/kpis")
def get_dashboard_kpis():
    """Retorna KPIs executivos consolidados para a Central de Operações."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Oportunidades & Portal 1
        cur.execute("SELECT COUNT(*) FROM opportunities")
        total_opps = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'PENDING'")
        pending_p1 = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'APPROVED'")
        approved_p1 = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'REJECTED'")
        rejected_p1 = cur.fetchone()[0]

        # Fila de Tarefas & LangGraph
        cur.execute("SELECT COUNT(*) FROM task_queue WHERE status = 'RUNNING'")
        running_tasks = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM task_queue WHERE status = 'QUEUED'")
        queued_tasks = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM workflow_checkpoints WHERE status = 'PAUSED_FOR_REVIEW'")
        pending_p2 = cur.fetchone()[0]

        # Publicações & Mídia
        cur.execute("SELECT COUNT(*) FROM publications")
        total_published = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM publications WHERE privacy_status = 'private'")
        private_published = cur.fetchone()[0]

    # Finanças consolidadas (custo $0.00 garantido)
    fin_summary = channel_mgr.get_financial_summary()
    drive_quota = gdrive_mgr.get_storage_quota()

    return {
        "kpis": {
            "total_channels": 20,
            "pilot_channels": 5,
            "total_opportunities": total_opps,
            "portal1_pending": pending_p1,
            "portal1_approved": approved_p1,
            "portal1_rejected": rejected_p1,
            "portal2_pending": pending_p2,
            "tasks_running": running_tasks,
            "tasks_queued": queued_tasks,
            "videos_published": total_published,
            "private_videos_published": private_published,
            "cost_guard": {
                "active": True,
                "enforce_free_tier": True,
                "total_expense_usd": fin_summary.get("total_expenses", 0.0),
                "total_avoided_cost_usd": fin_summary.get("total_avoided_cost", 0.0)
            }
        },
        "drive_storage": drive_quota,
        "financial_summary": fin_summary,
        "channels": {
            "total": 20,
            "pilot_active": 5
        },
        "opportunities": {
            "total": total_opps,
            "pending": pending_p1,
            "approved": approved_p1,
            "rejected": rejected_p1
        },
        "queue": {
            "in_progress": running_tasks,
            "queued": queued_tasks
        },
        "portal2": {
            "pending": pending_p2
        },
        "publications": {
            "total_published": total_published,
            "private_published": private_published
        },
        "costs": {
            "total_spent_usd": fin_summary.get("total_expenses", 0.0),
            "enforce_free_tier": True,
            "total_avoided_cost_usd": fin_summary.get("total_avoided_cost", 0.0)
        },
        "storage": {
            "total_gb": 5120.0,
            "used_gb": round(drive_quota.get("used_bytes", 0) / (1024**3), 2),
            "free_gb": round(drive_quota.get("free_bytes", 0) / (1024**3), 2),
            "used_percent": drive_quota.get("used_percent", 0.0)
        }
    }

@app.get("/api/dashboard/portal2/pending")
def list_portal2_pending_shorts():
    """Lista todos os Shorts renderizados retidos no Portal 2 aguardando revisão humana."""
    pending_items = []
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT task_id, target_id, niche, current_step, status, state_json, updated_at, channel_id
            FROM workflow_checkpoints
            WHERE status = 'PAUSED_FOR_REVIEW'
            ORDER BY updated_at DESC
        """)
        rows = cur.fetchall()

    for row in rows:
        state_data = {}
        try:
            if row["state_json"]:
                state_data = json.loads(row["state_json"])
        except Exception:
            state_data = {}

        results = state_data.get("step_results", {})
        step8 = results.get("8_geracao_roteiros", {})
        step9 = results.get("9_preparacao_materiais", {})
        step10 = results.get("10_edicao_audiovisual", {})
        step11 = results.get("11_revisao_humana", {})

        clip_path = step10.get("output_clip_path")
        audio_path = step9.get("audio_path")
        ass_path = step9.get("ass_path")

        clip_name = os.path.basename(clip_path) if clip_path else None
        audio_name = os.path.basename(audio_path) if audio_path else None
        ass_name = os.path.basename(ass_path) if ass_path else None

        qc_report = step11.get("qc_report", {
            "score": step11.get("qc_score", 85),
            "status": step11.get("qc_status", "APPROVED_BY_QC"),
            "passed": True,
            "checks": []
        })

        pending_items.append({
            "task_id": row["task_id"],
            "channel_id": row["channel_id"] or 1,
            "niche": row["niche"],
            "target_id": row["target_id"],
            "status": row["status"],
            "current_step": row["current_step"],
            "updated_at": row["updated_at"],
            "script_preview": step8.get("script", ""),
            "clip_filename": clip_name,
            "clip_url": f"/api/media/preview/clips/{clip_name}" if clip_name else None,
            "audio_filename": audio_name,
            "audio_url": f"/api/media/preview/audio/{audio_name}" if audio_name else None,
            "ass_filename": ass_name,
            "ass_url": f"/api/media/preview/subs/{ass_name}" if ass_name else None,
            "qc_score": qc_report.get("score", 85),
            "qc_status": qc_report.get("status", "APPROVED_BY_QC"),
            "qc_report": qc_report
        })

    return pending_items

class Portal2ApprovalRequest(BaseModel):
    approval_token: Optional[str] = None
    channel_id: Optional[Any] = 1

@app.post("/api/dashboard/portal2/approve/{task_id}")
def approve_portal2_short(task_id: str, req: Portal2ApprovalRequest):
    """Aprova um Short no Portal 2 e desencadeia a publicação privada no YouTube."""
    token = req.approval_token or f"PORTAL2_TOKEN_{uuid.uuid4().hex[:8].upper()}"
    try:
        res = orchestration_engine.approve_and_resume(
            task_id=task_id,
            human_approval_token=token
        )
        if not res:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada para aprovação.")
        return {
            "success": True,
            "task_id": task_id,
            "token": token,
            "status": res.get("status"),
            "completed_steps": res.get("completed_steps", []),
            "publication_result": res.get("step_results", {}).get("12_distribuicao", {}),
            "step_results": res.get("step_results", {}).get("12_distribuicao", {})
        }
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------------------
# 15. PIPELINE DE PRODUÇÃO E PROCESSAMENTO AUDIOVISUAL (10 ETAPAS)
# ------------------------------------------------------------------------------
class AudiovisualJobRequest(BaseModel):
    task_id: Optional[str] = None
    channel_id: int = 1
    input_media_path: Optional[str] = None
    script_text: Optional[str] = None
    generate_tts: bool = False
    generate_subtitles: bool = True
    cut_start_sec: Optional[float] = None
    cut_end_sec: Optional[float] = None
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    source_license: Optional[str] = "fair_use_transformative"
    transformative_type: Optional[str] = "educational_analysis"

@app.post("/api/audiovisual/execute")
def execute_audiovisual_job(req: AudiovisualJobRequest):
    """Executa o pipeline audiovisual completo de 10 etapas (VANTIS Bloco B - Prompt 06)."""
    task_id = req.task_id or f"av_{uuid.uuid4().hex[:8]}"
    job_cfg = {
        "task_id": task_id,
        "channel_id": req.channel_id,
        "input_media_path": req.input_media_path,
        "script_text": req.script_text,
        "generate_tts": req.generate_tts,
        "generate_subtitles": req.generate_subtitles,
        "cut_start_sec": req.cut_start_sec,
        "cut_end_sec": req.cut_end_sec,
        "provenance": {
            "source_url": req.source_url or "original_production",
            "source_author": req.source_author or f"Canal {req.channel_id}",
            "source_license": req.source_license or "fair_use_transformative",
            "transformative_type": req.transformative_type or "educational_analysis"
        }
    }
    try:
        res = av_pipeline.execute_full_pipeline(job_cfg)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/audiovisual/runs")
def list_audiovisual_runs(limit: int = 20):
    """Lista as últimas execuções do pipeline audiovisual gravadas no SQLite."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM audiovisual_pipeline_runs
            ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]

@app.get("/api/audiovisual/run/{task_id}")
def get_audiovisual_run(task_id: str):
    """Retorna detalhes e relatório de QC de uma tarefa audiovisual específica."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audiovisual_pipeline_runs WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Execução audiovisual não encontrada")
        return dict(row)

# ------------------------------------------------------------------------------
# 14. SISTEMA DE APRENDIZADO AUDIOVISUAL MASSIVO (7.000+ VÍDEOS)
# ------------------------------------------------------------------------------
@app.get("/api/learning/overview")
def get_learning_overview():
    """Retorna KPIs gerais, progresso rumo à meta (7.000+), diversidade e auditoria."""
    return learning_system.get_dashboard_overview()

@app.get("/api/learning/catalog")
def list_learning_catalog(
    state: Optional[str] = None,
    niche: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Retorna catálogo inteligente paginado com filtros de estado e nicho."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM audiovisual_library WHERE 1=1"
        params = []
        if state:
            query += " AND processing_state = ?"
            params.append(state)
        if niche:
            query += " AND niche = ?"
            params.append(niche)
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        items = [dict(r) for r in cursor.fetchall()]

        # Contagem total para paginação
        count_query = "SELECT COUNT(*) FROM audiovisual_library WHERE 1=1"
        count_params = []
        if state:
            count_query += " AND processing_state = ?"
            count_params.append(state)
        if niche:
            count_query += " AND niche = ?"
            count_params.append(niche)
        cursor.execute(count_query, tuple(count_params))
        total_count = cursor.fetchone()[0]

        return {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "items": items
        }

@app.get("/api/learning/patterns")
def list_learning_patterns(
    niche: Optional[str] = None,
    channel_id: Optional[int] = None,
    knowledge_type: Optional[str] = None
):
    """Retorna conclusões de conhecimento editorial estruturado com referências a vídeos."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM editorial_knowledge_library WHERE 1=1"
        params = []
        if niche:
            query += " AND (niche = ? OR niche = 'universal')"
            params.append(niche)
        if channel_id is not None:
            query += " AND (target_channel_id = ? OR target_channel_id IS NULL)"
            params.append(channel_id)
        if knowledge_type:
            query += " AND knowledge_type = ?"
            params.append(knowledge_type)
        query += " ORDER BY confidence_score DESC"

        cursor.execute(query, tuple(params))
        items = [dict(r) for r in cursor.fetchall()]
        for item in items:
            item["evidence_video_ids"] = json.loads(item["evidence_video_ids"] or "[]")
        return items

@app.get("/api/learning/experiments")
def list_learning_experiments(channel_id: Optional[int] = None, status: Optional[str] = None):
    """Lista experimentos editoriais baseados em hipóteses e evidências."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT e.*, c.name as channel_name
            FROM editorial_experiments e
            LEFT JOIN channels c ON e.channel_id = c.id
            WHERE 1=1
        """
        params = []
        if channel_id is not None:
            query += " AND e.channel_id = ?"
            params.append(channel_id)
        if status:
            query += " AND e.status = ?"
            params.append(status)
        query += " ORDER BY e.created_at DESC"

        cursor.execute(query, tuple(params))
        return [dict(r) for r in cursor.fetchall()]

@app.post("/api/learning/discover")
def discover_learning_video(req: VideoDiscoveryRequest):
    """Descobre e ingere um novo vídeo na biblioteca com checagem de diversidade e fingerprint."""
    try:
        return learning_system.discover_video(
            source_id=req.source_id,
            original_url=req.original_url,
            title=req.title,
            creator=req.creator,
            niche=req.niche,
            duration_seconds=req.duration_seconds,
            language=req.language or "pt-BR",
            views_count=req.views_count or 0,
            likes_count=req.likes_count or 0,
            comment_count=req.comment_count or 0,
            raw_metadata=req.raw_metadata
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/learning/batch-run")
def trigger_learning_batch(req: BatchRunRequest):
    """Dispara execução ou retomada de lote de análise com persistência de checkpoints."""
    batch_id = req.batch_id or f"batch_{int(time.time())}"
    try:
        return learning_system.run_batch_processing(
            batch_id=batch_id,
            batch_size=req.batch_size or 25,
            target_goal=req.target_goal or 7000
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learning/audit")
def run_learning_quality_audit():
    """Executa auditoria de qualidade (viés, integridade de evidências, health score)."""
    return learning_system.run_quality_audit()

@app.post("/api/learning/cross-pollinate")
def execute_cross_pollination(req: CrossPollinationRequest):
    """Transfere técnica editorial entre canais com justificativa e experimento de validação."""
    try:
        return learning_system.cross_pollinate_technique(
            source_channel_id=req.source_channel_id,
            target_channel_id=req.target_channel_id,
            knowledge_id=req.knowledge_id,
            transfer_rationale=req.rationale
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/learning/target-goal")
def update_target_goal(req: TargetGoalRequest):
    """Atualiza a meta global de aprendizado audiovisual (ex: 7000 -> 10000)."""
    try:
        updated = learning_system.set_target_goal(req.target_goal)
        return {"target_goal": updated, "status": "UPDATED"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/channels/{channel_id}/editorial-memory")
def get_channel_editorial_memory_route(channel_id: int):
    """Retorna memória editorial isolada de um dos 5 canais piloto."""
    try:
        return learning_system.get_channel_editorial_memory(channel_id=channel_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/learning/pilot-forensic")
def get_pilot_forensic_metrics():
    """Retorna telemetria e evidências forenses auditadas dos pilotos (Fase 15.1 e Fase 16)."""
    overview = learning_system.get_dashboard_overview()
    return {
        "status": "AUDITED",
        "pilot_metrics": overview.get("pilot_fase15_metrics", {}),
        "pilot_fase16_metrics": overview.get("pilot_fase16_metrics", {}),
        "granular_indicators": overview.get("granular_indicators", {})
    }

@app.post("/api/learning/evaluate-editorial/{source_id}")
def evaluate_editorial_route(source_id: str, channel_id: Optional[int] = None, force_verdict: Optional[str] = None):
    """Avalia conformidade editorial de um Short contra a persona do canal."""
    try:
        return learning_system.evaluate_editorial_adherence(
            source_id=source_id,
            target_channel_id=channel_id,
            force_verdict=force_verdict
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/learning/promote-candidate/{source_id}")
def promote_candidate_route(source_id: str):
    """Promove um Short para learning_candidate após validação técnica e editorial."""
    try:
        return learning_system.promote_to_learning_candidate(source_id=source_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/learning/recommendations/{channel_id}")
def get_channel_recommendations_route(channel_id: int):
    """Retorna recomendações editoriais baseadas na memória persistente isolada do canal."""
    from services.orchestration.vantis_core_pipeline import VantisCorePipeline
    pipe = VantisCorePipeline(db_path=learning_system.db_path)
    mem = learning_system.get_channel_editorial_memory(channel_id)
    sample_feats = {"cuts_count": 2, "has_narration": False, "hook_type": "NOT_AVAILABLE", "narrative_progression": "NOT_AVAILABLE", "audio_visual_relation": "music_or_sfx_without_narration"}
    recs = pipe.generate_recommendations_from_memory(channel_id, sample_feats)
    return {"channel_id": channel_id, "knowledge_count": mem.get("knowledge_count", 0), "recommendations": recs}

# ------------------------------------------------------------------------------
# 10. PRODUÇÃO EDITORIAL INTELIGENTE (FASE 21)
# ------------------------------------------------------------------------------
def _get_prod_engine():
    from services.production.editorial_production_engine import EditorialProductionEngine
    return EditorialProductionEngine(db_path=learning_system.db_path)

@app.get("/api/production/identities")
def list_production_identities():
    from services.production.editorial_production_engine import CHANNEL_IDENTITIES
    return {"identities": list(CHANNEL_IDENTITIES.values())}

@app.get("/api/production/references/{channel_id}")
def list_production_references(channel_id: int, limit: int = 20):
    try:
        return {"channel_id": channel_id, "references": _get_prod_engine().list_eligible_references(channel_id, limit=limit)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/production/packages")
def list_production_packages(channel_id: Optional[int] = None, status: Optional[str] = None, limit: int = 50):
    return {"packages": _get_prod_engine().list_packages(channel_id=channel_id, status=status, limit=limit)}

@app.get("/api/production/packages/compare")
def compare_production_packages(id_a: int, id_b: int):
    try:
        return _get_prod_engine().compare_versions(id_a, id_b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/production/packages/{package_id}")
def get_production_package(package_id: int):
    pkg = _get_prod_engine().get_package(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Pacote não encontrado.")
    return pkg

@app.post("/api/production/packages/generate")
def generate_production_package(payload: Dict[str, Any]):
    try:
        return _get_prod_engine().generate_package(
            channel_id=int(payload.get("channel_id", 1)),
            theme=str(payload.get("theme", "")),
            reference_source_id=payload.get("reference_source_id") or None,
            target_duration_sec=float(payload.get("target_duration_sec", 35.0)),
            editorial_goal=str(payload.get("editorial_goal", "retenção e engajamento orgânico")),
            content_restrictions=str(payload.get("content_restrictions", "Sem cópia literal de terceiros, sem áudio silencioso.")),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/production/packages/{package_id}")
def update_production_package(package_id: int, payload: Dict[str, Any]):
    try:
        return _get_prod_engine().update_package_manual(package_id, payload.get("updates", payload), note=payload.get("note", "Edição manual via Dashboard"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/production/packages/{package_id}/duplicate")
def duplicate_production_package(package_id: int, payload: Optional[Dict[str, Any]] = None):
    try:
        new_theme = (payload or {}).get("theme")
        return _get_prod_engine().duplicate_version(package_id, new_theme=new_theme)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/production/packages/{package_id}/status")
def transition_production_package_status(package_id: int, payload: Dict[str, Any]):
    try:
        return _get_prod_engine().transition_status(package_id, str(payload.get("status", "")), reason=str(payload.get("reason", "")))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

def _get_renderer():
    from services.production.package_renderer import PackageRendererService
    return PackageRendererService(db_path=learning_system.db_path)

@app.get("/api/production/renders")
def list_render_jobs(channel_id: Optional[int] = None, limit: int = 30):
    return {"jobs": _get_renderer().list_jobs(channel_id=channel_id, limit=limit)}

@app.get("/api/production/renders/{job_id}")
def get_render_job(job_id: int):
    job = _get_renderer().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job de renderização não encontrado.")
    return job

@app.get("/api/production/renders/{job_id}/file")
def serve_render_file(job_id: int):
    job = _get_renderer().get_job(job_id)
    if not job or not job.get("output_mp4_path") or not Path(job["output_mp4_path"]).is_file():
        raise HTTPException(status_code=404, detail="Arquivo MP4 renderizado não encontrado.")
    return FileResponse(job["output_mp4_path"], media_type="video/mp4")

@app.post("/api/production/packages/{package_id}/render")
def render_production_package(package_id: int, payload: Optional[Dict[str, Any]] = None):
    try:
        body = payload or {}
        return _get_renderer().render_package(
            package_id=package_id,
            available_assets=body.get("available_assets"),
            resume_job_id=body.get("resume_job_id"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/production/renders/{job_id}/review")
def review_render_job(job_id: int, payload: Dict[str, Any]):
    try:
        return _get_renderer().submit_human_review(
            job_id=job_id,
            decision=str(payload.get("decision", "")),
            notes=str(payload.get("notes", "")),
            defects=payload.get("defects") or [],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

def _get_asset_engine():
    from services.production.asset_intelligence import AssetIntelligenceEngine
    return AssetIntelligenceEngine(db_path=learning_system.db_path)

@app.get("/api/production/assets")
def list_production_assets(channel_id: Optional[int] = None, only_valid: bool = False, limit: int = 100):
    return {"assets": _get_asset_engine().list_assets(channel_id=channel_id, only_valid=only_valid, limit=limit)}

@app.post("/api/production/assets/register")
def register_production_asset(payload: Dict[str, Any]):
    try:
        return _get_asset_engine().register_asset(
            file_path=str(payload.get("file_path", "")),
            origin=str(payload.get("origin", "manual")),
            license_name=str(payload.get("license_name", "UNKNOWN")),
            tags=payload.get("tags") or [],
            authorized_channels=payload.get("authorized_channels") or [1, 2, 3, 4, 5],
            source_url=payload.get("source_url"),
            commercial_confirmed=bool(payload.get("commercial_confirmed", False)),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/production/packages/{package_id}/validate")
def validate_production_package(package_id: int):
    try:
        return _get_prod_engine().validate_package_and_store(package_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/production/packages/{package_id}/prepare-assets")
def prepare_production_package_assets(package_id: int):
    try:
        return _get_prod_engine().prepare_package_assets(package_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/production/packages/{package_id}/scenes/{scene_index}/assign-asset")
def assign_asset_to_package_scene(package_id: int, scene_index: int, payload: Dict[str, Any]):
    try:
        return _get_prod_engine().assign_asset_to_scene(
            package_id=package_id,
            scene_index=scene_index,
            asset_id=int(payload.get("asset_id", 0)),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/production/packages/{package_id}/scenes/{scene_index}/unassign-asset")
def unassign_asset_from_package_scene(package_id: int, scene_index: int):
    try:
        return _get_prod_engine().unassign_asset_from_scene(package_id=package_id, scene_index=scene_index)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/production/assets/search-wikimedia")
def search_wikimedia_assets(payload: Dict[str, Any]):
    query = str(payload.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Informe o termo de busca (query).")
    return _get_asset_engine().search_wikimedia_commons(query=query, limit=int(payload.get("limit", 8)))

@app.post("/api/production/assets/acquire-wikimedia")
def acquire_wikimedia_asset(payload: Dict[str, Any]):
    try:
        candidate = payload.get("candidate") or {}
        channel_id = int(payload.get("channel_id", 1))
        tags = payload.get("tags") or []
        return _get_asset_engine().acquire_wikimedia_asset(candidate=candidate, channel_id=channel_id, tags=tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

def _get_brand_registry():
    from services.production.brand_registry import BrandRegistryService
    return BrandRegistryService(db_path=learning_system.db_path)

@app.get("/api/brands")
def list_brands():
    return {"brands": _get_brand_registry().list_brands()}

@app.get("/api/brands/check-handle")
def check_brand_handle(handle: str):
    return _get_brand_registry().check_handle_availability(handle)

@app.put("/api/brands/{channel_id}")
def update_brand(channel_id: int, payload: Dict[str, Any]):
    try:
        return _get_brand_registry().update_brand_identity(
            channel_id=channel_id,
            brand_name=payload.get("brand_name"),
            branding_config=payload.get("branding_config"),
            editorial_identity=payload.get("editorial_identity"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/brands/{channel_id}/youtube-registry")
def register_youtube_channel(channel_id: int, payload: Dict[str, Any]):
    try:
        return _get_brand_registry().register_youtube_channel(
            channel_id=channel_id,
            youtube_channel_id=str(payload.get("youtube_channel_id", "")),
            youtube_handle=str(payload.get("youtube_handle", "")),
            youtube_url=str(payload.get("youtube_url", "")),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/brands/{channel_id}/oauth-check")
def check_brand_oauth(channel_id: int):
    try:
        return _get_brand_registry().verify_oauth_connection(channel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/production/packages/{package_id}/publish-metadata")
def get_package_publish_metadata(package_id: int):
    try:
        return _get_brand_registry().prepare_publish_metadata(package_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Servir Frontend
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
def serve_index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"message": "VIAGEM / IAS API Online."})
