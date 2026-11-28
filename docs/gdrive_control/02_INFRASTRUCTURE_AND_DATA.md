# 02 — INFRAESTRUTURA, BANCO E MODELO DE DADOS

Inspecione o stack existente e implemente a fundação de dados e serviços sem reconstruir o projeto.

## Domínios de dados
Considere, adaptando aos modelos existentes:
- User/workspace e permissões.
- Channels.
- Editorial profiles e regras.
- References e research sources.
- Content items e content versions.
- Scripts e assets.
- Agent runs, tasks, logs e tool calls.
- Feedback e memory records.
- Approval requests.
- Publishing jobs.
- Performance metrics.
- Financial records e cost events.
- Audit events.

## Requisitos
- IDs estáveis, timestamps, estados explícitos e relações consistentes.
- Isolamento por canal e workspace.
- Validação de entrada e constraints no banco.
- Migrações versionadas e reversíveis quando possível.
- Índices adequados e paginação.
- Transações para operações compostas.
- Idempotência para jobs e eventos.
- Não armazenar mídia pesada no banco; guardar metadados e referências.
- Segredos fora do banco/logs quando não necessário.
- Dados financeiros devem distinguir valores reais, estimados e desconhecidos.

## APIs
Documente contratos, schemas, erros, autenticação e paginação. Não crie endpoint duplicado. Não retorne sucesso falso quando a operação externa não ocorreu.

## Critérios de aceite
Migrações testadas, integridade referencial, isolamento por canal, testes de acesso e documentação dos contratos.
