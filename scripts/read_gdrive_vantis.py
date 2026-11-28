import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.gdrive_manager import GDriveManager

def main():
    mgr = GDriveManager()
    print("Autenticado:", mgr.is_authenticated())
    service = mgr.get_service()
    print("Google Drive API Service conectado com sucesso!")

    main_folder_id = "1KJp4_EpGIAdx1DpwTJ_8WyKDNbtgG_ZP"
    main_folder = service.files().get(fileId=main_folder_id, fields="id, name, mimeType").execute()
    print(f"Pasta Principal: {main_folder.get('name')} (ID: {main_folder.get('id')})")

    # Lista itens dentro da pasta principal
    query = f"'{main_folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    files = results.get("files", [])
    print(f"\nTotal de itens na pasta principal: {len(files)}")
    for f in files:
        print(f" - [{f.get('mimeType')}] {f.get('name')} (ID: {f.get('id')})")

    # Procura especificamente por VANTIS_PROJECT_CONTROL
    control_folder = next((f for f in files if "VANTIS_PROJECT_CONTROL" in f.get("name")), None)
    if not control_folder:
        # Busca recursivamente se não estiver na raiz
        q_search = "name contains 'VANTIS_PROJECT_CONTROL' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        search_res = service.files().list(q=q_search, fields="files(id, name, mimeType)").execute()
        if search_res.get("files"):
            control_folder = search_res["files"][0]

    if control_folder:
        ctrl_id = control_folder["id"]
        print(f"\n=== PASTA ENCONTRADA: {control_folder.get('name')} (ID: {ctrl_id}) ===")
        # Lista todo o conteúdo de VANTIS_PROJECT_CONTROL
        ctrl_query = f"'{ctrl_id}' in parents and trashed=false"
        ctrl_files = service.files().list(q=ctrl_query, fields="files(id, name, mimeType, modifiedTime)", pageSize=100).execute().get("files", [])
        print(f"Total de itens em {control_folder.get('name')}: {len(ctrl_files)}")
        for cf in sorted(ctrl_files, key=lambda x: x.get("name", "")):
            print(f"   * [{cf.get('mimeType')}] {cf.get('name')} (ID: {cf.get('id')})")
    else:
        print("\n[AVISO] Pasta 'VANTIS_PROJECT_CONTROL' não encontrada na pasta principal.")

if __name__ == "__main__":
    main()
