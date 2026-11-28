"""
VANTIS — Suíte de Testes da Fase 19: Drive-First, Cache Temporário, Lease, Migração de Dispositivo e Calibração Editorial
Usa mocks/fixtures isolados em diretório temporário (zero alterações no Drive real ou vídeos reais).
"""

import hashlib
import io
import json
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.storage.drive_storage_service import DriveStorageService, STORAGE_STATES, compute_hashes


class FakeMediaRequest:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self._idx = 0

    def next_chunk(self):
        if self._idx < len(self._chunks):
            res = self._chunks[self._idx]
            self._idx += 1
            return res
        return (None, {"id": "fake_id"})


class FakeDriveService:
    """Simula Google Drive API v3 em memória com suporte a upload resumível, download e falhas transitórias."""

    def __init__(self, fail_once: bool = False):
        self.files_store = {}
        self.bytes_store = {}
        self._counter = 100
        self.fail_once = fail_once
        self._failed_already = False

    def files(self):
        return self

    def list(self, q="", fields="", pageSize=10):
        # Parse simples de name = '...' e '<parent>' in parents
        name_filter = None
        parent_filter = None
        if "name = '" in q:
            name_filter = q.split("name = '")[1].split("'")[0]
        if "' in parents" in q:
            parent_filter = q.split("' in parents")[0].split("'")[-1]

        matched = []
        for fid, meta in self.files_store.items():
            if name_filter and meta["name"] != name_filter:
                continue
            if parent_filter and parent_filter not in meta.get("parents", []):
                continue
            matched.append(meta)

        req = MagicMock()
        req.execute.return_value = {"files": matched[:pageSize]}
        return req

    def get(self, fileId, fields=""):
        req = MagicMock()
        if fileId not in self.files_store:
            req.execute.side_effect = Exception("404 notFound")
        else:
            req.execute.return_value = self.files_store[fileId]
        return req

    def create(self, body, media_body=None, fields=""):
        self._counter += 1
        fid = f"drv_{self._counter}"
        if media_body is None:
            meta = {"id": fid, **body}
            self.files_store[fid] = meta
            req = MagicMock()
            req.execute.return_value = meta
            return req

        raw = Path(media_body._filename).read_bytes()
        self.bytes_store[fid] = raw
        meta = {
            "id": fid,
            "name": body["name"],
            "parents": body.get("parents", []),
            "size": str(len(raw)),
            "md5Checksum": hashlib.md5(raw).hexdigest(),
            "appProperties": body.get("appProperties", {}),
        }
        self.files_store[fid] = meta

        class _ChunkReq:
            def __init__(self, outer, m):
                self.outer = outer
                self.m = m
                self.step = 0

            def next_chunk(self):
                if self.outer.fail_once and not self.outer._failed_already:
                    self.outer._failed_already = True
                    raise Exception("503 transient network error")
                if self.step == 0:
                    self.step = 1
                    return (MagicMock(progress=lambda: 0.5), None)
                return (None, self.m)

        return _ChunkReq(self, meta)

    def update(self, fileId, body=None, media_body=None, fields=""):
        raw = Path(media_body._filename).read_bytes()
        self.bytes_store[fileId] = raw
        meta = self.files_store[fileId]
        meta["size"] = str(len(raw))
        meta["md5Checksum"] = hashlib.md5(raw).hexdigest()
        meta["appProperties"] = (body or {}).get("appProperties", {})
        return FakeMediaRequest([(None, meta)])

    def get_media(self, fileId):
        req = MagicMock()
        req.fileId = fileId
        req.raw_bytes = self.bytes_store.get(fileId, b"")
        return req


class TestFase19DriveFirstAndCalibration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.fake_svc = FakeDriveService()
        self.mgr = MagicMock()
        self.mgr.get_service.return_value = self.fake_svc
        self.storage = DriveStorageService(
            gdrive_manager=self.mgr,
            root_folder_id="root_vantis",
            cache_dir=self.temp_path / "cache",
            max_cache_mb=1.0,
            cache_ttl_sec=60,
            folder_map_path=self.temp_path / "folders.json",
        )
        self.storage.ensure_structure()

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def _patch_downloader(self, monkey_data: bytes):
        # Patch MediaIoBaseDownload inside googleapiclient.http
        import googleapiclient.http as gh
        orig = gh.MediaIoBaseDownload

        class FakeDl:
            def __init__(self, fd, req):
                self.fd = fd
                self.data = getattr(req, "raw_bytes", monkey_data)
                self.done = False

            def next_chunk(self):
                self.fd.write(self.data)
                self.done = True
                return (None, True)

        gh.MediaIoBaseDownload = FakeDl
        return orig

    def test_01_resumable_upload_resume_dedup_and_conflict(self):
        """Testa upload resumível, retomada após falha 503, deduplicação por hash e bloqueio de conflito."""
        self.fake_svc.fail_once = True
        sample = self.temp_path / "vid_a.mp4"
        sample.write_bytes(b"video_bytes_123456")

        up1 = self.storage.upload_file_resumable(sample, "VANTIS_DATA/media/benchmark_250/channel_1", logical_id="vid_a")
        self.assertTrue(up1["success"])
        self.assertEqual(up1["status"], "UPLOADED_VERIFIED")
        self.assertEqual(up1["storage_state"], "REMOTE_VERIFIED")

        # Mesmo arquivo -> deduplicação sem re-upload
        up2 = self.storage.upload_file_resumable(sample, "VANTIS_DATA/media/benchmark_250/channel_1", logical_id="vid_a")
        self.assertTrue(up2["success"])
        self.assertEqual(up2["status"], "REUSED_EXISTING")

        # Mesmo nome com conteúdo diferente -> bloqueia sobrescrita silenciosa
        sample.write_bytes(b"DIFFERENT_BYTES_999")
        up3 = self.storage.upload_file_resumable(sample, "VANTIS_DATA/media/benchmark_250/channel_1", logical_id="vid_a")
        self.assertFalse(up3["success"])
        self.assertEqual(up3["status"], "CONFLICT_HASH_MISMATCH")
        self.assertEqual(up3["storage_state"], "INTEGRITY_ERROR")

    def test_02_temp_cache_fetch_integrity_and_cleanup(self):
        """Testa recuperação remota sob demanda, verificação SHA256, erro de integridade e limpeza segura."""
        sample = self.temp_path / "vid_b.mp4"
        sample.write_bytes(b"authentic_short_content")
        h = compute_hashes(sample)
        up = self.storage.upload_file_resumable(sample, "VANTIS_DATA/media/benchmark_250/channel_2", logical_id="vid_b")

        import googleapiclient.http as gh
        orig = self._patch_downloader(b"authentic_short_content")
        try:
            cached = self.storage.fetch_to_temp_cache(up["drive_file_id"], "vid_b.mp4", expected_sha256=h["sha256"])
            self.assertTrue(cached["success"])
            self.assertEqual(cached["storage_state"], "TEMPORARILY_CACHED")
            self.assertTrue(Path(cached["local_path"]).is_file())

            # Limpeza segura remove do cache sem apagar do Drive
            removed = self.storage.cleanup_temp_cache("vid_b.mp4")
            self.assertEqual(removed, 1)
            self.assertFalse(Path(cached["local_path"]).exists())
            self.assertIsNotNone(self.storage.get_file_metadata(up["drive_file_id"]))

            # Hash errado -> INTEGRITY_ERROR
            bad = self.storage.fetch_to_temp_cache(up["drive_file_id"], "vid_b.mp4", expected_sha256="0" * 64)
            self.assertFalse(bad["success"])
            self.assertEqual(bad["storage_state"], "INTEGRITY_ERROR")
        finally:
            gh.MediaIoBaseDownload = orig

    def test_03_auth_and_network_failure_handling(self):
        """Testa falha de autenticação e falha de rede sem falso sucesso."""
        bad_mgr = MagicMock()
        bad_mgr.get_service.side_effect = PermissionError("OAuth ausente")
        bad_storage = DriveStorageService(gdrive_manager=bad_mgr, cache_dir=self.temp_path / "c2", folder_map_path=self.temp_path / "f2.json")
        with self.assertRaises(PermissionError):
            bad_storage.ensure_structure()

        # Falha de download retorna DOWNLOAD_FAILED
        res = self.storage.fetch_to_temp_cache("missing_id", "x.mp4")
        self.assertFalse(res["success"])
        self.assertEqual(res["storage_state"], "DOWNLOAD_FAILED")

    def test_04_device_lease_conflict_and_expired_recovery(self):
        """Testa conflito entre dois dispositivos e recuperação de lease expirado."""
        import googleapiclient.http as gh
        orig = self._patch_downloader(b"")
        try:
            l1 = self.storage.acquire_device_lease(device_id="notebook_A", ttl_seconds=600)
            self.assertTrue(l1["acquired"])

            # Notebook B tenta adquirir enquanto A está ativo -> conflito!
            l2 = self.storage.acquire_device_lease(device_id="notebook_B", ttl_seconds=600)
            self.assertFalse(l2["acquired"])
            self.assertEqual(l2["reason"], "LEASE_CONFLICT_ACTIVE_DEVICE")

            # Simula lease expirado
            expired_lease = {"device_id": "notebook_A", "status": "ACTIVE", "expires_at": time.time() - 10}
            self.storage.upload_json("VANTIS_DATA/checkpoints", "device_lease.json", expired_lease, overwrite=True)

            l3 = self.storage.acquire_device_lease(device_id="notebook_B", ttl_seconds=600)
            self.assertTrue(l3["acquired"])
            self.assertTrue(l3["lease"]["abandoned_previous_session"])
        finally:
            gh.MediaIoBaseDownload = orig

    def test_05_db_snapshot_and_new_notebook_restore(self):
        """Testa snapshot atômico SQLite, recuperação em notebook novo, memória persistente e isolamento."""
        db_orig = self.temp_path / "orig.db"
        run_migrations(db_path=db_orig)
        als = AudiovisualLearningSystem(db_path=db_orig)
        als.record_knowledge(
            niche="curiosidades", topic="drive_sync_test", title="Regra Remota C4",
            summary="Persistida no snapshot.", classification="APRENDIZADO_VALIDADO",
            evidence_video_ids=["v1", "v2"], counterexamples=["v3"], target_channel_id=4, pilot_phase=19,
        )

        import googleapiclient.http as gh
        orig = self._patch_downloader(b"")
        try:
            snap = self.storage.upload_db_snapshot(db_orig, device_id="notebook_A")
            self.assertTrue(snap["success"])

            db_new_laptop = self.temp_path / "new_notebook.db"
            rest = self.storage.restore_db_from_drive(db_new_laptop)
            self.assertTrue(rest["success"])
            self.assertTrue(db_new_laptop.is_file())

            als_new = AudiovisualLearningSystem(db_path=db_new_laptop)
            mem4 = als_new.get_channel_editorial_memory(4)
            mem1 = als_new.get_channel_editorial_memory(1)
            self.assertEqual(mem4["knowledge_count"], 1)
            self.assertEqual(mem1["knowledge_count"], 0)
        finally:
            gh.MediaIoBaseDownload = orig

    def test_06_dashboard_drive_first_states_and_labels(self):
        """Testa estados explícitos Drive-first e transparência no dashboard."""
        for st in ("REMOTE_AVAILABLE", "TEMPORARILY_CACHED", "REMOTE_VERIFIED", "INTEGRITY_ERROR", "DOWNLOAD_FAILED"):
            self.assertIn(st, STORAGE_STATES)

        db_dash = self.temp_path / "dash.db"
        run_migrations(db_path=db_dash)
        als = AudiovisualLearningSystem(db_path=db_dash)
        dash = als.get_dashboard_overview()
        self.assertIn("drive_storage_metrics", dash)
        dm = dash["drive_storage_metrics"]
        self.assertIn("videos_in_drive", dm)
        self.assertIn("videos_temporarily_cached", dm)
        self.assertIn("editorial_calibration_status", dm)
        self.assertEqual(dm["transparency_labels"]["youtube_studio_ctr_retention"], "NÃO_VERIFICADO")


if __name__ == "__main__":
    unittest.main()
