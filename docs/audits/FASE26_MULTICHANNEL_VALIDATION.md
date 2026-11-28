# VANTIS — FASE 26: VALIDAÇÃO EDITORIAL DO PRIMEIRO RENDER E REPLICAÇÃO CONTROLADA NOS 5 CANAIS

**Data:** 2026-11-27  
**Branch:** `develop` (preservando `main`)  
**Custo Efetivo:** `US$ 0,00`

---

## 1. Auditoria do Primeiro Vídeo (`vantis_ch4_pkg7_job1.mp4`)

- **Arquivo auditado:** `workspace/renders/vantis_ch4_pkg7_job1.mp4` (Pacote `#7`, Canal 4 — Ciência).
- **Integridade técnica:** `6,039,692 bytes`, `49.4s`, `1080x1920`, `h264`/`aac`, `-14.5 LUFS`, `40` cues `.ass`, `SHA256=6e0e3380de6fe509bcf0bc0f2c755ad3bae89276c5b289dbb01f678be657caf9`, decodificação integral `ffmpeg` sem erros (`RC=0`).
- **Inspeção visual dos 6 frames extraídos:**
  - Cenas 1, 3, 4, 5 e 6 aprovadas visualmente (enquadramento 9:16 limpo, legendas ASS nítidas em zona segura inferior).
  - **Defeito real encontrado na Cena 2 (`t=12s`):** A imagem `A Sampling of Galaxies From the Hubble Ultra Deep Field Image (2004-07-1463).jpg` era uma prancha com moldura branca e legenda em inglês cortada (`"Hubble Ultra Deep Field Details..."`), poluindo o visual abaixo das legendas em português.
- **Defeito crítico descoberto nos testes multicanal (`services/media_processing/tts_engine.py`):**
  - As vozes `pt-BR-JulioNeural` (Canal 2), `pt-BR-FabioNeural` (Canal 3) e `pt-BR-ValerioNeural` (Canal 5) foram descontinuadas na API Edge-TTS da Microsoft, restando ativas apenas `pt-BR-AntonioNeural`, `pt-BR-FranciscaNeural` e `pt-BR-ThalitaMultilingualNeural`.
- **Falha de teste legado corrigida (`tests/test_fase8_vantis_pipeline.py` + `services/semantic_memory/vector_memory.py`):**
  - Desempate por recência em `search_similar` e `top_k=500` para evitar saturação do `top_k=50` pelo histórico acumulado no banco vetorial.

---

## 2. Correções Realizadas

1. **Cena 2 do Pacote `#7`:** Registrada revisão humana no `job1` (`REQUEST_CHANGES`, defeito `images`), substituída a Cena 2 por `Hubble sees galaxies galore.jpg` (`VERIFIED_PUBLIC_DOMAIN`, `1920x1920`, sem moldura/texto) e gerado novo render `job2` (`vantis_ch4_pkg7_job2.mp4`), validado visualmente em `t=12s`.
2. **Vozes Edge-TTS dos 5 canais (`services/media_processing/tts_engine.py`):** Mapeamento atualizado para vozes `pt-BR` ativas (`AntonioNeural`, `FranciscaNeural`, `ThalitaMultilingualNeural`) com variações de `rate`/`pitch` por canal + retry automático com fallback ativo antes do `mock_fallback`.
3. **Estados de revisão & clareza no dashboard (`services/production/package_renderer.py`, `web/static/index.html`):** Suporte explícito a `APPROVED_AFTER_REVIEW` (distinguindo `READY_FOR_REVIEW`, `APPROVED_AFTER_REVIEW`, `CHANGES_REQUESTED`, `REJECTED`) e exibição separada no dashboard de: pacote preparado, pacote aprovado, vídeo renderizado, validado tecnicamente e aprovado após revisão.

---

## 3. Estado Editorial do Piloto Multicanal (5 Canais)

| Canal | Pacote | Estado Editorial | Assets Associados | Licenças & Atribuições | Aprovação Humana | Renders Físicos |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Futebol** | `#1` | `ASSETS_INCOMPLETE` (`88.9%`) | `4 / 6` (faltam cenas 1 e 3) | `3 VERIFIED_CC_BY` + `1 VERIFIED_CC0` | Pendente (`READY_FOR_REVIEW`) | `0` (bloqueado) |
| **2. Arquivo Sombrio** | `#3` | `ASSETS_INCOMPLETE` (`88.9%`) | `2 / 6` (faltam cenas 1, 4, 5, 6; revisar ícone da cena 3) | `2 VERIFIED_CC_BY` | Pendente (`READY_FOR_REVIEW`) | `0` (bloqueado) |
| **3. Humor** | `#5` | `ASSETS_INCOMPLETE` (`88.9%`) | `0 / 6` | — | Pendente (`READY_FOR_REVIEW`) | `0` (bloqueado) |
| **4. Ciência** | `#7` | **`EDITORIALLY_READY` (`100.0%`)** | **`6 / 6`** | `4 VERIFIED_PUBLIC_DOMAIN` + `2 VERIFIED_CC_BY` (atribuições registradas) | **`APPROVED_FOR_PRODUCTION`** (usuário) | **`2` renders (`job1` substituído por `job2` em `READY_FOR_REVIEW`)** |
| **5. Produtividade** | `#9` | `ASSETS_INCOMPLETE` (`88.9%`) | `0 / 6` | — | Pendente (`READY_FOR_REVIEW`) | `0` (bloqueado) |

---

## 4. Detalhes dos Renders Físicos Produzidos (Pacote `#7`, Canal 4)

- **Render Atual Corrigido (`render_jobs.id = 2`):**
  - **Caminho:** `workspace/renders/vantis_ch4_pkg7_job2.mp4`
  - **Status:** `READY_FOR_REVIEW` (aguardando revisão humana final; não publicado no YouTube)
  - **Duração / Tamanho:** `49.4s` | `6,288,263 bytes` (`6.00 MB`)
  - **Resolução / Codecs:** `1080x1920` (9:16) | `h264` / `aac`
  - **Loudness (EBU R128):** `-14.5 LUFS` | `6` cenas | `40` legendas `.ass`
  - **SHA256:** `7e9bd957f558ecab88f182a65f5751ba094634ea84060b90a2cec23bcf69d844`
- **Render Inicial (`render_jobs.id = 1`, preservado no histórico como `CHANGES_REQUESTED`):**
  - `workspace/renders/vantis_ch4_pkg7_job1.mp4` (`6,039,692 bytes`, `49.4s`, `SHA256=6e0e3380de6fe509bcf0bc0f2c755ad3bae89276c5b289dbb01f678be657caf9`).

---

## 5. Testes, Regressão, Custos e Próxima Recomendação

- **Suíte Fase 26 (`tests/test_fase26_multichannel_validation.py`):** `5 / 5` aprovados (`104.02s`).
- **Regressão Completa (`scripts/run_all_tests.py`):** **`28 / 28` suítes, `224 / 224` testes aprovados (`100.0%`, `0` falhas, `0` erros, `0` skipped, `1018.89s`)**.
- **Custos efetivos:** `US$ 0,00`.
- **Pendências reais:** Completar assets legítimos para `#1` (faltam 2), `#3` (faltam 4), `#5` (faltam 6) e `#9` (faltam 6), além da aprovação humana final do `job2` (`APPROVED_AFTER_REVIEW`) no dashboard.
- **Próxima recomendação técnica:** Integrar conector gratuito opcional de API Pexels/Pixabay (com chave gratuita de ambiente) ou upload em lote de acervo próprio no dashboard para destravar cenas cotidianas dos Canais 3 (Humor) e 5 (Produtividade), onde o Wikimedia Commons tem baixa cobertura fotográfica.
