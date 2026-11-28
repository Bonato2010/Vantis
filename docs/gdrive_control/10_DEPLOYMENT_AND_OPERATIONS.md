# 10 — DEPLOYMENT E OPERAÇÃO CONTÍNUA

Prepare execução confiável, monitoramento e recuperação.

## Ambiente
- Documentar versões e pré-requisitos.
- Configuração por ambiente.
- `.env.example` sem segredos.
- Scripts de setup e inicialização idempotentes.
- Health checks.
- Logs estruturados.
- Métricas de serviço.
- Migrações controladas.
- Backups e procedimento de restore.
- Monitoramento de filas e workers.
- Alertas para falhas relevantes.

## Continuidade
- Reinício seguro.
- Retomada de jobs.
- Tratamento de processos órfãos.
- Limites de concorrência.
- Rotação de logs.
- Limites de armazenamento.
- Plano de recuperação.

Não prometa operação 24/7 gratuita sem verificar hospedagem, limites, quotas e disponibilidade. Não habilite serviços pagos nem faça deploy público sem autorização específica.

## Critérios de aceite
Procedimento reproduzível em ambiente limpo, health checks funcionais, recuperação de falhas testada e custos/limitações documentados.
