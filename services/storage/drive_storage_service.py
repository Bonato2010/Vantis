"""
VANTIS — Serviço Central de Armazenamento Remoto Drive-First (Fase 19)
Google Drive como fonte única de verdade para ativos de mídia, manifestos,
memória editorial, snapshots SQLite, cache temporário e lease de concorrência.
"""

import hashlib
import io
import json
import os
import shutil
import socket
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.gdrive_manager import GDriveManager

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VANTIS_DRIVE_ROOT_ID = "1KJp4_EpGIAdx1DpwTJ_8WyKDNbtgG_ZP"
VANTIS_CONTROL_FOLDER_ID = "1rNbqXtnpBeo_1-GiR_vy-MW3yvybnNUH"

STORAGE_STATES = (
    "REMOTE_AVAILABLE",
    "TEMPORARILY_CACHED",
    "PROCESSING",
    "REMOTE_VERIFIED",
    "REMOTE_MISSING",
    "INTEGRITY_ERROR",
    "DOWNLOAD_FAILED",
)

VANTIS_DATA_SUBFOLDERS = [
    "media",
    "media/benchmark_250",
    "media/benchmark_250/channel_1",
    "media/benchmark_250/channel_2",
    "media/benchmark_250/channel_3",
    "media/benchmark_250/channel_4",
    "media/benchmark_250/channel_5",
    "media/benchmark_500",
    "media/future_research",
    "audio",
    "transcripts",
    "metadata",
    "manifests",
    "editorial_features",
    "editorial_memory",
    "editorial_memory/channel_1",
    "editorial_memory/channel_2",
    "editorial_memory/channel_3",
    "editorial_memory/channel_4",
    "editorial_memory/channel_5",
    "checkpoints",
    "databases",
    "analytics",
    "reports",
    "backups",
]


def compute_hashes(file_path: Path) -> Dict[str, Any]:
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    size = 0
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
            md5.update(chunk)
            size += len(chunk)
    return {"sha256": sha.hexdigest(), "md5": md5.hexdigest(), "size_bytes": size}


class DriveStorageService:
    """Camada de armazenamento remoto Drive-first com cache temporário e controle de concorrência."""

    def __init__(
        self,
        gdrive_manager: Optional[GDriveManager] = None,
        root_folder_id: str = VANTIS_DRIVE_ROOT_ID,
        cache_dir: Optional[Path] = None,
        max_cache_mb: float = 512.0,
        cache_ttl_sec: int = 3600,
        folder_map_path: Optional[Path] = None,
    ):
        self.mgr = gdrive_manager or GDriveManager()
        self.root_folder_id = root_folder_id
        self.cache_dir = Path(cache_dir) if cache_dir else (BASE_DIR / "workspace" / "cache" / "remote_tmp")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_mb = float(max_cache_mb)
        self.cache_ttl_sec = int(cache_ttl_sec)
        self.folder_map_path = Path(folder_map_path) if folder_map_path else (BASE_DIR / "config" / "vantis_drive_data_folders.json")
        self.folder_map_path.parent.mkdir(parents=True, exist_ok=True)
        self.folder_map: Dict[str, str] = self._load_folder_map()

    def _load_folder_map(self) -> Dict[str, str]:
        if self.folder_map_path.exists():
            try:
                return json.loads(self.folder_map_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_folder_map(self):
        self.folder_map_path.write_text(json.dumps(self.folder_map, indent=2, ensure_ascii=False), encoding="utf-8")

    def _get_service(self):
        return self.mgr.get_service()

    def _with_retry(self, fn: Callable[[], Any], max_retries: int = 4, base_delay: float = 1.5) -> Any:
        last_err: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                return fn()
            except Exception as e:
                last_err = e
                msg = str(e)
                retryable = any(code in msg for code in ("429", "500", "502", "503", "504", "timed out", "ConnectionReset", "10054"))
                if not retryable or attempt >= max_retries:
                    raise
                time.sleep(base_delay * (2 ** attempt))
        raise last_err  # pragma: no cover

    def _get_or_create_folder(self, name: str, parent_id: str) -> str:
        svc = self._get_service()
        safe_name = name.replace("'", "\\'")
        q = f"name = '{safe_name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = self._with_retry(lambda: svc.files().list(q=q, fields="files(id,name)", pageSize=5).execute())
        files = res.get("files", [])
        if files:
            return files[0]["id"]
        meta = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        created = self._with_retry(lambda: svc.files().create(body=meta, fields="id").execute())
        return created["id"]

    def ensure_structure(self) -> Dict[str, str]:
        """Cria/descobre de forma idempotente a hierarquia VANTIS_DATA no Google Drive."""
        data_root_id = self.folder_map.get("VANTIS_DATA")
        if not data_root_id:
            data_root_id = self._get_or_create_folder("VANTIS_DATA", self.root_folder_id)
            self.folder_map["VANTIS_DATA"] = data_root_id

        for rel_path in VANTIS_DATA_SUBFOLDERS:
            key = f"VANTIS_DATA/{rel_path}"
            if key in self.folder_map:
                continue
            parts = rel_path.split("/")
            parent_key = "VANTIS_DATA" if len(parts) == 1 else f"VANTIS_DATA/{'/'.join(parts[:-1])}"
            parent_id = self.folder_map[parent_key]
            self.folder_map[key] = self._get_or_create_folder(parts[-1], parent_id)

        self._save_folder_map()
        return self.folder_map

    def get_folder_id(self, folder_key: str) -> str:
        if folder_key not in self.folder_map:
            self.ensure_structure()
        if folder_key not in self.folder_map:
            raise KeyError(f"Pasta Drive desconhecida: {folder_key}")
        return self.folder_map[folder_key]

    def find_remote_file(self, folder_key: str, filename: str) -> Optional[Dict[str, Any]]:
        svc = self._get_service()
        parent_id = self.get_folder_id(folder_key)
        safe_name = filename.replace("'", "\\'")
        q = f"name = '{safe_name}' and '{parent_id}' in parents and trashed = false"
        res = self._with_retry(
            lambda: svc.files().list(
                q=q,
                fields="files(id,name,size,md5Checksum,appProperties,modifiedTime)",
                pageSize=5,
            ).execute()
        )
        files = res.get("files", [])
        return files[0] if files else None

    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        svc = self._get_service()
        try:
            return self._with_retry(
                lambda: svc.files().get(
                    fileId=file_id,
                    fields="id,name,size,md5Checksum,appProperties,parents,trashed,modifiedTime",
                ).execute()
            )
        except Exception as e:
            if "404" in str(e) or "notFound" in str(e):
                return None
            raise

    def upload_file_resumable(
        self,
        local_path: Path,
        folder_key: str,
        remote_name: Optional[str] = None,
        logical_id: Optional[str] = None,
        mimetype: str = "application/octet-stream",
        overwrite_if_changed: bool = False,
    ) -> Dict[str, Any]:
        """Upload resumível com deduplicação por hash, proteção contra sobrescrita e backoff."""
        from googleapiclient.http import MediaFileUpload

        local_path = Path(local_path)
        if not local_path.is_file():
            return {"success": False, "storage_state": "REMOTE_MISSING", "error": f"Arquivo local ausente: {local_path}"}

        hashes = compute_hashes(local_path)
        name = remote_name or local_path.name
        parent_id = self.get_folder_id(folder_key)

        existing = self.find_remote_file(folder_key, name)
        if existing:
            rem_md5 = existing.get("md5Checksum")
            rem_size = int(existing.get("size") or 0)
            if rem_md5 == hashes["md5"] and rem_size == hashes["size_bytes"]:
                return {
                    "success": True,
                    "status": "REUSED_EXISTING",
                    "storage_state": "REMOTE_VERIFIED",
                    "drive_file_id": existing["id"],
                    "remote_name": name,
                    "folder_key": folder_key,
                    **hashes,
                }
            if not overwrite_if_changed:
                return {
                    "success": False,
                    "status": "CONFLICT_HASH_MISMATCH",
                    "storage_state": "INTEGRITY_ERROR",
                    "drive_file_id": existing["id"],
                    "remote_name": name,
                    "remote_md5": rem_md5,
                    "local_md5": hashes["md5"],
                    "error": "Arquivo remoto existe com hash diferente; sobrescrita bloqueada.",
                }

        svc = self._get_service()
        media = MediaFileUpload(str(local_path), mimetype=mimetype, chunksize=4 * 1024 * 1024, resumable=True)
        app_props = {"sha256": hashes["sha256"]}
        if logical_id:
            app_props["logical_id"] = str(logical_id)

        if existing and overwrite_if_changed:
            request = svc.files().update(
                fileId=existing["id"],
                body={"appProperties": app_props},
                media_body=media,
                fields="id,name,size,md5Checksum,appProperties",
            )
        else:
            request = svc.files().create(
                body={"name": name, "parents": [parent_id], "appProperties": app_props},
                media_body=media,
                fields="id,name,size,md5Checksum,appProperties",
            )

        response = None
        retries = 0
        try:
            while response is None:
                try:
                    status, response = request.next_chunk()
                except Exception as e:
                    retries += 1
                    if retries > 4:
                        return {
                            "success": False,
                            "status": "UPLOAD_FAILED",
                            "storage_state": "REMOTE_MISSING",
                            "error": str(e),
                        }
                    time.sleep(1.5 * (2 ** (retries - 1)))
        finally:
            fd = getattr(media, "_fd", None)
            if fd is not None and not fd.closed:
                fd.close()

        rem_md5 = response.get("md5Checksum")
        rem_size = int(response.get("size") or 0)
        if rem_md5 != hashes["md5"] or rem_size != hashes["size_bytes"]:
            return {
                "success": False,
                "status": "POST_UPLOAD_INTEGRITY_MISMATCH",
                "storage_state": "INTEGRITY_ERROR",
                "drive_file_id": response.get("id"),
                "remote_md5": rem_md5,
                "local_md5": hashes["md5"],
            }

        return {
            "success": True,
            "status": "UPLOADED_VERIFIED",
            "storage_state": "REMOTE_VERIFIED",
            "drive_file_id": response["id"],
            "remote_name": name,
            "folder_key": folder_key,
            **hashes,
        }

    def upload_json(self, folder_key: str, filename: str, payload: Any, overwrite: bool = True) -> Dict[str, Any]:
        tmp = self.cache_dir / f"_tmp_upload_{filename}"
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            return self.upload_file_resumable(
                tmp, folder_key, remote_name=filename, mimetype="application/json", overwrite_if_changed=overwrite
            )
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except PermissionError:
                pass

    def download_json(self, folder_key: str, filename: str) -> Optional[Any]:
        meta = self.find_remote_file(folder_key, filename)
        if not meta:
            return None
        svc = self._get_service()
        from googleapiclient.http import MediaIoBaseDownload

        buf = io.BytesIO()
        req = svc.files().get_media(fileId=meta["id"])
        downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = self._with_retry(downloader.next_chunk)
        return json.loads(buf.getvalue().decode("utf-8"))

    # --- CACHE TEMPORÁRIO ON-DEMAND ---

    def _enforce_cache_limits(self):
        now = time.time()
        files = [p for p in self.cache_dir.iterdir() if p.is_file() and not p.name.startswith("_tmp_")]
        for p in list(files):
            if (now - p.stat().st_mtime) > self.cache_ttl_sec:
                p.unlink(missing_ok=True)
                files.remove(p)
        total_mb = sum(p.stat().st_size for p in files) / (1024 * 1024)
        if total_mb > self.max_cache_mb:
            files.sort(key=lambda x: x.stat().st_mtime)
            for p in files:
                p.unlink(missing_ok=True)
                total_mb = sum(f.stat().st_size for f in self.cache_dir.iterdir() if f.is_file()) / (1024 * 1024)
                if total_mb <= self.max_cache_mb * 0.8:
                    break

    def fetch_to_temp_cache(
        self,
        drive_file_id: str,
        filename: str,
        expected_sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Recupera vídeo remoto sob demanda para o cache temporário e valida SHA256."""
        self._enforce_cache_limits()
        dest = self.cache_dir / filename
        if dest.is_file() and expected_sha256:
            h = compute_hashes(dest)
            if h["sha256"] == expected_sha256:
                return {"success": True, "storage_state": "TEMPORARILY_CACHED", "local_path": str(dest), **h}

        svc = self._get_service()
        from googleapiclient.http import MediaIoBaseDownload

        try:
            req = svc.files().get_media(fileId=drive_file_id)
            with open(dest, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, req)
                done = False
                while not done:
                    _, done = self._with_retry(downloader.next_chunk)
        except Exception as e:
            dest.unlink(missing_ok=True)
            return {"success": False, "storage_state": "DOWNLOAD_FAILED", "error": str(e)}

        h = compute_hashes(dest)
        if expected_sha256 and h["sha256"] != expected_sha256:
            dest.unlink(missing_ok=True)
            return {
                "success": False,
                "storage_state": "INTEGRITY_ERROR",
                "error": f"SHA256 divergente: esperado={expected_sha256}, obtido={h['sha256']}",
            }
        return {"success": True, "storage_state": "TEMPORARILY_CACHED", "local_path": str(dest), **h}

    def cleanup_temp_cache(self, filename: Optional[str] = None) -> int:
        removed = 0
        if filename:
            p = self.cache_dir / filename
            if p.is_file():
                p.unlink(missing_ok=True)
                removed = 1
            return removed
        for p in self.cache_dir.iterdir():
            if p.is_file():
                p.unlink(missing_ok=True)
                removed += 1
        return removed

    # --- LEASE DE CONCORRÊNCIA E SNAPSHOT DE BANCO ---

    def acquire_device_lease(
        self,
        device_id: Optional[str] = None,
        operation: str = "general",
        ttl_seconds: int = 900,
    ) -> Dict[str, Any]:
        dev = device_id or socket.gethostname()
        now = time.time()
        current = self.download_json("VANTIS_DATA/checkpoints", "device_lease.json")
        abandoned = False
        if current and current.get("status") == "ACTIVE":
            if current.get("device_id") != dev and float(current.get("expires_at", 0)) > now:
                return {
                    "acquired": False,
                    "reason": "LEASE_CONFLICT_ACTIVE_DEVICE",
                    "active_device": current.get("device_id"),
                    "expires_at": current.get("expires_at"),
                }
            if float(current.get("expires_at", 0)) <= now and current.get("device_id") != dev:
                abandoned = True

        lease = {
            "device_id": dev,
            "operation": operation,
            "status": "ACTIVE",
            "acquired_at": now,
            "expires_at": now + ttl_seconds,
            "abandoned_previous_session": abandoned,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        up = self.upload_json("VANTIS_DATA/checkpoints", "device_lease.json", lease, overwrite=True)
        return {"acquired": bool(up.get("success")), "lease": lease}

    def renew_device_lease(self, device_id: Optional[str] = None, ttl_seconds: int = 900) -> Dict[str, Any]:
        dev = device_id or socket.gethostname()
        current = self.download_json("VANTIS_DATA/checkpoints", "device_lease.json") or {}
        if current.get("status") == "ACTIVE" and current.get("device_id") != dev:
            return {"renewed": False, "reason": "LEASE_OWNED_BY_OTHER_DEVICE"}
        current["device_id"] = dev
        current["status"] = "ACTIVE"
        current["expires_at"] = time.time() + ttl_seconds
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        up = self.upload_json("VANTIS_DATA/checkpoints", "device_lease.json", current, overwrite=True)
        return {"renewed": bool(up.get("success")), "lease": current}

    def release_device_lease(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        dev = device_id or socket.gethostname()
        current = self.download_json("VANTIS_DATA/checkpoints", "device_lease.json") or {}
        if current.get("status") == "ACTIVE" and current.get("device_id") not in (None, dev):
            return {"released": False, "reason": "LEASE_OWNED_BY_OTHER_DEVICE"}
        current["status"] = "RELEASED"
        current["released_by"] = dev
        current["released_at"] = datetime.now(timezone.utc).isoformat()
        up = self.upload_json("VANTIS_DATA/checkpoints", "device_lease.json", current, overwrite=True)
        return {"released": bool(up.get("success"))}

    def upload_db_snapshot(self, db_path: Path, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Gera backup atômico do SQLite e envia snapshot versionado ao Drive."""
        db_path = Path(db_path)
        dev = device_id or socket.gethostname()
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snap_name = f"shorts_central_{ts}_{dev}.db"
        snap_tmp = self.cache_dir / f"_tmp_{snap_name}"
        try:
            src = sqlite3.connect(db_path)
            dst = sqlite3.connect(snap_tmp)
            with dst:
                src.backup(dst)
            src.close()
            dst.close()
            up = self.upload_file_resumable(
                snap_tmp, "VANTIS_DATA/databases", remote_name=snap_name, mimetype="application/x-sqlite3"
            )
            if up.get("success"):
                pointer = {
                    "snapshot_name": snap_name,
                    "drive_file_id": up["drive_file_id"],
                    "sha256": up["sha256"],
                    "md5": up["md5"],
                    "size_bytes": up["size_bytes"],
                    "device_id": dev,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                self.upload_json("VANTIS_DATA/databases", "latest_snapshot.json", pointer, overwrite=True)
                return {"success": True, **pointer}
            return up
        finally:
            snap_tmp.unlink(missing_ok=True)

    def restore_db_from_drive(self, target_db_path: Path) -> Dict[str, Any]:
        pointer = self.download_json("VANTIS_DATA/databases", "latest_snapshot.json")
        if not pointer or not pointer.get("drive_file_id"):
            return {"success": False, "error": "Nenhum snapshot encontrado em VANTIS_DATA/databases."}
        res = self.fetch_to_temp_cache(
            pointer["drive_file_id"], pointer["snapshot_name"], expected_sha256=pointer.get("sha256")
        )
        if not res.get("success"):
            return res
        target_db_path = Path(target_db_path)
        target_db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(res["local_path"], target_db_path)
        self.cleanup_temp_cache(pointer["snapshot_name"])
        return {"success": True, "restored_to": str(target_db_path), "sha256": pointer.get("sha256")}
