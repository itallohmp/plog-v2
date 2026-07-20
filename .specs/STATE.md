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

**Feature:** filtro-protocolo
**Fase:** Concluída ✅ (branch `feature/filtro-protocolo`, 8 commits, ainda NÃO mergeada)
**Concluído:** filtro por TCP/UDP/ICMP com multi-seleção, de ponta a ponta (parser, schema, service, rota, UI). 24 testes do filtro; Verifier PASS após 1 iteração de fix (7/7 mutações mortas).
**Próximo passo:** merge de `feature/filtro-protocolo` em `main` (aguardando decisão do usuário).
**Blockers / dívidas conhecidas:** `tests/test_api.py` com 7 falhas 401 (fixture sem override de `verificar_token_acesso`) — contornado localmente em `tests/test_flow_protocolo.py` via `dependency_overrides`; a dívida em si segue aberta.
**Arquivos não commitados alheios:** `app/core/security.py` (reordenação de imports) e `Roteiro.pdf` (untracked).
