# VANTIS — CONFIGURAÇÃO DO AMBIENTE ANTIGRAVITY IDE

> **Guia para Desenvolvedores e Agentes de IA operando no Antigravity IDE**

---

## 1. Estrutura do Workspace no Antigravity

- **Diretório Raiz Recomendado:**
  `C:\Users\Daniz\.gemini\antigravity\scratch\Vantis`
- Para melhor desempenho e contexto durante as sessões de trabalho, o diretório acima deve estar definido como o Workspace ativo do Antigravity.

---

## 2. Servidores MCP (Model Context Protocol)

O Vantis suporta conexão com servidores MCP para instrumentação avançada:

- **Servidor MCP Interno (`mcp_server.py`):**
  - O repositório inclui `mcp_server.py` para exposição de ferramentas de gerenciamento de tarefas e status operacional.
  - Para executar localmente em modo standalone:
    ```powershell
    python mcp_server.py
    ```

- **Configuração no Antigravity:**
  Caso deseje registrar ferramentas MCP personalizadas no IDE, configure a chamada no arquivo de configuração do usuário com o comando de execução do Python apontando para o script absoluto correspondente.

---

## 3. Diretrizes de Execução no Ambiente

1. **Terminal e Shell:**
   - O ambiente opera com PowerShell no Windows.
   - Em comandos encadeados, utilize ponto e vírgula (`;`) em vez de operadores Unix bash inválidos (`&&`).

2. **Gerenciamento de Processos em Background:**
   - O dashboard (`web.app`) e execuções longas de renderização devem ser disparados em background com portas locais isoladas (ex.: `127.0.0.1:8000`).
