"""
Script de Backup Online e Atômico do Banco de Dados SQLite (Prompt 10 - Deploy & Operações).
Utiliza a SQLite Online Backup API para snapshots consistentes sem interromper escritas em WAL mode.
"""
import os
import sys
import gzip
import json
import sqlite3
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "shorts_central.db"
BACKUP_DIR = BASE_DIR / "backups"

def create_database_backup(db_path: Path = DB_PATH, backup_dir: Path = BACKUP_DIR, max_retention: int = 7) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"vantis_backup_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    print(f"[Backup] Iniciando backup atômico de: {db_path}")
    if not db_path.exists():
        raise FileNotFoundError(f"Banco de dados de origem não encontrado: {db_path}")

    # 1. Snapshot via SQLite Online Backup API
    source_conn = sqlite3.connect(str(db_path))
    dest_conn = sqlite3.connect(str(backup_path))
    with dest_conn:
        source_conn.backup(dest_conn, pages=100)
    dest_conn.close()
    source_conn.close()

    # 2. Verificação de integridade pós-backup
    verify_conn = sqlite3.connect(str(backup_path))
    integrity = verify_conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity.lower() != "ok":
        verify_conn.close()
        backup_path.unlink()
        raise RuntimeError(f"Falha na integridade do backup: {integrity}")

    # Contagem de tabelas para manifesto
    tables = [r[0] for r in verify_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    verify_conn.close()

    # 3. Manifesto JSON de auditoria
    meta = {
        "timestamp": datetime.datetime.now().isoformat(),
        "source_db": str(db_path),
        "backup_file": backup_filename,
        "backup_size_bytes": backup_path.stat().st_size,
        "integrity_check": integrity,
        "total_tables": len(tables),
        "tables": tables
    }
    meta_path = backup_dir / f"vantis_backup_{timestamp}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"[Backup] Backup concluído com sucesso: {backup_filename} ({meta['backup_size_bytes']} bytes, {len(tables)} tabelas)")

    # 4. Rotação / expurgo de backups antigos
    all_backups = sorted(list(backup_dir.glob("vantis_backup_*.db")), key=lambda p: p.stat().st_mtime)
    if len(all_backups) > max_retention:
        to_delete = all_backups[:-max_retention]
        for old in to_delete:
            old.unlink(missing_ok=True)
            old.with_suffix(".json").unlink(missing_ok=True)
            print(f"[Backup] Expurgo de backup antigo: {old.name}")

    return backup_path

if __name__ == "__main__":
    create_database_backup()
