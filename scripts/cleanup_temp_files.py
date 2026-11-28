"""
Script de Limpeza e Rotação de Arquivos Transitórios (Prompt 10 - Deploy & Operações).
Garante a diretriz de zero acúmulo de arquivos brutos ou temporários no disco local.
"""
import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DIRS_TO_PRUNE = [
    BASE_DIR / "workspace" / "temp",
    BASE_DIR / "workspace" / "audio",
    BASE_DIR / "workspace" / "subs"
]

def cleanup_transient_files(max_age_hours: float = 24.0) -> int:
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    removed_count = 0

    print(f"[Cleanup] Iniciando rotação de arquivos temporários (> {max_age_hours}h)...")
    for d in DIRS_TO_PRUNE:
        if not d.exists():
            continue
        for f in d.iterdir():
            if f.is_file():
                # Não remove arquivos de lock ou gitkeep
                if f.name.startswith(".") or f.suffix in [".gitignore"]:
                    continue
                try:
                    if f.stat().st_mtime < cutoff:
                        f.unlink()
                        removed_count += 1
                        print(f" -> Removido: {f.name}")
                except Exception as e:
                    print(f" -> Aviso: não foi possível remover {f.name}: {e}")

    print(f"[Cleanup] Limpeza concluída: {removed_count} arquivos transitórios expurgados.")
    return removed_count

if __name__ == "__main__":
    cleanup_transient_files()
