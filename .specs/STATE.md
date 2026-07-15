# PLOG — Project State

Memória do projeto para desenvolvimento spec-driven. Duas seções:
- **Decisions**: decisões arquiteturais duradouras (AD-NNN), escritas na fase Design.
- **Handoff**: snapshot do trabalho em andamento, atualizado ao pausar/encerrar sessão.

---

## Decisions

| ID     | Decisão | Contexto / Racional | Data |
| ------ | ------- | ------------------- | ---- |
| AD-001 | Busca de flows por intervalo de datas itera dia a dia; dias sem dados são ignorados e a consulta só falha (`FlowNotFoundError`) se **nenhum** dia do intervalo tiver dados. Consulta de um único dia sem dados continua falhando. | Feature `busca-intervalo-datas` (commit `a37179b`). Evita que um dia vazio no meio do intervalo zere o resultado. | 2026-07-15 |
| AD-002 | Testes automatizados rodam no virtualenv do Poetry (`plog-v2-*`), que contém as dependências do app. `pytest`/`pytest-cov`/`httpx` (de `requirements-dev.txt`) foram instalados nesse venv. | Python base do sistema não tem as libs do app; venv do Poetry não vinha com pytest. | 2026-07-15 |

---

## Handoff

**Feature:** regressao-intervalo-datas
**Fase:** Execute — concluída
**Branch:** `test/regressao-intervalo-datas` (a ser mergeado em `main`)
**Concluído:** testes de regressão do intervalo de datas (service + schema) escritos e verdes; Verifier executado.
**Próximo passo:** merge em `main`.
**Blockers / dívidas conhecidas:** `tests/test_api.py` tem 7 testes falhando com 401 (o fixture `client` não faz override de `verificar_token_acesso`). Pré-existente, **fora do escopo** desta feature.
**Arquivos não commitados alheios:** `app/core/security.py` (apenas reordenação de imports).
