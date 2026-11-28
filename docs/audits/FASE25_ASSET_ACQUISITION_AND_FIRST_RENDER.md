# VANTIS — FASE 25: AQUISIÇÃO CONTROLADA DE ASSETS, LICENCIAMENTO E PRIMEIRO RENDER DE PRODUÇÃO

**Data:** 2026-11-26  
**Branch:** `develop` (preservando `main`)  
**Custo Efetivo:** `US$ 0,00`

---

## 1. Auditoria do Bloqueio & Seleção do Piloto

- **Estado inicial:** `10` pacotes editoriais (`60` cenas em `ASSET_NEEDED`), `0` vídeos de produção renderizados.
- **Pacote escolhido:** **Pacote `#7` — Canal 4 (`Mente Curiosa & Ciência`)**: *"Por que o céu noturno é escuro mesmo com bilhões de estrelas"*, por possuir narrativa científica consolidada (Paradoxo de Olbers) e ampla disponibilidade de imagens astronômicas reais em Domínio Público (NASA/ESA/Hubble/JWST) e `CC BY-SA 4.0` no Wikimedia Commons.
- **Demais pacotes (`#1–#6`, `#8–#10`):** Mantidos em `READY_FOR_REVIEW` com suas `54` cenas restantes preservadas em `ASSET_NEEDED` (sem preenchimento aleatório nem reuso de `benchmark250`).

---

## 2. Assets Pesquisados, Adquiridos, Rejeitados e Licenças Verificadas

- **Fonte gratuita utilizada:** API pública do **Wikimedia Commons** (`search_wikimedia_commons` + `acquire_wikimedia_asset` em `services/production/asset_intelligence.py`).
- **Assets adquiridos e verificados para o Pacote `#7` (6/6 cenas):**
  1. **Cena 1:** `035 Vertical panorama of the Milky Way during Perseids seen from Oeschinensee Photo by Giles Laurent.jpg` (`1920x2778`, `CC BY-SA 4.0` -> `VERIFIED_CC_BY`, SHA256 `e3caf53a923f...`, atribuição registrada).
  2. **Cena 2:** `A Sampling of Galaxies From the Hubble Ultra Deep Field Image (2004-07-1463).jpg` (`1920x1537`, `Public domain` -> `VERIFIED_PUBLIC_DOMAIN`, SHA256 `92df0a870a8d...`).
  3. **Cena 3:** `Milky Way (colosimo-130705-012).jpg` (`1920x721`, `CC BY-SA 3.0` -> `VERIFIED_CC_BY`, substituiu candidato inicial de fogos de artifício por coerência temática).
  4. **Cena 4:** `Cartwheel Galaxy (NIRCam and MIRI Composite Image) (weic2211a).jpeg` (`1920x1767`, `Public domain` -> `VERIFIED_PUBLIC_DOMAIN`, SHA256 `ad515bc35de4...`).
  5. **Cena 5:** `Center of the Milky Way Galaxy IV – Composite.jpg` (`1920x960`, `Public domain` -> `VERIFIED_PUBLIC_DOMAIN`, SHA256 `2bfa23c86d5b...`).
  6. **Cena 6:** `30 Doradus, Tarantula Nebula.jpg` (`1920x1536`, `Public domain` -> `VERIFIED_PUBLIC_DOMAIN`, SHA256 `9b6a0386366a...`).
- **Rejeição de curadoria:** Candidato `DSC 6198 Bright fireworks burst over a calm sea...` descartado da Cena 3 por baixa aderência ao tema cosmológico (substituído por `Milky Way (colosimo-130705-012).jpg`).
- **Validação editorial do Pacote `#7`:** `EDITORIALLY_READY` (`100.0%`).

---

## 3. Aprovação Humana & Primeiro Vídeo Físico de Produção

- **Aprovação humana explícita:** Concedida pelo usuário antes da renderização (`APPROVED_FOR_PRODUCTION`).
- **Job de Renderização (`render_jobs.id = 1`):**
  - **Arquivo MP4:** `workspace/renders/vantis_ch4_pkg7_job1.mp4`
  - **Status:** **`READY_FOR_REVIEW`** (aguardando revisão humana final no dashboard; **não** marcado como `COMPLETED` e **não** publicado no YouTube)
  - **Resolução:** `1080x1920` (vertical 9:16)
  - **Duração:** `49.4s`
  - **Tamanho físico:** `6,039,692 bytes` (`5.76 MB`)
  - **Codecs:** `h264` (vídeo) / `aac` (áudio)
  - **Loudness medido (EBU R128):** `-14.5 LUFS`
  - **Cenas / Assets / Legendas:** `6` cenas, `6` assets verificados, `40` cues `.ass` sincronizados via Edge-TTS neural (`real_neural`)
  - **SHA256:** `6e0e3380de6fe509bcf0bc0f2c755ad3bae89276c5b289dbb01f678be657caf9`
  - **Decodificação integral (`ffmpeg -v error -i ... -f null -`):** Aprovada (`exit code 0`).

---

## 4. Limitações, Custos e Testes

- **Limitações:** Apenas o Pacote `#7` possui 6/6 cenas preenchidas até o momento; os outros 9 pacotes aguardam aquisição/seleção de ativos próprios ou licenciados e aprovação humana individual. Imagens horizontais são adaptadas para `1080x1920` via `scale+crop` central.
- **Custos:** `US$ 0,00` (Wikimedia Commons gratuito + Edge-TTS + FFmpeg).
- **Suíte Fase 25 (`tests/test_fase25_asset_acquisition_and_render.py`):** `6 / 6` aprovados (`52.96s`).
- **Regressão Completa (`scripts/run_all_tests.py`):** **`27 / 27` suítes, `219 / 219` testes aprovados (`100.0%`, `0` falhas, `0` erros, `0` skipped, `828.61s`)**.
