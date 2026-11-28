"""
VANTIS — Motor de Inteligência de Assets (Fase 24)
Interpreta cenas, mantém biblioteca organizada com hash/dimensões/licença,
verifica integridade técnica e direitos, e associa ativos às cenas sem inventar mídia.
"""
import hashlib
import json
import re
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent.parent.parent

VERIFIED_LICENSE_STATUSES = (
    "VERIFIED_CC0",
    "VERIFIED_PUBLIC_DOMAIN",
    "VERIFIED_CC_BY",
    "VERIFIED_OWN_LIBRARY",
    "VERIFIED_ROYALTY_FREE",
)

FORBIDDEN_BENCHMARK_MARKERS = ("benchmark250", "benchmark_250", "workspace\\downloads", "workspace/downloads")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _probe_media_dimensions(path: Path) -> Tuple[str, int, int, float, bool]:
    """Usa ffprobe para inspecionar arquivo real sem confiar apenas na extensão."""
    ext = path.suffix.lower()
    if ext in (".png", ".jpg", ".jpeg", ".webp"):
        media_type = "image"
    elif ext in (".mp4", ".mov", ".mkv", ".webm"):
        media_type = "video"
    elif ext in (".mp3", ".wav", ".ogg", ".m4a"):
        media_type = "audio"
    else:
        return "unknown", 0, 0, 0.0, False

    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=20)
        if res.returncode != 0 or not res.stdout.strip():
            return media_type, 0, 0, 0.0, False
        data = json.loads(res.stdout)
        streams = data.get("streams") or []
        fmt = data.get("format") or {}
        dur = float(fmt.get("duration") or 0.0)
        w, h = 0, 0
        for st in streams:
            if st.get("codec_type") == "video":
                w = int(st.get("width") or 0)
                h = int(st.get("height") or 0)
                break
        valid = (media_type == "audio" and dur > 0.0) or (media_type in ("image", "video") and w > 0 and h > 0)
        return media_type, w, h, round(dur, 2), valid
    except Exception:
        return media_type, 0, 0, 0.0, False


def normalize_license_status(license_name: str, commercial_confirmed: bool = False) -> Tuple[str, bool]:
    """Classifica licença sem presumir uso comercial quando não confirmado."""
    raw = (license_name or "").strip().lower()
    if not raw or raw in ("unknown", "desconhecida", "none"):
        return "LICENSE_UNVERIFIED", False
    if "cc0" in raw or "public domain" in raw or "domínio público" in raw:
        return ("VERIFIED_CC0" if "cc0" in raw else "VERIFIED_PUBLIC_DOMAIN"), False
    if "cc-by" in raw or "cc by" in raw:
        if "nc" in raw or "nd" in raw:
            return "RESTRICTED", True
        return "VERIFIED_CC_BY", True
    if raw in ("own_library", "propria", "acervo_proprio"):
        return "VERIFIED_OWN_LIBRARY", False
    if "royalty" in raw and commercial_confirmed:
        return "VERIFIED_ROYALTY_FREE", False
    return "LICENSE_UNVERIFIED", False


class AssetIntelligenceEngine:
    """Motor de interpretação de cenas, biblioteca de ativos, licenciamento e associação segura."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else (BASE_DIR / "database" / "shorts_central.db")
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS production_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_uid TEXT NOT NULL UNIQUE,
                    file_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    width INTEGER DEFAULT 0,
                    height INTEGER DEFAULT 0,
                    duration_sec REAL DEFAULT 0.0,
                    file_size_bytes INTEGER DEFAULT 0,
                    sha256 TEXT NOT NULL UNIQUE,
                    origin TEXT NOT NULL,
                    source_url TEXT,
                    license_name TEXT NOT NULL DEFAULT 'UNKNOWN',
                    license_status TEXT NOT NULL DEFAULT 'LICENSE_UNVERIFIED',
                    attribution_required INTEGER DEFAULT 0,
                    authorized_channels_json TEXT DEFAULT '[1,2,3,4,5]',
                    validation_status TEXT NOT NULL DEFAULT 'PENDING',
                    validation_notes TEXT,
                    tags_json TEXT DEFAULT '[]',
                    asset_name TEXT,
                    author TEXT,
                    attribution_text TEXT,
                    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(production_assets)").fetchall()}
            for col_name, col_def in (
                ("asset_name", "TEXT"),
                ("author", "TEXT"),
                ("attribution_text", "TEXT"),
                ("acquired_at", "TIMESTAMP"),
            ):
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE production_assets ADD COLUMN {col_name} {col_def}")
            conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["authorized_channels"] = json.loads(d.pop("authorized_channels_json") or "[]")
        d["tags"] = json.loads(d.pop("tags_json") or "[]")
        d["attribution_required"] = bool(d.get("attribution_required"))
        return d

    def register_asset(
        self,
        file_path: str,
        origin: str,
        license_name: str,
        tags: Optional[List[str]] = None,
        authorized_channels: Optional[List[int]] = None,
        source_url: Optional[str] = None,
        commercial_confirmed: bool = False,
        asset_name: Optional[str] = None,
        author: Optional[str] = None,
        attribution_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verifica integridade física, hash (deduplicação), dimensões e licença antes de registrar."""
        p = Path(file_path)
        resolved = str(p.resolve())
        lower_path = resolved.lower()
        if any(m in lower_path for m in FORBIDDEN_BENCHMARK_MARKERS):
            raise ValueError("Proibido registrar vídeos de benchmark de terceiros como ativo de produção.")
        if not p.is_file() or p.stat().st_size <= 0:
            raise ValueError(f"Arquivo de mídia inexistente ou vazio: {file_path}")

        sha256 = _sha256_file(p)
        with self._get_conn() as conn:
            existing = conn.execute("SELECT * FROM production_assets WHERE sha256 = ?", (sha256,)).fetchone()
            if existing:
                d = self._row_to_dict(existing)
                d["deduplicated"] = True
                return d

        media_type, width, height, dur_sec, probe_ok = _probe_media_dimensions(p)
        lic_status, attr_req = normalize_license_status(license_name, commercial_confirmed=commercial_confirmed)

        notes: List[str] = []
        if not probe_ok:
            val_status = "CORRUPT"
            notes.append("Falha na verificação ffprobe/dimensões.")
        elif media_type in ("image", "video") and (width < 360 or height < 360):
            val_status = "INCOMPATIBLE"
            notes.append(f"Resolução muito baixa ({width}x{height}).")
        else:
            val_status = "VALID"
            notes.append(f"Integridade verificada ({width}x{height}, {dur_sec}s).")

        if lic_status not in VERIFIED_LICENSE_STATUSES:
            notes.append(f"Licença '{lic_status}' impede uso automático em produção.")

        uid = f"ast_{uuid.uuid4().hex[:10]}"
        ch_list = authorized_channels or [1, 2, 3, 4, 5]
        tag_list = [str(t).strip().lower() for t in (tags or []) if str(t).strip()]

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO production_assets (
                    asset_uid, file_path, media_type, width, height, duration_sec,
                    file_size_bytes, sha256, origin, source_url, license_name,
                    license_status, attribution_required, authorized_channels_json,
                    validation_status, validation_notes, tags_json,
                    asset_name, author, attribution_text, acquired_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    uid, resolved, media_type, width, height, dur_sec,
                    p.stat().st_size, sha256, origin, source_url, license_name,
                    lic_status, 1 if attr_req else 0, json.dumps(ch_list),
                    val_status, " ".join(notes), json.dumps(tag_list, ensure_ascii=False),
                    asset_name or p.name, author or "", attribution_text or "",
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM production_assets WHERE id = ?", (cur.lastrowid,)).fetchone()
        out = self._row_to_dict(row)
        out["deduplicated"] = False
        return out

    def list_assets(
        self,
        channel_id: Optional[int] = None,
        only_valid: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM production_assets ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        out = [self._row_to_dict(r) for r in rows]
        if channel_id is not None:
            out = [a for a in out if int(channel_id) in (a.get("authorized_channels") or [])]
        if only_valid:
            out = [
                a for a in out
                if a.get("validation_status") == "VALID"
                and a.get("license_status") in VERIFIED_LICENSE_STATUSES
                and Path(a["file_path"]).is_file()
            ]
        return out

    def get_asset(self, asset_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            r = conn.execute("SELECT * FROM production_assets WHERE id = ?", (asset_id,)).fetchone()
        return self._row_to_dict(r) if r else None

    @staticmethod
    def analyze_scene_requirements(scene: Dict[str, Any], channel_id: int, theme: str) -> Dict[str, Any]:
        """Interpreta a descrição da cena e gera especificação estruturada de mídia."""
        desc = f"{scene.get('stage', '')} {scene.get('visual_description', '')} {theme}".lower()
        tokens = [t for t in re.findall(r"[a-zà-ú0-9]{4,}", desc) if t not in {"sobre", "para", "como", "cena", "estilo", "mais", "entre", "com"}]
        wants_video = any(k in desc for k in ("lance", "movimento", "corrida", "ação", "reunião", "corte", "dinâmico"))
        return {
            "preferred_media_type": "video_or_image" if wants_video else "image_or_video",
            "framing": "vertical_9_16_or_adaptable",
            "keywords": list(dict.fromkeys(tokens))[:8],
            "channel_id": int(channel_id),
            "origin_requirement": "verifiable_non_benchmark_source",
            "license_requirement": list(VERIFIED_LICENSE_STATUSES),
        }

    def match_assets_for_scenes(
        self,
        channel_id: int,
        theme: str,
        scenes: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Associa apenas ativos válidos, licenciados e semanticamente compatíveis; caso contrário mantém ASSET_NEEDED."""
        candidates = self.list_assets(channel_id=channel_id, only_valid=True, limit=200)
        incompatibilities: List[Dict[str, Any]] = []
        updated_scenes: List[Dict[str, Any]] = []
        used_asset_ids = set()

        for sc in scenes:
            sc_copy = dict(sc)
            reqs = self.analyze_scene_requirements(sc_copy, channel_id, theme)
            sc_copy["media_requirements"] = reqs

            # Preserva ativo já explicitamente atribuído se continuar válido e licenciado
            existing_id = sc_copy.get("asset_id")
            if existing_id:
                ast = self.get_asset(int(existing_id))
                if ast and ast["validation_status"] == "VALID" and ast["license_status"] in VERIFIED_LICENSE_STATUSES and Path(ast["file_path"]).is_file():
                    sc_copy["asset_path"] = ast["file_path"]
                    sc_copy["license_status"] = ast["license_status"]
                    sc_copy["media_asset_status"] = "ASSET_READY"
                    updated_scenes.append(sc_copy)
                    used_asset_ids.add(ast["id"])
                    continue
                else:
                    incompatibilities.append({"scene_index": sc_copy.get("scene_index"), "reason": "Ativo anterior inválido ou sem licença verificada."})

            kw_set = set(reqs["keywords"])
            scored: List[Tuple[int, Dict[str, Any], List[str]]] = []
            for ast in candidates:
                if ast["id"] in used_asset_ids:
                    continue
                ast_tags = set(ast.get("tags") or [])
                matched_kws = sorted(kw_set & ast_tags)
                if matched_kws:
                    scored.append((len(matched_kws), ast, matched_kws))
            scored.sort(key=lambda x: x[0], reverse=True)

            if scored:
                _, best_asset, matched_kws = scored[0]
                sc_copy["asset_id"] = best_asset["id"]
                sc_copy["asset_path"] = best_asset["file_path"]
                sc_copy["license_status"] = best_asset["license_status"]
                sc_copy["attribution_text"] = best_asset.get("attribution_text") or ""
                sc_copy["media_asset_status"] = "ASSET_READY"
                sc_copy["match_reason"] = f"Correspondência temática por palavras-chave {matched_kws} e licença {best_asset['license_status']}."
                sc_copy["alternatives"] = [
                    {"asset_id": alt["id"], "name": alt.get("asset_name") or Path(alt["file_path"]).name, "license_status": alt["license_status"]}
                    for _, alt, _ in scored[1:4]
                ]
                used_asset_ids.add(best_asset["id"])
            else:
                sc_copy.pop("asset_path", None)
                sc_copy.pop("asset_id", None)
                sc_copy["media_asset_status"] = "ASSET_NEEDED"
                sc_copy["license_status"] = "PENDING"
                sc_copy["match_reason"] = "Nenhuma correspondência temática verificada."
                sc_copy["alternatives"] = []
                incompatibilities.append({
                    "scene_index": sc_copy.get("scene_index"),
                    "reason": "Nenhum ativo local com licença verificada e correspondência temática encontrado; mantido ASSET_NEEDED.",
                })

            updated_scenes.append(sc_copy)

        return updated_scenes, incompatibilities

    @staticmethod
    def search_wikimedia_commons(query: str, limit: int = 8, timeout_sec: int = 12) -> Dict[str, Any]:
        """Consulta pública gratuita da API Wikimedia Commons verificando licença, autor e atribuição."""
        url = (
            "https://commons.wikimedia.org/w/api.php?action=query&format=json"
            "&generator=search&gsrnamespace=6&gsrlimit="
            f"{int(limit)}&gsrsearch={quote(query)}"
            "&prop=imageinfo&iiprop=url|extmetadata|mime|size&iiurlwidth=1920"
        )
        try:
            req = Request(url, headers={"User-Agent": "VantisEditorialBot/1.0 (zero-cost educational)"})
            with urlopen(req, timeout=timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            pages = (data.get("query") or {}).get("pages") or {}
            results = []
            for _, pg in pages.items():
                info = (pg.get("imageinfo") or [{}])[0]
                ext = info.get("extmetadata") or {}
                lic_short = (ext.get("LicenseShortName") or {}).get("value") or "UNKNOWN"
                raw_artist = (ext.get("Artist") or {}).get("value") or ""
                author = re.sub(r"<[^>]+>", "", raw_artist).strip() or "Autor não informado"
                lic_status, attr_req = normalize_license_status(lic_short, commercial_confirmed=True)
                mime = info.get("mime") or ""
                w = int(info.get("width") or 0)
                h = int(info.get("height") or 0)
                eligible = (
                    lic_status in VERIFIED_LICENSE_STATUSES
                    and mime in ("image/jpeg", "image/png", "image/webp")
                    and w >= 600 and h >= 600
                )
                attr_text = f"{pg.get('title', '').replace('File:', '')} by {author} ({lic_short}) via Wikimedia Commons" if attr_req else ""
                results.append({
                    "title": pg.get("title"),
                    "url": info.get("url"),
                    "download_url": info.get("thumburl") or info.get("url"),
                    "mime": mime,
                    "width": w,
                    "height": h,
                    "author": author[:120],
                    "license_name": lic_short,
                    "license_status": lic_status,
                    "attribution_required": attr_req,
                    "attribution_text": attr_text[:240],
                    "eligible": eligible,
                })
            return {"success": True, "source": "wikimedia_commons", "query": query, "results": results}
        except Exception as e:
            return {"success": False, "source": "wikimedia_commons", "query": query, "error": str(e), "results": []}

    def acquire_wikimedia_asset(
        self,
        candidate: Dict[str, Any],
        channel_id: int,
        tags: Optional[List[str]] = None,
        download_dir: Optional[Path] = None,
        timeout_sec: int = 25,
    ) -> Dict[str, Any]:
        """Baixa seletivamente apenas candidato permitido, valida com ffprobe e registra na biblioteca."""
        lic_name = str(candidate.get("license_name") or "UNKNOWN")
        lic_status, _ = normalize_license_status(lic_name, commercial_confirmed=True)
        if lic_status not in VERIFIED_LICENSE_STATUSES:
            raise ValueError(f"Download bloqueado: licença '{lic_name}' ({lic_status}) não autorizada para produção.")

        mime = str(candidate.get("mime") or "")
        ext = ".png" if "png" in mime else (".webp" if "webp" in mime else ".jpg")
        dl_url = candidate.get("download_url") or candidate.get("url")
        if not dl_url:
            raise ValueError("Candidato sem URL de download.")

        out_dir = download_dir or (BASE_DIR / "workspace" / "assets" / "acquired")
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(candidate.get("title") or "wikimedia_asset").replace("File:", ""))[:60].strip("_")
        target_path = out_dir / f"ch{int(channel_id)}_{safe_title}{ext}"

        try:
            req = Request(dl_url, headers={"User-Agent": "VantisEditorialBot/1.0 (zero-cost educational)"})
            with urlopen(req, timeout=timeout_sec) as resp:
                data = resp.read()
            if not data or len(data) < 2048:
                raise ValueError("Download incompleto ou arquivo vazio.")
            target_path.write_bytes(data)
        except Exception as e:
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            raise ValueError(f"Falha no download de '{dl_url}': {e}")

        reg = self.register_asset(
            file_path=str(target_path),
            origin="wikimedia_commons",
            license_name=lic_name,
            tags=tags or [],
            authorized_channels=[int(channel_id)],
            source_url=candidate.get("url") or dl_url,
            commercial_confirmed=True,
            asset_name=str(candidate.get("title") or target_path.name).replace("File:", ""),
            author=candidate.get("author"),
            attribution_text=candidate.get("attribution_text"),
        )
        if reg.get("validation_status") != "VALID":
            target_path.unlink(missing_ok=True)
            raise ValueError(f"Arquivo baixado falhou na inspeção física: {reg.get('validation_notes')}")
        return reg
