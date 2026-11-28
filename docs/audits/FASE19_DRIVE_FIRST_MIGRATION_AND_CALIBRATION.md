# VANTIS — FASE 19 | MIGRAÇÃO DEFINITIVA PARA GOOGLE DRIVE, ARMAZENAMENTO REMOTO E CALIBRAÇÃO EDITORIAL

**Data:** 2026-11-26  
**Branch:** `develop` (`main` preservada integralmente)  
**Custo Total:** **US$ 0,00** (`ENFORCE_FREE_TIER_ONLY = True`)  
**Lotes Futuros (500 / 7.000 vídeos):** **NÃO iniciados** (aguardam autorização explícita)

---

## 1. Arquitetura de Armazenamento Implementada
- **Camada Remota (`services/storage/drive_storage_service.py`):** `DriveStorageService` operando sobre OAuth2 oficial (`demello201019@gmail.com`) na pasta raiz `VANTIS` (`1KJp4_EpGIAdx1DpwTJ_8WyKDNbtgG_ZP`, **4.99 TB livres** de 5.0 TB).
- **Hierarquia `VANTIS_DATA` (26 pastas):** `media/benchmark_250/channel_{1..5}`, `media/benchmark_500`, `media/future_research`, `audio`, `transcripts`, `metadata`, `manifests`, `editorial_features`, `editorial_memory/channel_{1..5}`, `checkpoints`, `databases`, `analytics`, `reports`, `backups`.

## 2–7. Migração Verificável dos 250 Vídeos Existentes
- **Inventário local encontrado:** `241` arquivos em `C:\Users\jcvse\OneDrive\Desktop\Daniel\CENTRAL SHORTS\workspace\downloads\benchmark250` (`1,971.99 MB`, **MEDIDO**).
- **Migrados novos:** `221` arquivos (`UPLOADED_VERIFIED`).
- **Já existentes no Drive (reusados):** `20` arquivos (`REUSED_EXISTING`).
- **Verificados por SHA256 e MD5:** `241 / 241` (`100%`, **MEDIDO**).
- **Problemas / conflitos:** `0` conflitos de hash, `0` erros de upload.
- **Localização e IDs remotos:** Registrados integralmente em `docs/audits/phase19_drive_manifest.json` e em `VANTIS_DATA/manifests/benchmark_250_manifest.json`. Snapshot SQLite enviado: `shorts_central_20261126T195350Z_JC.db` (Drive ID: `1CIPnLbN7N0_dzcm0xRrvUSYYJOi-tp7f`). Memória editorial (`memory.json` dos 5 canais), `benchmark_250_features.json` e `benchmark_250_transcripts.json` também enviados.
- **Arquivos locais:** Preservados intactos (nenhum arquivo local foi apagado automaticamente; limpeza separada aguarda autorização).

## 8. Estratégia de Cache Temporário
- Cache efêmero em `workspace/cache/remote_tmp` com limite configurável (`max_cache_mb`), expiração por TTL (`cache_ttl_sec`), validação obrigatória de `SHA256` após download sob demanda e limpeza segura (`cleanup_temp_cache`), com estados explícitos (`REMOTE_AVAILABLE`, `TEMPORARILY_CACHED`, `PROCESSING`, `REMOTE_VERIFIED`, `REMOTE_MISSING`, `INTEGRITY_ERROR`, `DOWNLOAD_FAILED`).

## 9. Estratégia de Banco de Dados e Concorrência
- `device_lease.json` em `VANTIS_DATA/checkpoints` impede gravações simultâneas entre dois dispositivos (`LEASE_CONFLICT_ACTIVE_DEVICE`), suporta renovação (`renew_device_lease`) e recuperação de sessão abandonada após expiração do TTL.
- Snapshots SQLite atômicos via `sqlite3.Connection.backup`, versionados por timestamp/dispositivo e indexados em `latest_snapshot.json` com `SHA256`.

## 10. Reconstrução em Outro Notebook
- Documentada em `docs/operations/DRIVE_FIRST_SETUP.md`, `docs/operations/DEVICE_MIGRATION.md` e `docs/operations/REMOTE_STORAGE_ARCHITECTURE.md`: clonar `develop`, configurar OAuth2 em `credentials/`, adquirir lease, executar `restore_db_from_drive()` e baixar ativos sob demanda pelo manifesto.

## 11. Resultado da Calibração Editorial (Fase 18.2)
- Documentado em `docs/audits/FASE18_2_EDITORIAL_CALIBRATION.md`: no split de teste independente (`n=34`, `overlap=0`), o modelo calibrado atingiu **50.0% de precisão** (`11/22`, `+7.7 pp` sobre o baseline de `42.3%`), mantendo recall de `73.3%`, `33` decisões explicadas e `1` anti-pattern bloqueado (`is_causal_experiment = False`; métricas privadas do YouTube Studio permanecem `NÃO_VERIFICADO`).

## 12. Testes Executados
- `tests/test_fase19_drive_first_and_calibration.py`: `6 / 6` aprovados (`4.85s`) com mocks/fixtures isolados (sem alterar dados reais do Drive).
- Suíte completa (`scripts/run_all_tests.py`): **21 / 21 suítes — 184 / 184 testes aprovados (`100.0%`, `0` falhas, `0` erros, `0` ignorados, `724.84s`, `exit code 0`)**.

## 13–14. Sincronização Git e Google Drive
- Código versionado na `develop` (sem arquivos de vídeo, caches ou credenciais no Git) e espelho `podcast_cutter` sincronizado.
- Documentos de controle (`PROMPT_STATUS.md`, `EXECUTION_LOG.md`, `DECISIONS.md`) e relatórios sincronizados em `VANTIS_PROJECT_CONTROL`.

## 15–16. Custos, Limites e Pendências de Autorização
- **Custo:** **US$ 0,00** (`ENFORCE_FREE_TIER_ONLY = True`). **Quota Drive:** `4.99 TB` livres (`15.27 GB` usados de `5.0 TB`).
- **Pendências que dependem de autorização explícita do usuário:**
  1. Limpeza dos arquivos locais em `workspace/downloads/benchmark250` (~1.97 GB), agora que os 241 arquivos estão verificados no Drive.
  2. Execução do próximo lote controlado (500 vídeos) ou lote de 7.000 vídeos.
