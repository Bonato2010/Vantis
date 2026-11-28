# 09 — SEGURANÇA, TESTES E QUALIDADE

Faça revisão de segurança e qualidade antes de declarar o sistema pronto.

## Segurança
- Autenticação e autorização.
- Controle de acesso por workspace/canal.
- Validação e sanitização.
- Proteção contra injeção e abuso.
- Gestão de segredos.
- Logs sem tokens/PII desnecessária.
- Rate limiting.
- CORS/CSRF conforme stack.
- Upload seguro e limites de arquivo.
- Auditoria de ações sensíveis.
- Dependências vulneráveis.
- Backups e restauração.

## Testes
- Unitários.
- Integração.
- Contratos de API.
- Banco/migrações.
- Isolamento de canais.
- Orquestração e retomada.
- Gateway e custo.
- Pipeline audiovisual.
- Aprovação de publicação.
- Fluxos frontend.
- Regressão.

Não permita testes que publiquem conteúdo real, gerem custos ou alterem contas externas.

## Critérios de aceite
Relatório de testes, vulnerabilidades priorizadas, correções verificadas e riscos residuais documentados. Não declare segurança absoluta.
