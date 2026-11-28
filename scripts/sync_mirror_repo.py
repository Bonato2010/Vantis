# -*- coding: utf-8 -*-
"""
Script para sincronizar os arquivos atualizados do repositorio principal
CENTRAL SHORTS para o repositorio espelho podcast_cutter
mantendo 100% de paridade entre ambos.
"""
import os
import shutil
import sys
from pathlib import Path

SOURCE_DIR = Path("C:/Users/jcvse/OneDrive/Desktop/Daniel/CENTRAL SHORTS")
TARGET_DIR = Path("C:/Users/jcvse/podcast_cutter")

DIRS_TO_SYNC = [
    "core",
    "memory",
    "database/migrations",
    "services/learning",
    "services/media_processing",
    "services/video_analysis",
    "services/transcription",
    "services/discovery",
    "services/orchestration",
    "services/distribution",
    "services/model_gateway",
    "web/static/assets",
    "web/static",
    "tests",
    "scripts",
    "docs/gdrive_control",
    "docs/audit",
    "docs/audits",
    "features/assets"
]

FILES_TO_SYNC = [
    "database/schema.sql",
    "web/app.py",
    "run_all_tests.py",
    "run_dashboard.py",
    "INICIAR_CENTRAL_IAS.bat",
    ".env.example"
]

def sync_mirror():
    if not TARGET_DIR.exists():
        print(f"[ERRO] Diretorio de destino nao existe: {TARGET_DIR}")
        return False

    print(f"Sincronizando de {SOURCE_DIR} para {TARGET_DIR}...")
    synced_files = 0

    # Sincroniza arquivos avulsos
    for rel_file in FILES_TO_SYNC:
        src = SOURCE_DIR / rel_file
        dst = TARGET_DIR / rel_file
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"[OK] Copiado arquivo: {rel_file}")
            synced_files += 1

    # Sincroniza diretorios
    for rel_dir in DIRS_TO_SYNC:
        src_d = SOURCE_DIR / rel_dir
        dst_d = TARGET_DIR / rel_dir
        if src_d.exists():
            dst_d.mkdir(parents=True, exist_ok=True)
            for item in src_d.iterdir():
                if item.is_file() and not item.name.endswith(".pyc"):
                    target_file = dst_d / item.name
                    shutil.copy2(item, target_file)
                    synced_files += 1
            print(f"[OK] Diretorio sincronizado: {rel_dir}")

    print(f"\nSincronizacao concluida com sucesso! Total de arquivos sincronizados: {synced_files}")
    return True

if __name__ == "__main__":
    success = sync_mirror()
    sys.exit(0 if success else 1)
