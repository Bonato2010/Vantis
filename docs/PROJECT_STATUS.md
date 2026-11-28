# VANTIS — ESTADO ATUAL DO PROJETO E CONTROLE DE VERACIDADE

> **Data de Emissão:** 2026-11-28  
> **Branch de Desenvolvimento:** `develop`  
> **Branch Principal:** `main` (integrada)

---

## 1. Classificação de Veracidade dos Módulos

Para garantir total transparência e conformidade operacional, os módulos do VANTIS são categorizados rigorosamente:

| Componente | Categoria Real | Evidência / Detalhes |
| :--- | :--- | :--- |
| **Arquitetura Multiagente (10 Agentes)** | **IMPLEMENTADO & TESTADO** | Classes em `agents/`, testes unitários em `tests/test_fase9_agent_architecture.py`. |
| **Banco Relacional & Migrações** | **VALIDADO** | 12 arquivos SQL executados com sucesso em `database/shorts_central.db`. |
| **Dashboard Operacional Web** | **VALIDADO** | Servidor FastAPI + UI estática em `web/app.py`. |
| **Renderização Audiovisual 9:16** | **IMPLEMENTADO** | `PackageRendererService` e `FFmpegEngine` com renderização comprovada (`vantis_ch4_pkg7_job2.mp4` em histórico de auditoria). |
| **Voz Neural TTS (Edge-TTS)** | **VALIDADO** | Pacote instalado no ambiente local e validado sem custos de API. |
| **Aquisição de Mídia (Wikimedia Commons)** | **VALIDADO** | Aquisição sob licenças livres com hash SHA-256 (`AssetIntelligenceEngine`). |
| **Estrutura Google Drive 5 TB (13 Pastas)** | **CONFIGURADO & PRONTO** | `gdrive_credentials.json` adicionado localmente; fluxo de token aguardando login no navegador. |
| **5 Marcas Editoriais Candidatas** | **PLANEJADO / EM HOMOLOGAÇÃO** | Registradas na tabela `channel_brands` (Zona de Jogo, Dossiê Oculto, Caos em 60s, Horizonte Cósmico, Modo Ascensão). |
| **Canais Reais do YouTube** | **NÃO CRIADOS** | Canais aguardam criação manual no YouTube Studio. NENHUM canal ou ID falso foi simulado. |
| **Conexão OAuth do YouTube** | **NÃO CONFIGURADO** | Marcado estritamente como `OAUTH_DISCONNECTED`. Uploads bloqueados até autorização real. |
| **Gate de Aprovação Humana** | **VALIDADO** | Rejeição programada de qualquer tentativa de publicação sem token de aprovação humana. |

---

## 2. Bloqueios Atuais e Pendências Operacionais

1. **Credenciais do Google Drive (Aguardando Consentimento no Navegador):**
   - O arquivo `gdrive_credentials.json` já foi colocado em `credentials/`.
   - Falta executar `python auth_drive.py` uma única vez no navegador para gerar `credentials/gdrive_token.json`.

2. **FFmpeg no PATH do Sistema Local:**
   - O novo computador necessita do binário `ffmpeg.exe` instalado ou adicionado ao PATH para efetuar novas renderizações de vídeo MP4 localmente.

3. **Canais do YouTube:**
   - Criação manual dos canais no YouTube Studio para obtenção de `channel_id` oficial no formato `UC...`.
