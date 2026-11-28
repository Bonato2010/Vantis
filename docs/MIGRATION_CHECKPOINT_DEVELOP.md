# VANTIS — CHECKPOINT DE MIGRAÇÃO PARA OUTRO COMPUTADOR (BRANCH `develop`)

**Data do Checkpoint:** 2026-11-27  
**Branch Obrigatória:** `develop` (NUNCA trabalhar na `main` nem fazer merge entre `develop` e `main`)  
**Repositório Remoto:** `https://github.com/Bonato2010/IAS.git` (redireciona para `https://github.com/Bonato2010/Vantis.git`)

---

## 1. Como Clonar e Preparar o Repositório no Novo Computador

```bash
git clone -b develop https://github.com/Bonato2010/IAS.git "CENTRAL SHORTS"
cd "CENTRAL SHORTS"
git checkout develop
```

Confirme antes de iniciar qualquer trabalho:
```bash
git branch -v
```
Deve exibir `* develop`.

---

## 2. Dependências Externas e Ambiente

- **Python:** `3.12.8` (ou `3.12.x`)
- **FFmpeg / FFprobe:** obrigatórios no `PATH` do sistema (testado com `ffmpeg 9.1`).
- **Node.js:** não requerido pelo backend/dashboard atual (frontend servido em HTML/JS puro via FastAPI).
- **Pacotes Python principais** (o projeto não possui `requirements.txt` versionado até este checkpoint; instalar em virtualenv):

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn pydantic edge-tts google-api-python-client google-auth-oauthlib google-auth-httplib2 faster-whisper scenedetect opencv-python numpy fastembed yt-dlp litellm langgraph httpx
```

- **Variáveis de ambiente:** O núcleo de produção atual (`PackageRendererService`, Edge-TTS, FFmpeg, Wikimedia Commons, Dashboard) opera a **custo US$ 0,00** sem chaves pagas obrigatórias. Caso utilize provedores LLM opcionais, configure `GEMINI_API_KEY` ou `GROQ_API_KEY` em `.env` local (não versionar `.env`).

---

## 3. Inicialização do Banco, Dashboard e Validação

1. **Inicializar / migrar o banco SQLite:**
```bash
python -c "from database.migrate import run_migrations; run_migrations('database/shorts_central.db')"
```
2. **Iniciar o Dashboard Web (FastAPI + Uvicorn):**
```bash
uvicorn web.app:app --host 127.0.0.1 --port 8000
```
Acesse `http://127.0.0.1:8000`.
3. **Verificar se a instalação está funcionando:**
```bash
python scripts/run_all_tests.py
```

---

## 4. Inventário de Arquivos Não Versionados (Transferir Manualmente ou Recuperar do Drive)

Estes arquivos estão fora do Git por conterem dados locais, credenciais OAuth ou mídias binárias e **não devem ser apagados**:

| Caminho Local | Tamanho / Qtd | Estratégia de Migração |
| :--- | :--- | :--- |
| `database/shorts_central.db` | `8,028,160 bytes` | **Copiar manualmente** (ou restaurar snapshot mais recente em `VANTIS_DATA` no Google Drive) para preservar os 10 pacotes, 14 assets, 2 render jobs e 5 marcas. |
| `database/shorts_central_backup.db` | `172,032 bytes` | Copiar manualmente como backup secundário. |
| `credentials/gdrive_credentials.json` | `414 bytes` | **Transferir manualmente com segurança** (NUNCA versionar no Git). |
| `credentials/gdrive_token.json` | `768 bytes` | **Transferir manualmente** ou reautorizar o OAuth do Google Drive no novo computador. |
| `workspace/assets/acquired/` | `14` imagens | Copiar manualmente (assets reais baixados do Wikimedia Commons para os pacotes `#1`, `#3` e `#7`). |
| `workspace/renders/vantis_ch4_pkg7_job1.mp4` | `6,039,692 bytes` | Copiar manualmente (primeiro render histórico do Pacote `#7`, `CHANGES_REQUESTED`). |
| `workspace/renders/vantis_ch4_pkg7_job2.mp4` | `6,288,263 bytes` | Copiar manualmente (render corrigido do Pacote `#7`, `READY_FOR_REVIEW`). |
| `workspace/downloads/benchmark250/` | `241` vídeos | **Não precisa copiar manualmente** — já migrado integralmente para a pasta `VANTIS_DATA` no Google Drive (Fase 19); recuperável sob demanda via `DriveStorageService`. |
| `workspace/audio/`, `workspace/subs/`, `workspace/cache/` | Cache / intermediários | Gerados automaticamente em tempo de execução; cópia opcional. |

---

## 5. Documentos no Google Drive (`VANTIS_PROJECT_CONTROL`)

O script `scripts/sync_tracking_to_gdrive.py` mantém sincronizados no Google Drive:
- `PROMPT_STATUS.md`
- `EXECUTION_LOG.md`
- `DECISIONS.md`
- `BLOCKERS.md`
- Relatórios `FASE14_*.md` até `FASE27_*.md` (incluindo `FASE26_MULTICHANNEL_VALIDATION.md`)
- `MIGRATION_CHECKPOINT_DEVELOP.md` (este documento)

---

## 6. Ponto Exato para Retomar no Novo Computador

1. Pacote `#7` (**Horizonte Cósmico / Ciência**) já possui MP4 físico corrigido (`vantis_ch4_pkg7_job2.mp4`) em `READY_FOR_REVIEW` aguardando revisão humana final no dashboard (`APPROVED_AFTER_REVIEW`).
2. Pacotes `#1` (`4/6` assets), `#3` (`2/6` assets), `#5` (`0/6`) e `#9` (`0/6`) aguardam conclusão de assets e aprovação humana.
3. Os 5 canais YouTube estão com marcas configuradas (`channel_brands`), mas em `CHANNEL_NOT_CREATED` e `OAUTH_DISCONNECTED` aguardando criação manual no YouTube Studio.
