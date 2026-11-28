"""
IAS Database Enterprise Migrator v3.0
Aplica migrações sequenciais, consolida schemas, garante retrocompatibilidade
e preserva 100% dos dados pré-existentes sem perdas.
"""
import os
import sys
import sqlite3
from pathlib import Path
from typing import Union

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def run_migrations(db_path: Union[str, Path] = None) -> dict:
    if db_path is None:
        db_path = BASE_DIR / "database" / "shorts_central.db"
    else:
        db_path = Path(db_path)
    print(f"[Migrator] Processando banco de dados: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    cursor = conn.cursor()
    added_columns_count = 0

    try:
        # 1. Aplica scripts de migração ordenados
        migrations_dir = BASE_DIR / "database" / "migrations"
        if migrations_dir.exists():
            sql_files = sorted(migrations_dir.glob("*.sql"))
            for sql_file in sql_files:
                with open(sql_file, "r", encoding="utf-8") as f:
                    cursor.executescript(f.read())
                conn.commit()
                print(f" -> Migração {sql_file.name} executada.")

        # 2. Assegura colunas essenciais em tabelas pré-existentes (Idempotente)
        required_columns = {
        "video_references": [
            ("video_id", "TEXT"),
            ("youtube_id", "TEXT"),
            ("original_url", "TEXT"),
            ("url", "TEXT"),
            ("title", "TEXT"),
            ("author", "TEXT"),
            ("channel_title", "TEXT"),
            ("views_count", "INTEGER DEFAULT 0"),
            ("view_count", "INTEGER DEFAULT 0"),
            ("likes_count", "INTEGER DEFAULT 0"),
            ("like_count", "INTEGER DEFAULT 0"),
            ("comment_count", "INTEGER DEFAULT 0"),
            ("engagement_rate", "REAL DEFAULT 0.0"),
            ("duration_seconds", "REAL DEFAULT 0.0"),
            ("hook_transcript", "TEXT"),
            ("full_transcript", "TEXT"),
            ("transcript_text", "TEXT"),
            ("transcript_word_timestamps", "TEXT"),
            ("niche", "TEXT"),
            ("subcategory", "TEXT"),
            ("pacing_bpm", "REAL DEFAULT 0.0"),
            ("retention_score", "REAL DEFAULT 0.0"),
            ("format_features", "TEXT"),
            ("analysis_notes", "TEXT"),
            ("availability_status", "TEXT DEFAULT 'active'"),
            ("usage_permission", "TEXT DEFAULT 'reference_only'"),
            ("gdrive_file_id", "TEXT"),
            ("gdrive_backup_id", "TEXT"),
            ("tags", "TEXT"),
            ("channel_id", "INTEGER REFERENCES channels(id)")
        ],
        "scripts": [
            ("channel_id", "INTEGER REFERENCES channels(id)"),
            ("category_id", "INTEGER REFERENCES categories(id)"),
            ("opportunity_id", "INTEGER REFERENCES opportunities(id)"),
            ("editorial_profile_id", "INTEGER REFERENCES editorial_profiles(id)"),
            ("title", "TEXT"),
            ("archetype", "TEXT"),
            ("hook", "TEXT"),
            ("hook_3s", "TEXT"),
            ("core_narrative", "TEXT"),
            ("cta", "TEXT"),
            ("full_script", "TEXT"),
            ("full_script_json", "TEXT"),
            ("visual_cues", "TEXT"),
            ("audio_cues", "TEXT"),
            ("target_duration", "REAL"),
            ("recommended_duration", "REAL"),
            ("editing_style", "TEXT"),
            ("status", "TEXT DEFAULT 'draft'"),
            ("human_approved", "INTEGER DEFAULT 0"),
            ("approval_notes", "TEXT"),
            ("approved_by", "TEXT"),
            ("approved_at", "TIMESTAMP")
        ],
        "channels": [
            ("country", "TEXT DEFAULT 'BR'"),
            ("daily_upload_limit", "INTEGER DEFAULT 3"),
            ("oauth_refresh_token", "TEXT"),
            ("gdrive_folder_id", "TEXT")
        ],
        "content_patterns": [
            ("channel_id", "INTEGER REFERENCES channels(id)")
        ],
        "knowledge_nodes": [
            ("channel_id", "INTEGER REFERENCES channels(id)")
        ],
        "agent_decisions": [
            ("channel_id", "INTEGER REFERENCES channels(id)")
        ],
        "workflow_checkpoints": [
            ("channel_id", "INTEGER REFERENCES channels(id)")
        ],
        "semantic_vectors": [
            ("channel_id", "INTEGER REFERENCES channels(id)")
        ],
        "model_usage_logs": [
            ("channel_id", "INTEGER REFERENCES channels(id)")
        ],
        "opportunities": [
            ("rejection_reason", "TEXT"),
            ("rejection_category", "TEXT")
        ],
        "publications": [
            ("privacy_status", "TEXT DEFAULT 'private'"),
            ("human_approval_token", "TEXT"),
            ("approved_by", "TEXT"),
            ("approved_at", "TIMESTAMP"),
            ("gdrive_backup_id", "TEXT")
        ]
    }

        added_columns_count = 0
        for table_name, cols in required_columns.items():
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_cols = {row[1] for row in cursor.fetchall()}
            for col_name, col_type in cols:
                if col_name not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                        added_columns_count += 1
                    except Exception as e:
                        print(f" -> Aviso ao adicionar {col_name} em {table_name}: {e}")

        conn.commit()

        # Coleta contagem final
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'")
        tables = [r[0] for r in cursor.fetchall()]
        table_counts = {t: cursor.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}

        return {
            "status": "SUCCESS",
            "total_tables": len(tables),
            "added_columns": added_columns_count,
            "table_counts": table_counts
        }
    finally:
        conn.close()

if __name__ == "__main__":
    db_target = BASE_DIR / "database" / "shorts_central.db"
    res = run_migrations(db_target)
    print(f"\n[Migrator] Concluído! Total de tabelas: {res['total_tables']}, Colunas adicionadas: {res['added_columns']}")
    print(f"[Migrator] Resumo de registros: {res['table_counts']}")
