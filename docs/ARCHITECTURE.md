# VANTIS — ARQUITETURA OFICIAL DA PLATAFORMA

> **Status:** IMPLEMENTADO & ATUALIZADO  
> **Última Atualização:** 2026-11-28  
> **Branch Principal de Operação:** `develop`  
> **Branch de Estabilidade:** `main`

---

## 1. Visão Geral da Arquitetura

O **VANTIS** (anteriormente codinome IAS - *Intelligence & Automation System*) é uma plataforma profissional integrada para pesquisa, catalogação, geração de roteiros originais, síntese audiovisual 9:16 e governança de publicação de YouTube Shorts e Podcasts.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          VANTIS SYSTEM TOPOLOGY                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ FRONTEND / DASHBOARD ]                                                   │
│   FastAPI (REST API + Static SPA) -> http://127.0.0.1:8000                  │
│   Governança visual, revisão humana, inspeção de pacotes e telemetria       │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ MULTI-AGENT SYSTEM & DECISION CORE ]                                     │
│   • BaseVantisAgent / AgentRegistry: 10 Agentes Especializados              │
│   • Conselho Editorial (Mesa Redonda / ContentCompany)                      │
│   • ResearchOrchestrator: Descoberta e mineração multimodal                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ AUDIOVISUAL PRODUCTION & EDITORIAL ENGINE ]                              │
│   • PackageRendererService: Renderização vertical 9:16 (FFmpeg Engine)      │
│   • TTS Engine: Edge-TTS (Vozes neurais gratuitas sem custo de API)         │
│   • Subtitle Generator: Geração e estilização de legendas dinâmicas (.ass)  │
│   • AssetIntelligenceEngine: Aquisição e verificação (Wikimedia Commons)   │
│   • EditorialValidator: Trava estrita contra plágio e verificação semântica │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ STORAGE & PERSISTENCE LAYER ]                                            │
│   • Relacional: SQLite WAL mode (database/shorts_central.db)                │
│   • Vetorial: VectorMemoryService (Dense cosine distance / pgvector ready)  │
│   • Nuvem: Google Drive 5 TB (DriveStorageService - 13 pastas mandatórias)  │
│   • Local Workspace: workspace/ (buffer temporário de processamento)        │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ DISTRIBUTION & SAFETY GATES ]                                            │
│   • Trava de Custo: $0.00 Policy (bloqueio de chamadas pagas sem cota)      │
│   • Portal 1 & 2: Portais de conformidade editorial e técnica               │
│   • YouTubeUploader: Gate mandatório de aprovação humana + OAuth 2.0 real   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Camadas do Sistema

### 2.1 Camada Web e API (`web/`)
- Servidor REST assíncrono baseado em **FastAPI** montado em `web/app.py`.
- Interface administrativa corporativa em HTML5/CSS3/JavaScript puro em `web/static/index.html`.
- Fornece endpoints para controle de marcas, pacotes de produção, jobs de renderização, telemetria de serviços e governança OAuth.

### 2.2 Camada Multiagente (`agents/`)
- 10 agentes especializados (`agt_opp_research`, `agt_trend_analysis`, `agt_transcription`, `agt_scriptwriter`, `agt_media_prep_editing`, `agt_quality_review`, `agt_editorial_planning`, `agt_performance_analytics`, `agt_task_coordinator`, `agt_qc`).
- Cada agente possui isolamento de contexto, limites de processamento e persistência de logs em banco de dados (`agent_execution_logs`).

### 2.3 Motores de Produção (`services/media_processing/`, `core/`)
- **FFmpegEngine:** Renderização em 1080x1920 (9:16), 30 fps, áudio normalizado em padrão broadcast EBU R128 (-14 LUFS).
- **TTSNarrationService:** Síntese de voz com Edge-TTS neural sem custos de API externa.
- **AssetIntelligenceEngine:** Seleção de imagens e vídeos de domínio público com verificação de metadados, hash SHA-256 e licenças verificadas (CC-BY, CC0, Domínio Público).

### 2.4 Camada de Dados (`database/`, `services/semantic_memory/`)
- Banco relacional **SQLite** com 16 tabelas e 12 migrações estruturadas gerenciadas por `database/migrate.py`.
- Memória semântica vetorial com fallback determinístico local caso pgvector/FastEmbed não estejam instalados no host.

### 2.5 Camada de Segurança e Governança
- **Trava de Aprovação Humana:** Nenhuma publicação para o YouTube pode ser feita sem token explícito de aprovação humana e verificação física do arquivo renderizado.
- **Isolamento de Credenciais:** As chaves OAuth do Google Drive e YouTube residem em `credentials/` (ignorado pelo Git).
