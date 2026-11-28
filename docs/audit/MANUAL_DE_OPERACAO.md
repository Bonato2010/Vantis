# VANTIS — MANUAL DE OPERAÇÃO DA CENTRAL DE MÍDIA

Este manual descreve o procedimento operacional padrão para a gestão, produção e governança dos canais de YouTube Shorts utilizando a plataforma **VANTIS (Central de Inteligência & Operações Audiovisuais)**.

---

## 1. Visão Geral da Operação

O VANTIS opera como o sistema operacional tecnológico de uma empresa de mídia automatizada, projetado para administrar até 20 canais com total isolamento editorial, financeiro e de armazenamento.

A operação é dividida em **10 departamentos coordenados por agentes autônomos**, integrando o **Pipeline Central VANTIS de 17 etapas** e dois **portais mandatórios de intervenção humana (Human-in-the-Loop)**:
- **Portal 1 (Seleção Editorial)**: Filtro e aprovação editorial de oportunidades mineradas no YouTube antes da roteirização.
- **Portal 2 (Aprovação Final de Publicação)**: Auditoria técnica de qualidade (QC) e autorização expressa para publicação no YouTube (estritamente em modo privado com token).

---

## 2. Como Iniciar a Central

### Método 1: Inicializador Rápido (Recomendado no Windows)
1. Navegue até a pasta do projeto: `C:\Users\jcvse\OneDrive\Desktop\Daniel\CENTRAL SHORTS`.
2. Dê um duplo clique no arquivo **`INICIAR_CENTRAL_IAS.bat`**.
3. O navegador padrão será aberto automaticamente em: **`http://127.0.0.1:8000`**.

### Método 2: Linha de Comando (PowerShell / Terminal)
```powershell
cd "C:\Users\jcvse\OneDrive\Desktop\Daniel\CENTRAL SHORTS"
python run_dashboard.py
```

O servidor FastAPI iniciará, aplicando automaticamente quaisquer migrações pendentes no banco relacional `database/shorts_central.db` e disponibilizando a interface web unificada.

---

## 3. Os 5 Canais Piloto em Operação

Cada canal possui persona, voz neural, estilo tipográfico de legendas e pasta dedicada no Google Drive 5 TB:

| Canal | Nome | Nicho | Voz Neural (Edge-TTS) | Estilo de Legenda (ASS) | Pasta Google Drive |
|---|---|---|---|---|---|
| **#01** | Futebol em 60 Segundos | `futebol_outros` | `pt-BR-AntonioNeural` (+15% velocidade) | Amarelo Neon / Impact Bold | `1Qcd6DS3zA0OrNKSeDSPTHyl_P0y0l9jf` |
| **#02** | Arquivo Sombrio | `casos_policiais` | `pt-BR-JulioNeural` (-5% taxa, tom grave) | Ciano / Arial Black | `1-77U0s31i8e-Z3p6lC4tqK-hV7hF1p2s` |
| **#03** | Rir para Não Chorar | `humor` | `pt-BR-FabioNeural` (+10% taxa, dinâmico) | Branco-Verde / Dinâmico | `1aBCdEFgHIJKLMNOPQRSTUVWXYZ012345` |
| **#04** | Mente Curiosa & Ciência | `curiosidades` | `pt-BR-FranciscaNeural` (Natural) | Ciano-Magenta / Roboto | `1bCDefGHIJKLMNOPQRSTUVWXYZ0123456` |
| **#05** | Mente Focada & Produtividade | `desenvolvimento_pessoal`| `pt-BR-ValerioNeural` (Ponderado) | Ouro / Trebuchet MS | `1cDEfgHIJKLMNOPQRSTUVWXYZ01234567` |

---

## 4. Operando o Portal 1: Mineração & Governança de Pautas

O **Portal 1** garante que nenhuma produção seja iniciada a partir de ideias artificiais ou alucinações. Todas as referências são coletadas de vídeos reais do YouTube via `yt-dlp`.

### Procedimento Passo a Passo:
1. No menu lateral, clique em **`Portal 1: Oportunidades`**.
2. No painel superior, selecione o **Canal/Nicho** desejado (ex: *Canal 01 — Futebol*).
3. Digite um termo de busca no campo de consulta (ex: `golaço historico copa` ou deixe em branco para tendências do nicho).
4. Defina a quantidade de pautas a minerar (padrão: 5).
5. Clique em **"Varrer YouTube"**.
6. As oportunidades mineradas aparecerão na tabela abaixo com suas métricas reais (Views, Likes, Canal Fonte e Link original).
7. Para cada pauta:
   - Clique em **"Aprovar"** para liberar a oportunidade para produção de roteiro e indexá-la na memória semântica do canal.
   - Clique em **"Rejeitar"** para arquivar a pauta, informando a justificativa editorial (ex: *fora da persona*).

---

## 5. O Pipeline Central VANTIS (17 Etapas)

Ao aprovar uma pauta ou disparar um fluxo, o motor de orquestração executa o Pipeline Central VANTIS:

```
[01] Descoberta (yt-dlp)
   ↓
[02] Pesquisa (Metadados e Catálogo)
   ↓
[03] Análise de Tendências (Velocidade & Engajamento)
   ↓
[04] Seleção Editorial → PORTAL 1 (Validação Humana Mandatória)
   ↓
[05] Análise Audiovisual (PySceneDetect + OpenCV)
   ↓
[06] Transcrição (Faster-Whisper com Timestamps)
   ↓
[07] Identificação de Momentos & Ganchos (FastEmbed ONNX)
   ↓
[08] Roteirização Estruturada (LiteLLM & OmniRoute)
   ↓
[09] Preparação de Materiais (Edge-TTS por Canal)
   ↓
[10] Edição de Vídeo (Composição 9:16)
   ↓
[11] Legendas Dinâmicas (SubtitleGenerator ASS)
   ↓
[12] Renderização Vertical (FFmpeg 1080x1920 EBU R128 -14 LUFS)
   ↓
[13] Controle de Qualidade (QC Agent - Validação Técnica)
   ↓
[14] Aprovação Humana → RETENÇÃO NO PORTAL 2 (Aprovação com Token)
   ↓ (Pausa mandatória para validação humana)
[15] Preparação para Publicação (Upload 100% Privado + Backup Drive 5 TB)
   ↓
[16] Coleta de Métricas & Telemetria
   ↓
[17] Aprendizado Contínuo (Retroalimentação na Memória Vetorial por Canal)
```

Cada etapa salva seu estado no banco de dados (`workflow_checkpoints`), garantindo que a execução possa ser pausada, inspecionada e retomada sem perda de dados.

---

## 6. Operando o Portal 2: Estação de Inspeção Audiovisual & QC

O **Portal 2** é o portão de segurança final da plataforma. **Nenhum vídeo pode ser publicado sem aprovação humana expressa.**

### Procedimento Passo a Passo:
1. No menu lateral, clique em **`Portal 2: Aprovação & QC`**.
2. Os vídeos finalizados e retidos aparecerão como cartões de inspeção contendo:
   - **Player Audiovisual**: Reproduza o vídeo vertical ou a narração neural diretamente no navegador.
   - **Roteiro Estruturado**: Inspecione o texto completo do Hook (gancho), desenvolvimento e chamada para ação.
   - **Auditoria de Qualidade (Agente QC)**:
     - Formato 1080x1920 9:16 (OK)
     - Duração entre 15s e 59s (OK)
     - Normalização de áudio EBU R128 a -14 LUFS (OK)
     - Sincronização de eventos de legenda ASS (OK)
     - Pontuação de Conformidade (0 a 100)
3. No rodapé do cartão, confira o **Token de Aprovação Humana** (gerado automaticamente no formato `PORTAL2_TOKEN_XXXXXX`).
4. Clique no botão:
   **`APROVAR E PUBLICAR PRIVADO NO YOUTUBE (Portal 2)`**.
5. Confirme o diálogo de segurança. O sistema executará a etapa 12, gerando o manifesto de auditoria e registrando a publicação.

---

## 7. Distribuição Segura e Armazenamento Google Drive 5 TB

### Regras de Segurança Invioláveis:
- **Status de Privacidade Forçado**: Todos os uploads gerados pelo IAS são forçados para `privacyStatus = 'private'`. Nenhuma rotina de código possui permissão para publicar como `public` automaticamente.
- **Manifesto de Auditoria**: Cada publicação gera um arquivo `workspace/clips/manifest_{task_id}.json` contendo hash, metadados, token do operador humano, carimbo de data/hora e identificadores no Drive e YouTube.
- **Modo Zero Armazenamento Local Permanente**: Arquivos brutos e temporários gerados durante o processamento são transferidos para as respectivas pastas dos canais no Google Drive e expurgados do disco local após a auditoria.

### Conexão e Sincronização com o Drive:
Para renovar ou conectar a conta oficial de 5 TB de Daniel, execute o atalho:
`CONECTAR MEU GOOGLE DRIVE.bat`

---

## 8. Barreira de Custo Zero ($0.00)

O IAS opera com uma política rígida de despesas:
- **`enforce_free_tier = True`**: Todas as chamadas para modelos comerciais (GPT-4, Claude) são interceptadas pelo `ModelGateway` e desviadas para alternativas gratuitas (Gemini 2.5 Flash gratuito, Groq LLaMA 3.3, Ollama local ou síntese contextual interna).
- **Edge-TTS Neural Gratuito**: Narrações de alta fidelidade utilizam o serviço neural gratuito da Microsoft, sem necessidade de chaves de API pagas da ElevenLabs.
- **FFmpeg & Faster-Whisper Locais**: Todo o processamento de áudio, renderização de canvas, transcrição e corte de legendas executa localmente no hardware da estação de trabalho.

---

## 9. Manutenção & Testes Automatizados

Para verificar a integridade completa da plataforma a qualquer momento, execute a suíte de testes unificada cobrindo todas as 10 fases:

```powershell
# Executar a bateria completa de 67 testes (100% de sucesso):
python run_all_tests.py
```

Ou execute individualmente por fase:
```powershell
python tests/test_fase1_foundation.py
python tests/test_fase2_orchestration.py
python tests/test_fase3_multichannel.py
python tests/test_fase4_discovery_portal1.py
python tests/test_fase5_audiovisual.py
python tests/test_fase6_distribution.py
python tests/test_fase7_dashboard.py
python tests/test_fase8_vantis_pipeline.py
python tests/test_fase9_agent_architecture.py
python tests/test_fase10_audiovisual_pipeline.py
```

Todas as 10 suítes (67 testes) devem retornar `OK` com integridade operacional garantida.

---

## 10. Os 10 Agentes Operacionais Autônomos (Fase 9)

A plataforma conta com 10 agentes especializados registrados no `AgentRegistry`:
1. **`agt_opp_research` (OpportunityResearchAgent)**: Coleta e validação de tendências reais via `yt-dlp`.
2. **`agt_trend_analysis` (TrendAnalysisAgent)**: Cálculo de velocidade e projeção de viralidade.
3. **`agt_editorial_planner` (EditorialPlanningAgent)**: Verificação de persona, vocabulário e retenção no Portal 1.
4. **`agt_scriptwriter` (ScriptwritingAgent)**: Redação de roteiros estruturados adaptados ao canal.
5. **`agt_audiovisual_analyzer` (AudiovisualAnalysisAgent)**: Detecção de cenas (PySceneDetect) e crop vertical 9:16 (OpenCV).
6. **`agt_transcription` (TranscriptionAgent)**: Transcrição Faster-Whisper com timestamps detalhados.
7. **`agt_media_prep_editing` (MediaPrepEditingAgent)**: Síntese de voz Edge-TTS, legendas dinâmicas ASS e renderização FFmpeg.
8. **`agt_quality_reviewer` (QualityReviewAgent)**: Auditoria técnica QC antes da liberação para o Portal 2.
9. **`agt_performance_analytics` (PerformanceAnalyticsAgent)**: Telemetria de retenção, cálculo de economia ($0.00 gasto) e aprendizado contínuo.
10. **`agt_coordinator_distributor` (TaskCoordinatorAgent)**: Coordenação de ciclo de vida e distribuição com upload privado e aprovação humana.

---

## 11. O Pipeline de Produção e Processamento Audiovisual (Fase 10 / Bloco B)

O pipeline audiovisual opera de forma industrial em 10 etapas sequenciais e rastreáveis:
1. **Validação de Entrada**: Verificação de integridade física e de contêiner. Arquivos truncados ou corrompidos são rejeitados de imediato.
2. **Metadados e Direitos Autorais**: Extração técnica (FFprobe) e conformidade de direitos (proíbe reuploads não-transformativos).
3. **Transcrição Acelerada**: Faster-Whisper com timestamps em nível de palavra e frase.
4. **Análise de Cenas**: PySceneDetect para detecção de transições e OpenCV para Smart Crop 9:16 dinâmico.
5. **Seleção de Trechos**: Validação de cortes para o padrão de YouTube Shorts (15.0s a 59.0s).
6. **Preparação de Edição**: Configuração de layout, estilo visual de legendas ASS e voz neural por canal.
7. **Renderização FFmpeg**: Normalização EBU R128 (-14 LUFS) e renderização vertical H.264/AAC a 30fps.
8. **Previews e Miniaturas**: Geração de preview e extração de thumbnail de alta resolução (`.jpg`) no clímax do gancho inicial.
9. **Auditoria de Qualidade (QC)**: Checagem automatizada de 7 critérios antes de avançar para o Portal 2.
10. **Registro e Manifesto**: Gravação na tabela `audiovisual_pipeline_runs` do SQLite e preparação para revisão humana.
