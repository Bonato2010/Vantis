# VANTIS — Configuração Drive-First (`DRIVE_FIRST_SETUP.md`)

## 1. Pré-requisitos
- Python 3.12+ e FFmpeg instalados no PATH.
- Repositório clonado na branch `develop`:
  `git clone -b develop https://github.com/Bonato2010/Vantis.git`
- Credencial OAuth2 autorizada em `credentials/gdrive_credentials.json` (nunca versionada no Git).

## 2. Autenticação e Verificação de Quota
1. Autenticar OAuth2 gerando `credentials/gdrive_token.json` com escopo `https://www.googleapis.com/auth/drive`.
2. Verificar cota e acesso à pasta raiz `VANTIS` (`1KJp4_EpGIAdx1DpwTJ_8WyKDNbtgG_ZP`):
   ```python
   from services.storage.drive_storage_service import DriveStorageService
   s = DriveStorageService()
   print(s.mgr.get_storage_quota())
   s.ensure_structure()
   ```

## 3. Regras de Segurança
- `credentials/` e `workspace/` estão no `.gitignore` e nunca devem ir para o Git.
- `ENFORCE_FREE_TIER_ONLY = True` permanece ativo para evitar qualquer cobrança em APIs pagas.
- O armazenamento local (`workspace/cache/remote_tmp`) é apenas cache temporário descartável; o Google Drive (`VANTIS_DATA`) é a fonte única de verdade.
