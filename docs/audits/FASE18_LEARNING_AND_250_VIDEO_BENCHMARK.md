# VANTIS — FASE 18 | APRENDIZADO EDITORIAL REAL, MEMÓRIA EVOLUTIVA E BENCHMARK DE 250 VÍDEOS

**Data:** 2026-11-26  
**Branch:** `develop` (`main` preservada integralmente)  
**Custo Total:** **US$ 0,00** (`ENFORCE_FREE_TIER_ONLY = True`)  
**Regressão Completa:** **20 / 20 suítes — 176 / 176 testes aprovados (`100.0%`, `564.98s`, `exit code 0`)**  
**Próximo Passo Recomendado (NÃO INICIADO):** Lote controlado de **500 vídeos** (100 por canal, com checkpoints e expurgo pós-extração). O processamento de **7.000 vídeos** permanece **BLOQUEADO** até autorização explícita.

---

## 1. Resumo Executivo

A Fase 18 executou o ciclo completo de aprendizado editorial real do VANTIS a partir de **250 YouTube Shorts reais** (50 por canal), extraindo características audiovisuais e narrativas reais (`EditorialFeatureExtractor`), aplicando divisão estratificada anti-vazamento **70/15/15** (`train=168`, `validation=37`, `test=34`), evoluindo a memória editorial (`EditorialMemoryEngine`) e validando a utilidade antes e depois no conjunto de teste disjunto.

Ao final da Fase 18, o VANTIS passou de **0** para **3 aprendizados validados (`APRENDIZADO_VALIDADO`)** sustentados por lift positivo simultâneo em engajamento e views relativas com contraexemplos documentados, mantendo **7 correlações fracas ou mistas honestamente como `HIPÓTESE`**.

---

## 2. Distribuição dos Vídeos por Canal

| Canal | Nicho | Selecionados | Aprovados (`learning_candidate`) | Rejeitados (`editorially_rejected`) | Falhas (`failed`) | Fala Transcrita | Áudio Silencioso (`-70 LUFS`) |
|---:|---|---:|---:|---:|---:|---:|---:|
| **1** | Futebol (`futebol_outros`) | 50 | 47 | 3 | 0 | 32 | 3 |
| **2** | Arquivo Sombrio (`casos_policiais`) | 50 | 49 | 1 | 0 | 39 | 1 |
| **3** | Humor (`humor`) | 50 | 39 | 1 | 10 | 29 | 1 |
| **4** | Ciência (`curiosidades`) | 50 | 49 | 1 | 0 | 31 | 1 |
| **5** | Produtividade (`desenvolvimento_pessoal`) | 50 | 48 | 1 | 1 | 38 | 1 |
| **Total** | **5 Canais** | **250** | **232** | **7** | **11** | **169** | **7** |

---

## 3. Integridade dos Arquivos

- **239 / 250** vídeos baixados e decodificados com sucesso (`SHA256` 64 caracteres, FFprobe duração `<= 60s`, decodificação FFmpeg `-v error -f null -` e amostragem OpenCV).
- **11 falhas reais registradas:** 10 falhas transitórias de DNS (`getaddrinfo failed`) no Canal 3 durante oscilação de rede e 1 timeout de decodificação FFmpeg (`45s`) em arquivo `.webm` no Canal 5 (`za8PcNlFgOE`), todas isoladas via `CentralOperationsController` sem interromper o lote.
- **Deduplicação:** `0` sobreposições com os 143 vídeos históricos e `0` duplicatas entre canais (`duplicates_removed = []`).
- **Armazenamento físico:** `1,998,741,151 bytes` (**1,906.15 MB** / ~1.86 GB) em `workspace/downloads/benchmark250/ch_{1..5}/`.

---

## 4. Resultados da Análise Audiovisual

- **Transcrição Real (Faster-Whisper `tiny` CPU / legendas):** `169 / 239` elegíveis com fala real transcrita; vídeos sem fala receberam estado explícito sem placeholders.
- **Acústica (FFmpeg EBU R128 `-vn`):** `7` faixas silenciosas (`-70.0 LUFS`, `SILENT_AUDIO_TRACK`) detectadas e rejeitadas automaticamente (`editorially_rejected`).
- **Visual (PySceneDetect `pyav` + OpenCV):** Contagem real de cortes, intervalo médio entre cortes, movimento e detecção de texto na tela por Sobel.

---

## 5. Características Extraídas (`EditorialFeatureExtractor`)

Cada vídeo elegível recebeu vetor estruturado de **15 características reais** (`services/learning/editorial_feature_extractor.py`): `hook_type`, `time_to_first_relevant_event_sec`, `cuts_count`, `avg_cut_interval_sec`, `has_narration`, `information_density_wps`, `scene_variation_rate_per_min`, `text_on_screen_detected`, `suspense_structure`, `narrative_progression`, `explanation_clarity_score`, `emotional_intensity`, `presentation_speed_wpm`, `has_conclusion`, `audio_visual_relation`. Campos sem evidência física registram explicitamente **`NOT_AVAILABLE`** (nunca `0` sintético).

---

## 6. Conhecimentos Novos Gerados

Foram gerados **10 novos registros de conhecimento** (`IDs 137..146` em `editorial_knowledge_library`, `pilot_phase: 18`), exclusivamente a partir dos conjuntos `train + validation` (`205` vídeos), com zero contato com o conjunto `test` (`34` vídeos):

| ID | Canal | Característica | Classificação | Conf. | Evid. / Contraex. | Lift Positivo Real |
|---:|---|---|---|---:|---:|---|
| 137 | 1 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | 0.45 | 15 / 15 | Não (`med_eng 0.92% vs 1.84%`) |
| 138 | 1 | `estrutura_narrativa_real` | `HIPÓTESE` | 0.45 | 15 / 15 | Não (`med_eng 1.11% vs 1.67%`) |
| 139 | 2 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | 0.45 | 15 / 15 | Não (`med_eng 0.88% vs 1.61%`) |
| 140 | 2 | `estrutura_narrativa_real` | `HIPÓTESE` | 0.68 | 15 / 14 | Parcial (`rel_views 0.838x vs 1.8035x`) |
| 141 | 3 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | 0.45 | 15 / 14 | Não (`med_eng 1.03% vs 4.18%`) |
| 142 | 3 | `estrutura_narrativa_real` | `HIPÓTESE` | 0.45 | 15 / 15 | Não (`med_eng 1.05% vs 2.35%`) |
| **143** | **4** | `ritmo_de_cortes_dinamico` | **`APRENDIZADO_VALIDADO`** | **0.92** | 15 / 15 | **Sim** (`med_eng 6.055% vs 1.31%`; `rel 1.7775x vs 0.667x`) |
| 144 | 4 | `estrutura_narrativa_real` | `HIPÓTESE` | 0.68 | 15 / 15 | Parcial (`rel_views 0.861x vs 6.222x`) |
| **145** | **5** | `ritmo_de_cortes_dinamico` | **`APRENDIZADO_VALIDADO`** | **0.92** | 15 / 15 | **Sim** (`med_eng 2.47% vs 0.0%`; `rel 2.308x vs 0.615x`) |
| **146** | **5** | `estrutura_narrativa_real` | **`APRENDIZADO_VALIDADO`** | **0.92** | 15 / 15 | **Sim** (`med_eng 3.06% vs 0.0%`; `rel 1.2305x vs 0.7695x`) |

---

## 7. Conhecimentos Validados

**3 conhecimentos validados** (`IDs 143, 145, 146`) atenderam simultaneamente: `>= 5` evidências acima da mediana no `train+val`, `>= 3` contraexemplos/controle e lift positivo estrito em engajamento (`med_fav_eng > med_ctrl_eng`) sem colapso de views relativas (`med_fav_rel >= 0.9 * med_ctrl_rel`).

---

## 8. Hipóteses

**7 novas hipóteses (`IDs 137..142, 144`)** foram mantidas como `HIPÓTESE` porque apresentaram ganho apenas em views relativas ou engajamento inferior ao controle, impedindo promoção prematura de correlações fracas.

---

## 9. Contraexemplos

Todos os 10 conhecimentos possuem de **14 a 15 contraexemplos** reais vinculados em `metadata.counterexamples` (vídeos com a característica aplicada mas baixo desempenho, ou grupo controle com desempenho superior).

---

## 10. Conhecimentos Rejeitados / Contradições

- **1 contradição detectada e preservada:** `ID 116` (Canal 3, `estrutura_narrativa_real`) foi reavaliado contra o novo ciclo (`ID 132/142`) e mantido como `HIPÓTESE` com histórico registrado em `metadata.classification_history` (`med_eng(fav)=1.05% vs med_eng(ctrl)=2.35%`).
- **7 vídeos rejeitados na triagem editorial/acústica** por áudio silencioso (`-70.0 LUFS`).

---

## 11. Evolução da Memória Editorial

`EditorialMemoryEngine` (`services/learning/editorial_memory_engine.py`) distingue dados brutos, 15 características extraídas, hipóteses, conhecimentos validados, contraexemplos e recomendações por canal, mantendo `0` vazamentos entre os 5 canais (`other_channel_leaks = 0` em todos os canais).

---

## 12. Comparação Baseline vs Sistema Atualizado (Split `test` Disjunto, `n=34`, `overlap=0`)

- **Amostra:** `34` vídeos independentes (`15%` test split; `train+val = 205`, `overlap_with_training = 0`).
- **Baseline (regra simples `cuts >= 1`):** `TP=11`, `FP=15`, `FN=4`, Precisão = **42.3%**, `anti_patterns_blocked = 0`, `channel_specific_recommendations = 0`.
- **Sistema Atualizado (Fase 18):** `TP=9`, `FP=15`, `FN=6`, Precisão = **37.5%**, `anti_patterns_blocked = 1`, `channel_specific_recommendations = 33`, `decisions_explained = 33`.
- **Nota Metodológica:** `is_causal_experiment = False`. Trata-se de avaliação observacional retrospectiva; com apenas 3 regras validadas nos Canais 4 e 5, a predição numérica de engajamento por sinais públicos continua limitada pela ausência de curvas de retenção do YouTube Analytics, enquanto a capacidade de **bloqueio de anti-patterns** e **explicabilidade por canal** (`33/33`) evoluiu de `0` para operacional.

---

## 13. Resultados do Benchmark e Regressão

- **Benchmark 250 Vídeos:** `250/250` processados (`232` aprovados, `7` rejeitados, `11` falhas isoladas), **retomada comprovada via checkpoint** (`resumed_from_checkpoint_count = 225` após interrupções por `+0.1 LUFS` e timeout FFmpeg `45s`, sem duplicar arquivos ou registros), `avg_seconds_per_video = 49.43s` no trecho final, throughput `1.21 vídeos/min`.
- **Regressão Completa (`scripts/run_all_tests.py`):** **20 / 20 suítes — 176 / 176 testes aprovados (`100.0%`, `564.98s`, `exit code 0`)**, incluindo `tests/test_fase18_learning_and_benchmark.py` (`6/6`).

---

## 14. Consumo de Recursos

- **Tempo de CPU (trecho retomado):** `2,357.06s` CPU / `1,235.70s` wall-clock.
- **Armazenamento:** `1,906.15 MB` de mídia + `4.82 MB` no SQLite `database/shorts_central.db`.
- **RAM:** Medição de `WorkingSetSize` via `psapi` retornou `0.0 MB` no trecho inicial antes da correção para `K32GetProcessMemoryInfo` (registrado honestamente como limitação de telemetria deste lote).

---

## 15. Custos

- **US$ 0,00** estritamente mantido (`ENFORCE_FREE_TIER_ONLY = True`), zero chamadas a APIs comerciais pagas, zero publicação automática.

---

## 16. Problemas Encontrados

1. `MediaDownloader.download_short()` falhava ao extrair ID de URLs `/watch?v=<id>` (retornava `"watch"`).
2. `process_audio()` rejeitava Shorts reais masterizados acima de `0.0 LUFS` (ex.: `+0.1 LUFS`).
3. `verify_ffmpeg_decode()` não tratava `subprocess.TimeoutExpired` em arquivo `.webm` travado (`za8PcNlFgOE`).
4. Critério inicial `positive_lift = eng OR rel_views` promovia correlações fracas onde engajamento caía.

---

## 17. Correções Executadas

1. `services/media_processing/media_downloader.py`: Suporte a `urlparse`/`parse_qs` para `/watch?v=`, `/shorts/` e `youtu.be/`.
2. `services/learning/audiovisual_learning_system.py`: Limite de `estimated_lufs` ajustado para `-70.0 a +5.0 LUFS`, mais `pilot_fase18_metrics` com rótulos `MEDIDO` / `ESTIMADO` / `NÃO_VERIFICADO`.
3. `scripts/execute_benchmark_250_shorts.py`: Captura de `subprocess.TimeoutExpired` em `verify_ffmpeg_decode()` e uso de `K32GetProcessMemoryInfo`.
4. `services/learning/editorial_memory_engine.py`: Critério estrito `med_fav_eng > med_ctrl_eng and med_fav_rel >= 0.9 * med_ctrl_rel`.
5. `web/static/index.html` e `tests/test_fase18_learning_and_benchmark.py`: Painel de transparência Fase 18 e 6 testes dedicados.

---

## 18. Limitações

- Ausência de métricas privadas de retenção/CTR do YouTube Analytics (`NÃO_VERIFICADO`).
- Canal 3 teve 10 falhas transitórias de DNS durante oscilação momentânea da rede.
- Apenas Canais 4 e 5 atingiram regras `APRENDIZADO_VALIDADO` nesta amostra; Canais 1, 2 e 3 permanecem em `HIPÓTESE`.

---

## 19. Recomendação para a Próxima Fase

- **Veredito:** VANTIS validou o ciclo completo de aprendizado evolutivo e retomada segura no benchmark de 250 vídeos a custo **$0.00**.
- **Próximo Lote Proposto (NÃO INICIADO):** Lote controlado de **500 vídeos** (100 por canal), com checkpoints a cada 10 vídeos, expurgo/offload de mídia bruta pós-extração e foco nos Canais 1, 2 e 3 para confirmar ou descartar as 7 hipóteses restantes.
- **Lote de 7.000 vídeos:** Permanece **BLOQUEADO** até autorização explícita do usuário.
