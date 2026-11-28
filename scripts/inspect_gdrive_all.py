import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.gdrive_manager import GDriveManager

def list_folder_recursive(service, folder_id, folder_name="Root", indent=0):
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)", pageSize=100).execute()
    files = results.get("files", [])
    prefix = "  " * indent
    print(f"{prefix}+ [{folder_name}] (ID: {folder_id}) - {len(files)} itens")
    for f in sorted(files, key=lambda x: x.get("name", "")):
        if f.get("mimeType") == "application/vnd.google-apps.folder":
            list_folder_recursive(service, f["id"], f["name"], indent + 1)
        else:
            print(f"{prefix}  - {f.get('name')} ({f.get('mimeType')}) [ID: {f.get('id')}]")

def main():
    mgr = GDriveManager()
    service = mgr.get_service()
    root_id = "1KJp4_EpGIAdx1DpwTJ_8WyKDNbtgG_ZP"
    print("=== MAPEAMENTO COMPLETO DA PASTA PRINCIPAL VANTIS NO GOOGLE DRIVE ===")
    list_folder_recursive(service, root_id, "VANTIS")

if __name__ == "__main__":
    main()
