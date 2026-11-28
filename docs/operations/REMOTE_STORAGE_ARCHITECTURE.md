# VANTIS — Arquitetura de Armazenamento Remoto (`REMOTE_STORAGE_ARCHITECTURE.md`)

## Separação de Responsabilidades
- **GitHub (`develop`):** Código-fonte, testes, migrações SQL, documentação e manifestos leves.
- **Google Drive (`VANTIS` / `1KJp4_EpGIAdx1DpwTJ_8WyKDNbtgG_ZP`):** Fonte única de verdade para vídeos, áudios, transcrições, características editoriais, memória por canal, snapshots SQLite, checkpoints e relatórios.
- **Notebook / Máquina Local:** Ambiente efêmero de execução com cache temporário (`workspace/cache/remote_tmp`, limite configurável e TTL).

## Hierarquia no Drive
- `VANTIS_PROJECT_CONTROL/`: auditorias, logs, decisões, status de prompts.
- `VANTIS_DATA/`:
  - `media/benchmark_250/channel_{1..5}`, `media/benchmark_500`, `media/future_research`
  - `audio/`, `transcripts/`, `metadata/`, `manifests/`, `editorial_features/`
  - `editorial_memory/channel_{1..5}/`
  - `checkpoints/`, `databases/`, `analytics/`, `reports/`, `backups/`

## Estados Explícitos de Ativos
- `REMOTE_AVAILABLE` | `TEMPORARILY_CACHED` | `PROCESSING` | `REMOTE_VERIFIED` | `REMOTE_MISSING` | `INTEGRITY_ERROR` | `DOWNLOAD_FAILED`

## Concorrência e Proteção Contra Conflitos
- `VANTIS_DATA/checkpoints/device_lease.json` controla qual dispositivo detém o lock ativo (com TTL, renovação e detecção de sessão abandonada).
- Snapshots SQLite são gravados atomicamente via `sqlite3.Connection.backup`, versionados por timestamp/dispositivo e indexados em `latest_snapshot.json` com `SHA256` e `MD5`.
