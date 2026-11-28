import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.gdrive_manager import GDriveManager

def main():
    mgr = GDriveManager()
    service = mgr.get_service()
    
    # 1. Pastas no Drive
    res = service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name, parents)",
        pageSize=100
    ).execute()
    folders = res.get("files", [])
    print(f"Total de pastas encontradas no Drive: {len(folders)}")
    for f in folders:
        print(f" - [Pasta] {f.get('name')} (ID: {f.get('id')}) | Parents: {f.get('parents')}")

    # 2. Arquivos gerais recentes
    res_files = service.files().list(
        q="trashed=false",
        fields="files(id, name, mimeType, parents)",
        pageSize=50
    ).execute()
    files = res_files.get("files", [])
    print(f"\nAmostra de arquivos no Drive: {len(files)}")
    for f in files[:20]:
        print(f" - [{f.get('mimeType')}] {f.get('name')} (ID: {f.get('id')})")

if __name__ == "__main__":
    main()
