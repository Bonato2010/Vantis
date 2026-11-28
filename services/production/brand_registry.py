"""
VANTIS — Registro de Marcas, Canais Reais YouTube e Prontidão de Publicação (Fase 27)
Separa marca pública (brand_name), categoria editorial (editorial_category) e
canal real do YouTube (youtube_channel_id / handle / URL / OAuth), sem simular OAuth nem inventar IDs.
"""
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from services.production.editorial_production_engine import CHANNEL_IDENTITIES, EditorialProductionEngine

BASE_DIR = Path(__file__).resolve().parent.parent.parent

CHANNEL_STATUSES = (
    "BRAND_CONFIGURED",
    "CHANNEL_NOT_CREATED",
    "CHANNEL_CREATED_UNVERIFIED",
    "CHANNEL_VERIFIED",
    "READY_FOR_UPLOAD",
)

OAUTH_STATUSES = (
    "OAUTH_DISCONNECTED",
    "OAUTH_CONNECTED",
)

DEFAULT_BRAND_PROPOSALS: Dict[int, Dict[str, Any]] = {
    1: {
        "brand_name": "Zona de Jogo",
        "editorial_category": "Futebol",
        "proposed_handle": "@zonadejogo",
        "name_availability_status": "HANDLE_IN_USE_PUBLICLY",
        "availability_note": "Handle @zonadejogo retornou HTTP 200 no YouTube (provavelmente em uso; confirmar variante no YouTube Studio).",
        "branding_config": {
            "logo_path": None, "logo_status": "PENDING_DESIGN",
            "avatar_path": None, "avatar_status": "PENDING_DESIGN",
            "banner_path": None, "banner_status": "PENDING_DESIGN",
            "color_palette": ["#0B3D2E", "#16A34A", "#FACC15", "#FFFFFF"],
            "typography": "Montserrat ExtraBold / Inter",
            "thumbnail_style": "Lance em destaque com placar/seta de alto contraste",
            "audiovisual_identity": "Cortes dinâmicos 1.8s–3.0s, energia de arquibancada",
            "visual_approval_status": "PENDING_HUMAN_APPROVAL",
        },
    },
    2: {
        "brand_name": "Dossiê Oculto",
        "editorial_category": "Arquivo Sombrio",
        "proposed_handle": "@dossieoculto",
        "name_availability_status": "AVAILABILITY_UNVERIFIED",
        "availability_note": "Handle @dossieoculto retornou HTTP 404 na consulta pública; disponibilidade real deve ser confirmada no YouTube Studio.",
        "branding_config": {
            "logo_path": None, "logo_status": "PENDING_DESIGN",
            "avatar_path": None, "avatar_status": "PENDING_DESIGN",
            "banner_path": None, "banner_status": "PENDING_DESIGN",
            "color_palette": ["#0F172A", "#1E293B", "#DC2626", "#E2E8F0"],
            "typography": "Cinzel / Roboto Condensed",
            "thumbnail_style": "Documento frio, carimbo temporal e alto contraste",
            "audiovisual_identity": "Atmosfera investigativa sóbria, sem gore",
            "visual_approval_status": "PENDING_HUMAN_APPROVAL",
        },
    },
    3: {
        "brand_name": "Caos em 60s",
        "editorial_category": "Humor",
        "proposed_handle": "@caosem60s",
        "name_availability_status": "HANDLE_IN_USE_PUBLICLY",
        "availability_note": "Handle @caosem60s retornou HTTP 200 no YouTube (provavelmente em uso; confirmar variante no YouTube Studio).",
        "branding_config": {
            "logo_path": None, "logo_status": "PENDING_DESIGN",
            "avatar_path": None, "avatar_status": "PENDING_DESIGN",
            "banner_path": None, "banner_status": "PENDING_DESIGN",
            "color_palette": ["#FF5A1F", "#FACC15", "#111827", "#FFFFFF"],
            "typography": "Poppins Black / Nunito",
            "thumbnail_style": "Expressão cotidiana exagerada com texto curto de 3 palavras",
            "audiovisual_identity": "Timing cômico em 3 atos e cortes secos",
            "visual_approval_status": "PENDING_HUMAN_APPROVAL",
        },
    },
    4: {
        "brand_name": "Horizonte Cósmico",
        "editorial_category": "Ciência",
        "proposed_handle": "@horizontecosmico",
        "name_availability_status": "HANDLE_IN_USE_PUBLICLY",
        "availability_note": "Handle @horizontecosmico retornou HTTP 200 no YouTube (provavelmente em uso; confirmar variante no YouTube Studio).",
        "branding_config": {
            "logo_path": None, "logo_status": "PENDING_DESIGN",
            "avatar_path": None, "avatar_status": "PENDING_DESIGN",
            "banner_path": None, "banner_status": "PENDING_DESIGN",
            "color_palette": ["#060B1E", "#1D4ED8", "#38BDF8", "#F8FAFC"],
            "typography": "Space Grotesk / Inter",
            "thumbnail_style": "Astrofotografia limpa com pergunta contra-intuitiva",
            "audiovisual_identity": "Didática científica rigorosa com legendas de alta legibilidade",
            "visual_approval_status": "PENDING_HUMAN_APPROVAL",
        },
    },
    5: {
        "brand_name": "Modo Ascensão",
        "editorial_category": "Produtividade",
        "proposed_handle": "@modoascensao",
        "name_availability_status": "HANDLE_IN_USE_PUBLICLY",
        "availability_note": "Handle @modoascensao retornou HTTP 200 no YouTube (provavelmente em uso; confirmar variante no YouTube Studio).",
        "branding_config": {
            "logo_path": None, "logo_status": "PENDING_DESIGN",
            "avatar_path": None, "avatar_status": "PENDING_DESIGN",
            "banner_path": None, "banner_status": "PENDING_DESIGN",
            "color_palette": ["#111827", "#374151", "#10B981", "#F9FAFB"],
            "typography": "Inter Bold / JetBrains Mono",
            "thumbnail_style": "Minimalista com palavra-chave e contraste limpo",
            "audiovisual_identity": "Objetivo, prático e acionável em <60s",
            "visual_approval_status": "PENDING_HUMAN_APPROVAL",
        },
    },
}

FAKE_MARKERS = ("fake", "test", "dummy", "placeholder", "example", "simulado", "uc_000")


class BrandRegistryService:
    """Gerencia marcas públicas, categorias editoriais, canais reais do YouTube e prontidão OAuth."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else (BASE_DIR / "database" / "shorts_central.db")
        self._ensure_table_and_seed()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table_and_seed(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_brands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL UNIQUE,
                    brand_name TEXT NOT NULL,
                    editorial_category TEXT NOT NULL,
                    legacy_channel_name TEXT NOT NULL,
                    youtube_channel_id TEXT,
                    youtube_handle TEXT,
                    youtube_url TEXT,
                    name_availability_status TEXT NOT NULL DEFAULT 'AVAILABILITY_UNVERIFIED',
                    channel_status TEXT NOT NULL DEFAULT 'CHANNEL_NOT_CREATED',
                    oauth_status TEXT NOT NULL DEFAULT 'OAUTH_DISCONNECTED',
                    branding_config_json TEXT DEFAULT '{}',
                    editorial_identity_json TEXT DEFAULT '{}',
                    pending_actions_json TEXT DEFAULT '[]',
                    next_step TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            for ch_id, prop in DEFAULT_BRAND_PROPOSALS.items():
                exists = conn.execute("SELECT 1 FROM channel_brands WHERE channel_id = ?", (ch_id,)).fetchone()
                if not exists:
                    ident = CHANNEL_IDENTITIES.get(ch_id, {})
                    pending = [
                        f"Confirmar nome/handle disponível no YouTube Studio (candidato: {prop['proposed_handle']})",
                        "Criar canal manualmente no YouTube e registrar ID real (UC...)",
                        "Conectar OAuth 2.0 real do canal",
                        "Aprovar identidade visual (avatar/banner/logo)",
                    ]
                    conn.execute(
                        """
                        INSERT INTO channel_brands (
                            channel_id, brand_name, editorial_category, legacy_channel_name,
                            youtube_channel_id, youtube_handle, youtube_url,
                            name_availability_status, channel_status, oauth_status,
                            branding_config_json, editorial_identity_json, pending_actions_json, next_step
                        ) VALUES (?, ?, ?, ?, NULL, NULL, NULL, ?, 'CHANNEL_NOT_CREATED', 'OAUTH_DISCONNECTED', ?, ?, ?, ?)
                        """,
                        (
                            ch_id,
                            prop["brand_name"],
                            prop["editorial_category"],
                            ident.get("name", f"Canal {ch_id}"),
                            prop["name_availability_status"],
                            json.dumps(prop["branding_config"], ensure_ascii=False),
                            json.dumps(ident, ensure_ascii=False),
                            json.dumps(pending, ensure_ascii=False),
                            "Criar canal manualmente no YouTube e registrar Channel ID real.",
                        ),
                    )
            conn.commit()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["branding_config"] = json.loads(d.pop("branding_config_json") or "{}")
        d["editorial_identity"] = json.loads(d.pop("editorial_identity_json") or "{}")
        d["pending_actions"] = json.loads(d.pop("pending_actions_json") or "[]")
        d["channel_exists_on_youtube"] = bool(d.get("youtube_channel_id"))
        return d

    def list_brands(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM channel_brands ORDER BY channel_id ASC").fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_brand(self, channel_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            r = conn.execute("SELECT * FROM channel_brands WHERE channel_id = ?", (int(channel_id),)).fetchone()
        return self._row_to_dict(r) if r else None

    def update_brand_identity(
        self,
        channel_id: int,
        brand_name: Optional[str] = None,
        branding_config: Optional[Dict[str, Any]] = None,
        editorial_identity: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cur = self.get_brand(channel_id)
        if not cur:
            raise ValueError(f"Marca para canal {channel_id} não encontrada.")
        new_name = (brand_name or cur["brand_name"]).strip()
        if not new_name:
            raise ValueError("brand_name não pode ser vazio.")
        new_branding = dict(cur["branding_config"])
        if branding_config:
            new_branding.update(branding_config)
        new_editorial = dict(cur["editorial_identity"])
        if editorial_identity:
            new_editorial.update(editorial_identity)

        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE channel_brands
                SET brand_name = ?, branding_config_json = ?, editorial_identity_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE channel_id = ?
                """,
                (new_name, json.dumps(new_branding, ensure_ascii=False), json.dumps(new_editorial, ensure_ascii=False), int(channel_id)),
            )
            conn.commit()
        return self.get_brand(channel_id)

    def register_youtube_channel(
        self,
        channel_id: int,
        youtube_channel_id: str,
        youtube_handle: str,
        youtube_url: str,
    ) -> Dict[str, Any]:
        """Registra dados reais de um canal criado manualmente, rejeitando IDs/URLs fictícios."""
        cur = self.get_brand(channel_id)
        if not cur:
            raise ValueError(f"Canal {channel_id} não encontrado.")

        yt_id = (youtube_channel_id or "").strip()
        handle = (youtube_handle or "").strip()
        url = (youtube_url or "").strip()

        combined_lower = f"{yt_id} {handle} {url}".lower()
        if any(m in combined_lower for m in FAKE_MARKERS):
            raise ValueError("ID, handle ou URL aparentam ser fictícios; informe apenas dados reais do YouTube.")
        if not re.match(r"^UC[A-Za-z0-9_-]{22}$", yt_id):
            raise ValueError("youtube_channel_id inválido: deve seguir padrão oficial 'UC' + 22 caracteres.")
        if not re.match(r"^@[A-Za-z0-9._-]{3,30}$", handle):
            raise ValueError("youtube_handle inválido: deve iniciar com '@' (3–30 caracteres).")
        if not (url.startswith("https://www.youtube.com/") or url.startswith("https://youtube.com/")):
            raise ValueError("youtube_url inválida: deve iniciar com https://www.youtube.com/.")

        pending = [p for p in cur["pending_actions"] if "Criar canal manualmente" not in p]
        if cur["oauth_status"] != "OAUTH_CONNECTED" and "Conectar OAuth 2.0 real do canal" not in pending:
            pending.append("Conectar OAuth 2.0 real do canal")

        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE channel_brands
                SET youtube_channel_id = ?,
                    youtube_handle = ?,
                    youtube_url = ?,
                    channel_status = 'CHANNEL_CREATED_UNVERIFIED',
                    pending_actions_json = ?,
                    next_step = 'Autenticar OAuth 2.0 real para verificar propriedade do canal.',
                    updated_at = CURRENT_TIMESTAMP
                WHERE channel_id = ?
                """,
                (yt_id, handle, url, json.dumps(pending, ensure_ascii=False), int(channel_id)),
            )
            # Sincroniza somente youtube_channel_id em channels preservando name/niche históricos
            try:
                conn.execute("UPDATE channels SET youtube_channel_id = ? WHERE id = ?", (yt_id, int(channel_id)))
            except sqlite3.OperationalError:
                pass
            conn.commit()
        return self.get_brand(channel_id)

    def verify_oauth_connection(self, channel_id: int) -> Dict[str, Any]:
        """Verifica se existe refresh_token OAuth real no banco sem simular conexão."""
        cur = self.get_brand(channel_id)
        if not cur:
            raise ValueError(f"Canal {channel_id} não encontrado.")
        has_real_token = False
        try:
            with self._get_conn() as conn:
                row = conn.execute("SELECT oauth_refresh_token FROM channels WHERE id = ?", (int(channel_id),)).fetchone()
                if row and row["oauth_refresh_token"]:
                    tok = str(row["oauth_refresh_token"]).strip()
                    if tok and not tok.startswith("SEU_REFRESH_TOKEN") and not any(m in tok.lower() for m in FAKE_MARKERS):
                        has_real_token = True
        except sqlite3.OperationalError:
            has_real_token = False

        oauth_status = "OAUTH_CONNECTED" if has_real_token else "OAUTH_DISCONNECTED"
        ch_status = cur["channel_status"]
        if has_real_token and cur.get("youtube_channel_id"):
            ch_status = "CHANNEL_VERIFIED"
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE channel_brands SET oauth_status = ?, channel_status = ?, updated_at = CURRENT_TIMESTAMP WHERE channel_id = ?",
                (oauth_status, ch_status, int(channel_id)),
            )
            conn.commit()
        return self.get_brand(channel_id)

    @staticmethod
    def check_handle_availability(handle: str, timeout_sec: int = 8) -> Dict[str, Any]:
        """Consulta pública conservadora; nunca declara disponibilidade sem YouTube Studio."""
        h = (handle or "").strip()
        if not h.startswith("@"):
            h = "@" + h
        url = f"https://www.youtube.com/{h}"
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=timeout_sec) as resp:
                if resp.status == 200:
                    return {"handle": h, "status": "HANDLE_IN_USE_PUBLICLY", "http_status": 200}
            return {"handle": h, "status": "AVAILABILITY_UNVERIFIED", "http_status": None}
        except HTTPError as e:
            if e.code == 404:
                return {"handle": h, "status": "AVAILABILITY_UNVERIFIED", "http_status": 404, "note": "HTTP 404 público; confirmar disponibilidade no YouTube Studio."}
            return {"handle": h, "status": "AVAILABILITY_UNVERIFIED", "http_status": e.code}
        except Exception as e:
            return {"handle": h, "status": "AVAILABILITY_UNVERIFIED", "error": str(e)}

    def prepare_publish_metadata(self, package_id: int) -> Dict[str, Any]:
        """Prepara metadados de publicação e aplica bloqueios reais de canal, OAuth e aprovação humana."""
        eng = EditorialProductionEngine(db_path=self.db_path)
        pkg = eng.get_package(package_id)
        if not pkg:
            raise ValueError(f"Pacote {package_id} não encontrado.")
        ch_id = int(pkg["channel_id"])
        brand = self.get_brand(ch_id)
        content = pkg["package"]
        script = content.get("script") or {}
        attrs = content.get("production_checklist", {}).get("required_attributions") or []

        blockers: List[str] = []
        if pkg["status"] != "APPROVED_FOR_PRODUCTION":
            blockers.append(f"Pacote #{package_id} em estado '{pkg['status']}' (exige APPROVED_FOR_PRODUCTION).")
        if not brand or not brand.get("youtube_channel_id"):
            blockers.append("Canal real do YouTube ainda não criado/registrado.")
        elif brand.get("channel_status") not in ("CHANNEL_VERIFIED", "READY_FOR_UPLOAD"):
            blockers.append(f"Canal em estado '{brand.get('channel_status')}' (não verificado).")
        if not brand or brand.get("oauth_status") != "OAUTH_CONNECTED":
            blockers.append("OAuth do canal desconectado (OAUTH_DISCONNECTED).")

        desc_lines = [
            script.get("hook") or "",
            "",
            f"Marca: {brand['brand_name'] if brand else pkg['channel_name']} | Categoria: {brand['editorial_category'] if brand else pkg['niche']}",
        ]
        if attrs:
            desc_lines.append("")
            desc_lines.append("Créditos / Atribuições:")
            desc_lines.extend(f"- {a}" for a in attrs)

        return {
            "package_id": package_id,
            "channel_id": ch_id,
            "brand_name": brand["brand_name"] if brand else pkg["channel_name"],
            "editorial_category": brand["editorial_category"] if brand else pkg["niche"],
            "youtube_channel_id": brand.get("youtube_channel_id") if brand else None,
            "oauth_status": brand.get("oauth_status") if brand else "OAUTH_DISCONNECTED",
            "ready_to_upload": len(blockers) == 0,
            "blockers": blockers,
            "metadata": {
                "title": f"{pkg['theme'][:90]} #Shorts",
                "description": "\n".join(desc_lines).strip(),
                "tags": ["shorts", brand["editorial_category"].lower() if brand else pkg["niche"], brand["brand_name"] if brand else ""],
                "privacy_status": "private",
            },
        }
