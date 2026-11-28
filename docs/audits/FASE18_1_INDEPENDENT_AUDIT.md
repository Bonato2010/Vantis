# VANTIS — FASE 18.1 | AUDITORIA INDEPENDENTE + SINCRONIZAÇÃO DA DEVELOP

**Data:** 2026-11-26  
**Repositório:** `C:\Users\jcvse\OneDrive\Desktop\Daniel\CENTRAL SHORTS` (Espelho: `C:\Users\jcvse\podcast_cutter`)  
**Branch Ativa:** `develop` (`main` preservada integralmente)  
**Veredito de Liberação:** **`PASS_WITH_RESERVATIONS`** *(500 vídeos e 7.000 vídeos NÃO iniciados; aguardando autorização explícita)*

---

## 1. Consolidação e Sincronização da `develop` (Etapa 1)

- **Estado inicial verificado:** Branch ativa `develop` no commit `3962ca3` (`ahead 12` de `origin/develop`), working tree limpo, `0` commits novos no remoto (`git rev-list --left-right --count origin/develop...develop` = `0 12`).
- **Push inicial da Fase 18:** `git push origin develop` executado sem force push (`3dd3070..3962ca3`), SHA remoto confirmado via `git ls-remote origin refs/heads/develop` (`3962ca3253532a9af561069dce8727e2a55d9bbf`).
- **`main`:** Preservada intacta (`54052c5` local / `c38c139` no espelho).
- **Nota do remoto:** GitHub informou redirecionamento `Bonato2010/IAS.git` -> `Bonato2010/Vantis.git`.

---

## 2. Auditoria Física dos 250 Vídeos (Etapa 2)

| Métrica | Valor | Status |
|---|---:|---|
| Candidatos selecionados (`phase18_selected_candidates.json`) | 250 | **MEDIDO** |
| Arquivos físicos em `C:\Users\jcvse\OneDrive\Desktop\Daniel\CENTRAL SHORTS\workspace\downloads\benchmark250` | 241 arquivos (`2,067,785,724` bytes / `1,971.99 MB`) | **MEDIDO** |
| Downloads/análises elegíveis verificados no disco e SQLite | 239 / 239 | **MEDIDO** |
| Divergências de tamanho ou SHA256 recalculado | 0 | **MEDIDO** |
| Divergências de `processing_state` (DB vs JSON) | 0 (`232` `learning_candidate`, `7` `editorially_rejected`) | **MEDIDO** |
| Falhas reais no benchmark (10 DNS `getaddrinfo failed` + 1 timeout FFmpeg `za8PcNlFgOE.webm`) | 11 | **FALHOU** (isolado) |
| Transcrições reais verificadas (`full_transcript` + `speech_detected=True`) | 169 / 239 (`70` sem fala) | **MEDIDO** |

- **Caminho físico absoluto base:** `C:\Users\jcvse\OneDrive\Desktop\Daniel\CENTRAL SHORTS\workspace\downloads\benchmark250\ch_{1..5}\<video_id>.<ext>` (ex.: `...\ch_1\gOiQ-zxR-cI.mp4`, `...\ch_5\za8PcNlFgOE.webm`).

---

## 3. Auditoria dos 15 Recursos Editoriais (Etapa 3)

A auditoria independente detectou **incompatibilidade de chaves** em `EditorialFeatureExtractor.extract()`: o extrator buscava `transcript_preview`, `text_on_screen_detected` e `first_cut_timestamp_sec` na raiz, enquanto `process_transcript` e `process_visual` gravam `full_transcript`, `has_subtitles_on_screen` e `cut_intervals_sec`. Por isso, 5 recursos estavam zerados como `NOT_AVAILABLE`.

Após a correção e reextração nos **239** vídeos elegíveis:
- **`239/239` disponíveis (`0 NOT_AVAILABLE`):** `audio_visual_relation`, `avg_cut_interval_sec`, `cuts_count`, `emotional_intensity`, `has_narration`, `scene_variation_rate_per_min`, `text_on_screen_detected`.
- **`222/239` disponíveis (`17 NOT_AVAILABLE`):** `time_to_first_relevant_event_sec`.
- **`169/239` disponíveis (`70 NOT_AVAILABLE`):** `explanation_clarity_score`, `hook_type`, `information_density_wps`, `presentation_speed_wpm`.
- **`154/239` disponíveis (`85 NOT_AVAILABLE`):** `has_conclusion`, `narrative_progression`, `suspense_structure`.

---

## 4. Auditoria dos Aprendizados (Etapa 4)

A auditoria dos registros revelou que vídeos com denominador minúsculo (`1 view + 1 like = 100.0%` de engajamento) inflavam medianas de engajamento (afetando `IDs 143` e `145`). Foi aplicada guarda exigindo `views >= 30` para cálculo confiável de `med_fav_eng` / `med_ctrl_eng` e os 25 padrões (5 recursos × 5 canais) foram reavaliados em `train+val`:

- **5 `APRENDIZADO_VALIDADO`:** `ID 139` (Canal 2 `ritmo_de_cortes_dinamico`), `ID 154` (Canal 3 `progressao_narrativa_completa`), `ID 146` (Canal 5 `estrutura_narrativa_real`), `ID 159` (Canal 5 `gancho_inicial_forte`), `ID 160` (Canal 5 `progressao_narrativa_completa`). Todos possuem 14–15 evidências e 14–15 contraexemplos reais.
- **20 `HIPÓTESE`:** `IDs 137, 138, 140, 141, 142, 143, 144, 145, 147..153, 155..158, 161` mantidos sem promoção prematura.

---

## 5. Auditoria de Leakage e Divisão dos Dados (Etapa 5)

- **Divisão reproduzida:** `train = 168`, `validation = 37`, `test = 34` (total `239` elegíveis).
- **Integridade:** `train_test_id_overlap = 0`, `val_test_id_overlap = 0`, `train_val_id_overlap = 0`, `leak_free = True`.
- Os conhecimentos foram gerados exclusivamente com `train + validation` (`205` vídeos); o conjunto `test` (`34` vídeos) permaneceu intocado até a avaliação final.

---

## 6. Auditoria do Resultado Editorial (Etapa 6)

Reprodução no conjunto `test` disjunto (`n=34`, `overlap=0`, `is_causal_experiment=False`):

| Indicador | Baseline (`cuts >= 1`) | Modelo Atualizado (Fase 18.1) | Status |
|---|---:|---:|---|
| Precisão editorial (`TP / (TP + FP)`) | **42.3%** (`11 / 26`) | **40.0%** (`10 / 25`) | **MEDIDO** |
| Verdadeiros Positivos / Falsos Positivos / Falsos Negativos | `11 / 15 / 4` | `10 / 15 / 5` | **MEDIDO** |
| Recomendações específicas por canal | 0 | **33** | **MEDIDO** |
| Decisões explicadas | 0 | **33** | **MEDIDO** |
| Anti-patterns bloqueados | 0 | **1** | **MEDIDO** |
| Curvas de retenção / CTR do YouTube Analytics | — | — | **NÃO VERIFICADO** |

**Causa raiz da diferença de precisão (42.3% -> 40.0%):** Nos canais sem regra validada (Canais 1 e 4), o modelo atualizado exigiu `has_narration=True AND cuts_count >= 4`, sendo mais restritivo que o baseline (`cuts >= 1`) e deixando 1 vídeo positivo fora (`FN: 4 -> 5`). Não houve ajuste no conjunto de teste para maquiar o resultado.

---

## 7. Memória Editorial e Isolamento dos Canais (Etapa 7)

- Execução independente com `AudiovisualLearningSystem.get_channel_editorial_memory(1..5)` confirmou persistência após reinicialização, vinculação a `evidence_video_ids`, preservação de `classification_history` e **zero contaminação cruzada** entre os 5 canais.

---

## 8. Correções Executadas e Regressão Completa (Etapas 8 e 9)

1. `services/learning/editorial_feature_extractor.py`: Leitura correta de `full_transcript`, `has_subtitles_on_screen` e `cut_intervals_sec`.
2. `services/learning/editorial_memory_engine.py`: Guarda contra denominadores minúsculos (`views >= 30`) no cálculo das medianas de engajamento.
3. `tests/test_fase18_learning_and_benchmark.py`: Adicionados `test_07_extractor_reads_full_transcript_and_has_subtitles_on_screen` e `test_08_micro_denominator_guard_and_channel_memory_persistence`.
4. **Regressão Completa (`python scripts/run_all_tests.py`):** **20 / 20 suítes — 178 / 178 testes aprovados (`100.0%`, `0` falhas, `0` erros, `0` ignorados, `exit code 0`)**.

---

## 9. Veredito de Liberação (Etapa 11)

- **Classificação:** **`PASS_WITH_RESERVATIONS`**
- **Justificativa:** Toda a trilha física (239 arquivos/hashes), extração dos 15 recursos, memória isolada por canal, guarda anti-leakage, regressão `178/178` e sincronização da `develop` foram comprovadas. As ressalvas são: (a) 11 falhas de download/decode no benchmark, (b) precisão editorial em teste (`40.0%`) ainda limitada sem curvas privadas do YouTube Analytics (`NÃO VERIFICADO`) e (c) Canais 1 e 4 sem regras validadas após exclusão de micro-denominadores.
- **Lotes futuros:** Próximo lote de **500 vídeos** e lote de **7.000 vídeos** permanecem **NÃO INICIADOS** aguardando decisão explícita do usuário.
