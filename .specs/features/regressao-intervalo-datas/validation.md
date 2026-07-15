# Validation — Regressão Busca de Flows por Intervalo de Datas

**Verifier:** independente (fresh-eyes), evidence-or-zero.
**Data:** 2026-07-15
**Range de commits coberto:** `6bab0e1..HEAD`
- `1c80f5a` test(flows): add regression tests for date-interval flow search
- `1610c8b` docs(specs): scaffold spec-driven state and interval regression spec
- Diff em `tests/`: apenas `tests/test_flow_interval.py` (+140 linhas, novo arquivo).

## Veredito: PASS (gaps fechados na iteração 1 — ver seção 5)

**1ª passada:** todos os testes verdes; cada AC RINT-01..08 com assert no valor que a
spec define. O **discrimination sensor** revelou 2 mutantes sobreviventes (G1, G2) —
gaps de precisão de discriminação, não regressões silenciosas de AC.

**Re-verificação (iteração 1):** G1 e G2 corrigidos; os 3 mutantes antes sobreviventes
agora são **mortos**. Veredito final **PASS**. Detalhes na seção 5.

---

## 1. Gate

Comando:
```
python -m pytest tests/test_flow_interval.py -q
```
(venv Poetry `plog-v2-9tTC8FC8-py3.12`)

Resultado: **10 passed, 1 warning** (a warning é `StarletteDeprecationWarning`, não relacionada).

---

## 2. Cobertura ancorada na spec (evidence-or-zero)

| AC | Teste | file:line | Expressão do assert | Esperado pela spec | Status |
| -- | ----- | --------- | ------------------- | ------------------ | ------ |
| RINT-01 união multi-dia | `test_uniao_multi_dia` | `tests/test_flow_interval.py:60,62` | `assert resp.total == 2` / `assert datas == ["2026-07-14", "2026-07-15"]` | união dos eventos que casam em todo o intervalo | ⚠️ coberto (união discriminada; ver gap G1 sobre "que casam o filtro") |
| RINT-02 dia vazio ignorado | `test_dia_vazio_ignorado` | `tests/test_flow_interval.py:74,75,76` | `assert resp.total == 1` / `resp.registros[0].data[:10] == "2026-07-15"` / `resp.registros[0].origem == IP` | ignora dia vazio, retorna dias com dados, sem exceção | ✅ coberto |
| RINT-03 todos vazios → erro | `test_todos_dias_vazios_levanta` | `tests/test_flow_interval.py:83` | `with pytest.raises(FlowNotFoundError):` | levantar `FlowNotFoundError` | ✅ coberto |
| RINT-04 dia único vazio → erro | `test_dia_unico_vazio_levanta` | `tests/test_flow_interval.py:91` | `with pytest.raises(FlowNotFoundError):` | levantar `FlowNotFoundError` (legado) | ⚠️ coberto por tipo de exceção; ramo específico não discriminado (ver gap G2) |
| RINT-05 label do intervalo | `test_label_intervalo` | `tests/test_flow_interval.py:101` | `assert resp.data == "2026-07-14 a 2026-07-15"` | formato `"YYYY-MM-DD a YYYY-MM-DD"` | ✅ coberto |
| RINT-06 data_fim < data | `test_schema_data_fim_menor_rejeita` | `tests/test_flow_interval.py:107` | `with pytest.raises(ValidationError):` | rejeitar com `ValidationError` | ✅ coberto (killed by mut. c1) |
| RINT-07 > 31 dias | `test_schema_excede_maximo_rejeita` | `tests/test_flow_interval.py:115` | `with pytest.raises(ValidationError):` | rejeitar com `ValidationError` | ✅ coberto (killed by mut. c2) |
| RINT-08 `dias()` | `test_schema_dias_dia_unico` / `test_schema_dias_intervalo_ordenado` | `tests/test_flow_interval.py:129,130` / `:136-140` | `FlowQuery(data=d, data_fim=d).dias() == [d]` e `FlowQuery(data=d).dias() == [d]` / `== [14,15,16]` | um dia; e N+1 dias em ordem crescente | ✅ coberto |

Edge cases também cobertos:
- Limite inclusivo 31 dias: `test_schema_limite_maximo_aceito` `tests/test_flow_interval.py:124` — `assert len(query.dias()) == MAX_DIAS_INTERVALO`.

---

## 3. Discrimination sensor (mutation testing manual)

Cada mutação aplicada isoladamente e revertida com `git checkout --`. Testes NÃO alterados.

| # | Arquivo | Mutação | Resultado | Testes que falharam |
| - | ------- | ------- | --------- | ------------------- |
| a-v1 | `app/services/flow_service.py:37` | `data=dia_iso` → `data=None` | **SURVIVED** | nenhum (10 passed) |
| a-v2 | `app/services/flow_service.py:37` | `if pcap_event_matches(...)` → `if True or ...` (inclui todos) | **SURVIVED** | nenhum (10 passed) |
| b | `app/services/flow_service.py:28` | `if len(dias) == 1:` → `if False:` | **SURVIVED** | nenhum (10 passed) |
| c-v1 | `app/schemas/flow.py:39` | desativa `data_fim < data` (`if False and ...`) | **KILLED** | `test_schema_data_fim_menor_rejeita` |
| c-v2 | `app/schemas/flow.py:41` | desativa `> MAX_DIAS_INTERVALO` (`if False and ...`) | **KILLED** | `test_schema_excede_maximo_rejeita` |

### Diagnóstico complementar (para caracterizar os survivors)

- Mutação diagnóstica `for dia in dias:` → `for dia in dias[:1]:` (itera só o 1º dia):
  **KILLED** `test_uniao_multi_dia` e `test_dia_vazio_ignorado`.
  → Confirma que a **iteração/união multi-dia** (núcleo de RINT-01/02, o bug reportado) É discriminada.

### Por que os mutantes a/b sobreviveram (gaps)

- **G1 (mut. a):** o filtro por data intra-dia (`pcap_event_matches(..., data=dia_iso)`)
  não é morto porque o test-double `_service` retorna, para cada dia, apenas eventos
  já daquele dia e já com o IP correto. Nenhum teste injeta em um dia um evento de
  data/IP estranhos, então a cláusula "eventos **que casam o filtro**" de RINT-01
  não é discriminada. A união multi-dia em si É coberta (diagnóstico acima).
- **G2 (mut. b):** remover o re-raise do dia único (`if len(dias) == 1: raise`) não é
  morto porque, para um único dia sem dados, `dias_encontrados == 0` e o fallback
  em `flow_service.py:40-43` levanta o mesmo `FlowNotFoundError`. Como
  `test_dia_unico_vazio_levanta` só checa o **tipo** da exceção (não a mensagem nem
  o caminho), RINT-04 é indistinguível de RINT-03. O ramo específico é redundante
  para o comportamento observável testado.

Ambos os gaps são de **spec-precision** (comportamento observável do AC mantido),
não regressões de AC não asseguradas.

---

## 4. Estado final

- `git status` limpo em relação às mutações: nenhuma mutação persistida.
  (Única modificação presente é `app/core/security.py`, **pré-existente e fora de escopo**
  — não tocada por este verifier.)
- Gate re-executado após reverter tudo: **10 passed**.

---

## Gaps ranqueados (fix tasks sugeridas)

1. **G1 — RINT-01 cláusula "que casam o filtro" não discriminada.**
   Adicionar um caso em que o batch bruto de um dia contém um evento de outro dia
   e/ou de outro IP, e assertar que ele é excluído (`resp.total` não o conta).
   Mataria as mutações a-v1/a-v2.
2. **G2 — RINT-04 indistinguível de RINT-03.**
   Assertar a mensagem/identidade da exceção do dia único (ex.: que preserva a
   mensagem original do repositório), ou usar `pytest.raises(..., match=...)`,
   para distinguir o re-raise legado do fallback de intervalo. Mataria a mutação b.

---

## 5. Re-verificação (iteração 1 de 3) — gaps fechados

Correções aplicadas em `tests/test_flow_interval.py` (nenhum código de produção alterado):

- **G1:** novo teste `test_evento_fora_do_filtro_excluido` — injeta num dia um evento
  com IP `10.0.0.99` e outro com data `2026-07-13`, e assere `resp.total == 2`
  (apenas os que casam data+IP), discriminando o filtro intra-dia.
- **G2:** `test_dia_unico_vazio_levanta` agora usa `pytest.raises(FlowNotFoundError,
  match="sem dados para")` (re-raise legado do repositório) e
  `test_todos_dias_vazios_levanta` usa `match="intervalo"` (fallback de intervalo),
  distinguindo os dois caminhos.

**Gate após correção:** `pytest tests/test_flow_interval.py -q` → **11 passed**.

**Sensor re-executado (mutações antes sobreviventes):**

| # | Mutação | Resultado agora | Teste que matou |
| - | ------- | --------------- | --------------- |
| a-v1 | `data=dia_iso` → `data=None` | **KILLED** | `test_evento_fora_do_filtro_excluido` |
| a-v2 | `if pcap_event_matches(...)` → `if True or ...` | **KILLED** | `test_evento_fora_do_filtro_excluido` |
| b | `if len(dias) == 1:` → `if False:` | **KILLED** | `test_dia_unico_vazio_levanta` |

Working tree limpo após reverter todas as mutações. Veredito final: **PASS** —
8/8 ACs discriminados, 5/5 mutações prescritas mortas.
