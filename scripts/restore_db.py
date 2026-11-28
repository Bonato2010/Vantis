"""
Script de Restauração Segura de Banco de Dados SQLite (Prompt 10 - Deploy & Operações).
Valida integridade do arquivo de backup e cria pré-backup de segurança antes da substituição.
"""
import os
import sys
import shutil
import sqlite3
import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "shorts_central.db"
BACKUP_DIR = BASE_DIR / "backups"

def list_available_backups(backup_dir: Path = BACKUP_DIR):
    if not backup_dir.exists():
        return []
    return sorted(list(backup_dir.glob("vantis_backup_*.db")), key=lambda p: p.stat().st_mtime, reverse=True)

def restore_database_backup(backup_path: Optional[Path] = None, target_db: Path = DB_PATH) -> bool:
    if not backup_path:
        backups = list_available_backups()
        if not backups:
            raise FileNotFoundError("Nenhum arquivo de backup encontrado em 'backups/'.")
        backup_path = backups[0]
        print(f"[Restore] Utilizando backup mais recente: {backup_path.name}")

    backup_path = Path(backup_path)
    if not backup_path.exists():
        raise FileNotFoundError(f"Arquivo de backup especificado não existe: {backup_path}")

    # 1. Validação de integridade antes do restore
    verify_conn = sqlite3.connect(str(backup_path))
    integrity = verify_conn.execute("PRAGMA integrity_check").fetchone()[0]
    verify_conn.close()
    if integrity.lower() != "ok":
        raise RuntimeError(f"Backup corrompido! Abortando restore. Integridade: {integrity}")

    # 2. Criação de pré-backup de segurança do banco atual se ele existir
    if target_db.exists():
        pre_backup = target_db.parent / f"pre_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(target_db, pre_backup)
        print(f"[Restore] Pré-backup do banco atual criado em: {pre_backup.name}")

    # 3. Restauração atômica via SQLite Backup API
    target_db.parent.mkdir(parents=True, exist_ok=True)
    source_conn = sqlite3.connect(str(backup_path))
    dest_conn = sqlite3.connect(str(target_db))
    with dest_conn:
        source_conn.backup(dest_conn, pages=100)
    dest_conn.close()
    source_conn.close()

    print(f"[Restore] Restauração concluída com sucesso para: {target_db}")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        restore_database_backup(Path(sys.argv[1]))
    else:
        restore_database_backup()
