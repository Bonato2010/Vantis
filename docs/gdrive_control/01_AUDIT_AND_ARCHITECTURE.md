# 01 — AUDITORIA E ARQUITETURA

Faça uma auditoria técnica completa, primeiro somente leitura. Depois produza um plano incremental e implemente correções arquiteturais seguras.

## Auditar
- Estrutura do repositório, módulos, dependências e convenções.
- Frontend, backend, banco, APIs, autenticação e configuração.
- Orquestração de agentes e filas.
- Model Gateway, provedores e política de custos.
- Memória e recuperação contextual.
- Pesquisa, roteiros, mídia, transcrição, edição e publicação.
- Drive, YouTube e integrações externas.
- Testes, CI, logs, observabilidade e documentação.
- Código morto, mocks, valores hardcoded, endpoints fictícios e duplicações.

## Entregáveis
- `docs/architecture/current-state.md`
- `docs/architecture/target-state.md`
- `docs/architecture/module-map.md`
- `docs/architecture/api-contracts.md`
- `docs/architecture/risks-and-gaps.md`

## Regras
- Diferencie claramente produção, protótipo, mock e implementação parcial.
- Não declare um StateGraph funcional se a execução real não usar o grafo.
- Não chame vetores hash/lexicais de embeddings semânticos.
- Não esconda fallback simulado.
- Não substitua uma tecnologia funcional sem benefício comprovado.
- Prefira arquitetura modular e simples; não adicione frameworks por moda.
- Preserve compatibilidade e migre gradualmente.

## Critérios de aceite
Auditoria reproduzível, mapa de dependências, riscos priorizados, plano por etapas e contratos de integração documentados.
