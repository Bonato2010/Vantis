# IAS — Diretrizes de Estrutura Git e Fluxo de Trabalho (Workflow)

Este documento define a governança de versionamento, ciclo de vida de branches, padrões de commit e processos de integração para o projeto **IAS (Intelligence & Automation System)**.

---

## 1. Estrutura Principal de Branches

| Branch | Papel | Política de Estabilidade | Destino de Merges |
| :--- | :--- | :--- | :--- |
| **`main`** | Versão estável e auditada em produção. | **100% Estável.** Nunca recebe commits diretos. Apenas merges validados vindos de `develop`. | Deploy / Release Tag |
| **`develop`** | Branch central de integração contínua. | **Funcional e Testada.** Reúne as features concluídas e validadas pela suíte de testes. | Base para novas features e fonte de merges para `main`. |

---

## 2. Branches Especializadas (`feature/*`)

Para evitar sobreposição e manter o desenvolvimento atômico e rastreável, cada subsistema é desenvolvido em sua respectiva branch especializada antes de ser integrado na `develop`:

1. **`feature/orchestration`**
   - **Objetivo:** Integração do **LangGraph**, definição do grafo de 12 etapas, persistência de checkpoints e retomada de tarefas interrompidas.
2. **`feature/semantic-memory`**
   - **Objetivo:** Integração com **pgvector** e memória semântica vetorial, scripts de migração PostgreSQL e fallback vetorial local para busca por significado.
3. **`feature/transcription`**
   - **Objetivo:** Pipeline de transcrição de alta precisão com suporte a **WhisperX** / **Faster-Whisper**, timestamps por palavra e estilização dinâmica de legendas ASS (estilo Hormozi/viral).
4. **`feature/video-analysis`**
   - **Objetivo:** Integração com **PySceneDetect** (cortes de cena), **OpenCV** (enquadramento inteligente e detecção de movimento) e **yt-dlp** (metadados e máquina de estados de autorização).
5. **`feature/model-gateway`**
   - **Objetivo:** Integração com **LiteLLM**, roteamento inteligente multi-provedor (Gemini, Claude, GPT-4o, Ollama), controle de tokens e custos em variáveis de ambiente protegidas.
6. **`feature/media-processing`**
   - **Objetivo:** Renderização profissional com **FFmpeg**, cortes com re-encode em 1080x1920 (9:16), queima de legendas, normalização de áudio (EBU R128) e perfis anti-duplicação.
7. **`feature/dashboard`**
   - **Objetivo:** Painel de controle corporativo unificado (FastAPI + UI sóbria), telemetria em tempo real das 7 integrações, fila de aprovação e monitor de execução.
8. **`feature/testing`**
   - **Objetivo:** Bateria completa de testes automatizados de ponta a ponta para validação de regressão e estabilidade contínua.

---

## 3. Fluxo de Trabalho (Gitflow IAS)

```
[ main ] <------------------------- (Merge auditado e tagueado)
   │
   ▼
[ develop ] <---------------------- (Merge de feature testada)
   │
   ├──> [ feature/orchestration ] ───> Testes de Grafo ───┘
   ├──> [ feature/semantic-memory ] ─> Testes Vetoriais ──┘
   ├──> [ feature/transcription ] ───> Testes de Legenda ─┘
   ├──> [ feature/video-analysis ] ──> Testes de Cena ────┘
   ├──> [ feature/model-gateway ] ───> Testes de LLM ─────┘
   └──> [ feature/media-processing ] > Testes FFmpeg ─────┘
```

### Regras de Ouro:
1. **Nunca comitar credenciais, chaves de API, arquivos `.token.json`, `.env` ou pastas temporárias pesadas.**
2. **Nunca implementar funcionalidades diretamente na branch `main`.**
3. **Sempre rodar a suíte de testes antes de fazer merge para `develop`.**
4. **Preservar o histórico de commits sem descartar implementações existentes.**

---

## 4. Convenção de Commits (Conventional Commits)

Cada commit deve seguir a estrutura: `<tipo>(<escopo>): <descrição clara>`

* **`feat`**: Nova funcionalidade ou módulo de serviço.  
  *Ex: `feat(orchestration): implementa LangGraph StateGraph de 12 etapas com checkpoints`*
* **`fix`**: Correção de bug ou ajuste de integração.  
  *Ex: `fix(transcription): ajusta escape de caracteres em legendas ASS`*
* **`docs`**: Atualizações de documentação e manuais técnicos.  
  *Ex: `docs(architecture): adiciona guia de migração do pgvector`*
* **`refactor`**: Refatoração interna sem alterar contratos ou funcionalidades.  
  *Ex: `refactor(media_processing): desacopla lógica de cálculo de corte do FFmpeg`*
* **`test`**: Criação ou atualização de testes automatizados.  
  *Ex: `test(services): adiciona testes unitários para o LiteLLM gateway`*
* **`chore`**: Tarefas de manutenção, dependências e configurações.  
  *Ex: `chore(deps): adiciona langgraph e litellm ao ambiente`*

---

## 5. Como Operar Branches no IAS

### Criar uma nova feature branch:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/<nome-da-funcionalidade>
```

### Integrar feature concluída em `develop`:
```bash
# 1. Executa bateria de testes
python -m pytest tests/

# 2. Atualiza branch develop
git checkout develop
git pull origin develop

# 3. Faz o merge mantendo histórico
git merge --no-ff feature/<nome-da-funcionalidade>

# 4. Envia para o repositório remoto
git push origin develop
```

### Resolução de Conflitos:
Caso haja conflito durante o merge:
1. O desenvolvedor deve inspecionar os arquivos em conflito: `git status`.
2. Resolver os marcadores `<<<<<<<`, `=======`, `>>>>>>>` manualmente sem apagar o trabalho da outra branch.
3. Marcar o arquivo como resolvido: `git add <arquivo>`.
4. Finalizar o commit de merge: `git commit -m "merge: resolve conflitos de integração"`.
