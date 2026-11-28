"""
Script para sincronizar documentos de rastreamento (EXECUTION_LOG, PROMPT_STATUS, DECISIONS, BLOCKERS)
com a pasta oficial VANTIS_PROJECT_CONTROL no Google Drive.
"""
import io
import os
import sys
from pathlib import Path
from googleapiclient.http import MediaFileUpload

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.gdrive_manager import GDriveManager

CTRL_FOLDER_ID = "1rNbqXtnpBeo_1-GiR_vy-MW3yvybnNUH"
DOCS_TO_SYNC = [
    "EXECUTION_LOG.md",
    "PROMPT_STATUS.md",
    "DECISIONS.md",
    "BLOCKERS.md"
]
ADDITIONAL_DOCS = [
    ("FASE14_INDEPENDENT_AUDIT.md", BASE_DIR / "docs" / "audits" / "FASE14_INDEPENDENT_AUDIT.md"),
    ("FASE15_REAL_SHORTS_PILOT.md", BASE_DIR / "docs" / "audits" / "FASE15_REAL_SHORTS_PILOT.md"),
    ("FASE15_1_FORENSIC_AUDIT.md", BASE_DIR / "docs" / "audits" / "FASE15_1_FORENSIC_AUDIT.md"),
    ("FASE16_PILOT_100_SHORTS.md", BASE_DIR / "docs" / "audits" / "FASE16_PILOT_100_SHORTS.md"),
    ("FASE17_SCALE_READINESS_AUDIT.md", BASE_DIR / "docs" / "audits" / "FASE17_SCALE_READINESS_AUDIT.md"),
    ("FASE17_1_INDEPENDENT_SCALE_AUDIT.md", BASE_DIR / "docs" / "audits" / "FASE17_1_INDEPENDENT_SCALE_AUDIT.md"),
    ("FASE18_LEARNING_AND_250_VIDEO_BENCHMARK.md", BASE_DIR / "docs" / "audits" / "FASE18_LEARNING_AND_250_VIDEO_BENCHMARK.md"),
    ("FASE18_1_INDEPENDENT_AUDIT.md", BASE_DIR / "docs" / "audits" / "FASE18_1_INDEPENDENT_AUDIT.md"),
    ("FASE18_2_EDITORIAL_CALIBRATION.md", BASE_DIR / "docs" / "audits" / "FASE18_2_EDITORIAL_CALIBRATION.md"),
    ("FASE19_DRIVE_FIRST_MIGRATION_AND_CALIBRATION.md", BASE_DIR / "docs" / "audits" / "FASE19_DRIVE_FIRST_MIGRATION_AND_CALIBRATION.md"),
    ("FASE20_OPERATIONAL_AUDIT.md", BASE_DIR / "docs" / "audits" / "FASE20_OPERATIONAL_AUDIT.md"),
    ("FASE21_EDITORIAL_PRODUCTION.md", BASE_DIR / "docs" / "audits" / "FASE21_EDITORIAL_PRODUCTION.md"),
    ("FASE22_AUDIOVISUAL_RENDERING.md", BASE_DIR / "docs" / "audits" / "FASE22_AUDIOVISUAL_RENDERING.md"),
    ("FASE23_FIRST_REAL_PRODUCTION.md", BASE_DIR / "docs" / "audits" / "FASE23_FIRST_REAL_PRODUCTION.md"),
    ("FASE24_ASSET_INTELLIGENCE_AND_SCRIPT_QUALITY.md", BASE_DIR / "docs" / "audits" / "FASE24_ASSET_INTELLIGENCE_AND_SCRIPT_QUALITY.md"),
    ("FASE25_ASSET_ACQUISITION_AND_FIRST_RENDER.md", BASE_DIR / "docs" / "audits" / "FASE25_ASSET_ACQUISITION_AND_FIRST_RENDER.md"),
    ("FASE26_MULTICHANNEL_VALIDATION.md", BASE_DIR / "docs" / "audits" / "FASE26_MULTICHANNEL_VALIDATION.md"),
    ("FASE27_BRAND_IDENTITY_AND_YOUTUBE_REGISTRY.md", BASE_DIR / "docs" / "audits" / "FASE27_BRAND_IDENTITY_AND_YOUTUBE_REGISTRY.md"),
    ("MIGRATION_CHECKPOINT_DEVELOP.md", BASE_DIR / "docs" / "MIGRATION_CHECKPOINT_DEVELOP.md")
]

def sync_tracking_to_gdrive():
    mgr = GDriveManager()
    service = mgr.get_service()
    local_dir = BASE_DIR / "docs" / "gdrive_control"

    # List existing files in folder
    res = service.files().list(
        q=f"'{CTRL_FOLDER_ID}' in parents and trashed = false",
        fields="files(id, name)"
    ).execute()
    existing_files = {f["name"]: f["id"] for f in res.get("files", [])}

    print(f"[Drive Sync] Pasta VANTIS_PROJECT_CONTROL possui {len(existing_files)} arquivos.")

    for doc_name in DOCS_TO_SYNC:
        local_file = local_dir / doc_name
        if not local_file.exists():
            print(f"[Aviso] Arquivo local não encontrado: {local_file}")
            continue

        media = MediaFileUpload(str(local_file), mimetype="text/markdown", resumable=True)

        if doc_name in existing_files:
            file_id = existing_files[doc_name]
            print(f"[Drive Sync] Atualizando {doc_name} (ID: {file_id})...")
            updated = service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id, name, modifiedTime"
            ).execute()
            print(f" -> Atualizado com sucesso: {updated.get('name')} em {updated.get('modifiedTime')}")
        else:
            print(f"[Drive Sync] Criando novo {doc_name} na pasta...")
            meta = {
                "name": doc_name,
                "parents": [CTRL_FOLDER_ID]
            }
            created = service.files().create(
                body=meta,
                media_body=media,
                fields="id, name, webViewLink"
            ).execute()
            print(f" -> Criado com sucesso: {created.get('name')} (ID: {created.get('id')})")

    for doc_name, local_file in ADDITIONAL_DOCS:
        if not local_file.exists():
            print(f"[Aviso] Arquivo adicional local não encontrado: {local_file}")
            continue

        media = MediaFileUpload(str(local_file), mimetype="text/markdown", resumable=True)

        if doc_name in existing_files:
            file_id = existing_files[doc_name]
            print(f"[Drive Sync] Atualizando {doc_name} (ID: {file_id})...")
            updated = service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id, name, modifiedTime"
            ).execute()
            print(f" -> Atualizado com sucesso: {updated.get('name')} em {updated.get('modifiedTime')}")
        else:
            print(f"[Drive Sync] Criando novo {doc_name} na pasta...")
            meta = {
                "name": doc_name,
                "parents": [CTRL_FOLDER_ID]
            }
            created = service.files().create(
                body=meta,
                media_body=media,
                fields="id, name, webViewLink"
            ).execute()
            print(f" -> Criado com sucesso: {created.get('name')} (ID: {created.get('id')})")

    print("[Drive Sync] Sincronização de rastreamento concluída com sucesso!")

if __name__ == "__main__":
    sync_tracking_to_gdrive()
