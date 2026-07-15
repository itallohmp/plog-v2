# Regressão — Busca de Flows por Intervalo de Datas

## Problem Statement

A busca de flows por intervalo de datas (`data` + `data_fim`) foi adicionada recentemente
(commit `a37179b`), mas a suíte de testes só cobre consultas de **um único dia**. Não há
teste que trave a lógica de intervalo — regressões futuras (ou um deploy com backend
desatualizado) passariam despercebidas. Esta feature adiciona os testes de regressão que
faltam, sem alterar comportamento de produção.

## Goals

- [x] Cobrir a lógica multi-dia de `FlowService.buscar_flows` com testes derivados do comportamento especificado (AD-001).
- [x] Cobrir as validações de intervalo de `FlowQuery` (schema).
- [x] Suíte nova verde no venv do Poetry, sem tocar em código de produção.

## Out of Scope

| Item | Motivo |
| ---- | ------ |
| Corrigir os 7 testes 401 de `tests/test_api.py` | Pré-existente, não relacionado ao intervalo de datas; requer override do dependency de auth. |
| Alterar `flow_service.py` / `flow.py` / `pcap_parser.py` | A lógica já está correta (verificada); esta feature só adiciona testes. |
| Testes de camada HTTP (`/api/flows`) para intervalo | Bloqueados pelo mesmo problema de auth acima; cobertos indiretamente pela camada de service. |

---

## Assumptions & Open Questions

| Assumption / decisão | Default escolhido | Racional | Confirmado? |
| -------------------- | ----------------- | -------- | ----------- |
| Os testes usam um repositório mock que varia o retorno por dia | Mock com `side_effect` mapeando `date → eventos` | Reproduz o comportamento real de dias com/sem dados sem depender de SSH | y |
| Formato do timestamp dos eventos é ISO `YYYY-MM-DDThh:mm:ss` | Igual à fixture `sample_flows.json` e às telas de produção | `pcap_event_matches` compara `t_first[:10]` com a data ISO do dia | y |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Regressão da lógica multi-dia (service) ⭐ MVP

**User Story**: Como mantenedor do PLOG, quero testes que travem a busca por intervalo de
datas, para que uma regressão na iteração dia-a-dia seja detectada automaticamente.

**Why P1**: É o coração do bug reportado (intervalo retornava vazio quando um dia não tinha dados).

**Acceptance Criteria**:

1. WHEN a consulta tem `data`..`data_fim` cobrindo vários dias, e cada dia retorna eventos daquele dia, THEN o service SHALL retornar a **união** dos eventos que casam o filtro em todo o intervalo.
2. WHEN um dia do intervalo não tem dados (`FlowNotFoundError`) mas ao menos um outro dia tem, THEN o service SHALL ignorar o dia vazio e retornar os eventos dos dias com dados (SEM levantar exceção).
3. WHEN **nenhum** dia do intervalo tem dados, THEN o service SHALL levantar `FlowNotFoundError`.
4. WHEN a consulta é de um único dia (`data_fim` ausente) e esse dia não tem dados, THEN o service SHALL levantar `FlowNotFoundError` (comportamento legado preservado).
5. WHEN a consulta é por intervalo (`data_fim` != `data`), THEN o campo `data` da resposta SHALL ter o formato `"YYYY-MM-DD a YYYY-MM-DD"`.

**Independent Test**: rodar `pytest tests/test_flow_interval.py` — todos verdes.

---

### P2: Regressão das validações de intervalo (schema)

**User Story**: Como mantenedor, quero que as regras de validação do intervalo em `FlowQuery`
estejam travadas por teste.

**Why P2**: Protege limites de entrada; complementa a lógica do service.

**Acceptance Criteria**:

1. WHEN `data_fim` < `data`, THEN `FlowQuery` SHALL rejeitar com `ValidationError`.
2. WHEN o intervalo excede `MAX_DIAS_INTERVALO` (31) dias, THEN `FlowQuery` SHALL rejeitar com `ValidationError`.
3. WHEN `data_fim` == `data`, THEN `FlowQuery.dias()` SHALL retornar exatamente `[data]` (um dia).
4. WHEN `data_fim` é `N` dias após `data` (dentro do limite), THEN `dias()` SHALL retornar os `N+1` dias em ordem crescente.

**Independent Test**: rodar `pytest tests/test_flow_interval.py -k schema` — todos verdes.

---

## Edge Cases

- WHEN o primeiro dia do intervalo é vazio e o último tem dados THEN o resultado SHALL conter os eventos do último dia (ordem de iteração não descarta dias posteriores). *(caso exato do bug reportado)*
- WHEN o intervalo tem exatamente 31 dias THEN `FlowQuery` SHALL aceitar (limite inclusivo).

---

## Requirement Traceability

| Requirement ID | Story | Fase | Status |
| -------------- | ----- | ---- | ------ |
| RINT-01 | P1 AC1 (união multi-dia) | Execute | Verified |
| RINT-02 | P1 AC2 (dia vazio ignorado) | Execute | Verified |
| RINT-03 | P1 AC3 (todos vazios → erro) | Execute | Verified |
| RINT-04 | P1 AC4 (dia único vazio → erro) | Execute | Verified |
| RINT-05 | P1 AC5 (label do intervalo) | Execute | Verified |
| RINT-06 | P2 AC1 (data_fim < data) | Execute | Verified |
| RINT-07 | P2 AC2 (> 31 dias) | Execute | Verified |
| RINT-08 | P2 AC3+AC4 (`dias()`) | Execute | Verified |

**Coverage:** 8 requisitos, 8 mapeados para testes, 0 sem mapeamento.

---

## Success Criteria

- [x] `pytest tests/test_flow_interval.py` verde no venv do Poetry.
- [x] Zero alterações em código de produção (`git diff` toca apenas `tests/` e `.specs/`).
- [x] Verifier confirma que os testes matam mutações de comportamento (discrimination sensor).
