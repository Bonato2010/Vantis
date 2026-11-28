# VANTIS — FASE 27: IDENTIDADE DAS 5 MARCAS, CADASTRO REAL DOS CANAIS E PREPARAÇÃO PARA PUBLICAÇÃO

**Data:** 2026-11-27  
**Branch:** `develop` (preservando `main`)  
**Custo Efetivo:** `US$ 0,00`

---

## 1. Marcas Configuradas, Categorias e Disponibilidade Verificada

| Canal ID | Marca Candidata (`brand_name`) | Categoria (`editorial_category`) | Nome Histórico (`channels.name`) | Handle Candidato & Consulta Pública Real | Estado do Canal YouTube | OAuth |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `1` | **Zona de Jogo** | Futebol | `Canal 01 - Futebol em 60 Segundos` | `@zonadejogo` -> `HTTP 200` (`HANDLE_IN_USE_PUBLICLY`) | `CHANNEL_NOT_CREATED` (`youtube_channel_id = NULL`) | `OAUTH_DISCONNECTED` |
| `2` | **Dossiê Oculto** | Arquivo Sombrio | `Canal 02 - Arquivo Sombrio (Casos Reais)` | `@dossieoculto` -> `HTTP 404` (`AVAILABILITY_UNVERIFIED` — confirmar no Studio) | `CHANNEL_NOT_CREATED` (`youtube_channel_id = NULL`) | `OAUTH_DISCONNECTED` |
| `3` | **Caos em 60s** | Humor | `Canal 03 - Rir para Não Chorar` | `@caosem60s` -> `HTTP 200` (`HANDLE_IN_USE_PUBLICLY`) | `CHANNEL_NOT_CREATED` (`youtube_channel_id = NULL`) | `OAUTH_DISCONNECTED` |
| `4` | **Horizonte Cósmico** | Ciência | `Canal 04 - Mente Curiosa & Ciência` | `@horizontecosmico` -> `HTTP 200` (`HANDLE_IN_USE_PUBLICLY`) | `CHANNEL_NOT_CREATED` (`youtube_channel_id = NULL`) | `OAUTH_DISCONNECTED` |
| `5` | **Modo Ascensão** | Produtividade | `Canal 05 - Mente Focada & Produtividade` | `@modoascensao` -> `HTTP 200` (`HANDLE_IN_USE_PUBLICLY`) | `CHANNEL_NOT_CREATED` (`youtube_channel_id = NULL`) | `OAUTH_DISCONNECTED` |

> **Transparência:** Nenhum canal real foi criado automaticamente, nenhum ID/URL fictício foi registrado, e nenhuma conexão OAuth foi simulada. Todos os 5 canais aguardam criação manual no YouTube Studio e escolha de handle disponível quando o candidato já estiver em uso.

---

## 2. Auditoria da Integração YouTube / OAuth Existente

- **Tabela `channels`:** Todos os 5 canais estão com `youtube_channel_id = None` e `oauth_refresh_token = None`.
- **`core/youtube_uploader.py` (`YouTubeUploader`):** Possui trava estrita `human_approved` + `human_approval_token` e força `privacy_status='private'`, mas entra em modo de simulação quando `refresh_token` não está configurado.
- **Proteção adicionada na Fase 27 (`services/production/brand_registry.py`):**
  - `register_youtube_channel()` valida formato oficial (`^UC[A-Za-z0-9_-]{22}$`, `@handle`, `https://www.youtube.com/...`) e bloqueia marcadores fictícios (`fake`, `test`, `placeholder`, etc.).
  - `verify_oauth_connection()` verifica token real sem simular (`OAUTH_DISCONNECTED` quando ausente).
  - `prepare_publish_metadata(package_id)` gera metadados com marca/categoria/atribuições e **bloqueia** publicação (`ready_to_upload=False`) enquanto o pacote não estiver aprovado, o canal não estiver verificado ou `oauth_status != 'OAUTH_CONNECTED'`.

---

## 3. Funcionalidades Implementadas & Preservação Histórica

- **Migração `database/migrations/012_brand_identity_and_youtube_registry.sql` & `services/production/brand_registry.py`:** Separação explícita entre `brand_name`, `editorial_category`, `legacy_channel_name`, dados reais do YouTube, `channel_status`, `oauth_status` e `branding_config` editável (paleta, tipografia, estilo de thumbnail, logo/avatar/banner em `PENDING_HUMAN_APPROVAL`).
- **Pacotes históricos preservados:** `#1`, `#3`, `#5`, `#7` e `#9` mantidos integralmente vinculados às suas categorias e histórico (`vantis_ch4_pkg7_job2.mp4` preservado sem re-renderização desnecessária).
- **API & Dashboard (`web/app.py`, `web/static/index.html`):** Endpoints `/api/brands`, `/api/brands/check-handle`, `/api/brands/{channel_id}`, `/api/brands/{channel_id}/youtube-registry`, `/api/brands/{channel_id}/oauth-check`, `/api/production/packages/{id}/publish-metadata`, além do painel **Marcas, Canais Reais & Prontidão YouTube (Fase 27)**.

---

## 4. Testes, Regressão, Custos e Próxima Etapa

- **Suíte Fase 27 (`tests/test_fase27_brand_identity_and_youtube_registry.py`):** `5 / 5` aprovados (`1.82s` na bateria / `13.95s` isolado).
- **Regressão Completa (`scripts/run_all_tests.py`):** **`29 / 29` suítes, `229 / 229` testes aprovados (`100.0%`, `0` falhas, `0` erros, `0` skipped, `699.69s`)**.
- **Custos:** `US$ 0,00`.
- **Pendências:** Criação manual dos 5 canais no YouTube Studio (ajustando handles caso `@zonadejogo`, `@caosem60s`, `@horizontecosmico` ou `@modoascensao` estejam ocupados), registro dos `UC...` reais no dashboard, conexão OAuth 2.0 real e aprovação visual das identidades.
- **Próxima etapa recomendada:** Criar manualmente o canal piloto de Ciência (**Horizonte Cósmico**) no YouTube Studio, registrar o `youtube_channel_id` real e conectar o OAuth 2.0 no dashboard para validar o primeiro upload privado controlado.
