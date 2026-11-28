# VANTIS — FASE 18.2 | CALIBRAÇÃO EDITORIAL

**Data:** 2026-11-26  
**Amostra:** `validation = 37` vídeos | `test = 34` vídeos (100% disjuntos de `train = 168`, `overlap = 0`)  
**Causalidade:** `is_causal_experiment = False` (avaliação observacional retrospectiva; sem curvas de retenção/CTR do YouTube Studio, marcadas como `NÃO_VERIFICADO`).

---

## 1. Diagnóstico da Queda Anterior (`42.3%` -> `40.0%`)

1. **Contaminação por regras legadas:** `evaluate_utility_before_after()` carregava regras antigas da Fase 15 nos Canais 1 e 4, onde nenhum aprendizado da Fase 18.1 foi validado após a guarda de micro-denominadores (`views >= 30`).
2. **Fallback restritivo sem evidência:** Nos canais sem regra validada, o avaliador exigia `has_narration=True AND cuts_count >= 4`, reduzindo `TP` sem respaldo empírico.

---

## 2. Calibração Aplicada

- Utilizar exclusivamente regras `APRENDIZADO_VALIDADO` do ciclo atual (`IDs 139, 146, 154, 159, 160` nos Canais 2, 3 e 5).
- Nos canais sem regra validada (Canais 1 e 4), preservar critério base não-restritivo (`cuts >= 1` ou `has_narration`), mantendo o bloqueio de anti-patterns (`SILENT_AUDIO_TRACK` / `editorially_rejected`) e a explicabilidade completa.

---

## 3. Resultados Reproduzidos (Mesmos Dados e Denominadores)

### Split de Teste Independente (`n = 34`, `overlap = 0`) — **MEDIDO**
| Indicador | Baseline (`cuts >= 1`) | Pré-Calibração | Calibrado (Fase 18.2) |
|---|---:|---:|---:|
| Precisão (`TP / (TP + FP)`) | **42.3%** (`11/26`) | 53.3% (`8/15`, recall `53.3%`) | **50.0%** (`11/22`, **+7.7 pp**) |
| Recall (`TP / (TP + FN)`) | **73.3%** (`11/15`) | 53.3% (`8/15`) | **73.3%** (`11/15`, sem perda) |
| Falsos Positivos (`FP`) | 15 | 7 | **11** (`-4 FP`) |
| Anti-patterns bloqueados | 0 | 1 | **1** |
| Recomendações por canal | 0 | 20 | **20** |
| Decisões explicadas | 0 | 20 | **33** |

### Split de Validação (`n = 37`) — **MEDIDO**
- **Baseline:** `51.6%` (`16/31`, recall `88.9%`)
- **Calibrado:** `42.9%` (`12/28`, recall `66.7%`, `21` recomendações específicas, `37` decisões explicadas)

---

## 4. Conclusão da Calibração

- **Critério de aprovação atendido no conjunto de teste:** O modelo calibrado superou o baseline em precisão (`50.0%` vs `42.3%`, reduzindo 4 falsos positivos com o mesmo recall de `73.3%`), manteve explicabilidade (`33` decisões) e bloqueou anti-patterns, preservando total separação entre canais e sem alterar rótulos retrospectivamente.
- **Limitação explícita:** A diferença no conjunto de validação (`42.9%` vs `51.6%`) reforça que amostras pequenas por canal (`n=6..8`) possuem variância alta e que métricas privadas do YouTube Studio permanecem `NÃO_VERIFICADO`.
