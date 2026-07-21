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
| AD-003 | Todo deploy que altera código Python exige **restart do processo**. `StaticFiles` serve o frontend lido do disco a cada request, mas as rotas ficam em memória desde o boot: sem restart, JS novo + rota antiga = parâmetro novo ignorado em silêncio (resultado errado, sem erro). | Diagnosticado no bug de `data_fim`; vale igualmente para `protocolo` e para as sessões NAT. | 2026-07-20 |
| AD-004 | Sessões NAT são correlacionadas **em memória** (sem banco): create+delete da mesma chave `(roteador, origem, ip_nat, pblock_start, pblock_size)` — sem `proto` — pareados por **pilha cronológica (LIFO)**. `total` passa a contar sessões, não eventos (campo `eventos` preserva a contagem crua). Eventos sem chave completa viram sessão "indefinida". | Feature `sessoes-nat`. A pilha impede que a realocação de um bloco atribua tráfego ao assinante errado; o banco só agregaria custo e uma 2ª fonte de verdade. | 2026-07-21 |
| AD-005 | Sessões abertas (create sem delete na janela) são resolvidas por **consulta filtrada ao nfdump** (dia seguinte → hoje), não relendo dias inteiros. Expressão montada por allowlist de valores tipados + `shlex.quote`. Desligável por `PLOG_NAT_LOOKAHEAD`. A **sintaxe de filtro NAT do nfdump ainda precisa ser confirmada** contra o servidor real (ver `features/sessoes-nat/nfdump-filtro.md`). | Alocações duram até 6 meses; reler 180 dias seria inviável. O pushdown escala com o que casa o filtro, não com o volume (~200 mil/dia). | 2026-07-21 |

---

## Handoff

**Feature:** sessoes-nat
**Fase:** Execute concluída, na branch `feature/sessoes-nat` (10 commits). **Não mergeada.**
**Concluído:** correlação de sessões NAT de ponta a ponta (parser `nat_session.py`, schema `FlowSession`, service, repositório com pushdown, UI com selo de status). ~50 testes novos; gate 108 verde. Sensor de mutação confirmou o teste de realocação.
**Próximo passo:**
  1. ⚠️ **Confirmar a sintaxe de filtro do nfdump** no servidor real (AD-005 / `features/sessoes-nat/nfdump-filtro.md`) antes de confiar no lookahead — hoje ele é desligável por `PLOG_NAT_LOOKAHEAD=0`.
  2. Rodar o Verifier independente; depois merge em `main`.
  3. ⚠️ REINICIAR o backend no servidor após o deploy (AD-003).
**Blockers / dívidas conhecidas:** `tests/test_api.py` com 7 falhas 401 (fixture sem override de `verificar_token_acesso`), contornada em `tests/test_flow_protocolo.py`. Divergência de URL `db.py` × `alembic.ini` (mina terrestre para futura migration).
**Arquivos não commitados alheios:** `app/core/security.py` (reordenação de imports) e `Roteiro.pdf` (untracked).
