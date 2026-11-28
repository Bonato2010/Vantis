# IAS — Arquitetura-Alvo e Especificação Operacional de Mídia

**Versão:** 3.0  
**Status:** Aprovado para Implementação (Prompt 02)  
**Projeto:** IAS (Intelligence & Automation System)  
**Escopo:** Operação Multicanal (Até 20 Canais de YouTube Shorts, Piloto com 5 Canais)  

---

## 1. Visão Geral da Arquitetura

O **IAS** opera como uma empresa de mídia automatizada organizada em departamentos especializados, coordenada por um **Controlador Central de Operações** com persistência de tarefas e governança humana em duas etapas críticas (Descoberta e Publicação).

```
[ Camada 1: Governança & Portais Human-in-the-Loop ]
       │
       ├── Portal 1: Aprovação de Oportunidades & Pautas
       └── Portal 2: Aprovação de Roteiro & Vídeo Renderizado Final
       │
[ Camada 2: Controlador Central & Orquestrador LangGraph ]
       │
       ├── Fila Persistente de Tarefas (Task Queue com prioridades e retentativas)
       └── Grafo de 12 Etapas Resilientes com Checkpoints e Recuperabilidade
       │
[ Camada 3: Departamentos Especializados (Agentes & Motores) ]
       │
       ├── 1. Diretoria & Controle Geral
       ├── 2. Inteligência de Mercado (yt-dlp + Trends real)
       ├── 3. Estratégia Editorial (20 Perfis e Canais Isolados)
       ├── 4. Roteirização (Público, WPM e ganchos autênticos)
       ├── 5. Produção Audiovisual (Narração TTS + Assets visuais)
       ├── 6. Edição Inteligente (Whisper + OpenCV Smart Crop + FFmpeg 9:16 EBU R128)
       ├── 7. Controle de Qualidade (QC: Retenção, Originalidade, Diretrizes)
       ├── 8. Distribuição (Upload YouTube v3 com Trava "Private")
       ├── 9. Inteligência de Desempenho (Métricas pós-publicação e aprendizado)
       └── 10. Administração & Finanças (Controle de despesas, custos e receitas)
       │
[ Camada 4: Gateway de IA & OmniRoute ]
       │
       ├── Integração com Proxy Local OmniRoute (C:\Users\jcvse\.omniroute)
       ├── Modelos Locais (Ollama) & Provedores Gratuitos (Gemini Free Tier, Groq)
       └── Trava Orçamentária Mandatória (ENFORCE_FREE_TIER_ONLY = True)
       │
[ Camada 5: Armazenamento & Banco Particionado ]
       │
       ├── Google Drive 5 TB (Ativos brutos, renderizados e backups nas 13 pastas)
       └── Banco Relacional Central (SQLite WAL / Supabase PostgreSQL particionado por channel_id)
```

---

## 2. Departamentos e Responsabilidades

### 1. Diretoria e Controle
* **Responsabilidade:** Distribuição de tarefas, controle de concorrência, priorização de filas e monitoramento operacional.
* **Saída:** Tarefas despachadas com ID único, prioridade e status rastreável.

### 2. Inteligência de Mercado
* **Responsabilidade:** Pesquisa contínua de nichos, microculturas, bordões, memes e oportunidades virais no YouTube Shorts.
* **Regra de Ouro:** Não inventa métricas. Cada oportunidade possui fonte, país, idioma, justificativa e pontuação explicável. Entra na fila do Portal 1 para aprovação humana.

### 3. Estratégia Editorial (Multicanal)
* **Responsabilidade:** Gerencia o posicionamento, arquétipos, público-alvo, idioma e diretrizes de cada um dos 20 canais.
* **Regra de Ouro:** Não transfere automaticamente identidade ou referências culturais entre canais distintos.

### 4. Roteirização
* **Responsabilidade:** Transforma oportunidades aprovadas em roteiros estruturados (Gancho 0-3s, Premissa, Conflito, Clímax e CTA), respeitando o ritmo e público do canal.

### 5. Produção Audiovisual
* **Responsabilidade:** Síntese de voz, obtenção de trilhas sonoras e assets complementares.
* **Regra de Ouro:** Respeita quotas e custos antes de invocar APIs de voz.

### 6. Edição Inteligente
* **Responsabilidade:** Renderização vertical 9:16 (1080x1920) acelerada, Smart Crop via OpenCV, ritmo de cortes via PySceneDetect, legendas dinâmicas animadas em Karaoke via Faster-Whisper (.ass) e normalização de áudio em -14 LUFS (EBU R128).

### 7. Controle de Qualidade (QC)
* **Responsabilidade:** Avalia retenção estimada, originalidade, enquadramento e conformidade com as diretrizes do YouTube antes de enviar para o Portal 2.

### 8. Distribuição
* **Responsabilidade:** Prepara metadados (título, descrição, tags) e agenda uploads para o canal apropriado via YouTube Data API v3.
* **Regra de Ouro:** Upload sempre configurado com status `private` até liberação humana definitiva.

### 9. Inteligência de Desempenho
* **Responsabilidade:** Coleta de visualizações, likes, comentários e retenção após publicação para refinar os playbooks dos canais.

### 10. Administração e Finanças
* **Responsabilidade:** Apuração informativa de custos operacionais (tokens, infraestrutura), receitas de AdSense/parcerias e margem líquida.
* **Regra de Ouro:** O sistema informa; o proprietário decide alocações e investimentos.

---

## 3. Diretrizes de Governança e Segurança

1. **Human-in-the-Loop em 2 Portais:**
   * Portal 1: Nenhuma oportunidade entra em roteirização sem aprovação humana.
   * Portal 2: Nenhum vídeo é agendado ou publicado sem aprovação final do vídeo renderizado.
2. **Blindagem de Custos de IA:**
   * O sistema roda em modo `ENFORCE_FREE_TIER_ONLY`. Chamadas tarifadas exigem aprovação explícita.
3. **Isolamento de Memória por Canal:**
   * Todas as tabelas de conhecimento e vetores utilizam `channel_id` obrigatório para evitar misturar personalidades de canais.
4. **Armazenamento 5 TB no Google Drive:**
   * Arquivos pesados residem exclusivamente no Drive (13 pastas centrais + 20 subpastas de canais). O disco local atua apenas como buffer transitório.
