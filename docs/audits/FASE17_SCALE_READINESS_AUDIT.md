# VANTIS — FASE 17: AUDITORIA DE ESCALA, VALIDAÇÃO DOS APRENDIZADOS E PREPARAÇÃO PARA 7.000 VÍDEOS

**Data de Auditoria:** 24 de Novembro de 2026  
**Ambiente:** Antigravity IDE (`branch: develop`, repositório principal `CENTRAL SHORTS / IAS` e espelho `podcast_cutter`)  
**Classificação Final:** **`READY_WITH_RESERVATIONS`**  
**Execução de 7.000 Vídeos:** **BLOQUEADA / NÃO INICIADA NESTA FASE**  
**Custo Real Incorrido:** **\$0.00**  

---

## 1. AUDITORIA DOS 23 APRENDIZADOS DA FASE 16

Todos os 23 registros de conhecimento gerados na Fase 16 (`pilot_phase: 16`) foram auditados individualmente quanto à sustentação empírica real (`engagement_ratio`, presença de contraexemplos, curvas de retenção e escopo por canal). **12 dos 15 itens originalmente marcados como `APRENDIZADO_VALIDADO` não possuíam sustentação suficiente e foram rebaixados**, preservando integralmente o histórico anterior em `metadata.classification_history`:

- **3 `APRENDIZADO_VALIDADO` confirmados:** `Presença de Narração Estruturada` nos canais 3 (Humor), 4 (Ciência) e 5 (Produtividade), com dominância empírica de engajamento sobre vídeos sem fala, transcrições reais via Faster-Whisper e contraexemplos documentados.
- **8 reclassificados para `HIPÓTESE`:** Todos os 5 registros de `Cortes Ágeis (>= 4)` (IDs 104, 109, 114, 119, 123 — na amostra global, `cuts >= 4` teve engajamento médio `1.873%` vs `1.941%` para `cuts < 4`, e não há curvas de retenção privada do YouTube Studio), além de Loudness/Narração no Canal 1 e Narração no Canal 2 onde vídeos musicais sem fala obtiveram engajamento superior.
- **4 reclassificados para `PENDENTE_DE_VALIDACAO`:** `Loudness Efetivo (-24 a -6 LUFS)` nos canais 2, 3, 4 e 5 (IDs 110, 115, 120, 124), por terem sido criados com `0` contraexemplos e representarem norma técnica universal e não diferencial editorial específico de canal.
- **5 `OBSERVAÇÃO` confirmadas:** Amostras únicas (`N=1`) de plano contínuo (IDs 107, 112, 117, 122, 126).
- **3 `ANTI_PATTERN` confirmados:** Rejeições reais do piloto (`2TFGeAHjPA8` áudio silencioso `-70.0 LUFS`, `tfJSsxukhKY` simulador de jogo no Canal 2, `GggELAqG63s` pack de efeitos sonoros no Canal 3).

### Tabela Completa dos 23 Registros Auditados
| ID | Canal | Categoria | Classificação Atual | Histórico Anterior | Confiança | Evidências | Contraexemplos | Criado em |
|:---:|:---:|---|---|---|:---:|:---:|:---:|---|
| **104** | Ch1 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | APRENDIZADO_VALIDADO | 0.68 | 6 | 2 | 2026-11-24 21:22:16 |
| **105** | Ch1 | `padrao_loudness_comercial` | `HIPÓTESE` | APRENDIZADO_VALIDADO | 0.70 | 6 | 1 | 2026-11-24 21:22:16 |
| **106** | Ch1 | `estrutura_narrativa_real` | `HIPÓTESE` | APRENDIZADO_VALIDADO | 0.70 | 6 | 2 | 2026-11-24 21:22:16 |
| **107** | Ch1 | `plano_continuo_observacao` | `OBSERVAÇÃO` | — (mantido) | 0.65 | 1 | 1 | 2026-11-24 21:22:16 |
| **108** | Ch1 | `anti_pattern_editorial_ou_acustico` | `ANTI_PATTERN` | — (mantido) | 0.90 | 1 | 0 | 2026-11-24 21:22:16 |
| **109** | Ch2 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | APRENDIZADO_VALIDADO | 0.68 | 6 | 2 | 2026-11-24 21:22:16 |
| **110** | Ch2 | `padrao_loudness_comercial` | `PENDENTE_DE_VALIDACAO` | APRENDIZADO_VALIDADO | 0.72 | 6 | 0 | 2026-11-24 21:22:16 |
| **111** | Ch2 | `estrutura_narrativa_real` | `HIPÓTESE` | APRENDIZADO_VALIDADO | 0.70 | 6 | 2 | 2026-11-24 21:22:16 |
| **112** | Ch2 | `plano_continuo_observacao` | `OBSERVAÇÃO` | — (mantido) | 0.65 | 1 | 1 | 2026-11-24 21:22:16 |
| **113** | Ch2 | `anti_pattern_editorial_ou_acustico` | `ANTI_PATTERN` | — (mantido) | 0.70 | 1 | 0 | 2026-11-24 21:22:16 |
| **114** | Ch3 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | APRENDIZADO_VALIDADO | 0.68 | 4 | 2 | 2026-11-24 21:22:16 |
| **115** | Ch3 | `padrao_loudness_comercial` | `PENDENTE_DE_VALIDACAO` | APRENDIZADO_VALIDADO | 0.72 | 6 | 0 | 2026-11-24 21:22:16 |
| **116** | Ch3 | `estrutura_narrativa_real` | `APRENDIZADO_VALIDADO` | — (mantido) | 0.90 | 6 | 1 | 2026-11-24 21:22:16 |
| **117** | Ch3 | `plano_continuo_observacao` | `OBSERVAÇÃO` | — (mantido) | 0.65 | 1 | 1 | 2026-11-24 21:22:16 |
| **118** | Ch3 | `anti_pattern_editorial_ou_acustico` | `ANTI_PATTERN` | — (mantido) | 0.70 | 1 | 0 | 2026-11-24 21:22:16 |
| **119** | Ch4 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | APRENDIZADO_VALIDADO | 0.68 | 6 | 2 | 2026-11-24 21:22:16 |
| **120** | Ch4 | `padrao_loudness_comercial` | `PENDENTE_DE_VALIDACAO` | APRENDIZADO_VALIDADO | 0.72 | 6 | 0 | 2026-11-24 21:22:16 |
| **121** | Ch4 | `estrutura_narrativa_real` | `APRENDIZADO_VALIDADO` | — (mantido) | 0.90 | 6 | 2 | 2026-11-24 21:22:16 |
| **122** | Ch4 | `plano_continuo_observacao` | `OBSERVAÇÃO` | — (mantido) | 0.65 | 1 | 1 | 2026-11-24 21:22:16 |
| **123** | Ch5 | `ritmo_de_cortes_dinamico` | `HIPÓTESE` | APRENDIZADO_VALIDADO | 0.68 | 6 | 2 | 2026-11-24 21:22:16 |
| **124** | Ch5 | `padrao_loudness_comercial` | `PENDENTE_DE_VALIDACAO` | APRENDIZADO_VALIDADO | 0.72 | 6 | 0 | 2026-11-24 21:22:16 |
| **125** | Ch5 | `estrutura_narrativa_real` | `APRENDIZADO_VALIDADO` | — (mantido) | 0.90 | 6 | 2 | 2026-11-24 21:22:16 |
| **126** | Ch5 | `plano_continuo_observacao` | `OBSERVAÇÃO` | — (mantido) | 0.65 | 1 | 1 | 2026-11-24 21:22:16 |

---

## 2. RESULTADO DA VALIDAÇÃO CRUZADA ENTRE CANAIS

Testada via `AudiovisualLearningSystem.query_editorial_rule_for_channel()` e suíte `test_fase17_scale_readiness.py` (`test_03`):

| Cenário Testado | Permitido? | Motivo / Mecanismo |
|---|:---:|---|
| Futebol (Ch1) consultado por Ciência (Ch4) | **BLOQUEADO** | `cross_channel_contamination_blocked` |
| Humor (Ch3) consultado por Produtividade (Ch5) | **BLOQUEADO** | `cross_channel_contamination_blocked` |
| Arquivo Sombrio (Ch2) consultado por Ciência (Ch4) | **BLOQUEADO** | `cross_channel_contamination_blocked` |
| Norma Técnica Universal (`target_channel_id = NULL`) consultada por Ciência (Ch4) | **SIM** | `universal_technical` (separado de regras editoriais de canal) |

---

## 3. UTILIDADE EDITORIAL MEDIDA (TESTE A/B EM HOLDOUT INDEPENDENTE)

Avaliação executada em **20 vídeos reais da Fase 15** (`id BETWEEN 24 AND 43`), com **sobreposição `overlap_with_training = 0`** em relação aos 100 vídeos da Fase 16:

| Métrica Específica | Modo A (Sem Fase 16) | Modo B (Com Fase 16 Auditada) | Delta / Observação |
|---|:---:|:---:|---|
| Detecção de conteúdo fora de nicho | 0 | **1** | Capturou `Oy5m1qwhlv8` (`SHORT JEANS`) |
| Detecção de áudio silencioso (`<= -65 LUFS`) | 0 | **3** | Capturou os 3 áudios `-70.0 LUFS` da Fase 15 |
| Recomendações específicas por canal | 0 | **12** | Ativo nos canais 3, 4 e 5 |
| Orientação narrativa / ganchos | 0 | **12** | Baseado em transcrição real |
| Alertas de anti-pattern emitidos | 0 | **14** | Proteção ativa contra falhas conhecidas |
| Precisão na predição de alto engajamento (`>= 1.5%`) | 33.3% | **47.4%** | Melhora (+14.1 pp), porém ainda moderada |

**Avaliação Honesta:** O Modo B melhora substancialmente a triagem editorial, o bloqueio de anti-patterns e a especificidade das recomendações nos canais 3–5, mas **não resolve a predição causal de retenção/engajamento** nos canais 1 e 2 nem substitui métricas privadas do YouTube Studio Analytics.

---

## 4. LIMITAÇÕES ENCONTRADAS

1. **Ausência de métricas privadas de retenção segundo-a-segundo:** O sistema mede engajamento público (`likes/views`) e propriedades físicas reais, não curvas de retenção interna.
2. **Proporção de tela no lote da Fase 16:** `0/100` vídeos coletados via `ytsearch` tinham `height > width` (`9:16` nativo); eram clipes curtos `<= 60s` majoritariamente em `16:9` / `4:3`. A coleta de 7.000 precisará de filtro explícito de verticalidade quando o foco for enquadramento `9:16`.
3. **Cobertura editorial desigual:** Canais 1 (Futebol) e 2 (Arquivo Sombrio) ainda não possuem regras de performance validadas (permanecem como `HIPÓTESE`).
4. **Volume de disco para mídia bruta:** Manter 7.000 arquivos locais simultaneamente exigiria ~63–88 GB, tornando recomendável o processamento em sublotes de 250–500 vídeos com offload/expurgo controlado.

---

## 5. ARQUITETURA DE FILAS E PROCESSAMENTO

Auditada e reforçada em `services/orchestration/central_controller.py` e `services/learning/audiovisual_learning_system.py`:
- **Fila Persistente (`task_queue`):** Prioridade, controle de concorrência por canal (`max_concurrent_per_channel`), proteção contra submissão duplicada.
- **Retentativas e Falhas Permanentes:** Backoff exponencial (`RETRYING`) com suporte a `permanent=True` em `fail_task_with_retry()` para encerrar imediatamente falhas permanentes (vídeo deletado/privado/>60s) sem desperdiçar ciclos.
- **Recuperação pós-queda:** `recover_stalled_tasks()` + checkpoints persistentes em `learning_batch_checkpoints` + retomada idempotente por `source_id` e `sha256`.
- **Separação de Estágios:** `downloaded` -> `technical_analysis_complete` -> `editorial_analysis_complete` -> `learning_candidate` / `editorially_rejected` / `failed`.

---

## 6. ESTIMATIVAS DE CAPACIDADE PARA 7.000 VÍDEOS (PREMISSAS & FÓRMULAS)

*Nota: Todos os números abaixo são **estimativas projetadas** (`is_estimate = True`) a partir das medições reais do piloto de 100 vídeos (`8.02 MB/vídeo`, `33.5s/vídeo` sequencial em CPU).*

- **Fórmula Armazenamento (GB):** `7000 * avg_mb_per_video / 1024 * safety_margin`
- **Fórmula Tempo Total (h):** `7000 * ((avg_analysis_sec + 5.0) * (1 + retry_overhead) / effective_workers) / 3600`
- **Fórmula Pico de RAM (GB):** `0.8 * effective_workers + 0.6`

| Cenário | Workers Efetivos | Margem Segurança | Armazenamento Mídia Bruta | Crescimento SQLite | Tempo Estimado | Pico RAM | Custo Estimado |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Conservador** | 4.0 | 1.15x | 63.02 GB | 161.0 MB | 19.65 h | 3.8 GB | **$0.00** |
| **Realista** | 2.8 | 1.3x | 71.24 GB | 182.0 MB | 29.94 h | 2.84 GB | **$0.00** |
| **Pessimista** | 1.5 | 1.6x | 87.68 GB | 224.0 MB | 62.38 h | 1.8 GB | **$0.00** |

---

## 7. ESTRATÉGIA DE SELEÇÃO DOS 7.000 VÍDEOS (NÃO EXECUTADA)

Implementada e validada em `services/discovery/scale_selector.py` (`ScaleSelectionPlanner`) sem iniciar downloads em massa:
- **Estratificação Anti-Viés de Popularidade:** Quotas por faixa de visualizações (`emerging < 10k`: 30%, `mid_tier 10k–500k`: 40%, `viral > 500k`: 30%), evitando aprender apenas com outliers mega-virais.
- **Critérios Rígidos Pré-Ingestão:** ID único, URL válida, disponibilidade ativa, duração `0 < d <= 60.0s`, adequação editorial ao canal de origem, diversidade de fala/ritmo/formato.
- **Separação Treino / Validação / Teste:** Atribuição determinística de `dataset_split` (`70% train`, `15% validation`, `15% test`) por canal.

---

## 8. PROTEÇÃO CONTRA APRENDIZADO DEFEITUOSO & EXPLICABILIDADE

Reforçada em `AudiovisualLearningSystem.record_knowledge()` e `explain_knowledge()`:
- **Deduplicação de Aprendizados:** Mescla evidências quando já existe regra com mesmo canal, nicho, tipo e título.
- **Bloqueio de Evidência Corrompida:** Rejeita `record_knowledge()` se qualquer `evidence_video_id` estiver em `failed` ou `error`.
- **Contraexemplos Obrigatórios (`require_counterexamples=True`):** Regras sem contraexemplos são rebaixadas para `PENDENTE_DE_VALIDACAO`.
- **Contrato de Explicabilidade (`explain_knowledge(id)`):** Responde explicitamente por que funciona, quais vídeos sustentam e em quais situações pode falhar.

---

## 9. ESTADO DO DASHBOARD E OBSERVABILIDADE

Todos os 17+ indicadores solicitados na Seção 9 são extraídos diretamente de `shorts_central.db` e `ModelGatewayService` (zero valores fixos), e exibidos em `web/static/index.html`:

```json
{
  "pilot_name": "Fase 16 - Piloto Controlado 100 Shorts",
  "candidates_selected": 100,
  "total_shorts_pilot": 100,
  "downloaded": 100,
  "physically_validated": 100,
  "technically_analyzed": 100,
  "editorially_analyzed": 100,
  "editorially_approved": 97,
  "editorially_rejected": 3,
  "videos_with_transcripts": 79,
  "videos_insufficient_speech": 21,
  "silent_audio_detected": 1,
  "learning_candidates": 97,
  "validated_learnings": 3,
  "observations_count": 5,
  "hypotheses_count": 12,
  "anti_patterns_count": 3,
  "total_knowledge_recorded": 23,
  "failures": 0,
  "retries_count": 0,
  "avg_processing_time_sec": 33.44,
  "cost_usd": 0.0,
  "storage_used_bytes": 840630006,
  "storage_used_mb": 801.69,
  "success_rate_per_channel": {
    "1": 100.0,
    "2": 100.0,
    "3": 100.0,
    "4": 100.0,
    "5": 100.0
  },
  "circuit_breakers_triggered": 0
}
```

---

## 10. RESULTADO DOS TESTES

- **Suíte dedicada Fase 17:** `python tests/test_fase17_scale_readiness.py -v` -> **10/10 aprovados** (exit code `0`)
- **Regressão completa após edição final:** `python scripts/run_all_tests.py` -> **19/19 suítes, 170/170 testes unitários aprovados (100.0%, 0 falhas, 0 erros, 0 skipped, 576.91s, exit code `0`)**.

---

## 11. CUSTOS E RISCOS

- **Custo Operacional Real:** **\$0.00** (100% local com Faster-Whisper CPU, FFmpeg, PySceneDetect, OpenCV e `ModelGatewayService(enforce_free_tier=True)`).
- **Principais Riscos para 7.000 Vídeos:** Rate limiting / bot-check do YouTube em rajadas longas (mitigado por jitter 3–6.5s, backoff exponencial e circuit breakers), saturação de disco se não houver offload em sublotes de 250–500 vídeos, e generalização prematura de regras ainda em `HIPÓTESE`.

---

## 12. RECOMENDAÇÃO FINAL

> ### **Classificação: `READY_WITH_RESERVATIONS`**
> 
> A arquitetura de filas, checkpoints, isolamento multitenant, explicabilidade, controle de custo zero e bateria de 170 testes está **aprovada e operacional**. A futura escala para 7.000 vídeos é tecnicamente viável **com as seguintes ressalvas obrigatórias**:
> 1. Executar em sublotes controlados de **250 a 500 vídeos** com limpeza/offload de mídia bruta para o Google Drive.
> 2. Aplicar filtro explícito de proporção vertical (`9:16`) na seleção quando o objetivo for estudar composição vertical nativa.
> 3. Manter as 8 hipóteses e 4 pendências da Fase 16 fora do conjunto de regras validadas até obter evidência estatística nos sublotes de treinamento (`train` 70% / `validation` 15% / `test` 15%).
> 
> **O processamento dos 7.000 vídeos NÃO foi iniciado nesta fase e aguarda decisão após análise deste relatório.**

*Relatório gerado e verificado em 24/11/2026 19:22:09.*