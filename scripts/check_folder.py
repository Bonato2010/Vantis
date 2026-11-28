import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.gdrive_manager import GDriveManager

def main():
    mgr = GDriveManager()
    service = mgr.get_service()
    folder = service.files().get(fileId='1FgJRD9EIR0lRwIAqCX2W2NmYCd7OdJol', fields='id, name, mimeType, parents').execute()
    print(f"Pasta: {folder.get('name')} (ID: {folder.get('id')}) | Parents: {folder.get('parents')}")

    # Lista itens dentro dessa pasta
    query = f"'1FgJRD9EIR0lRwIAqCX2W2NmYCd7OdJol' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute().get("files", [])
    print(f"Itens dentro de {folder.get('name')}: {len(results)}")
    for r in sorted(results, key=lambda x: x.get("name")):
        print(f" - [{r.get('mimeType')}] {r.get('name')} (ID: {r.get('id')})")

if __name__ == "__main__":
    main()
