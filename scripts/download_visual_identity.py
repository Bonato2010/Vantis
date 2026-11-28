import sys
import io
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.gdrive_manager import GDriveManager
from googleapiclient.http import MediaIoBaseDownload

def download_folder_contents(service, folder_id, target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)", pageSize=100).execute()
    files = results.get("files", [])
    
    for f in sorted(files, key=lambda x: x.get("name", "")):
        f_id = f["id"]
        f_name = f["name"]
        f_mime = f["mimeType"]
        
        if f_mime == "application/vnd.google-apps.folder":
            sub_target = target_dir / f_name
            print(f" -> Criando subdiretório: {sub_target.relative_to(BASE_DIR)}")
            download_folder_contents(service, f_id, sub_target)
        else:
            file_dest = target_dir / f_name
            print(f"   * Baixando {f_name} -> {file_dest.relative_to(BASE_DIR)}...")
            request = service.files().get_media(fileId=f_id)
            with open(file_dest, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

def main():
    mgr = GDriveManager()
    service = mgr.get_service()
    visual_identity_folder_id = "1SSe9SHWn4NiaSQZd54xxWSRXAnQ6tfYu"
    
    print("=== BAIXANDO PACOTE COMPLETO DE IDENTIDADE VISUAL DO GOOGLE DRIVE ===")
    # Baixa para web/static/assets/ e features/
    target_web = BASE_DIR / "web" / "static" / "assets"
    target_features = BASE_DIR / "features"
    
    download_folder_contents(service, visual_identity_folder_id, target_web)
    
    print("\n[Identidade Visual] Download concluído com sucesso!")

if __name__ == "__main__":
    main()
