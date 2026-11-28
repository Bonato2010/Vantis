# VANTIS — PROJECT CONTROL
## Biblioteca oficial de prompts e execução autônoma

Esta pasta é a fonte oficial de instruções do projeto VANTIS. O Antigravity IDE deve ler os arquivos por meio do MCP do Google Drive, respeitando a ordem, as dependências e as regras abaixo.

### Como instalar
1. Envie a pasta `VANTIS_PROJECT_CONTROL` para o Google Drive.
2. Confirme que o MCP do Google Drive está conectado ao Antigravity IDE e consegue listar e ler os arquivos.
3. Abra o repositório VANTIS no Antigravity.
4. Cole uma única vez o conteúdo de `00_MASTER_ORCHESTRATOR.md` ou peça ao agente para ler esse arquivo diretamente pelo Drive.
5. O agente deve descobrir a localização da pasta no Drive por pesquisa/listagem MCP. Não invente IDs, caminhos ou links.

### Regra de operação
- O repositório é a fonte da verdade sobre o estado do código.
- O Drive é a fonte da verdade sobre o plano, os prompts e os registros de execução.
- Trabalhe na branch `develop`; preserve `main`.
- Não assuma que um prompt foi concluído só porque foi lido ou iniciado.
- Registre evidências, testes, arquivos alterados e pendências.
- Não duplique funcionalidades já existentes. Audite antes de implementar.
- Se o MCP não permitir escrever no Drive, mantenha os logs no repositório e informe a limitação; não finja que sincronizou.

### Ordem geral
00 Orquestração → 01 Auditoria/Arquitetura → 02 Infraestrutura/Dados → 03 Agentes/Memória → 04 Pesquisa/Editorial → 05 Produção audiovisual → 06 Dashboard → 07 YouTube → 08 Cinco canais → 09 Segurança/Testes → 10 Deploy/Operação → 11 Treinamento e expansão.

A ordem é um mapa de dependências, não uma autorização para ignorar bloqueios técnicos. Algumas etapas podem avançar em paralelo quando os contratos estiverem definidos e não houver conflito de arquivos.
