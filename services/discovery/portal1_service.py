"""
IAS Portal 1: Governança Humana de Descoberta & Aprovação de Pautas
Garante que nenhuma oportunidade ou referência entre no pipeline de produção
sem validação humana explícita, verificação de direitos autorais e conformidade editorial.
"""
import os
import sys
import json
import sqlite3
import datetime
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.video_analysis.yt_metadata import VideoMetadataService
from services.semantic_memory.vector_memory import VectorMemoryService
from memory.central_memory import CentralMemory

logger = logging.getLogger("IAS.Portal1")

VALID_REJECTION_CATEGORIES = [
    "direitos_autorais",
    "saturado",
    "fora_da_persona",
    "baixa_qualidade",
    "sensacionalismo"
]

class Portal1GovernanceService:
    """Serviço de governança editorial do Portal 1 (Human-in-the-Loop de Pautas)."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(BASE_DIR / "database" / "shorts_central.db")
        self.meta_svc = VideoMetadataService(db_path=self.db_path)
        self.vector_mem = VectorMemoryService(db_path=self.db_path)
        self.central_mem = CentralMemory(db_path=Path(self.db_path))

    def list_opportunities(
        self,
        status: Optional[str] = "PENDING_REVIEW",
        channel_id: Optional[int] = None,
        niche: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Lista oportunidades de conteúdo mineradas com filtros por status e canal."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = """
                SELECT opportunity_id, source_platform, source_url, niche, subniche,
                       title_concept, context_description, popularity_evidence,
                       confidence_score, recommended_channel_id, technical_justification,
                       status, rejection_reason, rejection_category, reviewed_by, reviewed_at, created_at
                FROM opportunities WHERE 1=1
            """
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if channel_id:
                query += " AND recommended_channel_id = ?"
                params.append(channel_id)
            if niche:
                query += " AND niche = ?"
                params.append(niche)

            query += " ORDER BY confidence_score DESC, created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for r in rows:
                pop_raw = r[7]
                pop_evidence = json.loads(pop_raw) if pop_raw else {}
                results.append({
                    "opportunity_id": r[0],
                    "source_platform": r[1],
                    "source_url": r[2],
                    "niche": r[3],
                    "subniche": r[4],
                    "title_concept": r[5],
                    "context_description": r[6],
                    "popularity_evidence": pop_evidence,
                    "confidence_score": r[8],
                    "recommended_channel_id": r[9],
                    "technical_justification": r[10],
                    "status": r[11],
                    "rejection_reason": r[12],
                    "rejection_category": r[13],
                    "reviewed_by": r[14],
                    "reviewed_at": r[15],
                    "created_at": r[16]
                })
            return results

    def get_opportunity(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        """Recupera detalhes de uma oportunidade específica."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT opportunity_id, source_platform, source_url, niche, subniche,
                       title_concept, context_description, popularity_evidence,
                       confidence_score, recommended_channel_id, technical_justification,
                       status, rejection_reason, rejection_category, reviewed_by, reviewed_at, created_at
                FROM opportunities WHERE opportunity_id = ?
            """, (opportunity_id,))
            r = cursor.fetchone()
            if not r:
                return None
            pop_evidence = json.loads(r[7]) if r[7] else {}
            return {
                "opportunity_id": r[0],
                "source_platform": r[1],
                "source_url": r[2],
                "niche": r[3],
                "subniche": r[4],
                "title_concept": r[5],
                "context_description": r[6],
                "popularity_evidence": pop_evidence,
                "confidence_score": r[8],
                "recommended_channel_id": r[9],
                "technical_justification": r[10],
                "status": r[11],
                "rejection_reason": r[12],
                "rejection_category": r[13],
                "reviewed_by": r[14],
                "reviewed_at": r[15],
                "created_at": r[16]
            }

    def approve_opportunity(
        self,
        opportunity_id: str,
        reviewer: str = "Diretor Editorial",
        auto_dispatch: bool = False
    ) -> Dict[str, Any]:
        """
        Aprova uma oportunidade de conteúdo no Portal 1.
        Avança o ciclo de vida do vídeo e indexa o gancho na memória semântica.
        """
        opp = self.get_opportunity(opportunity_id)
        if not opp:
            return {"success": False, "error": f"Oportunidade '{opportunity_id}' não encontrada"}

        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE opportunities
                SET status = 'APPROVED', reviewed_by = ?, reviewed_at = ?, updated_at = ?
                WHERE opportunity_id = ?
            """, (reviewer, now_iso, now_iso, opportunity_id))
            conn.commit()

        # Extrai ID do vídeo a partir da URL ou opportunity_id
        source_url = opp["source_url"]
        video_id = source_url.split("/")[-1].replace("watch?v=", "")

        # Avança a máquina de estados de direitos e produção
        self.meta_svc.advance_status(video_id, "autorizado", notes=f"Autorizado pelo Portal 1 por {reviewer}")
        self.meta_svc.advance_status(video_id, "aprovado_para_produção", notes="Liberado para roteirização e produção")

        # Indexa na memória semântica vetorial
        self.vector_mem.index_hook(
            hook_id=f"hook_{video_id}",
            hook_text=opp["title_concept"],
            retention_score=opp["confidence_score"],
            niche=opp["niche"]
        )

        dispatch_res = None
        if auto_dispatch:
            from services.orchestration.central_controller import CentralOperationsController
            controller = CentralOperationsController(db_path=self.db_path)
            dispatch_res = controller.dispatch_workflow(
                task_id=f"wf_{opportunity_id}",
                target_id=video_id,
                niche=opp["niche"],
                channel_id=opp["recommended_channel_id"],
                priority=80
            )

        logger.info(f"[Portal1] Oportunidade {opportunity_id} APROVADA por {reviewer}.")
        return {
            "success": True,
            "opportunity_id": opportunity_id,
            "status": "APPROVED",
            "video_id": video_id,
            "channel_id": opp["recommended_channel_id"],
            "reviewed_by": reviewer,
            "indexed_in_memory": True,
            "dispatched_workflow": dispatch_res is not None,
            "workflow_state": dispatch_res
        }

    def reject_opportunity(
        self,
        opportunity_id: str,
        rejection_reason: str,
        rejection_category: str = "fora_da_persona",
        reviewer: str = "Diretor Editorial"
    ) -> Dict[str, Any]:
        """
        Rejeita uma oportunidade no Portal 1 com registro do motivo e categoria,
        alimentando a memória negativa para a IA não insistir no mesmo padrão.
        """
        opp = self.get_opportunity(opportunity_id)
        if not opp:
            return {"success": False, "error": f"Oportunidade '{opportunity_id}' não encontrada"}

        if rejection_category not in VALID_REJECTION_CATEGORIES:
            rejection_category = "fora_da_persona"

        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE opportunities
                SET status = 'REJECTED', rejection_reason = ?, rejection_category = ?,
                    reviewed_by = ?, reviewed_at = ?, updated_at = ?
                WHERE opportunity_id = ?
            """, (rejection_reason, rejection_category, reviewer, now_iso, now_iso, opportunity_id))
            conn.commit()

        # Atualiza ciclo de vida
        source_url = opp["source_url"]
        video_id = source_url.split("/")[-1].replace("watch?v=", "")
        self.meta_svc.advance_status(video_id, "rejeitado", notes=f"Rejeitado no Portal 1 ({rejection_category}): {rejection_reason}")

        # Alimenta memória central com feedback negativo (aprendizado da IA)
        self.central_mem.record_knowledge_node(
            category_slug=opp["niche"],
            node_type="rejected_pattern",
            title=f"Rejeição Editorial: {opp['title_concept'][:40]}",
            pattern_data={
                "niche": opp["niche"],
                "reason": rejection_reason,
                "category": rejection_category,
                "confidence_was": opp["confidence_score"]
            },
            effectiveness_score=0.0
        )

        # Indexa padrão negativo na memória vetorial isolada por canal (Prompt 11)
        self.vector_mem.index_item(
            item_id=f"rejected_{opportunity_id}",
            text=f"PADRÃO REJEITADO: {opp['title_concept']}. Motivo: {rejection_reason} ({rejection_category})",
            category="rejected_pattern",
            metadata={
                "opportunity_id": opportunity_id,
                "niche": opp["niche"],
                "reason": rejection_reason,
                "category": rejection_category,
                "confidence_score": opp["confidence_score"]
            },
            channel_id=opp["recommended_channel_id"]
        )

        logger.info(f"[Portal1] Oportunidade {opportunity_id} REJEITADA por {reviewer}. Motivo: {rejection_reason} ({rejection_category})")
        return {
            "success": True,
            "opportunity_id": opportunity_id,
            "status": "REJECTED",
            "video_id": video_id,
            "rejection_reason": rejection_reason,
            "rejection_category": rejection_category,
            "reviewed_by": reviewer,
            "feedback_learned": True
        }

    def get_governance_metrics(self) -> Dict[str, Any]:
        """Retorna indicadores operacionais do Portal 1 (taxa de aprovação, motivos de rejeição)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM opportunities GROUP BY status")
            status_counts = {r[0]: r[1] for r in cursor.fetchall()}

            cursor.execute("SELECT rejection_category, COUNT(*) FROM opportunities WHERE status = 'REJECTED' GROUP BY rejection_category")
            rejection_counts = {r[0]: r[1] for r in cursor.fetchall() if r[0]}

            total = sum(status_counts.values())
            pending = status_counts.get("PENDING_REVIEW", 0)
            approved = status_counts.get("APPROVED", 0)
            rejected = status_counts.get("REJECTED", 0)
            
            reviewed_total = approved + rejected
            approval_rate = round((approved / reviewed_total * 100), 2) if reviewed_total > 0 else 0.0

            return {
                "total_opportunities": total,
                "pending_review": pending,
                "approved": approved,
                "rejected": rejected,
                "approval_rate_pct": approval_rate,
                "rejections_by_category": rejection_counts
            }
