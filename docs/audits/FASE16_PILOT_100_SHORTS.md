# VANTIS — RELATÓRIO DO PILOTO CONTROLADO DA FASE 16
## Piloto Controlado de 100 Shorts | Validação de Escala, Rigor Físico e Aprendizado Real

**Data de Auditoria e Consolidação:** 24 de Novembro de 2026  
**Ambiente de Execução:** Antigravity IDE (`branch: develop` em `CENTRAL SHORTS / IAS`)  
**Repositório Espelho:** `C:\Users\jcvse\podcast_cutter` (`branch: develop`)  
**Base Relacional:** `database/shorts_central.db` (SQLite WAL)  
**Custo Real Apurado:** **$0.00 (Política de Custo Zero estritamente ativa)**  
**Veredicto Final do Gate:** **PILOTO APROVADO — PRONTO PARA AUDITORIA DE ESCALA**  
**Restrição Mandatória:** **NÃO INICIAR OS 7.000 VÍDEOS NESTA FASE.**  

---

## 1. VEREDITO FINAL E RESUMO CONSOLIDADO

A Fase 16 executou, auditou e reprocessou integralmente o piloto controlado de **100 YouTube Shorts únicos**, confirmando operacionalidade ponta a ponta sem métricas sintéticas, sem placeholders narrativos e sem valores fixos no dashboard:

- **Veredito Final:** **PILOTO APROVADO — PRONTO PARA AUDITORIA DE ESCALA**
- **Vídeos Selecionados:** 100 (20 únicos por canal nos 5 canais)
- **Vídeos Baixados:** 100 arquivos físicos em `workspace/downloads/pilot100/ch_{1..5}/`
- **Arquivos Fisicamente Validados:** 100 (SHA256 completo 64-char, decodificação FFmpeg `-v error -f null -` OK, leitura de frames OpenCV OK, duração entre 5.08s e 59.92s)
- **Análises Técnicas Completas:** 100 (visual PySceneDetect + OpenCV + acústica FFmpeg EBU R128 `-vn` + transcrição local Faster-Whisper CPU)
- **Análises Editoriais Completas:** 100 (97 aprovados / 3 rejeitados por critérios contextuais ou acústicos)
- **Candidatos a Aprendizado:** 97
- **Rejeições:** 3 (1 áudio silencioso `-70.0 LUFS` + 2 desvios editoriais contextuais genuínos)
- **Falhas Técnicas / Corrupção:** 0 (0 arquivos corrompidos, 0 falhas de decodificação)
- **Aprendizados Gerados e Validados (Fase 16):** 23 registros na Fase 16 (15 `APRENDIZADO_VALIDADO`, 5 `OBSERVAÇÃO`, 3 `ANTI_PATTERN`)
- **Custo Real:** **$0.00**
- **Armazenamento Utilizado:** **840,630,006 bytes (801.69 MB)**
- **Testes Executados:** **18/18 suítes / 160/160 testes unitários aprovados (100.0%, exit code 0)**, incluindo 23 testes específicos da Fase 16

---

## 2. GATE DE PRÉ-EXECUÇÃO VERIFICADO

| Item | Requisito | Evidência Auditada | Status |
|---|---|---|:---:|
| 1 | Branch atual `develop` | `CENTRAL SHORTS` e `podcast_cutter` na branch `develop`; `main` preservada | **CONFORME** |
| 2 | Repositório principal íntegro | Migrações `001` a `008` aplicadas; dados históricos (`id <= 43`, `knowledge <= 64`) preservados | **CONFORME** |
| 3 | Ausência de conflitos não relacionados | Working tree controlada e sincronizada antes dos commits | **CONFORME** |
| 4-5 | Bateria completa de testes e exit code | `python scripts/run_all_tests.py` -> 18/18 suítes, 160/160 testes PASS, `exit code 0` | **CONFORME** |
| 6 | FFmpeg, OpenCV, PySceneDetect, Whisper | `ffmpeg 9.1-full_build`, `OpenCV 4.10.0`, `PySceneDetect (pyav)`, `faster_whisper tiny` | **CONFORME** |
| 7 | Espaço em disco suficiente | > 295 GB livres para ~802 MB usados | **CONFORME** |
| 8 | Configuração de custo zero | `ModelGatewayService(enforce_free_tier=True)` -> `$0.00` | **CONFORME** |
| 9 | Checkpoint e retomada idempotente | Tabela `learning_batch_checkpoints` (`batch_id = 'pilot_100_fase16'`) | **CONFORME** |
| 10 | Script validado + circuit breakers | `scripts/execute_pilot_100_shorts.py` com 5 gatilhos de circuit breaker testados | **CONFORME** |

---

## 3. RESULTADOS POR CANAL (20 SHORTS POR CANAL)

| Canal ID | Canal | Nicho | Selecionados | Baixados / Validados | Aprovados (`learning_candidate`) | Rejeitados (`editorially_rejected`) | Com Fala Transcrita | Taxa Sucesso Técnico | Armazenamento |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | Canal 01: Futebol em 60 Segundos | `futebol_outros` | 20 | 20 | 19 | 1 | 14/20 | 100.0% | 299.56 MB |
| **2** | Canal 02: Arquivo Sombrio (Casos Reais) | `casos_policiais` | 20 | 20 | 19 | 1 | 15/20 | 100.0% | 178.77 MB |
| **3** | Canal 03: Rir para Não Chorar (Humor) | `humor` | 20 | 20 | 19 | 1 | 18/20 | 100.0% | 65.57 MB |
| **4** | Canal 04: Mente Curiosa & Ciência | `curiosidades` | 20 | 20 | 20 | 0 | 14/20 | 100.0% | 170.05 MB |
| **5** | Canal 05: Mente Focada & Produtividade | `desenvolvimento_pessoal` | 20 | 20 | 20 | 0 | 18/20 | 100.0% | 87.72 MB |
| **TOTAL** | **5 Canais Piloto** | **Multi-nicho** | **100** | **100** | **97** | **3** | **79/100** | **100.0%** | **801.69 MB** |

---

## 4. ANÁLISE MULTIMODAL FÍSICA E TRANSPARÊNCIA METODOLÓGICA

### 4.1. Integridade Física, Codecs e Proporção Real de Tela
- **Decodificação FFmpeg (`ffmpeg -v error -f null -`) e Leitura OpenCV:** 100/100 vídeos decodificados com zero falhas.
- **Duração Física Real:** Mínima `5.08s`, Máxima `59.92s` (0 vídeos $> 60.0$s admitidos).
- **Distribuição de Codecs de Vídeo:** `h264` (52), `av1` (27), `vp9` (21)
- **Distribuição de Codecs de Áudio:** `opus` (100)
- **Proporção Real Medida (FFprobe):** Apenas **`0/100` são nativamente `9:16` verticais (`height > width`)**; os 100 vídeos coletados via `ytsearch` (`duration <= 60`) são majoritariamente clipes curtos em `1920:1080` (0), `1280:720` (0), `3840:2160` (0) e formatos `4:3`/`16:9`. Este achado real é documentado explicitamente em limitações e na recomendação de escala (evitando alegar enquadramento `9:16` inexistente nos arquivos baixados).

### 4.2. Análise Visual Real (PySceneDetect `pyav` + OpenCV)
- **Cenas e Cortes:** Média de 6.0 cortes por vídeo (mínimo 0, máximo 45), com intervalos reais entre cortes (`cut_intervals_sec`, `avg_cut_interval_sec`) persistidos em `analysis_payload.visual_and_editing`.
- **Frames Representativos, Movimento e Texto na Tela:** Amostragem de até 5 frames espaçados por vídeo (`representative_frames`), variação de enquadramento medida por deslocamento de centro de massa de movimento (`framing_changes_detected`) e detecção de texto na tela por densidade de bordas Sobel nas faixas superior/inferior (`opencv_sobel_band_density`), substituindo valores fixos anteriores.

### 4.3. Análise Acústica Real (FFmpeg EBU R128 com `-vn`)
| Classificação Acústica | Faixa / Critério | Quantidade | Observação |
|---|---|:---:|---|
| `VALID_AUDIO` | -24.0 a -6.0 LUFS | 86 | Áudio comercial utilizável |
| `QUIET_AUDIO_TRACK` | -65.0 a -24.0 LUFS | 12 | Audível com volume baixo |
| `HOT_LOUD_AUDIO` | > -6.0 LUFS (clipping potencial) | 1 | Volume elevado / risco de clipping |
| `SILENT_AUDIO_TRACK` | <= -65.0 LUFS | 1 | Rejeição compulsória (`2TFGeAHjPA8` em -70.0 LUFS) |
| `NO_AUDIO_TRACK` / `DECODING_FAILURE` / `MEASUREMENT_FAILURE` | Falha de stream/codec/filtro | 0 | Zero falhas após correção `-vn` em 4K |

### 4.4. Análise Narrativa Real (Legendas + Faster-Whisper CPU Local)
- **79/100 vídeos** obtiveram transcrição real com identificação de `hook_type`, `narrative_structure`, `development_summary`, `transitions_detected`, `conclusion_type`, `has_call_to_action` e `multimodal_correlation`.
- **21/100 vídeos** (musicais/sem fala audível detectada) foram registrados honestamente com `narrative_analysis_status = "insufficient_speech_evidence"` (`speech_detected = false`), sem gerar métricas falsas de WPM ou placeholders textuais.

---

## 5. REJEIÇÕES REAIS AUDITADAS (SEM IDs FORÇADOS)

| Video ID | Canal | Título Real | Loudness / Acústica | Veredicto | Motivo Real Registrado no Banco |
|---|---|---|---|---|---|
| `2TFGeAHjPA8` | C1 (`futebol_outros`) | Drible do Riquelme esse é monstro | -70.0 LUFS (`SILENT_AUDIO_TRACK`) | `REJECTED_SILENT_AUDIO` | silent_audio_track: SILENT_AUDIO_TRACK (-70.0 LUFS) unusable for acoustic/editorial learning (Item 9 guard) |
| `tfJSsxukhKY` | C2 (`casos_policiais`) | Testando essa belezinha Br Policia Simulator #Shorts | -2.7 LUFS (`HOT_LOUD_AUDIO`) | `REJECTED_OFF_TOPIC` | editorial_mismatch: context 'simulator' (jogo_simulador) incompatible with Canal 02 - Arquivo Sombrio (Casos Reais) (casos_policiais) |
| `GggELAqG63s` | C3 (`humor`) | 5 EFEITOS SONOROS DE SURPRESA + LINK GRATUITO DOS SONS- | -10.8 LUFS (`VALID_AUDIO`) | `REJECTED_OFF_TOPIC` | editorial_mismatch: context 'efeitos sonoros' (pack_recursos_edicao) incompatible with Canal 03 - Rir para Não Chorar (humor) |

---

## 6. APRENDIZADOS GERADOS, REGRA DE OURO E ISOLAMENTO DE CANAIS

Todos os registros gerados na Fase 16 (`pilot_phase: 16`, totalizando 23 entradas isoladas dos registros históricos das Fases 14–15.1) possuem `target_channel_id` estrito, `evidence_video_ids`, `confidence_explanation`, `counterexamples` e `limitations`:

| ID | Canal | Classificação | Confiança | Evidências | Título | Limitação Documentada |
|:---:|:---:|---|:---:|:---:|---|---|
| **104** | Canal 1 | `APRENDIZADO_VALIDADO` | 0.92 | 6 | Cortes Ágeis (>= 4) em Vídeos Curtos de Canal 01 - Futebol em 60 Segundos | Observação estrutural de ritmo de edição; não substitui curva real de ... |
| **105** | Canal 1 | `APRENDIZADO_VALIDADO` | 0.93 | 6 | Loudness Efetivo (-24 a -6 LUFS) em Canal 01 - Futebol em 60 Segundos | Medição de loudness não distingue isoladamente música instrumental de ... |
| **106** | Canal 1 | `APRENDIZADO_VALIDADO` | 0.90 | 6 | Presença de Narração Estruturada em Canal 01 - Futebol em 60 Segundos | Transcrição automática Whisper (modelo tiny em CPU) pode conter imprec... |
| **107** | Canal 1 | `OBSERVAÇÃO` | 0.65 | 1 | Plano Contínuo (< 4 cortes) em Canal 01 - Futebol em 60 Segundos | Amostra única (N=1); insuficiência estatística por definição.... |
| **108** | Canal 1 | `ANTI_PATTERN` | 0.90 | 1 | Anti-Pattern Detectado em Canal 01 - Futebol em 60 Segundos: 2TFGeAHjPA8 | Baseado na ocorrência específica identificada durante o lote piloto.... |
| **109** | Canal 2 | `APRENDIZADO_VALIDADO` | 0.92 | 6 | Cortes Ágeis (>= 4) em Vídeos Curtos de Canal 02 - Arquivo Sombrio (Casos Reais) | Observação estrutural de ritmo de edição; não substitui curva real de ... |
| **110** | Canal 2 | `APRENDIZADO_VALIDADO` | 0.93 | 6 | Loudness Efetivo (-24 a -6 LUFS) em Canal 02 - Arquivo Sombrio (Casos Reais) | Medição de loudness não distingue isoladamente música instrumental de ... |
| **111** | Canal 2 | `APRENDIZADO_VALIDADO` | 0.90 | 6 | Presença de Narração Estruturada em Canal 02 - Arquivo Sombrio (Casos Reais) | Transcrição automática Whisper (modelo tiny em CPU) pode conter imprec... |
| **112** | Canal 2 | `OBSERVAÇÃO` | 0.65 | 1 | Plano Contínuo (< 4 cortes) em Canal 02 - Arquivo Sombrio (Casos Reais) | Amostra única (N=1); insuficiência estatística por definição.... |
| **113** | Canal 2 | `ANTI_PATTERN` | 0.70 | 1 | Anti-Pattern Detectado em Canal 02 - Arquivo Sombrio (Casos Reais): tfJSsxukhKY | Baseado na ocorrência específica identificada durante o lote piloto.... |
| **114** | Canal 3 | `APRENDIZADO_VALIDADO` | 0.92 | 4 | Cortes Ágeis (>= 4) em Vídeos Curtos de Canal 03 - Rir para Não Chorar | Observação estrutural de ritmo de edição; não substitui curva real de ... |
| **115** | Canal 3 | `APRENDIZADO_VALIDADO` | 0.93 | 6 | Loudness Efetivo (-24 a -6 LUFS) em Canal 03 - Rir para Não Chorar | Medição de loudness não distingue isoladamente música instrumental de ... |
| **116** | Canal 3 | `APRENDIZADO_VALIDADO` | 0.90 | 6 | Presença de Narração Estruturada em Canal 03 - Rir para Não Chorar | Transcrição automática Whisper (modelo tiny em CPU) pode conter imprec... |
| **117** | Canal 3 | `OBSERVAÇÃO` | 0.65 | 1 | Plano Contínuo (< 4 cortes) em Canal 03 - Rir para Não Chorar | Amostra única (N=1); insuficiência estatística por definição.... |
| **118** | Canal 3 | `ANTI_PATTERN` | 0.70 | 1 | Anti-Pattern Detectado em Canal 03 - Rir para Não Chorar: GggELAqG63s | Baseado na ocorrência específica identificada durante o lote piloto.... |
| **119** | Canal 4 | `APRENDIZADO_VALIDADO` | 0.92 | 6 | Cortes Ágeis (>= 4) em Vídeos Curtos de Canal 04 - Mente Curiosa & Ciência | Observação estrutural de ritmo de edição; não substitui curva real de ... |
| **120** | Canal 4 | `APRENDIZADO_VALIDADO` | 0.93 | 6 | Loudness Efetivo (-24 a -6 LUFS) em Canal 04 - Mente Curiosa & Ciência | Medição de loudness não distingue isoladamente música instrumental de ... |
| **121** | Canal 4 | `APRENDIZADO_VALIDADO` | 0.90 | 6 | Presença de Narração Estruturada em Canal 04 - Mente Curiosa & Ciência | Transcrição automática Whisper (modelo tiny em CPU) pode conter imprec... |
| **122** | Canal 4 | `OBSERVAÇÃO` | 0.65 | 1 | Plano Contínuo (< 4 cortes) em Canal 04 - Mente Curiosa & Ciência | Amostra única (N=1); insuficiência estatística por definição.... |
| **123** | Canal 5 | `APRENDIZADO_VALIDADO` | 0.92 | 6 | Cortes Ágeis (>= 4) em Vídeos Curtos de Canal 05 - Mente Focada & Produtividade | Observação estrutural de ritmo de edição; não substitui curva real de ... |
| **124** | Canal 5 | `APRENDIZADO_VALIDADO` | 0.93 | 6 | Loudness Efetivo (-24 a -6 LUFS) em Canal 05 - Mente Focada & Produtividade | Medição de loudness não distingue isoladamente música instrumental de ... |
| **125** | Canal 5 | `APRENDIZADO_VALIDADO` | 0.90 | 6 | Presença de Narração Estruturada em Canal 05 - Mente Focada & Produtividade | Transcrição automática Whisper (modelo tiny em CPU) pode conter imprec... |
| **126** | Canal 5 | `OBSERVAÇÃO` | 0.65 | 1 | Plano Contínuo (< 4 cortes) em Canal 05 - Mente Focada & Produtividade | Amostra única (N=1); insuficiência estatística por definição.... |

---

## 7. TELEMETRIA DO DASHBOARD CONSISTENTE COM O BANCO DE DADOS

Valores extraídos diretamente de `AudiovisualLearningSystem.get_dashboard_overview()['pilot_fase16_metrics']` (expostos também em `/api/learning/pilot-forensic` e exibidos no painel Fase 16 em `web/static/index.html`):

```json
{
  "pilot_name": "Fase 16 - Piloto Controlado 100 Shorts",
  "candidates_selected": 100,
  "total_shorts_pilot": 100,
  "downloaded": 100,
  "physically_validated": 100,
  "technically_analyzed": 100,
  "editorially_analyzed": 100,
  "editorially_approved": 97,
  "editorially_rejected": 3,
  "silent_audio_detected": 1,
  "learning_candidates": 97,
  "validated_learnings": 15,
  "total_knowledge_recorded": 23,
  "failures": 0,
  "cost_usd": 0.0,
  "storage_used_bytes": 840630006,
  "storage_used_mb": 801.69,
  "success_rate_per_channel": {
    "1": 100.0,
    "2": 100.0,
    "3": 100.0,
    "4": 100.0,
    "5": 100.0
  },
  "circuit_breakers_triggered": 0
}
```

---

## 8. PROBLEMAS ENCONTRADOS E CORREÇÕES REALIZADAS

Durante a auditoria rigorosa dos artefatos da Fase 16 antes da declaração final, os seguintes problemas reais foram detectados e corrigidos:

1. **Timeout EBU R128 em vídeos 4K (`sp7KGFCNjJk`):** `FFmpegEngine.measure_loudness()` decodificava o stream de vídeo VP9 3840x2160 junto com o áudio, estourando o timeout de 30s e classificando erroneamente o vídeo como `DECODING_FAILURE` / `-70.0 LUFS`. **Correção:** adição de `-vn` no comando FFmpeg e separação real entre `DECODING_FAILURE` (`verify_decode_integrity`) e `MEASUREMENT_FAILURE`. Com isso, `sp7KGFCNjJk` mediu `-18.7 LUFS` (`VALID_AUDIO`).
2. **Ausência de transcrição real em 92/100 vídeos:** A execução anterior usava string placeholder quando não havia legenda prévia no YouTube. **Correção:** remoção total do fallback sintético e integração do `WhisperTranscriptionService` (`faster_whisper` modelo `tiny` em CPU, custo `$0.00`), resultando em 79 transcrições faladas reais e 21 marcações honestas de `insufficient_speech_evidence`.
3. **Rejeições editoriais forçadas manualmente (`INTENTIONAL_REJECTION_IDS`):** O script anterior forçava rejeição artificial em `WyS5Ijgirtw` (abordagem policial real no Canal 2) e `r3CribedVGU` (disciplina no Canal 5), enquanto aprovava `tfJSsxukhKY` (simulador de jogo) e `GggELAqG63s` (pack de efeitos sonoros). **Correção:** remoção integral de `INTENTIONAL_REJECTION_IDS` e implementação de avaliação contextual real (`title + transcrição + descrição`) em `evaluate_editorial_adherence()`.
4. **Falso positivo lexical (`'vestido'` em letra de rap):** A substring `'vestido'` rejeitou indevidamente `xWxw0PIZWrU` (`#Shorts #PoliciaCivil`). **Correção:** refino para termos inequívocos de vestuário (`vestido feminino`, `vestido longo`) e limpeza de `discard_reason` no SQL quando um vídeo é aprovado em reavaliação.
5. **Métricas visuais e proporção de tela sem verificação real:** Substituição de `has_subtitles_on_screen=True` e `cuts_count // 2` por medição OpenCV (`Sobel band density`, `framing_changes_detected`, `representative_frames`), intervalos reais de corte do PySceneDetect (`backend='pyav'`, 10x mais rápido em AV1), e reporte honesto da proporção real (`0/100` nativos 9:16).
6. **Valores fixos no Dashboard e testes ausentes:** Remoção de literais fixos (`100`, `0.0`, `0`) em `pilot_fase16_metrics` para leitura estrita de SQLite/`ModelGatewayService`, exposição na UI (`web/static/index.html`), e adição de 7 novos testes cobrindo arquivo ausente, corrompido, hash incorreto, sem áudio, falha de decodificação, checkpoint/retomada e todos os gatilhos de circuit breakers (`23/23` testes na Fase 16; `160/160` no total).

---

## 9. EVIDÊNCIAS, ARQUIVOS JSON E RECOMENDAÇÃO PARA PRÓXIMA FASE

- **Manifesto de Seleção (100 candidatos únicos):** `docs/audits/phase16_selected_candidates.json`
- **Dados Consolidados da Execução Física:** `docs/audits/phase16_pilot_execution_data.json`
- **Suíte de Testes da Fase 16:** `tests/test_fase16_pilot_100_shorts.py` (23 testes passando)
- **Recomendação para a Próxima Fase:**
  1. Realizar auditoria independente de escala sobre este piloto antes de autorizar os 7.000 vídeos.
  2. Na coleta massiva futura, adicionar filtro explícito de proporção vertical (`height > width` ou `aspect_ratio ~ 9:16`) na etapa de seleção quando o objetivo for estudar composição nativa vertical de Shorts, mantendo `Smart Crop 9:16` para clipes `16:9`.
  3. **Manter o processamento dos 7.000 vídeos BLOQUEADO até autorização formal.**

---

## 10. MATRIZ FORENSE COMPLETA DOS 100 SHORTS AUDITADOS

| # | Video ID | Canal / Nicho | Duração | Tamanho (Bytes) | SHA256 (Prefixo/Sufixo) | Codecs (V/A) | Resolução | Cortes | Loudness (LUFS) | Diagnóstico Acústico | Fala (Palavras) | Estado Final |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 001 | `wJuR6kQFjjk` | C1: futebol_outros | 14.52s | 2,193,508 | `465fb9e5...453b0bd7` | av1/opus | 1280x720 | 3 | -26.3 | `QUIET_AUDIO_TRACK` | 25 | `learning_candidate` |
| 002 | `qnaGs3qlnAs` | C1: futebol_outros | 38.02s | 41,862,231 | `3e967a04...25bf3ee9` | av1/opus | 2160x1440 | 34 | -16.2 | `VALID_AUDIO` | 118 | `learning_candidate` |
| 003 | `KLqw31G16Lg` | C1: futebol_outros | 16.38s | 3,946,029 | `ffd96b03...0e759e40` | h264/opus | 1280x720 | 1 | -18.0 | `VALID_AUDIO` | 20 | `learning_candidate` |
| 004 | `8sDB-gLltq4` | C1: futebol_outros | 37.08s | 24,574,807 | `d3d32f11...27f3c061` | h264/opus | 1920x1080 | 9 | -13.0 | `VALID_AUDIO` | 43 | `learning_candidate` |
| 005 | `68s3cUgkkrU` | C1: futebol_outros | 14.90s | 6,834,111 | `3da85746...b0141e05` | h264/opus | 1920x1080 | 0 | -15.3 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 006 | `4Z0h_f9gBGc` | C1: futebol_outros | 29.42s | 11,523,562 | `10e22ba0...b2703c4b` | h264/opus | 1920x1080 | 3 | -24.5 | `QUIET_AUDIO_TRACK` | 54 | `learning_candidate` |
| 007 | `2TFGeAHjPA8` | C1: futebol_outros | 9.90s | 318,329 | `d25de6ba...14e2fa60` | h264/opus | 320x288 | 3 | -70.0 | `SILENT_AUDIO_TRACK` | 0 | `editorially_rejected` |
| 008 | `zm8L0IdpTIE` | C1: futebol_outros | 34.38s | 12,477,772 | `61de23c7...5b2eafd0` | av1/opus | 1920x1080 | 1 | -7.1 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 009 | `jkjkM4y2gvk` | C1: futebol_outros | 56.66s | 15,932,925 | `c41d04e9...4f877533` | h264/opus | 1280x720 | 4 | -12.5 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 010 | `qDWP4QQo9FA` | C1: futebol_outros | 36.92s | 7,108,410 | `f8d17d3f...271cf321` | h264/opus | 1280x720 | 7 | -28.3 | `QUIET_AUDIO_TRACK` | 90 | `learning_candidate` |
| 011 | `84EI9Clbe6o` | C1: futebol_outros | 11.76s | 4,153,615 | `c19c3c0c...f963dce0` | vp9/opus | 1920x1080 | 0 | -16.7 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 012 | `JZttQBluEnM` | C1: futebol_outros | 54.72s | 18,570,169 | `980d4e99...4390ead5` | h264/opus | 1920x1080 | 14 | -10.4 | `VALID_AUDIO` | 103 | `learning_candidate` |
| 013 | `2Y8If6UC7VU` | C1: futebol_outros | 58.32s | 14,337,558 | `3fd9b524...1ff248e6` | h264/opus | 1920x1080 | 13 | -10.6 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 014 | `M7fENC_MZ0g` | C1: futebol_outros | 46.62s | 15,338,965 | `b3ad7b21...35aa4713` | h264/opus | 1920x1080 | 12 | -8.7 | `VALID_AUDIO` | 3 | `learning_candidate` |
| 015 | `W_K1BMYDs4E` | C1: futebol_outros | 20.50s | 1,395,464 | `c23d307c...fd6edf98` | vp9/opus | 640x360 | 6 | -18.1 | `VALID_AUDIO` | 20 | `learning_candidate` |
| 016 | `GM77hpKBaDE` | C1: futebol_outros | 54.74s | 13,640,214 | `9258ca16...b229e36c` | h264/opus | 1920x1080 | 13 | -13.0 | `VALID_AUDIO` | 64 | `learning_candidate` |
| 017 | `RCA0GyNSIoo` | C1: futebol_outros | 54.48s | 16,251,562 | `953facdb...989fb3c9` | h264/opus | 1920x1080 | 15 | -11.0 | `VALID_AUDIO` | 31 | `learning_candidate` |
| 018 | `n_S4thgK7IA` | C1: futebol_outros | 45.92s | 98,804,015 | `18bd3cd6...49e9f88f` | vp9/opus | 3840x2160 | 10 | -11.6 | `VALID_AUDIO` | 48 | `learning_candidate` |
| 019 | `Iss2VSknHxs` | C1: futebol_outros | 25.72s | 4,109,288 | `92e1b2b1...3d0c3138` | h264/opus | 1272x720 | 9 | -13.6 | `VALID_AUDIO` | 4 | `learning_candidate` |
| 020 | `1l0ZUUtBgPU` | C1: futebol_outros | 6.34s | 741,127 | `d507bcb4...6868ddf1` | h264/opus | 638x480 | 3 | -13.8 | `VALID_AUDIO` | 13 | `learning_candidate` |
| 021 | `6xSxgmicWXw` | C2: casos_policiais | 41.92s | 16,530,809 | `eedfaa62...93621998` | h264/opus | 1920x1080 | 6 | -7.6 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 022 | `K_sagUSoNFw` | C2: casos_policiais | 27.74s | 2,868,528 | `80511ac8...3a43dc7c` | av1/opus | 1920x1080 | 3 | -16.9 | `VALID_AUDIO` | 60 | `learning_candidate` |
| 023 | `WyS5Ijgirtw` | C2: casos_policiais | 31.42s | 11,674,219 | `9b75f50d...f5343fcb` | vp9/opus | 1920x1080 | 1 | -16.0 | `VALID_AUDIO` | 57 | `learning_candidate` |
| 024 | `P_B5PBy84WA` | C2: casos_policiais | 57.38s | 21,697,868 | `9bf13b76...d7abc681` | vp9/opus | 1920x1080 | 5 | -19.7 | `VALID_AUDIO` | 42 | `learning_candidate` |
| 025 | `ikYbeX5FRvk` | C2: casos_policiais | 42.32s | 2,075,461 | `37b2bf0d...02f616b0` | vp9/opus | 640x352 | 4 | -8.1 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 026 | `xWxw0PIZWrU` | C2: casos_policiais | 57.68s | 12,435,292 | `f09ffc28...4793398c` | h264/opus | 1120x720 | 34 | -9.3 | `VALID_AUDIO` | 153 | `learning_candidate` |
| 027 | `mAWUojr5iaQ` | C2: casos_policiais | 24.82s | 4,910,365 | `0bce80dc...f903f0e6` | av1/opus | 1920x1080 | 5 | -24.6 | `QUIET_AUDIO_TRACK` | 65 | `learning_candidate` |
| 028 | `tSa4O41J45E` | C2: casos_policiais | 8.72s | 424,706 | `04104866...166ba8dc` | av1/opus | 1280x720 | 0 | -19.8 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 029 | `iq8XFfGf9jU` | C2: casos_policiais | 55.54s | 23,755,078 | `71f4abd3...390b0c51` | h264/opus | 1280x720 | 32 | -18.9 | `VALID_AUDIO` | 118 | `learning_candidate` |
| 030 | `eahtGuPAvkk` | C2: casos_policiais | 52.84s | 6,293,465 | `4ec41f39...a1d750da` | av1/opus | 1920x1080 | 4 | -16.6 | `VALID_AUDIO` | 124 | `learning_candidate` |
| 031 | `qSOUqYL3bHQ` | C2: casos_policiais | 39.98s | 10,426,928 | `c9a4c00a...6866b445` | av1/opus | 1920x1080 | 3 | -23.6 | `VALID_AUDIO` | 113 | `learning_candidate` |
| 032 | `cgTaYRUu-L8` | C2: casos_policiais | 24.24s | 2,404,035 | `992542a2...d63ff7fb` | h264/opus | 1280x720 | 2 | -16.9 | `VALID_AUDIO` | 46 | `learning_candidate` |
| 033 | `tfJSsxukhKY` | C2: casos_policiais | 41.64s | 4,591,691 | `41fa09c5...19a48688` | h264/opus | 854x480 | 5 | -2.7 | `HOT_LOUD_AUDIO` | 22 | `editorially_rejected` |
| 034 | `IO2mi3gdSKU` | C2: casos_policiais | 43.36s | 20,887,090 | `244466e6...a87e1b08` | vp9/opus | 1920x1080 | 4 | -12.7 | `VALID_AUDIO` | 4 | `learning_candidate` |
| 035 | `LgEcPoLMJR4` | C2: casos_policiais | 36.14s | 2,947,998 | `e20e3586...c4a71e12` | av1/opus | 1920x1080 | 4 | -25.0 | `QUIET_AUDIO_TRACK` | 104 | `learning_candidate` |
| 036 | `2VRpFzyxYp4` | C2: casos_policiais | 17.32s | 3,644,490 | `ca408265...9da72045` | av1/opus | 1920x1080 | 4 | -16.3 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 037 | `VhFwWC0z2fA` | C2: casos_policiais | 31.02s | 1,531,794 | `f1f77b31...b3a93927` | vp9/opus | 638x360 | 5 | -11.4 | `VALID_AUDIO` | 18 | `learning_candidate` |
| 038 | `wNjrknLZiKM` | C2: casos_policiais | 41.88s | 10,865,318 | `46e4192c...d09f19f1` | h264/opus | 1920x1080 | 0 | -22.8 | `VALID_AUDIO` | 127 | `learning_candidate` |
| 039 | `DLhH-nJv9Gk` | C2: casos_policiais | 47.84s | 25,060,847 | `71c0a56b...f6e5a0bb` | h264/opus | 1920x1080 | 45 | -8.2 | `VALID_AUDIO` | 123 | `learning_candidate` |
| 040 | `dzlqkcZwCcI` | C2: casos_policiais | 37.56s | 2,431,666 | `e75e3564...5d399d9c` | vp9/opus | 640x352 | 4 | -9.2 | `VALID_AUDIO` | 1 | `learning_candidate` |
| 041 | `wsX-lX9gaPE` | C3: humor | 16.60s | 2,547,361 | `b5f5adec...10ae1674` | vp9/opus | 3840x2160 | 0 | -14.3 | `VALID_AUDIO` | 39 | `learning_candidate` |
| 042 | `KVcc8sCMIic` | C3: humor | 10.02s | 2,409,630 | `9bb5de1e...009f4a50` | h264/opus | 1280x720 | 2 | -24.3 | `QUIET_AUDIO_TRACK` | 10 | `learning_candidate` |
| 043 | `uXS7pgwnOKo` | C3: humor | 9.02s | 213,078 | `e489d7a2...b7fc3697` | av1/opus | 640x360 | 2 | -14.4 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 044 | `M3BwlQPMOrg` | C3: humor | 41.52s | 15,656,232 | `109d81ec...aec8e6b8` | vp9/opus | 1600x1200 | 2 | -10.9 | `VALID_AUDIO` | 118 | `learning_candidate` |
| 045 | `ye3L0Kns4q0` | C3: humor | 14.14s | 629,728 | `8d2acc9f...89294255` | vp9/opus | 638x360 | 3 | -10.1 | `VALID_AUDIO` | 15 | `learning_candidate` |
| 046 | `ZXFf1YjIrM8` | C3: humor | 14.14s | 809,859 | `7b9e67de...24c87fa7` | vp9/opus | 638x360 | 3 | -10.6 | `VALID_AUDIO` | 23 | `learning_candidate` |
| 047 | `ZEnlZUYZB3k` | C3: humor | 14.14s | 719,893 | `52ba3f3c...b1ea9982` | vp9/opus | 638x360 | 3 | -10.4 | `VALID_AUDIO` | 29 | `learning_candidate` |
| 048 | `0mrnUGZMffw` | C3: humor | 16.06s | 752,820 | `4bc09617...c4185f4b` | vp9/opus | 638x360 | 3 | -12.0 | `VALID_AUDIO` | 25 | `learning_candidate` |
| 049 | `ASsUkhSN2sY` | C3: humor | 36.26s | 1,478,926 | `193df720...72485a30` | vp9/opus | 638x360 | 6 | -11.7 | `VALID_AUDIO` | 76 | `learning_candidate` |
| 050 | `bFjP-8Jj3fI` | C3: humor | 8.02s | 5,512,219 | `3e92ae7b...0ae98a9f` | h264/opus | 1920x1080 | 0 | -21.6 | `VALID_AUDIO` | 19 | `learning_candidate` |
| 051 | `a5bKQ6WW4MA` | C3: humor | 14.14s | 696,819 | `db297772...568bc92e` | vp9/opus | 638x360 | 3 | -10.6 | `VALID_AUDIO` | 17 | `learning_candidate` |
| 052 | `GggELAqG63s` | C3: humor | 13.72s | 629,109 | `5c84fd49...08863c39` | av1/opus | 1920x1080 | 0 | -10.8 | `VALID_AUDIO` | 0 | `editorially_rejected` |
| 053 | `1CbDrNNLLa8` | C3: humor | 10.62s | 1,096,506 | `0a7c0e1b...3690a9ba` | h264/opus | 540x480 | 1 | -13.1 | `VALID_AUDIO` | 13 | `learning_candidate` |
| 054 | `ux9pmIOa878` | C3: humor | 58.08s | 2,683,112 | `76b3fafc...3065fd2c` | vp9/opus | 640x352 | 16 | -18.0 | `VALID_AUDIO` | 20 | `learning_candidate` |
| 055 | `zTDrFuKtGHk` | C3: humor | 53.06s | 3,311,385 | `44e4ec05...26fd5be7` | h264/opus | 640x480 | 13 | -11.5 | `VALID_AUDIO` | 91 | `learning_candidate` |
| 056 | `s4cKEYvdFMw` | C3: humor | 58.12s | 1,790,806 | `dded1161...c74c9920` | av1/opus | 854x480 | 1 | -13.3 | `VALID_AUDIO` | 182 | `learning_candidate` |
| 057 | `OEC3iug1tl0` | C3: humor | 24.88s | 7,351,169 | `fe71f417...c55a27de` | h264/opus | 1712x1080 | 3 | -11.0 | `VALID_AUDIO` | 42 | `learning_candidate` |
| 058 | `RtDOzI5DrNU` | C3: humor | 20.04s | 944,196 | `ecf7870a...5e4d9942` | h264/opus | 1280x720 | 0 | -13.3 | `VALID_AUDIO` | 73 | `learning_candidate` |
| 059 | `aWOeNG4hss4` | C3: humor | 50.54s | 8,872,794 | `cc2dd0a7...5b78f028` | av1/opus | 1920x1080 | 24 | -21.5 | `VALID_AUDIO` | 179 | `learning_candidate` |
| 060 | `eXAI6iyqYjA` | C3: humor | 38.66s | 10,651,313 | `f7d54518...18996254` | h264/opus | 1920x1080 | 1 | -11.2 | `VALID_AUDIO` | 5 | `learning_candidate` |
| 061 | `N9I9EGpbCm4` | C4: curiosidades | 56.30s | 17,226,195 | `d09fe3c4...38c76eba` | h264/opus | 1920x1080 | 9 | -20.9 | `VALID_AUDIO` | 118 | `learning_candidate` |
| 062 | `xIpZc8t6wWI` | C4: curiosidades | 54.36s | 6,211,085 | `a2c557f6...c3272dc9` | av1/opus | 1920x1080 | 15 | -18.1 | `VALID_AUDIO` | 146 | `learning_candidate` |
| 063 | `O5BE2gd2GdU` | C4: curiosidades | 10.04s | 1,126,127 | `7d1f9f96...148f030a` | av1/opus | 1280x720 | 4 | -16.3 | `VALID_AUDIO` | 21 | `learning_candidate` |
| 064 | `JslhLIFaOC0` | C4: curiosidades | 52.64s | 14,956,823 | `ed132769...d0b8b812` | vp9/opus | 3840x2160 | 5 | -19.6 | `VALID_AUDIO` | 100 | `learning_candidate` |
| 065 | `9FpSx4XWDLw` | C4: curiosidades | 59.72s | 3,790,322 | `48ba0a35...3e0b6270` | h264/opus | 720x480 | 5 | -21.8 | `VALID_AUDIO` | 132 | `learning_candidate` |
| 066 | `uPqylip16Ic` | C4: curiosidades | 41.42s | 1,215,400 | `498ebd4c...b508a752` | h264/opus | 1920x1080 | 3 | -23.7 | `VALID_AUDIO` | 41 | `learning_candidate` |
| 067 | `TE7U-06CB00` | C4: curiosidades | 10.02s | 2,156,793 | `00de484e...2793055a` | h264/opus | 1280x720 | 4 | -16.3 | `VALID_AUDIO` | 37 | `learning_candidate` |
| 068 | `5n6L8xj5uGU` | C4: curiosidades | 26.02s | 8,623,763 | `eeb11418...ae5d6993` | h264/opus | 1920x1080 | 2 | -17.8 | `VALID_AUDIO` | 69 | `learning_candidate` |
| 069 | `C1JusZSNCL8` | C4: curiosidades | 14.12s | 2,072,846 | `4ca59da6...ded17043` | h264/opus | 1620x1080 | 0 | -14.2 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 070 | `ovltnO4EOwk` | C4: curiosidades | 59.20s | 4,676,679 | `dc34f32c...03006429` | h264/opus | 1920x1080 | 3 | -14.5 | `VALID_AUDIO` | 106 | `learning_candidate` |
| 071 | `-s_n5eyOGkI` | C4: curiosidades | 39.32s | 10,563,553 | `bff5260d...abda917a` | h264/opus | 1280x720 | 17 | -9.4 | `VALID_AUDIO` | 95 | `learning_candidate` |
| 072 | `hSyWqUxR_84` | C4: curiosidades | 43.46s | 13,264,585 | `2f1000fc...ca68da4e` | av1/opus | 3840x2160 | 10 | -16.4 | `VALID_AUDIO` | 121 | `learning_candidate` |
| 073 | `W2kqs6F_-hM` | C4: curiosidades | 24.36s | 13,199,797 | `c87bc862...a861fc2e` | h264/opus | 1920x1080 | 13 | -17.3 | `VALID_AUDIO` | 75 | `learning_candidate` |
| 074 | `HRLpvzETd4M` | C4: curiosidades | 32.00s | 840,265 | `40f9b5f7...26bee359` | vp9/opus | 640x352 | 0 | -25.4 | `QUIET_AUDIO_TRACK` | 83 | `learning_candidate` |
| 075 | `9UUuHuDNSKg` | C4: curiosidades | 49.48s | 10,444,756 | `b831718c...a9c1b6f2` | h264/opus | 1280x720 | 7 | -18.7 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 076 | `L1Feq5-y5J0` | C4: curiosidades | 42.24s | 1,755,213 | `87d03aed...447826fa` | av1/opus | 1920x1080 | 2 | -14.4 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 077 | `sp7KGFCNjJk` | C4: curiosidades | 46.80s | 54,258,632 | `14ab1e36...ad3694d5` | vp9/opus | 3840x2160 | 13 | -18.7 | `VALID_AUDIO` | 138 | `learning_candidate` |
| 078 | `ueti1YAGsXI` | C4: curiosidades | 22.36s | 5,808,811 | `2bf4dccb...bbdb9f2c` | av1/opus | 1920x1080 | 1 | -26.0 | `QUIET_AUDIO_TRACK` | 0 | `learning_candidate` |
| 079 | `1NFfOC4r9N0` | C4: curiosidades | 38.72s | 3,117,361 | `8983aacf...84d1f1c8` | h264/opus | 1280x720 | 2 | -19.0 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 080 | `-rT8PbFyn24` | C4: curiosidades | 26.78s | 3,006,428 | `1faf6792...3fc909a7` | h264/opus | 640x480 | 3 | -14.5 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 081 | `i7QH1fsB01A` | C5: desenvolvimento_pessoal | 18.66s | 3,792,735 | `10ead091...79c1f93a` | h264/opus | 1920x1080 | 1 | -30.0 | `QUIET_AUDIO_TRACK` | 25 | `learning_candidate` |
| 082 | `r3CribedVGU` | C5: desenvolvimento_pessoal | 28.66s | 5,683,737 | `b5f2f507...4021042d` | h264/opus | 1280x720 | 5 | -17.8 | `VALID_AUDIO` | 56 | `learning_candidate` |
| 083 | `x7vdcTpEwPI` | C5: desenvolvimento_pessoal | 57.40s | 5,305,259 | `2ecbd063...0a81043b` | av1/opus | 1920x1080 | 0 | -11.7 | `VALID_AUDIO` | 191 | `learning_candidate` |
| 084 | `cPERLUfT1TI` | C5: desenvolvimento_pessoal | 25.58s | 2,657,657 | `fe26dcc9...7dabdae4` | av1/opus | 1920x1080 | 8 | -26.3 | `QUIET_AUDIO_TRACK` | 56 | `learning_candidate` |
| 085 | `fCnF70xpmug` | C5: desenvolvimento_pessoal | 28.74s | 6,890,392 | `924edc9a...78c6c20a` | av1/opus | 1920x1080 | 8 | -26.4 | `QUIET_AUDIO_TRACK` | 63 | `learning_candidate` |
| 086 | `5CwgIGVeABc` | C5: desenvolvimento_pessoal | 28.84s | 5,101,801 | `b47eb06a...4e46c62c` | av1/opus | 1920x1080 | 8 | -26.4 | `QUIET_AUDIO_TRACK` | 59 | `learning_candidate` |
| 087 | `JzQl0D33NNs` | C5: desenvolvimento_pessoal | 59.92s | 13,100,346 | `ee0925a5...d5b0e162` | h264/opus | 1920x1080 | 10 | -21.8 | `VALID_AUDIO` | 134 | `learning_candidate` |
| 088 | `ghFftcYJgPw` | C5: desenvolvimento_pessoal | 50.18s | 9,605,365 | `1e29896c...5a0931c2` | h264/opus | 1920x1080 | 3 | -21.4 | `VALID_AUDIO` | 60 | `learning_candidate` |
| 089 | `pgvV1SASs5A` | C5: desenvolvimento_pessoal | 47.78s | 2,718,730 | `fe555428...02f39fdf` | av1/opus | 1920x1080 | 9 | -15.6 | `VALID_AUDIO` | 49 | `learning_candidate` |
| 090 | `34O9fkZueVs` | C5: desenvolvimento_pessoal | 28.36s | 1,218,463 | `0ff89764...da82f5d0` | h264/opus | 768x720 | 1 | -14.1 | `VALID_AUDIO` | 6 | `learning_candidate` |
| 091 | `Mhd8dEaYUXc` | C5: desenvolvimento_pessoal | 32.46s | 9,802,878 | `84a5673a...1b704826` | h264/opus | 1920x1080 | 5 | -14.3 | `VALID_AUDIO` | 72 | `learning_candidate` |
| 092 | `aEOGg1V5d4U` | C5: desenvolvimento_pessoal | 20.62s | 4,461,509 | `578fb4f9...8923d403` | h264/opus | 1920x1080 | 1 | -19.0 | `VALID_AUDIO` | 42 | `learning_candidate` |
| 093 | `W7Z2cw4zUzo` | C5: desenvolvimento_pessoal | 17.78s | 800,547 | `511aec59...2b84a0c7` | h264/opus | 1280x720 | 5 | -14.5 | `VALID_AUDIO` | 35 | `learning_candidate` |
| 094 | `XVKP6L1cD0Y` | C5: desenvolvimento_pessoal | 5.08s | 280,558 | `deb8958e...91c94305` | av1/opus | 618x360 | 0 | -11.0 | `VALID_AUDIO` | 8 | `learning_candidate` |
| 095 | `y_zzFldWZKE` | C5: desenvolvimento_pessoal | 5.08s | 249,135 | `057198cb...bf2d7a16` | av1/opus | 618x360 | 0 | -12.6 | `VALID_AUDIO` | 14 | `learning_candidate` |
| 096 | `CNzXgYRppjc` | C5: desenvolvimento_pessoal | 42.76s | 12,225,036 | `edd23f3a...27f22216` | h264/opus | 1920x1080 | 5 | -21.3 | `VALID_AUDIO` | 96 | `learning_candidate` |
| 097 | `MF8jOm7KjUA` | C5: desenvolvimento_pessoal | 18.00s | 2,271,518 | `b58abb78...16e95741` | h264/opus | 782x720 | 0 | -14.1 | `VALID_AUDIO` | 54 | `learning_candidate` |
| 098 | `sTbbfN00ars` | C5: desenvolvimento_pessoal | 20.05s | 3,578,401 | `84bb4e68...c4f182b8` | h264/opus | 1920x1080 | 0 | -23.1 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 099 | `jjYaxjd1nKI` | C5: desenvolvimento_pessoal | 14.25s | 1,515,660 | `b5744b49...3f676e97` | h264/opus | 1920x1080 | 1 | -22.0 | `VALID_AUDIO` | 0 | `learning_candidate` |
| 100 | `arjfLMDIVy4` | C5: desenvolvimento_pessoal | 20.10s | 726,581 | `16462df3...4d4bb0d4` | av1/opus | 640x480 | 0 | -11.5 | `VALID_AUDIO` | 69 | `learning_candidate` |

---

## 11. DECLARAÇÃO DO GATE FINAL

> ### **PILOTO APROVADO — PRONTO PARA AUDITORIA DE ESCALA**
> 
> **NÃO INICIAR OS 7.000 VÍDEOS NESTA FASE.** Todos os 100 Shorts foram validados fisicamente, com análises reais baseadas em evidências, circuit breakers e retomada testados, dashboard 100% consistente com o banco e custo real mantido em `$0.00`.

*Relatório auditado em 24/11/2026 18:35:46.*