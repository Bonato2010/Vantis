# IAS — Tecnologias e Repositórios Open Source Essenciais

Este documento detalha as 8 tecnologias fundamentais integradas à plataforma **IAS (Intelligence & Automation System)**, especificando suas licenças, motivações arquiteturais, modos de execução, requisitos de hardware e políticas de contingência (fallback).

---

## Matriz Resumo das Tecnologias

| Tecnologia | Repositório Oficial | Licença | Função no IAS | Hardware / Custo | Modo Contingência (Fallback) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LangGraph** | `langchain-ai/langgraph` | MIT | Orquestração do pipeline em 12 etapas com checkpoints | CPU / Gratuito | Grafo de estados sequencial nativo |
| **pgvector** | `pgvector/pgvector` | PostgreSQL (MIT-style) | Memória semântica vetorial e busca por similaridade | CPU / Gratuito | Vetorização local em Numpy + SQLite |
| **WhisperX / Faster-Whisper** | `m-bain/whisperX` + `SYSTRAN/faster-whisper` | BSD-4 / Apache 2.0 | Transcrição temporal alinhada por palavra e legendas ASS | CPU/GPU (CUDNN) | Faster-Whisper CPU com VAD |
| **PySceneDetect** | `Breakthrough/PySceneDetect` | BSD-3 | Detecção visual de cortes e transições de cena | CPU / Gratuito | Filtro de cena nativo do FFmpeg |
| **LiteLLM** | `BerriAI/litellm` | Apache 2.0 | Gateway multi-provedor (Gemini/OpenAI/Claude/Ollama) | CPU / Por token usado | Provedor direto via SDK / mock seguro |
| **yt-dlp** | `yt-dlp/yt-dlp` | Unlicense | Catalogação de metadados e máquina de estados | CPU / Gratuito | Ingestão manual de metadados JSON |
| **FFmpeg** | `FFmpeg/FFmpeg` | LGPL / GPL | Renderização 9:16 vertical, áudio EBU R128 e queima ASS | CPU/GPU (NVENC) | Renderização CPU via libx264 |
| **OpenCV** | `opencv/opencv` | Apache 2.0 | Análise de enquadramento, movimento e Smart Crop 9:16 | CPU / Gratuito | Crop central estático proporcional |

---

## 1. Orquestração — LangGraph
- **Repositório:** `https://github.com/langchain-ai/langgraph`
- **Motivação:** Permite que as 12 etapas do IAS (Pesquisa → Catalogação → Metadados → Transcrição → Análise → Padrões → Agentes → Roteiros → Materiais → Edição → Revisão → Distribuição) operem em um fluxo persistente, rastreável e capaz de retomar execuções interrompidas a partir de checkpoints.
- **Configuração:** Gerenciado em `services/orchestration/langgraph_engine.py`.
- **Como Desativar/Substituir:** A classe `IASOrchestrationEngine` possui detecção automática: se a biblioteca não estiver presente, chaveia para o executor síncrono nativo sem interrupção de serviço.

---

## 2. Memória Semântica — pgvector
- **Repositório:** `https://github.com/pgvector/pgvector`
- **Motivação:** Permite pesquisar ganchos virais, temas de podcasts e estruturas narrativas por **significado e contexto**, e não apenas por palavras-chave exatas.
- **Banco de Dados:** Utiliza PostgreSQL com a extensão `pgvector`. Quando a variável `DATABASE_URL` não for fornecida ou o Postgres estiver offline, o adaptador comuta automaticamente para o motor vetorial local embutido em `services/semantic_memory/vector_memory.py` utilizando cálculos de distância de cosseno via Numpy e persistência em SQLite.
- **Migrações:** O script `services/semantic_memory/migrations/001_pgvector_setup.sql` contém a DDL completa (tabelas de vetores, índices HNSW/IVFFlat).

---

## 3. Transcrição e Alinhamento — WhisperX / Faster-Whisper
- **Repositório:** `https://github.com/m-bain/whisperX` e `https://github.com/SYSTRAN/faster-whisper`
- **Motivação:** Cortes curtos para YouTube Shorts dependem de legendas dinâmicas perfeitamente sincronizadas ao milissegundo. O Faster-Whisper (já instalado e testado) fornece processamento rápido em CTranslate2; o WhisperX adiciona alinhamento fonético preciso e identificação de locutores (diarização).
- **Saída:** O módulo `services/transcription/whisper_service.py` gera legendas `.ass` estilizadas no padrão viral (destaque de palavras-chave, cores de alto contraste para 9:16).

---

## 4. Detecção de Cenas — PySceneDetect
- **Repositório:** `https://github.com/Breakthrough/PySceneDetect`
- **Motivação:** Detecta alterações bruscas e graduais de enquadramento para identificar cortes ideais, calcular o ritmo visual (BPM) e evitar cortes no meio de falas ou reações.
- **Configuração:** Gerenciado em `services/video_analysis/scene_detector.py`.
- **Fallback:** Se o PySceneDetect não estiver disponível, o serviço utiliza o filtro interno do FFmpeg `select='gt(scene,0.3)'` para extrair timestamps de corte.

---

## 5. Gateway de Modelos — LiteLLM
- **Repositório:** `https://github.com/BerriAI/litellm`
- **Motivação:** Centraliza chamadas para dezenas de provedores de IA (Google Gemini, OpenAI GPT, Anthropic Claude, Groq Llama, Ollama local), oferecendo fila de contingência (fallback automático em caso de rate-limit) e rastreamento rigoroso de custos e tokens.
- **Segurança:** Configurado em `services/model_gateway/gateway.py`. As chaves de API residem exclusivamente em variáveis de ambiente (`GEMINI_API_KEY`, `OPENAI_API_KEY`, etc.), nunca sendo expostas em logs ou na interface web.

---

## 6. Análise e Catalogação — yt-dlp
- **Repositório:** `https://github.com/yt-dlp/yt-dlp`
- **Motivação:** Extrai metadados completos de referências (duração, autor, tags, transcrições embutidas) com suporte à máquina de estados estrita:
  `catalogado → acessível → autorizado → analisado → aprovado para produção`.
- **Conformidade:** O download bruto de mídia é condicionado à autorização expressa do produtor de conteúdo.

---

## 7. Processamento Audiovisual — FFmpeg
- **Repositório:** `https://github.com/FFmpeg/FFmpeg`
- **Motivação:** Motor de renderização de alto desempenho para conversão em proporção vertical 9:16 (1080x1920), normalização de áudio em loudness padrão broadcast (EBU R128: -14 LUFS para Shorts/TikTok) e geração de variantes anti-duplicação para múltiplos canais.
- **Configuração:** Gerenciado em `services/media_processing/ffmpeg_engine.py`, com localização automática do executável do sistema ou winget.

---

## 8. Análise Visual e Enquadramento — OpenCV
- **Repositório:** `https://github.com/opencv/opencv`
- **Motivação:** Permite o **Smart Crop 9:16**. Em vez de aplicar um corte estático no centro do vídeo horizontal (o que frequentemente corta o rosto do participante), o OpenCV calcula a região de maior saliência/movimento ou rastreia a posição do interlocutor para centralizar o enquadramento vertical de forma fluida.
- **Configuração:** `services/video_analysis/visual_analyzer.py`.
