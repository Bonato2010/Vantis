"""
VANTIS / IAS - Script de Auditoria Operacional do Ambiente
Verifica runtimes, dependências, integridade de banco de dados, portas, uso de disco e status do Git.
"""
import os
import sys

# Desativa busca remota do mapa de custos para evitar esperas de rede
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

import shutil
import socket
import sqlite3
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def run_audit():
    print("=" * 65)
    print("        VANTIS / IAS - AUDITORIA OPERACIONAL DO AMBIENTE        ")
    print("=" * 65)

    # 1. Runtimes e Ferramentas
    print("\n[1. RUNTIMES E FERRAMENTAS]")
    print(f"Python: {sys.version.splitlines()[0]} ({sys.executable})")

    tools = ["node", "npm", "pnpm", "git", "ffmpeg"]
    for t in tools:
        path = shutil.which(t)
        if path:
            try:
                ver = subprocess.run([t, "--version"], capture_output=True, text=True, timeout=5).stdout.strip()
                print(f"  - {t:10}: DETECTADO -> {ver.splitlines()[0]} ({path})")
            except Exception as e:
                print(f"  - {t:10}: DETECTADO -> ({path}) (Erro versão: {e})")
        else:
            if t == "ffmpeg":
                winget_ff = Path(r"C:\Users\jcvse\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.1-full_build\bin\ffmpeg.exe")
                if winget_ff.exists():
                    print(f"  - {t:10}: DETECTADO (WinGet) -> {winget_ff}")
                else:
                    print(f"  - {t:10}: NÃO DETECTADO")
            else:
                print(f"  - {t:10}: NÃO DETECTADO")

    # 2. Armazenamento em Disco
    print("\n[2. ARMAZENAMENTO EM DISCO]")
    try:
        total, used, free = shutil.disk_usage("C:\\")
        print(f"  Drive C: Total: {total // (1024**3)} GB | Usado: {used // (1024**3)} GB | Livre: {free // (1024**3)} GB ({free/total*100:.1f}% livre)")
    except Exception as e:
        print(f"  Erro ao ler disco: {e}")

    # 3. Aceleração por Hardware / GPU
    print("\n[3. ACELERAÇÃO E HARDWARE]")
    try:
        import torch
        print(f"  PyTorch: {torch.__version__}")
        has_cuda = torch.cuda.is_available()
        print(f"  CUDA Disponível: {has_cuda}")
        if has_cuda:
            print(f"  Dispositivo: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("  PyTorch não instalado no ambiente Python padrão (Modo CPU puro ativo).")

    # 4. Auditoria de Dependências Python
    print("\n[4. PACOTES E DEPENDÊNCIAS PYTHON ESSENCIAIS]")
    core_pkgs = [
        "langgraph", "langchain_core", "litellm", "scenedetect", "cv2",
        "faster_whisper", "pgvector", "fastapi", "uvicorn", "numpy", "yt_dlp"
    ]
    for pkg in core_pkgs:
        try:
            mod = __import__(pkg)
            v = getattr(mod, "__version__", "instalado")
            print(f"  - {pkg:16}: OK (v{v})")
        except ImportError:
            print(f"  - {pkg:16}: AUSENTE / NÃO INSTALADO")
        except Exception as e:
            print(f"  - {pkg:16}: ERRO ({e})")

    # 5. Status do Repositório Git
    print("\n[5. AUDITORIA DO REPOSITÓRIO GIT]")
    print(f"  Diretório: {BASE_DIR}")
    try:
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=str(BASE_DIR), capture_output=True, text=True).stdout.strip()
        status_s = subprocess.run(["git", "status", "-s"], cwd=str(BASE_DIR), capture_output=True, text=True).stdout.strip()
        last_commit = subprocess.run(["git", "log", "-n", "1", "--oneline"], cwd=str(BASE_DIR), capture_output=True, text=True).stdout.strip()
        remotes = subprocess.run(["git", "remote", "-v"], cwd=str(BASE_DIR), capture_output=True, text=True).stdout.strip()
        print(f"  Branch Ativa: {branch}")
        print(f"  Último Commit: {last_commit}")
        print(f"  Alterações não commitadas:\n    {status_s or 'Nenhuma (Working tree limpa)'}")
        print(f"  Remoto configurado:\n    {remotes.splitlines()[0] if remotes else 'Nenhum'}")
    except Exception as ge:
        print(f"  Erro ao auditar Git: {ge}")

    # 6. Integridade do Banco SQLite
    print("\n[6. INTEGRIDADE DO BANCO DE DADOS RELACIONAL]")
    db_file = BASE_DIR / "database" / "shorts_central.db"
    if db_file.exists():
        size_kb = os.path.getsize(db_file) / 1024
        print(f"  Arquivo: {db_file} ({size_kb:.1f} KB)")
        try:
            conn = sqlite3.connect(str(db_file))
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            integ = cur.fetchone()[0]
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cur.fetchall()]
            print(f"  Integridade: {integ}")
            print(f"  Total de Tabelas: {len(tables)}")
            
            key_tables = [
                "video_references", "content_patterns", "channels",
                "workflow_checkpoints", "semantic_vectors", "video_lifecycle",
                "model_usage_logs", "categories"
            ]
            for kt in key_tables:
                if kt in tables:
                    cur.execute(f"SELECT COUNT(*) FROM {kt};")
                    c = cur.fetchone()[0]
                    print(f"    * {kt:22}: {c} registros")
            conn.close()
        except Exception as dbe:
            print(f"  Erro ao inspecionar banco: {dbe}")
    else:
        print(f"  Arquivo de banco não encontrado: {db_file}")

    # 7. Portas de Rede e Serviços
    print("\n[7. REDE E PORTAS]")
    ports_to_test = [8000, 3000, 5000, 8080, 5432, 6379]
    for pt in ports_to_test:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)
        r = s.connect_ex(("127.0.0.1", pt))
        state = "OCUPADA / ESCUTANDO" if r == 0 else "LIVRE"
        service_hint = ""
        if pt == 8000: service_hint = "(FastAPI Dashboard IAS)"
        elif pt == 5432: service_hint = "(PostgreSQL / pgvector)"
        elif pt == 3000: service_hint = "(Frontend Dev Server)"
        print(f"  Porta {pt:5}: {state:20} {service_hint}")
        s.close()

    print("\n" + "=" * 65)
    print("                 FIM DA AUDITORIA OPERACIONAL                   ")
    print("=" * 65)

if __name__ == "__main__":
    run_audit()
