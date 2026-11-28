# VANTIS — FASE 24: ASSET INTELLIGENCE, ROTEIROS COMPLETOS E PREPARAÇÃO AUTOMÁTICA PARA PRODUÇÃO

**Data:** 2026-11-26  
**Branch:** `develop` (preservando `main`)  
**Custo Efetivo:** `US$ 0,00`

---

## 1. Situação Inicial e Problemas Encontrados

A auditoria inicial dos **10 pacotes editoriais existentes** (gerados na Fase 21 em `database/shorts_central.db`, 2 por canal) identificou falhas concretas:
- **Roteiros baseados em template superficial:** todos os 10 pacotes repetiam fórmulas genéricas inserindo `{theme}` e possuíam campo `climax` ausente (`None`), sem `context`, sem `sources` e sem registro de limitações.
- **Repetição acidental de texto:** pacote `#5` (Canal 3 — Humor) continha `"Sabe quando Quando a reunião online..."`.
- **Falso positivo de placeholder corrigido no validador:** `TODO` em maiúsculas vs palavra portuguesa `"todo"` (`Quase todo torcedor...`, `Todo mundo entra...`).
- **Ausência de especificação estruturada de mídia e biblioteca de ativos:** as `6` cenas de cada pacote estavam em `ASSET_NEEDED` sem `media_requirements` nem verificação de hash, dimensões ou direitos de utilização.
- **Classificação inicial antes da correção:** `6` pacotes em `REFERENCE_INSUFFICIENT` (`#1, #2, #3, #4, #7, #8` a `55.6%`) e `4` em `SCRIPT_NEEDS_REVISION` (`#5, #6, #9, #10` a `55.6%–66.7%`).

---

## 2. Soluções Implementadas

1. **Biblioteca e Motor de Inteligência de Assets (`services/production/asset_intelligence.py` + `database/migrations/011_asset_intelligence_and_validation.sql`):**
   - Tabela `production_assets` com `asset_uid`, `file_path`, `media_type`, `width`, `height`, `duration_sec`, `sha256` (único para deduplicação), `origin`, `source_url`, `license_name`, `license_status`, `attribution_required`, `authorized_channels_json`, `validation_status`, `tags_json`.
   - Verificação física real via `ffprobe` (rejeita corrompidos ou baixa resolução) e bloqueio explícito de arquivos do `workspace/downloads/benchmark250`.
   - Classificação conservadora de licença (`VERIFIED_CC0`, `VERIFIED_PUBLIC_DOMAIN`, `VERIFIED_CC_BY`, `VERIFIED_OWN_LIBRARY`, `VERIFIED_ROYALTY_FREE`, `LICENSE_UNVERIFIED`, `RESTRICTED`).
   - Interpretação de cenas (`analyze_scene_requirements`) e associação segura (`match_assets_for_scenes`), mantendo `ASSET_NEEDED` quando não houver mídia compatível e licenciada.
   - Conector público gratuito da API Wikimedia Commons (`search_wikimedia_commons`) verificando `LicenseShortName` e tratando falhas offline sem quebrar.

2. **Motor de Roteiros Completos & 5 Identidades Editoriais (`services/production/script_quality_engine.py`):**
   - Estrutura completa por canal: `hook`, `context`, `development`, `climax`, `closing`, `cta`, `full_narration`, `sources`, `fact_vs_speculation_note`, `limitations`.
   - Limpeza automática de repetições consecutivas (`clean_accidental_repetitions`), zero `None`, respeito ao ritmo/duração por canal e isolamento rigoroso de memória.

3. **Validador Editorial Automático (`EditorialValidator` + `editorial_validation_reports`):**
   - 9 verificações explícitas (completude, ausência de placeholders, ausência de repetições, coerência roteiro-cenas, duração compatível, fontes quando necessárias, pendências de assets, direitos de uso e isolamento de canal).
   - Pontuação explicável (`0–100%`) e classificação explícita (`EDITORIALLY_READY`, `SCRIPT_NEEDS_REVISION`, `ASSETS_INCOMPLETE`, `REFERENCE_INSUFFICIENT`, `BLOCKED`), nunca substituindo a aprovação humana.

4. **Dashboard & API (`web/app.py`, `web/static/index.html`):**
   - Endpoints `GET /api/production/assets`, `POST /api/production/assets/register`, `POST /api/production/packages/{id}/validate`, `POST /api/production/packages/{id}/prepare-assets`, `POST /api/production/packages/{id}/scenes/{scene_index}/assign-asset`.
   - Área de preparação editorial permitindo editar roteiro completo, consultar problemas detectados, reexecutar validador, comparar versões, associar ativos por cena e visualizar status de licenciamento.

---

## 3. Piloto Controlado nos 10 Pacotes Existentes

Relatório individual completo salvo em `docs/audits/phase24_pilot_10_packages_report.json`:

| Pacote | Canal | Antes | Depois | Status | Pendências Reais |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `#1`, `#2` | 1 — Futebol | `REFERENCE_INSUFFICIENT` (`55.6%`) | `ASSETS_INCOMPLETE` (`88.9%`) | `READY_FOR_REVIEW` | `6/6` cenas `ASSET_NEEDED` |
| `#3`, `#4` | 2 — Arquivo Sombrio | `REFERENCE_INSUFFICIENT` (`55.6%`) | `ASSETS_INCOMPLETE` (`88.9%`) | `READY_FOR_REVIEW` | `6/6` cenas `ASSET_NEEDED` |
| `#5`, `#6` | 3 — Humor | `SCRIPT_NEEDS_REVISION` (`55.6%–66.7%`) | `ASSETS_INCOMPLETE` (`88.9%`) | `READY_FOR_REVIEW` | `6/6` cenas `ASSET_NEEDED` |
| `#7`, `#8` | 4 — Ciência | `REFERENCE_INSUFFICIENT` (`55.6%`) | `ASSETS_INCOMPLETE` (`88.9%`) | `READY_FOR_REVIEW` | `6/6` cenas `ASSET_NEEDED` |
| `#9`, `#10` | 5 — Produtividade | `SCRIPT_NEEDS_REVISION` (`66.7%`) | `ASSETS_INCOMPLETE` (`88.9%`) | `READY_FOR_REVIEW` | `6/6` cenas `ASSET_NEEDED` |

- **Roteiros corrigidos:** `10 / 10` (`8/9` verificações aprovadas, `0` falhas de texto/fontes/repetição).
- **Assets associados automaticamente:** `0` (nenhum ativo local licenciado e tematicamente compatível disponível; vídeos de `benchmark250` mantidos bloqueados).
- **Pacotes prontos (`EDITORIALLY_READY`):** `0` (todos aguardam ativos reais para as 6 cenas e aprovação humana explícita).

---

## 4. Testes, Regressão e Próximos Passos

- **Suíte Fase 24 (`tests/test_fase24_asset_intelligence_and_scripts.py`):** `7 / 7` aprovados (`5.90s`).
- **Regressão Completa (`scripts/run_all_tests.py`):** **`26 / 26` suítes, `213 / 213` testes aprovados (`100.0%`, `0` falhas, `0` erros, `0` skipped, `681.15s`)**.
- **Custos:** `US$ 0,00`.
- **Próximos passos:** Registrar ativos originais ou licenciados (CC0 / CC-BY / acervo próprio) na biblioteca via `/api/production/assets/register` ou dashboard, associar às cenas dos 5 pacotes prioritários e realizar a aprovação humana explícita para liberar a renderização física.
