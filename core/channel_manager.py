"""
Módulo de Gerenciamento Estratégico dos 20 Canais de YouTube (IAS Multichannel System).
Controla identidade editorial, isolamento por canal, perfis visuais,
estilos de legenda, vozes de narração, limites de upload e finanças.
"""
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "shorts_central.db"

class ChannelManager:
    """Gerenciador central de multitenancy, identidades e configurações dos 20 canais."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DB_PATH)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def list_all_channels(self) -> List[Dict[str, Any]]:
        """Retorna todos os 20 canais com métricas consolidadas e status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.*, 
                       (SELECT COUNT(*) FROM scripts s WHERE s.channel_id = c.id) as total_scripts,
                       (SELECT COUNT(*) FROM publications p WHERE p.channel_id = c.id) as total_published
                FROM channels c
                ORDER BY c.channel_number ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_channel_by_id(self, channel_id: Any) -> Optional[Dict[str, Any]]:
        """Recupera detalhes estratégicos de um canal específico por id, número ou slug."""
        import re
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if isinstance(channel_id, str):
                if channel_id.isdigit():
                    num = int(channel_id)
                    cursor.execute("SELECT * FROM channels WHERE id = ? OR channel_number = ?", (num, num))
                else:
                    match = re.search(r'canal_0*(\d+)', channel_id.lower())
                    if match:
                        num = int(match.group(1))
                        cursor.execute("SELECT * FROM channels WHERE id = ? OR channel_number = ?", (num, num))
                    else:
                        cursor.execute("SELECT * FROM channels WHERE name LIKE ? OR category LIKE ?", (f"%{channel_id}%", f"%{channel_id}%"))
            else:
                cursor.execute("SELECT * FROM channels WHERE id = ? OR channel_number = ?", (channel_id, channel_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_channel(self, channel_id: Any) -> Optional[Dict[str, Any]]:
        """Alias para get_channel_by_id."""
        return self.get_channel_by_id(channel_id)

    def get_editorial_profile(self, channel_id: Any) -> Optional[Dict[str, Any]]:
        """Retorna o perfil editorial consolidado para os agentes."""
        prof = self.get_channel_profile(channel_id)
        if not prof:
            return {}
        return {
            "channel_id": prof.get("channel_id"),
            "name": prof.get("name"),
            "niche": prof.get("niche"),
            "tone_of_voice": prof.get("communication_tone", "dinâmico"),
            "target_audience": prof.get("target_audience", "Geral"),
            "visual_style": prof.get("editing_style", "moderno"),
            "subtitle_font": prof.get("subtitle_style", {}).get("font", "Arial Black"),
            "target_voice": prof.get("voice_profile", {}).get("voice_id", "pt-BR-AntonioNeural"),
            "forbidden_terms": prof.get("catchphrases", []),
            "brand_colors": prof.get("brand_colors", {})
        }

    def get_channel_settings(self, channel_id: int) -> Dict[str, Any]:
        """Recupera todas as configurações específicas de um canal (cores, voz, legendas, arquétipo)."""
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return {}
        real_id = channel["id"]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT setting_key, setting_value FROM channel_settings WHERE channel_id = ?", (real_id,))
            rows = cursor.fetchall()
            settings = {}
            for row in rows:
                k = row["setting_key"]
                v = row["setting_value"]
                try:
                    settings[k] = json.loads(v)
                except Exception:
                    settings[k] = v
            return settings

    def set_channel_setting(self, channel_id: int, key: str, value: Any) -> bool:
        """Define ou atualiza uma configuração personalizada de um canal."""
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return False
        real_id = channel["id"]

        val_str = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO channel_settings (channel_id, setting_key, setting_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (real_id, key, val_str))
            conn.commit()
            return cursor.rowcount > 0

    def get_channel_profile(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """
        Retorna o perfil consolidado e completo do canal, unindo metadados,
        arquétipo editorial, identidade visual, estilo de legenda e perfil de voz.
        """
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return None

        settings = self.get_channel_settings(channel["id"])
        
        # Valores padrão seguros para canais sem configurações avançadas
        default_brand_colors = {"primary": "#FF0000", "secondary": "#FFFFFF", "background": "#000000", "highlight": "#FFFF00"}
        default_subtitle_style = {"font": "Arial Black", "fontsize": 75, "primary_colour": "&H00FFFFFF&", "outline_colour": "&H00000000&", "bold": 1, "outline": 4}
        default_voice_profile = {"engine": "edge-tts", "voice_id": "pt-BR-AntonioNeural", "rate": "+10%", "pitch": "+0Hz"}

        return {
            "channel_id": channel["id"],
            "channel_number": channel["channel_number"],
            "name": channel["name"],
            "niche": channel["niche"],
            "subniche": channel.get("subniche"),
            "target_audience": channel.get("target_audience"),
            "communication_tone": channel.get("communication_tone"),
            "editing_style": channel.get("editing_style"),
            "editorial_strategy": channel.get("editorial_strategy"),
            "gdrive_folder_id": channel.get("gdrive_folder_id"),
            "archetype_slug": settings.get("archetype_slug", "estrategista_retencao"),
            "wpm_target": int(settings.get("wpm_target", 165)),
            "brand_colors": settings.get("brand_colors", default_brand_colors),
            "subtitle_style": settings.get("subtitle_style", default_subtitle_style),
            "voice_profile": settings.get("voice_profile", default_voice_profile),
            "catchphrases": settings.get("catchphrases", []),
            "status": channel.get("status", "active")
        }

    def get_channel_editorial_guidelines(self, channel_id: int) -> str:
        """
        Gera diretrizes detalhadas de injeção de prompt para os agentes de roteirização
        e produção, garantindo que o canal mantenha sua voz e não homogeneíze com os demais.
        """
        prof = self.get_channel_profile(channel_id)
        if not prof:
            return "Atue como roteirista profissional de YouTube Shorts."

        catchphrases_str = "\n".join([f"- \"{c}\"" for c in prof["catchphrases"]]) if prof["catchphrases"] else "- Sem bordões fixos."

        return (
            f"=== DIRETRIZES EDITORIAIS EXCLUSIVAS: {prof['name'].upper()} ===\n"
            f"Nicho: {prof['niche']} (Subnicho: {prof['subniche']})\n"
            f"Público-Alvo: {prof['target_audience']}\n"
            f"Tom de Comunicação: {prof['communication_tone']}\n"
            f"Arquétipo Editorial: {prof['archetype_slug']}\n"
            f"Ritmo Desejado: {prof['wpm_target']} Palavras Por Minuto (WPM)\n"
            f"Estilo de Edição: {prof['editing_style']}\n"
            f"Estratégia Editorial: {prof['editorial_strategy']}\n"
            f"Bordões Característicos:\n{catchphrases_str}\n"
            f"REGRAS:\n"
            f"1. Não utilize gírias ou jargões de outros nichos.\n"
            f"2. Estruture em: Gancho nos primeiros 3s, Revelação/Tensão e CTA alinhado ao canal.\n"
            f"3. Respeite rigorosamente a personalidade do canal.\n"
        )

    def get_gdrive_folder_id(self, channel_id: int) -> str:
        """Recupera o ID da pasta do Google Drive do canal com fallback seguro."""
        channel = self.get_channel_by_id(channel_id)
        if channel and channel.get("gdrive_folder_id"):
            return channel["gdrive_folder_id"]

        # Consulta config/gdrive_folders.json
        cfg_path = BASE_DIR / "config" / "gdrive_folders.json"
        ch_key = f"canal_{str(channel_id).zfill(2)}"
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if ch_key in data:
                        return data[ch_key]
            except Exception:
                pass

        return "1Qcd6DS3zA0OrNKSeDSPTHyl_P0y0l9jf" # Fallback Canal 01

    def update_channel_strategy(
        self,
        channel_id: int,
        name: Optional[str] = None,
        niche: Optional[str] = None,
        subniche: Optional[str] = None,
        target_audience: Optional[str] = None,
        editing_style: Optional[str] = None,
        communication_tone: Optional[str] = None,
        editorial_strategy: Optional[str] = None,
        posting_frequency: Optional[str] = None,
        status: Optional[str] = None
    ) -> bool:
        """Atualiza a identidade e estratégia editorial de um canal."""
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return False
        real_id = channel["id"]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE channels SET
                    name = COALESCE(?, name),
                    niche = COALESCE(?, niche),
                    subniche = COALESCE(?, subniche),
                    target_audience = COALESCE(?, target_audience),
                    editing_style = COALESCE(?, editing_style),
                    communication_tone = COALESCE(?, communication_tone),
                    editorial_strategy = COALESCE(?, editorial_strategy),
                    posting_frequency = COALESCE(?, posting_frequency),
                    status = COALESCE(?, status)
                WHERE id = ?
            """, (name, niche, subniche, target_audience, editing_style, communication_tone, 
                  editorial_strategy, posting_frequency, status, real_id))
            conn.commit()
            return cursor.rowcount > 0

    def create_channel(
        self,
        name: str,
        niche: str,
        subniche: Optional[str] = None,
        target_audience: Optional[str] = None,
        language: str = "pt-BR",
        communication_tone: Optional[str] = None,
        editing_style: Optional[str] = None,
        posting_frequency: Optional[str] = None,
        goals: Optional[str] = None,
        editorial_strategy: Optional[str] = None,
        visual_identity: Optional[Dict[str, Any]] = None,
        voice_profile: Optional[Dict[str, Any]] = None,
        subtitle_style: Optional[Dict[str, Any]] = None,
        content_formats: Optional[List[str]] = None,
        references: Optional[List[str]] = None,
        rules_restrictions: Optional[List[str]] = None,
        catchphrases: Optional[List[str]] = None,
        archetype_slug: Optional[str] = None,
        status: str = "draft"
    ) -> Dict[str, Any]:
        """
        Cadastra um novo canal no sistema (suporta rascunho parcial e completude incremental).
        Garante isolamento completo e integridade de multitenancy conforme Prompt 08.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(channel_number), 0) + 1 FROM channels")
            next_num = cursor.fetchone()[0]

            vis_ident_str = json.dumps(visual_identity, ensure_ascii=False) if visual_identity else None

            cursor.execute("""
                INSERT INTO channels (
                    channel_number, name, niche, subniche, target_audience, language,
                    visual_identity, editing_style, communication_tone, posting_frequency,
                    goals, editorial_strategy, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                next_num, name, niche, subniche, target_audience, language,
                vis_ident_str, editing_style, communication_tone, posting_frequency,
                goals, editorial_strategy, status
            ))
            channel_id = cursor.lastrowid
            conn.commit()

        # Configurações adicionais salvas em channel_settings
        if archetype_slug:
            self.set_channel_setting(channel_id, "archetype_slug", archetype_slug)
        if visual_identity:
            self.set_channel_setting(channel_id, "brand_colors", visual_identity)
        if voice_profile:
            self.set_channel_setting(channel_id, "voice_profile", voice_profile)
        if subtitle_style:
            self.set_channel_setting(channel_id, "subtitle_style", subtitle_style)
        if content_formats:
            self.set_channel_setting(channel_id, "content_formats", content_formats)
        if references:
            self.set_channel_setting(channel_id, "references", references)
        if rules_restrictions:
            self.set_channel_setting(channel_id, "rules_restrictions", rules_restrictions)
        if catchphrases:
            self.set_channel_setting(channel_id, "catchphrases", catchphrases)

        return self.get_channel_profile(channel_id)

    def archive_channel(self, channel_id: Any) -> bool:
        """Arquiva um canal, desativando-o para operações regulares sem perda de histórico."""
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return False
        real_id = channel["id"]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE channels SET status = 'archived' WHERE id = ?", (real_id,))
            conn.commit()
            return cursor.rowcount > 0

    def set_pilot_channel(self, channel_id: Any) -> bool:
        """Marca o canal selecionado como canal-piloto ativo para testes e produção."""
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return False
        real_id = channel["id"]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM channel_settings WHERE setting_key = 'is_pilot'")
            conn.commit()
        return self.set_channel_setting(real_id, "is_pilot", True)

    def get_channel_readiness(self, channel_id: Any) -> Dict[str, Any]:
        """
        Avalia o grau de completude da configuração do canal (0 a 100%).
        Lista campos pendentes e próximos passos recomendados para início de produção.
        """
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return {"error": "Canal não encontrado", "completion_percentage": 0, "is_ready_for_production": False}

        settings = self.get_channel_settings(channel["id"])
        
        checks = [
            ("name", bool(channel.get("name")), "Nome do canal"),
            ("niche", bool(channel.get("niche")), "Nicho editorial"),
            ("target_audience", bool(channel.get("target_audience")), "Público-alvo definido"),
            ("communication_tone", bool(channel.get("communication_tone")), "Tom de voz e comunicação"),
            ("visual_identity", bool(settings.get("brand_colors") or channel.get("visual_identity")), "Identidade visual (cores da marca)"),
            ("voice_profile", bool(settings.get("voice_profile")), "Perfil de voz de narração TTS"),
            ("subtitle_style", bool(settings.get("subtitle_style")), "Estilo de legenda dinâmico"),
            ("posting_frequency", bool(channel.get("posting_frequency")), "Frequência de publicação planejada"),
            ("rules_restrictions", bool(settings.get("rules_restrictions") or settings.get("catchphrases")), "Regras editoriais e restrições"),
            ("gdrive_folder", bool(channel.get("gdrive_folder_id")), "Pasta Google Drive associada")
        ]

        completed_count = sum(1 for _, ok, _ in checks if ok)
        total_checks = len(checks)
        percentage = round((completed_count / total_checks) * 100)
        missing_fields = [label for _, ok, label in checks if not ok]

        next_steps = []
        if "Tom de voz e comunicação" in missing_fields:
            next_steps.append("Definir o tom de comunicação (ex: enérgico, investigativo, irônico)")
        if "Perfil de voz de narração TTS" in missing_fields:
            next_steps.append("Selecionar a voz neural preferida para os Shorts (Edge-TTS)")
        if "Estilo de legenda dinâmico" in missing_fields:
            next_steps.append("Configurar a tipografia e cor das legendas ASS")
        if "Regras editoriais e restrições" in missing_fields:
            next_steps.append("Adicionar termos proibidos, bordões e diretrizes de retenção")
        if not next_steps:
            next_steps.append("Canal 100% configurado e pronto para produção autônoma de Shorts.")

        is_pilot = bool(settings.get("is_pilot", False)) or channel.get("channel_number") == 1

        return {
            "channel_id": channel["id"],
            "channel_number": channel["channel_number"],
            "name": channel["name"],
            "status": channel.get("status", "draft"),
            "is_pilot": is_pilot,
            "completion_percentage": percentage,
            "is_ready_for_production": percentage >= 80,
            "missing_fields": missing_fields,
            "next_steps": next_steps
        }

    def get_channel_memory_summary(self, channel_id: Any) -> Dict[str, Any]:
        """
        Retorna o sumário da memória e feedback exclusivo do canal (aprovações vs rejeições).
        Comprova o isolamento de memória semântica entre canais.
        """
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return {}
        real_id = channel["id"]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM opportunities
                WHERE recommended_channel_id = ?
                GROUP BY status
            """, (real_id,))
            opp_stats = {r["status"]: r["count"] for r in cursor.fetchall()}

            cursor.execute("""
                SELECT COUNT(*) as vector_count
                FROM semantic_vectors
                WHERE channel_id = ?
            """, (real_id,))
            v_row = cursor.fetchone()
            vector_count = v_row["vector_count"] if v_row else 0

            return {
                "channel_id": real_id,
                "channel_name": channel["name"],
                "approved_opportunities": opp_stats.get("APPROVED", 0),
                "rejected_opportunities": opp_stats.get("REJECTED", 0),
                "pending_review": opp_stats.get("PENDING_REVIEW", 0),
                "semantic_vectors_indexed": vector_count,
                "isolation_namespace": f"channel_{real_id}"
            }

    def record_financial_entry(
        self,
        channel_id: int,
        entry_type: str,
        category: str,
        amount_usd: float,
        description: str = "",
        reference_id: Optional[str] = None
    ) -> int:
        """Registra lançamento financeiro isolado por canal (custo ou receita)."""
        channel = self.get_channel_by_id(channel_id)
        real_id = channel["id"] if channel else 1

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO financial_logs (channel_id, log_type, category, amount_usd, description, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (real_id, entry_type, category, amount_usd, description, json.dumps({"reference_id": reference_id} if reference_id else {})))
            conn.commit()
            return cursor.lastrowid

    def get_financial_summary(self, channel_id: Optional[Any] = None) -> Dict[str, Any]:
        """Calcula balanço financeiro isolado por canal ou consolidado para toda a plataforma."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if channel_id is not None:
                channel = self.get_channel_by_id(channel_id)
                real_id = channel["id"] if channel else 1
                cursor.execute("""
                    SELECT log_type, SUM(amount_usd) as total
                    FROM financial_logs
                    WHERE channel_id = ?
                    GROUP BY log_type
                """, (real_id,))
            else:
                real_id = "all"
                cursor.execute("""
                    SELECT log_type, SUM(amount_usd) as total
                    FROM financial_logs
                    GROUP BY log_type
                """)
            rows = cursor.fetchall()
            
            costs = 0.0
            revenues = 0.0
            avoided = 0.0
            for r in rows:
                lt = r["log_type"]
                val = float(r["total"] or 0.0)
                if lt in ("cost", "expense"):
                    costs += val
                elif lt == "revenue":
                    revenues += val
                elif lt == "avoided_cost":
                    avoided += val

            margin = revenues - costs
            roi_pct = ((margin / costs) * 100) if costs > 0 else 0.0

            return {
                "channel_id": real_id,
                "total_costs_usd": round(costs, 4),
                "total_expenses": round(costs, 4),
                "total_revenue_usd": round(revenues, 4),
                "total_avoided_cost": round(avoided, 4),
                "net_profit_usd": round(margin, 4),
                "roi_percentage": round(roi_pct, 2)
            }
