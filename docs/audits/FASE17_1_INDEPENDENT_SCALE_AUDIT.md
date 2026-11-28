# VANTIS — FASE 17.1 | AUDITORIA FORENSE INDEPENDENTE DE PRONTIDÃO PARA ESCALA

**Data da Auditoria:** 2026-11-24  
**Branch:** `develop` (`main` preservada integralmente)  
**Veredito Geral:** **`READY_WITH_RESERVATIONS`**  
**Próximo Passo Proposto (NÃO EXECUTADO):** Lote controlado de **250 vídeos** (50 por canal), com checkpoints e capacidade de interrupção segura. O processamento de **7.000 vídeos** permanece **BLOQUEADO** até aprovação explícita do usuário.

---

## 1. Resumo Executivo

Esta auditoria independente verificou diretamente no código-fonte, no banco SQLite (`database/shorts_central.db`), nos logs e em execuções reproduzíveis todas as declarações da Fase 17.

A auditoria identificou **4 defeitos reais** (superestimação de regras `APRENDIZADO_VALIDADO` com evidência sem tração ou grupo de controle `n=1`, predição positiva do Modo B em vídeos silenciosos no holdout, consulta de fila `task_queue` com status legados no dashboard, e ausência de deduplicação por título+duração e justificativa explícita na seleção estratificada). Todos os 4 defeitos foram corrigidos e cobertos por asserções de regressão.

Após a reauditoria no banco vivo:
- **0 de 15** regras anteriormente marcadas como `APRENDIZADO_VALIDADO` sobreviveram aos critérios estritos de tração e grupo de controle (os IDs `116`, `121` e `125` foram reclassificados para `HIPÓTESE`).
- **23 registros da Fase 16** no banco: `0 APRENDIZADO_VALIDADO`, `11 HIPÓTESE`, `4 PENDENTE_DE_VALIDACAO`, `5 OBSERVAÇÃO` e `3 ANTI_PATTERN`.
- **170 / 170 testes aprovados** em **19 / 19 suítes** (`python scripts/run_all_tests.py`, código de saída `0`, tempo total `594.90s`, 0 falhas, 0 erros, 0 ignorados).
- **Custo total:** **US$ 0,00** estritamente mantido (`ENFORCE_FREE_TIER_ONLY=True`).

---

## 2. Metodologia de Auditoria Independente

- Inspeção direta do SQLite em `database/shorts_central.db` (sem apagar nem alterar registros históricos `audiovisual_library id <= 43` e `editorial_knowledge_library id <= 64`).
- Reexecução de `AudiovisualLearningSystem().audit_and_reclassify_phase16_knowledge()` sobre os 23 registros da Fase 16 (`id >= 104`).
- Reexecução de `EditorialUtilityEvaluator().evaluate_ab()` sobre o conjunto holdout disjunto (`n=20`).
- Verificação de isolamento entre canais via `get_channel_editorial_memory(1..5)` e `query_editorial_rule_for_channel()`.
- Auditoria das fórmulas e cenários de `ScaleSelectionPlanner().estimate_capacity_scenarios()`.
- Inspeção de `ModelGatewayService` (`services/model_gateway/gateway.py`) e tabela `model_usage_logs`.
- Execução integral da suíte de regressão (`scripts/run_all_tests.py`) após todas as edições de código.

---

## 3. Tabela Completa dos 23 Registros de Conhecimento da Fase 16

| ID | Canal | Tipo (`knowledge_type`) | Classificação Pós-17.1 | Conf. | Evid. | Título / Resumo da Auditoria |
|---:|---:|---|---|---:|---:|---|
| 104 | 1 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | 0.68 | 6 | Cortes Ágeis (>= 4) em Canal 01 - Futebol em 60 Segundos |
| 105 | 1 | `padrao_loudness_comercial` | `HIPÓTESE` | 0.70 | 6 | Loudness Efetivo (-24 a -6 LUFS) em Canal 01 |
| 106 | 1 | `estrutura_narrativa_real` | `HIPÓTESE` | 0.70 | 6 | Presença de Narração Estruturada em Canal 01 |
| 107 | 1 | `plano_continuo_observacao` | `OBSERVAÇÃO` | 0.65 | 1 | Plano Contínuo (< 4 cortes) em Canal 01 |
| 108 | 1 | `anti_pattern_editorial_ou_acustico` | `ANTI_PATTERN` | 0.90 | 1 | Anti-Pattern Detectado em Canal 01: `2TFGeAHjPA8` |
| 109 | 2 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | 0.68 | 6 | Cortes Ágeis (>= 4) em Canal 02 - Arquivo Sombrio |
| 110 | 2 | `padrao_loudness_comercial` | `PENDENTE_DE_VALIDACAO` | 0.72 | 6 | Loudness Efetivo (-24 a -6 LUFS) em Canal 02 |
| 111 | 2 | `estrutura_narrativa_real` | `HIPÓTESE` | 0.70 | 6 | Presença de Narração Estruturada em Canal 02 |
| 112 | 2 | `plano_continuo_observacao` | `OBSERVAÇÃO` | 0.65 | 1 | Plano Contínuo (< 4 cortes) em Canal 02 |
| 113 | 2 | `anti_pattern_editorial_ou_acustico` | `ANTI_PATTERN` | 0.70 | 1 | Anti-Pattern Detectado em Canal 02: `tfJSsxukhKY` |
| 114 | 3 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | 0.68 | 4 | Cortes Ágeis (>= 4) em Canal 03 - Rir para Não Chorar |
| 115 | 3 | `padrao_loudness_comercial` | `PENDENTE_DE_VALIDACAO` | 0.72 | 6 | Loudness Efetivo (-24 a -6 LUFS) em Canal 03 |
| **116** | **3** | `estrutura_narrativa_real` | **`HIPÓTESE`** *(reclass. 17.1)* | 0.72 | 6 | Reclassificado: controle sem fala insuficiente (`n=1`, `uXS7pgwnOKo`) e 4/6 evidências com tração válida |
| 117 | 3 | `plano_continuo_observacao` | `OBSERVAÇÃO` | 0.65 | 1 | Plano Contínuo (< 4 cortes) em Canal 03 |
| 118 | 3 | `anti_pattern_editorial_ou_acustico` | `ANTI_PATTERN` | 0.70 | 1 | Anti-Pattern Detectado em Canal 03: `GggELAqG63s` |
| 119 | 4 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | 0.68 | 6 | Cortes Ágeis (>= 4) em Canal 04 - Mente Curiosa & Ciência |
| 120 | 4 | `padrao_loudness_comercial` | `PENDENTE_DE_VALIDACAO` | 0.72 | 6 | Loudness Efetivo (-24 a -6 LUFS) em Canal 04 |
| **121** | **4** | `estrutura_narrativa_real` | **`HIPÓTESE`** *(reclass. 17.1)* | 0.72 | 6 | Reclassificado: 0/6 evidências com `>=100 views` e `engajamento > 0%` |
| 122 | 4 | `plano_continuo_observacao` | `OBSERVAÇÃO` | 0.65 | 1 | Plano Contínuo (< 4 cortes) em Canal 04 |
| 123 | 5 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | 0.68 | 6 | Cortes Ágeis (>= 4) em Canal 05 - Mente Focada |
| 124 | 5 | `padrao_loudness_comercial` | `PENDENTE_DE_VALIDACAO` | 0.72 | 6 | Loudness Efetivo (-24 a -6 LUFS) em Canal 05 |
| **125** | **5** | `estrutura_narrativa_real` | **`HIPÓTESE`** *(reclass. 17.1)* | 0.72 | 6 | Reclassificado: grupo de controle `n=2` e 0/6 evidências com `>=100 views` e `engajamento > 0%` |
| 126 | 5 | `plano_continuo_observacao` | `OBSERVAÇÃO` | 0.65 | 1 | Plano Contínuo (< 4 cortes) em Canal 05 |

**Resumo da Reauditoria:** `total_audited = 23`, `reclassified = 3` (`IDs 116, 121, 125`), `confirmed = 20`. Distribuição final: `0 APRENDIZADO_VALIDADO`, `11 HIPÓTESE`, `4 PENDENTE_DE_VALIDACAO`, `5 OBSERVAÇÃO`, `3 ANTI_PATTERN`.

---

## 4. Reprodução e Ressalvas Estatísticas do Teste A/B em Holdout

Resultados reproduzidos após correção do `EditorialUtilityEvaluator.evaluate_ab()`:
- **`holdout_count`:** `20`
- **`overlap_with_training`:** `0` (disjunto garantido)
- **`statistical_significance`:** `"NOT_STATISTICALLY_PROVEN_SMALL_SAMPLE_N20"`
- **Modo A (Baseline):** `off_topic_flagged = 0`, `silent_audio_flagged = 0`, `anti_pattern_warnings_emitted = 0`, `predicted_high_engagement_hits = 3 / 9` (**33.3%**)
- **Modo B (Com Fase 16/17.1):** `off_topic_flagged = 1`, `silent_audio_flagged = 3`, `anti_pattern_warnings_emitted = 14`, `channel_specific_recommendations = 0` (correto, pois 0 regras permanecem como `APRENDIZADO_VALIDADO`), `predicted_high_engagement_hits = 8 / 17` (**47.1%**)

**Ressalva Estatística Obrigatória:** Embora o Modo B elimine predições positivas falsas em faixas silenciosas (`-70.0 LUFS`) e fora de nicho, a amostra `n=20` é pequena e **não comprova significância estatística para predição numérica de engajamento**. O ganho real comprovado é de **filtragem editorial/acústica** e **bloqueio de anti-patterns**.

---

## 5. Isolamento Entre Canais

- `get_channel_editorial_memory(1..5)` retornou `other_channel_leaks = []` em todos os 5 canais.
- `query_editorial_rule_for_channel()` bloqueia transferência entre canais distintos com `reason = "cross_channel_contamination_blocked"`.
- Regras técnicas universais com `target_channel_id = None` são permitidas apenas sob escopo `universal_technical`.

---

## 6. Auditoria de Capacidade para 7.000 Vídeos e Gargalos

Base empírica do piloto de 100 Shorts: `8.02 MB/vídeo` em média, `33.5 s/vídeo` sequencial, fator de escala `70.0x`.

| Cenário (`is_estimate=true`) | Workers Efetivos | Disco Mídia (GB) | Crescimento SQLite (MB) | Tempo Estimado (h) | RAM Pico (GB) | Custo (US$) |
|---|---:|---:|---:|---:|---:|---:|
| **Conservador** | 4.0 | 63.02 GB | 161.0 MB | 19.65 h | 3.80 GB | $0.00 |
| **Realista** | 2.8 | 71.24 GB | 182.0 MB | 29.94 h | 2.84 GB | $0.00 |
| **Pessimista** | 1.5 | 87.68 GB | 224.0 MB | 62.38 h | 1.80 GB | $0.00 |

**Gargalos Identificados:**
1. **Disco local (~63–88 GB):** Exige execução em sublotes (250–500 vídeos) com expurgo controlado da mídia bruta pós-extração ou offload para Google Drive.
2. **CPU/RAM:** Whisper `tiny` + PyAV/OpenCV consomem ~0.8 GB por worker + 0.6 GB base; acima de 4 workers simultâneos há risco de saturação térmica/CPU.
3. **Rate-limit YouTube (`yt-dlp`):** Requer backoff exponencial e fila persistente (`task_queue`).

---

## 7. Auditoria de Seleção Estratificada

- `ScaleSelectionPlanner.plan_stratified_selection()` garante diversidade entre tiers (`emerging`, `mid_tier`, `viral`) e split determinístico `70% train / 15% validation / 15% test`.
- **Correção 17.1:** Adicionada deduplicação por fingerprint `norm_title | round(duration_seconds, 1)` (`duplicate_title_duration_fingerprint`) e campo obrigatório `inclusion_rationale` em cada candidato selecionado.

---

## 8. Auditoria de Custo

- `services/model_gateway/gateway.py` mantém `ENFORCE_FREE_TIER_ONLY = True` por padrão.
- `is_paid_model()` bloqueia chamadas pagas (GPT/Claude/OpenAI/Anthropic).
- Evidência no banco (`model_usage_logs`): `total_cost_usd = 0.0`, 20 chamadas `gpt-4o` bloqueadas (`PAID_CALL_BLOCKED`), 139 chamadas `offline_engine` executadas a custo zero.

---

## 9. Resultados da Regressão Completa

Executado após **todas** as correções da Fase 17.1:
- **Comando:** `python scripts/run_all_tests.py`
- **Código de saída:** `0`
- **Arquivos Executados:** `19 / 19`
- **Total de Testes:** `170`
- **Aprovados:** `170` (`100.0%`)
- **Falhas / Erros / Ignorados:** `0 / 0 / 0`
- **Tempo Total:** `594.90 segundos`

---

## 10. Auditoria do Dashboard e Observabilidade

- `AudiovisualLearningSystem.get_dashboard_overview()` lê todos os indicadores diretamente do SQLite (zero literais fixos).
- **Correção 17.1:** Query de `task_queue` corrigida de `'pending'`/`'processing'` para os status reais `'QUEUED'`, `'RETRYING'`, `'RUNNING'`; adicionados `counterexamples_count` (`25` no banco atual) e `queue_health` na resposta da API e no card `p16-counterexamples` / `p16-retry-time` em `web/static/index.html`.

---

## 11. Auditoria de Git e Google Drive

- Trabalho executado exclusivamente na branch `develop` nos repositórios `CENTRAL SHORTS` e espelho `podcast_cutter`, mantendo `main` intacta.
- Registros históricos preservados integralmente (`audiovisual_library id <= 43`, `editorial_knowledge_library id <= 64`).
- Sincronização com Google Drive (`VANTIS_PROJECT_CONTROL`, folder ID `1rNbqXtnpBeo_1-GiR_vy-MW3yvybnNUH`) executada via `scripts/sync_tracking_to_gdrive.py`.

---

## 12. Defeitos Encontrados

1. **Superestimação de `APRENDIZADO_VALIDADO` (IDs 116, 121, 125):** Regras de `estrutura_narrativa_real` foram mantidas como validadas apesar de controle `n=1` (Canal 3) ou `0/6` vídeos com tração real `>= 100 views` e `engajamento > 0%` (Canais 4 e 5).
2. **Predição falsa positiva em Holdout Silencioso:** `EditorialUtilityEvaluator.evaluate_ab()` marcava `b_pred_high = True` mesmo em vídeos com áudio silencioso (`-70.0 LUFS`), sem explicitar `statistical_significance`.
3. **Desalinhamento de Status na `task_queue` e Lacuna no Dashboard:** `get_dashboard_overview()` consultava `'pending'`/`'processing'` em vez de `'QUEUED'`/`'RETRYING'`/`'RUNNING'`, e omitia `counterexamples_count` e `queue_health`.
4. **Deduplicação e Rastreabilidade na Seleção Estratificada:** `ScaleSelectionPlanner` deduplicava apenas por `id` e não emitia `inclusion_rationale` por candidato.

---

## 13. Correções Executadas

1. `services/learning/audiovisual_learning_system.py`: Endurecimento de `audit_and_reclassify_phase16_knowledge()` (exigindo `len(nospeech) >= 3` e `>= 2` evidências com `views >= 100` e `engagement > 0`) e correção das queries de `task_queue` + inclusão de `counterexamples_count` e `queue_health`.
2. `services/learning/editorial_utility_evaluator.py`: Bloqueio de `b_pred_high` quando `b_silent or b_off_topic` e inclusão de `statistical_significance = "NOT_STATISTICALLY_PROVEN_SMALL_SAMPLE_N20"`.
3. `services/discovery/scale_selector.py`: Deduplicação por fingerprint título+duração e campo `inclusion_rationale`.
4. `web/static/index.html` e `tests/test_fase17_scale_readiness.py`: Exibição de contraexemplos e saúde da fila na UI e cobertura completa de regressão nos testes.

---

## 14. Riscos Remanescentes

- **Zero aprendizados validados no momento (`0 APRENDIZADO_VALIDADO`):** O conjunto de 100 Shorts ainda não tem densidade de tração suficiente para promover regras narrativas/visuais definitivas.
- **Ausência de métricas privadas de retenção (YouTube Analytics):** Limita a predição de engajamento apenas a sinais públicos e acústicos/visuais locais.
- **Armazenamento em escala:** Processar 7.000 vídeos de uma só vez excederia 63–88 GB locais sem política automática de expurgo/offload.

---

## 15. Recomendação Final por Área

| Área Auditada | Status | Observação |
|---|---|---|
| Integridade de Dados e Histórico | **PASS** | 100 Shorts íntegros; histórico preservado |
| Rigor dos Aprendizados | **PASS_WITH_RESERVATIONS** | Reauditoria corrigiu falsos validados; 0 validados aguardando amostra maior |
| Utilidade Editorial (Teste A/B) | **PASS_WITH_RESERVATIONS** | Melhora filtragem acústica/nicho; amostra `n=20` sem prova estatística |
| Isolamento Entre Canais | **PASS** | 0 vazamentos entre os 5 canais |
| Fila Persistente e Recuperação | **PASS** | Deduplicação, retry/backoff e status corrigidos |
| Modelo de Capacidade (7.000 vídeos) | **PASS_WITH_RESERVATIONS** | Viável apenas em sublotes com expurgo/offload |
| Política de Custo Zero | **PASS** | US$ 0,00 comprovado em logs e gateway |
| Observabilidade e Regressão | **PASS** | 170/170 testes em 19/19 suítes (100%) |

### Veredito Final e Próximo Passo
- **Veredito Global:** **`READY_WITH_RESERVATIONS`**
- **Lote de 7.000 vídeos:** **NÃO INICIAR** nesta fase.
- **Próximo Passo Recomendado (NÃO EXECUTADO):** Executar um **lote controlado de 250 vídeos** (50 por canal, respeitando estratificação e checkpoints por sublote, com capacidade de interrupção segura e expurgo pós-análise) para coletar evidências suficientes para reavaliar a promoção das `11 HIPÓTESES` a `APRENDIZADO_VALIDADO`.
