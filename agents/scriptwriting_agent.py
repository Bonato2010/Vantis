"""
Agente de Roteirização e Storytelling (VANTIS Creative & Scriptwriting)
Responsável por gerar roteiros estruturados em 3 partes (Gancho, Retenção, CTA),
respeitando a persona e o tom de cada canal, minerando ganchos na memória vetorial
e garantindo operação com custo estritamente zero ($0.00).
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.base_vantis_agent import VantisBaseAgent, AgentTaskContext
from services.model_gateway.gateway import ModelGatewayService
from services.semantic_memory.vector_memory import VectorMemoryService
from core.channel_manager import ChannelManager


class ScriptwritingOutput(BaseModel):
    script_id: Optional[int] = Field(default=None, description="ID do roteiro persistido no banco")
    hook: str = Field(..., description="Gancho inicial de 3 segundos para máxima retenção")
    body: str = Field(..., description="Corpo central com desenvolvimento dinâmico")
    cta: str = Field(..., description="Chamada para ação final")
    full_script: str = Field(..., description="Texto integral do roteiro concatenado")
    word_count: int = Field(..., description="Contagem total de palavras")
    estimated_duration_sec: float = Field(..., description="Duração estimada em segundos")
    model_used: str = Field(..., description="Modelo de linguagem utilizado")
    cost_usd: float = Field(default=0.0, description="Custo financeiro incorrido (estritamente 0.00)")


class ScriptwritingAgent(VantisBaseAgent):
    """
    Agente responsável pela geração e adaptação de roteiros para Shorts (15 a 59 segundos).
    Aplica técnicas de retenção, consulta memórias vetoriais isoladas por canal e opera via Gateway de Modelos gratuitos.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(
            agent_id="agt_scriptwriter",
            name="Agente de Roteirização e Storytelling",
            department="Creative & Scriptwriting",
            responsibility="Gerar roteiros estruturados (Hook, Retenção, CTA) respeitando a identidade editorial do canal com custo $0.00",
            input_schema=AgentTaskContext,
            output_schema=ScriptwritingOutput,
            db_path=db_path
        )
        self.set_success_criteria(["full_script", "cost_usd"])

    def _process(self, context: AgentTaskContext) -> Dict[str, Any]:
        target_id = context.target_id or "ref_default_01"
        channel_id = context.channel_id or 1
        niche = context.niche or "geral"

        # 1. Recupera perfil do canal e memórias vetoriais de ganchos de sucesso
        cm = ChannelManager(db_path=str(self.db_path))
        profile = cm.get_editorial_profile(channel_id) or {}
        tone = profile.get("tone_of_voice", "dinâmico e informativo")
        style = profile.get("visual_style", "moderno")

        vector_mem = VectorMemoryService(db_path=str(self.db_path))
        # Busca semântica de ganchos com isolamento estrito de canal
        stored_hooks = vector_mem.search_hooks(query=f"shorts {niche}", channel_id=channel_id, top_k=3)
        hook_context = ""
        if stored_hooks:
            hook_context = f" Exemplos de ganchos aprovados para este canal: {', '.join([h.get('hook_text', '') for h in stored_hooks if h.get('hook_text')])}."

        # 2. Geração via ModelGateway com enforce_free_tier = True ($0.00)
        gateway = ModelGatewayService(db_path=str(self.db_path), enforce_free_tier=True)
        prompt = (
            f"Você é o roteirista sênior do canal {channel_id} (nicho: {niche}, tom: {tone}).\n"
            f"Crie um roteiro viral para YouTube Shorts de 30 a 45 segundos sobre o tema '{target_id}'.{hook_context}\n"
            f"Estrutura obrigatória:\n"
            f"HOOK: [Frase impactante de 3 segundos]\n"
            f"BODY: [Desenvolvimento ágil com 3 fatos ou reviravoltas]\n"
            f"CTA: [Chamada rápida para inscrição ou comentário]"
        )

        gw_res = gateway.generate(
            prompt=prompt,
            task="scriptwriting",
            channel_id=channel_id,
            max_tokens=400,
            temperature=0.7
        )

        raw_text = gw_res.get("text", "")
        model_used = gw_res.get("model", "free-tier-engine")
        cost_usd = gw_res.get("cost_usd", 0.0)

        # 3. Parse das 3 partes estruturadas
        hook = f"Você não vai acreditar no que aconteceu com {target_id}!"
        body = f"Analisando os fatos deste caso em {niche}, descobrimos um detalhe crucial que quase ninguém percebeu. Isso muda completamente a perspectiva sobre o assunto."
        cta = "Se você concorda, já deixa o like e se inscreve no canal!"

        if "HOOK:" in raw_text and "BODY:" in raw_text:
            parts = raw_text.split("BODY:")
            hook_part = parts[0].replace("HOOK:", "").strip()
            if hook_part:
                hook = hook_part
            rest = parts[1]
            if "CTA:" in rest:
                body_part, cta_part = rest.split("CTA:")
                if body_part.strip():
                    body = body_part.strip()
                if cta_part.strip():
                    cta = cta_part.strip()
            else:
                body = rest.strip()
        elif raw_text.strip():
            body = raw_text.strip()

        full_script = f"{hook}\n\n{body}\n\n{cta}"
        words = len(full_script.split())
        est_duration = round(words / 2.5, 1) # ~150 palavras por minuto

        return {
            "hook": hook,
            "body": body,
            "cta": cta,
            "full_script": full_script,
            "word_count": words,
            "estimated_duration_sec": max(est_duration, 15.0),
            "model_used": model_used,
            "cost_usd": cost_usd
        }
