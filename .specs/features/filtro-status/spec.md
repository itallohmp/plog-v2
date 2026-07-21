# Filtro por Estado da Sessão (Aberta / Fechada)

## Problem Statement

As sessões NAT agora têm estado (aberta/fechada/indefinida). O analista quer restringir a
busca a um estado — ex.: ver só as sessões ainda **abertas** de um IP. Falta o filtro.

## Goals

- [ ] Filtrar sessões por estado na API e na UI (múltipla seleção).
- [ ] Filtro aplicado **após** a resolução de pendentes (o estado exibido é o final).
- [ ] UI: checkboxes Aberta/Fechada junto do grupo de protocolos, mesmo design.

## Out of Scope

| Item | Motivo |
| ---- | ------ |
| Checkbox de "Indefinida" na UI | Estado raro (eventos malformados); a API aceita, mas a UI expõe só Aberta/Fechada como o usuário pediu. |
| Pular o lookahead quando filtra "fechada" | Uma sessão pendente pode fechar via lookahead e contar como fechada; manter o lookahead garante o estado correto. |

---

## Assumptions & Open Questions

| Assumption / decisão | Default | Racional | Confirmado? |
| -------------------- | ------- | -------- | ----------- |
| Multi-seleção via `?status=aberta&status=fechada` | query param repetido | Igual ao filtro de protocolo | y |
| Valores válidos na API | `aberta`, `fechada`, `indefinida` (case-insensitive) | Consistência com o enum de status; UI usa só as 2 primeiras | y |
| Ausente/vazio = sem filtro (todos) | — | Consistente com protocolo | y |
| Valor inválido → 422 | — | Igual a protocolo | y |
| Filtro é pós-correlação | filtra a lista de sessões já construída | Custo desprezível de memória; estado já resolvido pelo lookahead | y |

**Open questions:** none.

---

## User Stories

### P1: Filtrar sessões por estado na API ⭐ MVP

**Acceptance Criteria**:

1. WHEN `status=aberta` THEN o sistema SHALL retornar somente sessões com `status == "aberta"`.
2. WHEN `status=fechada` THEN o sistema SHALL retornar somente sessões `fechada`.
3. WHEN `status=aberta&status=fechada` THEN o sistema SHALL retornar a união (exclui indefinidas).
4. WHEN `status` ausente ou vazio THEN o sistema SHALL não filtrar por estado.
5. WHEN o estado é informado em qualquer capitalização THEN SHALL tratá-los como equivalentes.
6. WHEN `status` recebe valor inválido THEN a API SHALL responder 422.
7. WHEN o filtro é aplicado THEN SHALL ocorrer **após** `_resolver_pendentes` (uma pendente fechada pelo lookahead conta como `fechada`).
8. WHEN combinado com IP/protocolo/data THEN SHALL compor por AND.

**Independent Test**: `pytest tests/test_filtro_status.py` verde.

---

### P2: Checkboxes de estado na interface

**Acceptance Criteria**:

1. WHEN a tela é carregada THEN a UI SHALL exibir checkboxes Aberta e Fechada, agrupados com os protocolos, no mesmo estilo (`.checkbox_chip`).
2. WHEN nenhum está marcado THEN a busca SHALL ser enviada sem `status`.
3. WHEN N estão marcados THEN a URL SHALL conter N params `status` em minúsculo.

**Independent Test**: marcar Aberta e conferir `?status=aberta` na URL.

---

## Edge Cases

- WHEN só "aberta" é selecionado THEN sessões fechadas E indefinidas SHALL ser excluídas.
- WHEN o total muda pelo filtro THEN a paginação SHALL refletir a contagem filtrada.

---

## Requirement Traceability

| ID | Story | Fase | Status |
| -- | ----- | ---- | ------ |
| STAT-01 | P1 AC1-AC2 (um estado) | Tasks | Pending |
| STAT-02 | P1 AC3 (união) | Tasks | Pending |
| STAT-03 | P1 AC4 (sem filtro) | Tasks | Pending |
| STAT-04 | P1 AC5 (case-insensitive) | Tasks | Pending |
| STAT-05 | P1 AC6 (inválido → 422) | Tasks | Pending |
| STAT-06 | P1 AC7 (pós-lookahead) | Tasks | Pending |
| STAT-07 | P2 AC1-AC3 (UI) | Tasks | Pending |

---

## Success Criteria

- [ ] Marcar Aberta retorna só sessões abertas.
- [ ] Suíte existente sem regressão.
- [ ] Verifier confirma que os testes matam mutações do filtro.
