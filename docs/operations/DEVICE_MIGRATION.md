# VANTIS — Migração Entre Notebooks e Dispositivos (`DEVICE_MIGRATION.md`)

## Objetivo
Permitir reconstruir o VANTIS em um novo notebook **sem copiar gigabytes de vídeos manualmente**.

## Passo a Passo em um Novo Dispositivo
1. **Instalar dependências:** `pip install -r requirements.txt` (e FFmpeg).
2. **Clonar o código:** `git clone -b develop https://github.com/Bonato2010/Vantis.git`.
3. **Configurar OAuth do Drive:** Colocar `credentials/gdrive_credentials.json` e autenticar `credentials/gdrive_token.json` (conta autorizada).
4. **Verificar estrutura e lease:**
   ```python
   from services.storage.drive_storage_service import DriveStorageService
   storage = DriveStorageService()
   storage.ensure_structure()
   lease = storage.acquire_device_lease(operation="device_migration")
   ```
   Se outro dispositivo estiver ativo (`LEASE_CONFLICT_ACTIVE_DEVICE`), aguarde a liberação ou expiração do TTL.
5. **Restaurar banco SQLite oficial do Drive:**
   ```python
   from pathlib import Path
   storage.restore_db_from_drive(Path("database/shorts_central.db"))
   ```
   O método baixa `VANTIS_DATA/databases/latest_snapshot.json`, valida o `SHA256` e restaura o SQLite atomicamente.
6. **Recuperar manifesto remoto e memória editorial:**
   - `storage.download_json("VANTIS_DATA/manifests", "benchmark_250_manifest.json")`
   - `storage.download_json("VANTIS_DATA/editorial_memory/channel_{1..5}", "memory.json")`
7. **Processar vídeo sob demanda (sem cópia permanente):**
   - `storage.fetch_to_temp_cache(drive_file_id, filename, expected_sha256)` baixa para `workspace/cache/remote_tmp`, valida `SHA256` e permite executar FFmpeg/OpenCV/Whisper.
   - Ao concluir, `storage.cleanup_temp_cache(filename)` libera o disco local.
8. **Finalizar sessão:** `storage.release_device_lease()` e, se alterou o banco, `storage.upload_db_snapshot(Path("database/shorts_central.db"))`.
