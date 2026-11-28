# 07 — INTEGRAÇÃO YOUTUBE

Implemente integração segura com a YouTube Data API, respeitando documentação e quotas atuais.

## Capacidades
- OAuth e conexão de conta.
- Identificação dos canais autorizados.
- Leitura de dados permitidos.
- Preparação de título, descrição, tags e thumbnail.
- Upload e agendamento como fluxo preparado.
- Consulta de status e erros.
- Registro de quota e operações.
- Analytics disponíveis conforme permissões.

## Segurança
- Tokens protegidos e nunca registrados em logs.
- Escopos mínimos.
- Renovação segura quando suportada.
- Revogação e desconexão.
- Rate limits e tratamento de quota.
- Não armazenar credenciais no repositório.

## Aprovação
A publicação real deve exigir aprovação explícita. O backend deve validar o estado aprovado, o usuário autorizado e o pacote final. A UI sozinha não é barreira suficiente.

Durante desenvolvimento, use mocks claramente identificados ou ambiente de teste. Não publique, agende nem altere canais reais sem autorização específica.

## Critérios de aceite
Testes automatizados de OAuth/contratos, tratamento de erros e prova de que publicação não aprovada é bloqueada no backend.
