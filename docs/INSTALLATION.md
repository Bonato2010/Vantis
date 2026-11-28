# VANTIS — GUIA OFICIAL DE INSTALAÇÃO EM NOVO COMPUTADOR

> **Ambiente Alvo:** Windows 10/11 (PowerShell)  
> **Versão do Python:** Python 3.12.x ou 3.13.x (64-bit)  
> **Status:** VALIDADO EM NOVO DISPOSITIVO (2026-11-28)

---

## 1. Pré-Requisitos do Sistema

1. **Python 3.12 ou 3.13 (64-bit):**
   - Baixe em [python.org](https://www.python.org/downloads/)
   - **IMPORTANTE:** Marque a opção *"Add Python to PATH"* durante a instalação.

2. **Git para Windows:**
   - Baixe em [git-scm.com](https://git-scm.com/)

3. **FFmpeg e FFprobe (Obrigatórios para processamento de vídeo):**
   - Instale via WinGet no PowerShell:
     ```powershell
     winget install Gyan.FFmpeg
     ```
   - Ou faça download em [ffmpeg.org](https://ffmpeg.org/download.html) e adicione a pasta `bin` ao `PATH` do sistema.

---

## 2. Clonagem e Preparação do Repositório

```powershell
# 1. Clonar o repositório oficial apontando para a branch develop
git clone -b develop https://github.com/Bonato2010/Vantis.git "Vantis"
cd "Vantis"

# 2. Confirmar que a branch ativa é develop
git branch -v
# Deve exibir: * develop
```

---

## 3. Instalação das Dependências Python

Execute a instalação das dependências essenciais:

```powershell
python -m pip install --upgrade pip
python -m pip install "fastapi<0.115.0" "starlette<0.39.0" pydantic httpx uvicorn edge-tts google-api-python-client google-auth-oauthlib google-auth-httplib2 opencv-python numpy
```

*(Opcional para recursos de aprendizado vetorial avançado e transcrição local: `pip install faster-whisper fastembed yt-dlp`)*

---

## 4. Inicialização do Banco de Dados Relacional

Execute a suite de migrações automáticas:

```powershell
python -c "import sys; sys.path.insert(0, '.'); from database.migrate import run_migrations; run_migrations('database/shorts_central.db')"
```

---

## 5. Conexão do Google Drive 5 TB (OAuth 2.0)

1. No Google Cloud Console, baixe o arquivo de credenciais OAuth (Desktop App).
2. Salve o arquivo em:
   `credentials/gdrive_credentials.json`
3. Execute o script de autenticação:
   ```powershell
   python auth_drive.py
   # Ou execute dando duplo clique em: "CONECTAR MEU GOOGLE DRIVE.bat"
   ```
4. Autorize a conta no navegador. O token permanente será gerado automaticamente em `credentials/gdrive_token.json`.

---

## 6. Inicialização do Dashboard da Central

Para iniciar o servidor web operacional:

```powershell
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
# Ou execute dando duplo clique em: "INICIAR_CENTRAL_IAS.bat"
```

Acesse a plataforma no navegador em: **`http://127.0.0.1:8000`**

---

## 7. Execução dos Testes Automatizados

Para certificar que todo o ambiente está 100% funcional:

```powershell
python scripts/run_all_tests.py
```
