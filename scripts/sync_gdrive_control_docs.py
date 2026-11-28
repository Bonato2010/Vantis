import io
import sys
from pathlib import Path
from googleapiclient.http import MediaIoBaseDownload

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.gdrive_manager import GDriveManager

def sync_control_docs():
    mgr = GDriveManager()
    service = mgr.get_service()

    target_dir = BASE_DIR / "docs" / "gdrive_control"
    target_dir.mkdir(parents=True, exist_ok=True)

    ctrl_folder_id = "1rNbqXtnpBeo_1-GiR_vy-MW3yvybnNUH"
    results = service.files().list(
        q=f"'{ctrl_folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType, modifiedTime)"
    ).execute()

    files = results.get("files", [])
    print(f"Sincronizando {len(files)} arquivos de controle do Google Drive...")

    for f in sorted(files, key=lambda x: x["name"]):
        file_id = f["id"]
        file_name = f["name"]
        dest_path = target_dir / file_name

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        with open(dest_path, "wb") as out:
            out.write(fh.getvalue())
        print(f" -> Baixado: {file_name} ({len(fh.getvalue())} bytes)")

    print(f"\n[OK] Todos os documentos sincronizados em: {target_dir}")

if __name__ == "__main__":
    sync_control_docs()
