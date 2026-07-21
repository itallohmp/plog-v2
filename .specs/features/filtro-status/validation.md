# Validation — Filtro por Estado da Sessão (filtro-status)

**Verifier independente (fresh-eyes).** Autor != Verifier. Regra: evidence-or-zero
(só conta como coberto quando cita `file:line` + a expressão do assert).

## Veredito: **PASS**

- Todos os ACs testáveis por harness (STAT-01..06, STAT-08) têm teste ancorado que
  bate com a spec e mata mutações de comportamento.
- STAT-07 (UI, P2) verificado **manualmente** no browser (sem harness JS) — não conta
  como teste automatizado, mas o código-fonte da UI foi inspecionado e confere.
- Sensor de discriminação: 3/3 mutações **KILLED**. Nenhum mutante sobrevivente.

---

## Gate (suíte, sem regressão)

Runner: `python -m pytest <arquivos> -q`
Comando:
`tests/test_filtro_status.py tests/test_flow_protocolo.py tests/test_nat_sessao.py tests/test_nat_lookahead.py tests/unit -q`

**Resultado: 104 passed, 1 warning.** (`tests/test_api.py` excluído por 7 falhas 401
pré-existentes, fora do escopo desta feature.)

Range verificado: `d0c01ad^..HEAD`
- `d0c01ad` feat(flows): filter NAT sessions by state (aberta/fechada)
- `162d9fc` feat(ui): add session-state checkboxes next to protocol filter

---

## Cobertura por AC (spec-anchored)

| AC | Descrição (spec) | Evidência (file:line + assert) | Status |
| -- | ---------------- | ------------------------------ | ------ |
| STAT-01 | P1 AC1-AC2: um estado retorna só aquele estado | `tests/test_filtro_status.py:79-80` `assert resp.total == 1` / `resp.registros[0].status == "fechada"`; `:86-87` `status == "aberta"` | ✅ Coberto |
| STAT-02 | P1 AC3: união aberta+fechada (exclui indefinida) | `tests/test_filtro_status.py:92-95` `assert resp.total == 2` / `sorted(...) == ["aberta", "fechada"]` | ✅ Coberto |
| STAT-03 | P1 AC4: ausente/vazio = sem filtro (todos) | `tests/test_filtro_status.py:65-66` `estados_filtro() is None` (None e `[]`); `:99-100` `assert resp.total == 2` | ✅ Coberto |
| STAT-04 | P1 AC5: case-insensitive (+ dedup) | `tests/test_filtro_status.py:60-61` `FlowQuery(..., status=["Aberta","ABERTA"]).estados_filtro() == {"aberta"}` | ✅ Coberto |
| STAT-05 | P1 AC6: inválido → 422 / ValidationError | `tests/test_filtro_status.py:70-71` `pytest.raises(ValidationError)` (schema); `:163-165` `assert r.status_code == 422` + `erro == "Parametros invalidos"` (borda HTTP) | ✅ Coberto |
| STAT-06 | P1 AC7: filtro APÓS `_resolver_pendentes` (pendente fechada via lookahead conta como fechada) | `tests/test_filtro_status.py:127-128` `assert resp.total == 1` / `status == "fechada"`; `:131-132` filtrando "aberta" `assert resp2.total == 0` | ✅ Coberto |
| STAT-07 | P2 AC1-AC3: UI checkboxes Aberta/Fechada | **MANUAL** (browser, sem harness JS). Fonte: `static/plog.html:100-104` (`input name="status" value="aberta"/"fechada"` em `.checkbox_chip`); `static/script.js:299-304` `getSelectedStatus()`; `:334` `for (const estado of estados) params.append("status", estado)` | ⚠️ Manual (não automatizado) |
| STAT-08 | P1 AC8: compõe por AND com protocolo/IP/data | `tests/test_filtro_status.py:106-108` `status=["fechada"], protocolo=["tcp"]` → `assert resp.total == 1` / `protocolo == "TCP"` | ✅ Coberto |

Nota: AC8 é testado (rotulado STAT-08 no docstring do teste) mas **não aparece na
tabela Requirement Traceability da spec** (que lista só STAT-01..07). Gap de rastreio
documental, não de cobertura — ver Gaps.

### Evidência de implementação (código real)
- Campo `status`: `app/schemas/flow.py:24`. Validador `_validar_status`: `:57-71`.
  Const `ESTADOS_SESSAO`: `:11`. `estados_filtro()`: `:96-100`.
- Filtro pós-lookahead no service: `app/services/flow_service.py:118` (`_resolver_pendentes`)
  seguido de `:123-125` (`estados = query.estados_filtro(); if estados is not None: ...`).
- Param de rota `status`: `app/api/routes/flows.py:42-44`, repassado em `:59`.
- UI: `static/plog.html:97-105`, `static/script.js:299-304, 313, 334`.

---

## Sensor de discriminação (mutação de comportamento)

Cada mutação injetada isoladamente na árvore commitada, medida, e **revertida via
`git checkout --` imediatamente após**. Testes não foram alterados.

| # | Mutação | Alvo | Esperado | Resultado |
| - | ------- | ---- | -------- | --------- |
| a | Neutralizar filtro de estado (`if False and estados is not None`) | `app/services/flow_service.py:124` | matar testes de filtro por status | **KILLED** — 4 failed (test_so_fechada, test_so_aberta, test_compoe_com_protocolo, test_pendente_fechada_pelo_lookahead) |
| b | `_validar_status` aceita qualquer string (checagem desligada) | `app/schemas/flow.py:66` | matar teste de inválido→422/ValidationError | **KILLED** — 2 failed (test_invalido_rejeitado, test_rota_status_invalido_422) |
| c | Filtro de estado ANTES de `_resolver_pendentes` (ordem trocada) | `app/services/flow_service.py:117-125` | matar test_pendente_fechada_pelo_lookahead | **KILLED** — 1 failed (test_pendente_fechada_pelo_lookahead_conta_como_fechada) |

**3/3 KILLED. Nenhum mutante sobreviveu.** Árvore restaurada; `git status` limpo
(apenas alheios: `app/core/security.py` M, `Roteiro.pdf` untracked). Gate re-rodado
verde (104 passed) após reversões.

---

## Gaps (ranqueados)

1. **[Baixo — rastreio documental]** AC8 (composição AND) é testado
   (`test_filtro_status.py:102-108`, docstring "STAT-08") mas a tabela Requirement
   Traceability da spec (linhas 77-85) só vai até STAT-07. Sugestão: adicionar linha
   STAT-08 na tabela ou renumerar. Não afeta cobertura de comportamento.
2. **[Baixo — esperado por design]** STAT-07 (UI) sem teste automatizado — validado
   manualmente no browser. Consistente com a spec ("Independent Test: marcar Aberta e
   conferir `?status=aberta` na URL") e ausência de harness JS no projeto. O código da
   UI foi inspecionado e confere com os ACs P2.

Nenhum gap de comportamento aberto.
