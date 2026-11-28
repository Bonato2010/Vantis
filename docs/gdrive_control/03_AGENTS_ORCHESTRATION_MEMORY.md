# 03 — AGENTES, ORQUESTRAÇÃO E MEMÓRIA

Implemente um sistema de agentes realmente executável, observável e controlável.

## Papéis possíveis
- Research Agent: coleta e organiza fontes.
- Trend/Opportunity Agent: detecta oportunidades com evidência.
- Planner Agent: transforma oportunidades em pautas.
- Script Agent: cria roteiros.
- Editorial Reviewer: verifica aderência às regras do canal.
- Production Agent: coordena etapas audiovisuais.
- Quality Agent: valida áudio, vídeo, legendas e especificações.
- Publishing Preparation Agent: prepara metadados e pacote de publicação.
- Analytics Agent: resume métricas reais.

Não crie agentes sem responsabilidade definida. Prefira ferramentas compartilhadas e workflows explícitos a agentes redundantes.

## Orquestração
- Estados persistentes.
- Execuções retomáveis.
- Filas e workers quando adequados.
- Timeout, retries com backoff e limites.
- Idempotency keys.
- Cancelamento seguro.
- Logs estruturados e rastreabilidade por canal/conteúdo.
- Erros tipados e estados de falha.
- Limites de concorrência e consumo.

## Memória
Separar:
1. Memória global do produto.
2. Perfil editorial por canal.
3. Regras obrigatórias por canal.
4. Exemplos aprovados/rejeitados.
5. Feedback e justificativas.
6. Histórico factual e resultados.

Recuperar somente o contexto relevante para o canal e tarefa atual. Não misturar identidades editoriais.

Não afirmar aprendizado permanente quando só houve gravação de feedback. Implementar persistência, recuperação e testes.

## Critérios de aceite
Workflows reais executados em testes, retomada após falha, isolamento entre canais, rastreabilidade e demonstração de que feedback armazenado influencia o contexto futuro.
