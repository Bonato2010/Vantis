"""
VANTIS — Fase 19: Migração Verificável dos 250 Vídeos e Estado Persistente para Google Drive
- Inventaria arquivos locais em workspace/downloads/benchmark250
- Recalcula tamanho, SHA256 e MD5
- Deduplica contra o Drive sem sobrescrever conflitos
- Faz upload resumível e verificável para VANTIS_DATA/media/benchmark_250/channel_{1..5}
- Envia manifesto, transcrições, características editoriais, memória por canal e snapshot SQLite
- NÃO apaga os arquivos locais durante a migração
"""

import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.storage.drive_storage_service import DriveStorageService, compute_hashes

DL_ROOT = BASE_DIR / "workspace" / "downloads" / "benchmark250"
EXEC_JSON = BASE_DIR / "docs" / "audits" / "phase18_benchmark_execution_data.json"
MANIFEST_OUT = BASE_DIR / "docs" / "audits" / "phase19_drive_manifest.json"
DB_PATH = BASE_DIR / "database" / "shorts_central.db"


def main():
    start = time.time()
    storage = DriveStorageService()
    quota = storage.mgr.get_storage_quota()
    print("=== QUOTA GOOGLE DRIVE ===", json.dumps(quota, ensure_ascii=False), flush=True)

    folders = storage.ensure_structure()
    print(f"=== ESTRUTURA VANTIS_DATA VERIFICADA ({len(folders)} pastas) ===", flush=True)

    lease_res = storage.acquire_device_lease(operation="migrate_benchmark250", ttl_seconds=3600)
    if not lease_res.get("acquired"):
        raise RuntimeError(f"Conflito de lease ativo: {lease_res}")

    try:
        # Carrega registros do benchmark para associar metadados
        exec_recs = {}
        if EXEC_JSON.exists():
            for r in json.loads(EXEC_JSON.read_text(encoding="utf-8")).get("records", []):
                exec_recs[r["video_id"]] = r

        # Carrega manifesto parcial se existir (retomada segura)
        prev_entries = {}
        if MANIFEST_OUT.exists():
            try:
                prev = json.loads(MANIFEST_OUT.read_text(encoding="utf-8"))
                for item in prev.get("files", []):
                    if item.get("storage_state") == "REMOTE_VERIFIED" and item.get("drive_file_id"):
                        prev_entries[item["local_path"]] = item
            except Exception:
                pass

        disk_files = sorted([p for p in DL_ROOT.rglob("*") if p.is_file()])
        print(f"=== INVENTÁRIO LOCAL: {len(disk_files)} arquivos em {DL_ROOT} ===", flush=True)

        migrated_count = 0
        reused_count = 0
        conflict_count = 0
        error_count = 0
        manifest_files = []

        for idx, p in enumerate(disk_files, 1):
            local_str = str(p.resolve())
            ch_dir_name = p.parent.name  # ch_1 .. ch_5
            ch_num = ch_dir_name.replace("ch_", "") if ch_dir_name.startswith("ch_") else "1"
            folder_key = f"VANTIS_DATA/media/benchmark_250/channel_{ch_num}"
            vid_id = p.stem

            if local_str in prev_entries:
                manifest_files.append(prev_entries[local_str])
                reused_count += 1
                continue

            hashes = compute_hashes(p)
            up = storage.upload_file_resumable(
                p, folder_key=folder_key, remote_name=p.name, logical_id=vid_id
            )
            rec_info = exec_recs.get(vid_id, {})

            entry = {
                "logical_id": vid_id,
                "channel_id": int(ch_num) if ch_num.isdigit() else 0,
                "filename": p.name,
                "local_path": local_str,
                "folder_key": folder_key,
                "drive_file_id": up.get("drive_file_id"),
                "size_bytes": hashes["size_bytes"],
                "sha256": hashes["sha256"],
                "md5": hashes["md5"],
                "upload_status": up.get("status"),
                "storage_state": up.get("storage_state"),
                "benchmark_state": rec_info.get("state", "extra_local_file"),
                "migrated_at": datetime.now(timezone.utc).isoformat(),
            }
            manifest_files.append(entry)

            if up.get("status") == "UPLOADED_VERIFIED":
                migrated_count += 1
            elif up.get("status") == "REUSED_EXISTING":
                reused_count += 1
            elif up.get("status") == "CONFLICT_HASH_MISMATCH":
                conflict_count += 1
            else:
                error_count += 1

            if idx % 10 == 0 or idx == len(disk_files):
                storage.renew_device_lease(ttl_seconds=3600)
                MANIFEST_OUT.write_text(
                    json.dumps(
                        {
                            "manifest_name": "VANTIS_BENCHMARK_250_REMOTE_MANIFEST",
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                            "total_local_files": len(disk_files),
                            "migrated_new": migrated_count,
                            "reused_existing": reused_count,
                            "conflicts": conflict_count,
                            "errors": error_count,
                            "files": manifest_files,
                        },
                        indent=2,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                print(
                    f"  [{idx}/{len(disk_files)}] novos={migrated_count} | reusados={reused_count} | "
                    f"conflitos={conflict_count} | erros={error_count} | {time.time() - start:.0f}s",
                    flush=True,
                )

        # Exporta e envia artefatos estruturados de estado para o Drive
        als = AudiovisualLearningSystem(db_path=DB_PATH)
        for ch_id in range(1, 6):
            mem = als.get_channel_editorial_memory(ch_id)
            storage.upload_json(f"VANTIS_DATA/editorial_memory/channel_{ch_id}", "memory.json", mem, overwrite=True)

        # Features e transcrições reais dos 239 elegíveis
        features_export = []
        transcripts_export = []
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            for r in conn.execute("SELECT source_id, title, analysis_payload FROM audiovisual_library WHERE id > 143").fetchall():
                pay = json.loads(r["analysis_payload"] or "{}")
                if pay.get("editorial_features"):
                    features_export.append({"source_id": r["source_id"], "editorial_features": pay["editorial_features"]})
                narr = pay.get("narrative_and_script", {})
                if narr.get("speech_detected") and narr.get("full_transcript"):
                    transcripts_export.append({
                        "source_id": r["source_id"],
                        "title": r["title"],
                        "transcription_engine": narr.get("transcription_engine"),
                        "full_transcript": narr.get("full_transcript"),
                    })

        storage.upload_json("VANTIS_DATA/editorial_features", "benchmark_250_features.json", features_export, overwrite=True)
        storage.upload_json("VANTIS_DATA/transcripts", "benchmark_250_transcripts.json", transcripts_export, overwrite=True)

        snap_res = storage.upload_db_snapshot(DB_PATH)
        print("=== SNAPSHOT SQLITE ENVIADO ===", snap_res.get("snapshot_name"), snap_res.get("drive_file_id"), flush=True)

        manifest_payload = json.loads(MANIFEST_OUT.read_text(encoding="utf-8"))
        manifest_payload["sqlite_snapshot"] = snap_res
        manifest_payload["features_count"] = len(features_export)
        manifest_payload["transcripts_count"] = len(transcripts_export)
        manifest_payload["elapsed_seconds"] = round(time.time() - start, 2)
        MANIFEST_OUT.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        storage.upload_json("VANTIS_DATA/manifests", "benchmark_250_manifest.json", manifest_payload, overwrite=True)
        print(
            f"=== MIGRAÇÃO DRIVE CONCLUÍDA: {len(manifest_files)} arquivos | "
            f"novos={migrated_count} | reusados={reused_count} | conflitos={conflict_count} | erros={error_count} ===",
            flush=True,
        )
    finally:
        storage.release_device_lease()


if __name__ == "__main__":
    main()
