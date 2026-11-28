# VANTIS — FLUXO DE DESENVOLVIMENTO E DIRETRIZES GIT

> **Estratégia Oficial de Branches:** Gitflow Adaptado  
> **Branch Principal de Trabalho:** `develop`  
> **Branch de Release Homologada:** `main`

---

## 1. Princípios Fundamentais

1. **Desenvolvimento Exclusivo na `develop`:**
   - Nenhum commit de feature ou refatoração deve ser feito diretamente na branch `main`.
   - A branch `main` representa o estado estável e homologado do sistema.

2. **Promoção para a `main`:**
   - A promoção de código da `develop` para a `main` ocorre exclusivamente após validação completa da suíte de testes e auditoria documental.
   - Sempre utilize merge com criação explícita de commit de integração (`git merge --no-ff develop`), preservando o histórico e a autoria dos commits anteriores.
   - **NUNCA utilize `git push --force` ou rebase destrutivo.**

3. **Isolamento de Segredos e Arquivos Locais:**
   - Credenciais OAuth (`credentials/*.json`), bancos locais em execução (`database/*.db`), mídias renderizadas (`workspace/renders/`) e arquivos `.env` jamais devem ser comitados.
   - O `.gitignore` deve ser mantido estritamente configurado para impedir inclusões acidentais.

---

## 2. Ciclo de Vida do Trabalho

```
         (Feature / Correção)
develop ─────────► [ Validação & Testes ] ─────────► develop (Commit)
                                                          │
                                         (Homologação)    │ git merge --no-ff develop
                                                          ▼
main ──────────────────────────────────────────────► main (Tag / Deploy)
```

### Comandos de Rotina:

```bash
# 1. Iniciar o dia ou tarefa na develop atualizada
git checkout develop
git pull origin develop

# 2. Criar uma branch de feature quando necessário
git checkout -b feature/nome-da-funcionalidade

# 3. Validar a bateria de testes antes de integrar
python scripts/run_all_tests.py

# 4. Integrar na develop
git checkout develop
git merge --no-ff feature/nome-da-funcionalidade
git push origin develop
```

---

## 3. Padrão de Mensagens de Commit

O Vantis adota a convenção de **Conventional Commits**:

- `feat(modulo): descricao da funcionalidade`
- `fix(modulo): correcao de erro`
- `docs(modulo): atualizacoes de documentacao`
- `test(modulo): testes automatizados`
- `chore(modulo): ajustes de configuracao, dependencias ou infraestrutura`
