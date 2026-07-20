# Validation — Filtro por Protocolo

**Verifier:** independente (fresh-eyes, autor ≠ verificador)
**Data:** 2026-07-20
**Branch:** `feature/filtro-protocolo`
**Range verificado:** `438da79^..HEAD` (`438da79`, `2b9676f`, `c4f0ae9`, `daba8f0`, `e982531`, `0e7caca`)
**Regra:** evidence-or-zero — só conta como coberto com `file:line` + expressão do assert.

## Veredito: **PASS (com gaps declarados)**

O núcleo do filtro (parser, schema, service) está coberto por asserts derivados da spec e
sobrevive ao sensor de discriminação: 6/6 mutações de comportamento no núcleo foram mortas.
Os gaps remanescentes (camada HTTP e frontend) já estavam declarados em `tasks.md` como
"sem teste" e não invalidam o comportamento entregue, mas são registrados abaixo.

---

## 1. Gate

| Nível | Comando | Resultado |
| ----- | ------- | --------- |
| Quick | `pytest tests/test_flow_protocolo.py -q` | **21 passed** |
| Full  | `pytest tests/test_flow_protocolo.py tests/test_flow_interval.py tests/test_flow_service.py tests/unit -q` | **60 passed** |

Breakdown do full: `test_flow_protocolo.py` 21, `test_flow_interval.py` 11,
`test_flow_service.py` 7, `unit/test_flow_parser.py` 3,
`unit/test_flow_repository_parser.py` 5, `unit/test_pcap_parser.py` 13.

`tests/test_api.py` **não executado** (7 falhas 401 pré-existentes, fora de escopo por spec §Out of Scope).

Runner: `plog-v2-9tTC8FC8-py3.12`. Gate re-executado após todas as mutações: verde,
`git status` limpo quanto às mutações (apenas `app/core/security.py` modificado e
`Roteiro.pdf` untracked, ambos alheios à feature e não tocados).

---

## 2. Cobertura spec-anchored (PROTO-01..09)

| AC | Spec exige | Evidência (`file:line` + assert) | Resultado |
| -- | ---------- | -------------------------------- | --------- |
| **PROTO-01** | `tcp`→proto 6, `udp`→17, `icmp`→1; só esses retornam | `tests/test_flow_protocolo.py:31` `assert PROTOCOLO_NUMEROS == {"icmp": 1, "tcp": 6, "udp": 17}`<br>`:35-37` `pcap_event_matches(_evento(TCP), protocolos={TCP}) is True` / `(_evento(UDP), protocolos={TCP}) is False` / `(_evento(ICMP), protocolos={TCP}) is False`<br>`:41-42` idem UDP; `:46-47` idem ICMP<br>`:95-100` `FlowQuery(data=DIA, protocolo=["tcp"]).protocolos_numericos() == {TCP}` (e udp/icmp)<br>`:151-152` `resp.total == 1` e `[r.protocolo for r in resp.registros] == ["TCP"]` | ✅ |
| **PROTO-02** | Multi-protocolo = união, exclui os demais | `:52-54` `protocolos={TCP,UDP}` → TCP `is True`, UDP `is True`, ICMP `is False`<br>`:96-99` `FlowQuery(...protocolo=["tcp","udp"]).protocolos_numericos() == {TCP, UDP}`<br>`:160-161` `resp.total == 2` e `sorted(...) == ["TCP", "UDP"]` | ✅ |
| **PROTO-03** | Ausente/vazio = sem filtro (todos) | `:58-60` loop sobre `(TCP,UDP,ICMP,GRE)`: `protocolos=None is True` e `protocolos=set() is True`<br>`:110-111` `FlowQuery(data=DIA).protocolos_numericos() is None` e `protocolo=[]` → `is None`<br>`:169-170` `resp.total == 4` e `sorted(...) == ["47", "ICMP", "TCP", "UDP"]` (GRE presente) | ✅ |
| **PROTO-04** | Proto fora do conjunto / ausente / não numérico → excluído | `:64` `pcap_event_matches(_evento(GRE), protocolos={TCP,UDP,ICMP}) is False`<br>`:68-70` `todos = set(PROTOCOLO_NUMEROS.values())` → GRE `is False`, `protocolos=None` `is True`<br>`:75-76` evento sem chave `proto`: `protocolos={TCP} is False`, `None is True`<br>`:80` `pcap_event_matches(_evento("abc"), protocolos={TCP}) is False` | ✅ |
| **PROTO-05** | Case-insensitive (`TCP`/`tcp`/`Tcp`) | `:104-106` `FlowQuery(...protocolo=["TCP"]).protocolos_numericos() == {TCP}`, `["Udp"] == {UDP}`, `["iCmP"] == {ICMP}`<br>`:118-120` `["tcp","TCP"]` → `{TCP}` (dedup case-insensitive) | ✅ |
| **PROTO-06** | Valor inválido → **422** com corpo `{"erro": "Parametros invalidos", ...}` | `:124-125` `pytest.raises(ValidationError): FlowQuery(data=DIA, protocolo=["foo"])`<br>`:129-130` idem para `["6"]` (número rejeitado)<br>Caminho 422 existe em `app/api/routes/flows.py:61-68` (`except ValidationError` → `JSONResponse({"erro": "Parametros invalidos", ...}, status_code=422)`) mas **nenhum teste asserta status 422 nem o corpo**. | ⚠️ spec-precision gap |
| **PROTO-07** | AND com IP/porta/data | `:85-89` `pcap_event_matches(evento, ip="100.64.18.210", protocolos={TCP}) is True`; `ip="10.0.0.1", protocolos={TCP} is False`; `ip="100.64.18.210", protocolos={UDP} is False`<br>`:181-183` `resp.total == 1`, `registros[0].protocolo == "TCP"`, `registros[0].origem == "100.64.18.210"` | ✅ (AND com `porta` e `data` não tem assert dedicado — coberto por simetria de implementação, não por evidência) |
| **PROTO-08** | UI exibe multi-seleção com exatamente TCP/UDP/ICMP | Sem harness JS. Implementado em `static/plog.html:72-80` (`<select id="protocolo" multiple size="3">` com 3 `<option>`). Declarado como verificação manual em `tasks.md:30` e `tasks.md:90`. | ⚠️ manual — **não contado** como coberto |
| **PROTO-09** | 0 marcados → sem param; N marcados → N params em minúsculo | Sem harness JS. Implementado em `static/script.js:292-296` (`getSelectedProtocols`) e `:322-323` (`for (const protocolo of protocolos) params.append("protocolo", protocolo)`). Declarado manual em `tasks.md:30`. | ⚠️ manual — **não contado** como coberto |

**Cobertura automatizada:** 7/9 ACs plenamente cobertos (PROTO-01..05, 07 ✅; PROTO-06 parcial).
2/9 (PROTO-08, 09) sem cobertura automatizada por ausência declarada de harness JS.

Nenhum caso de spec-precision gap por **valor errado** foi encontrado: todos os números
asseridos (1/6/17) conferem com a spec e com IANA, e o comportamento "todos os três ≠ sem
filtro" (spec §Edge Cases) está codificado explicitamente em `:68-70`.

---

## 3. Discrimination sensor

Mutações de comportamento injetadas uma por vez, revertidas com `git checkout --` após cada rodada.
Arquivos de teste **não** foram alterados.

| # | Arquivo | Mutação | Testes que falharam | Veredito |
| - | ------- | ------- | ------------------- | -------- |
| a | `app/parsers/pcap_parser.py` | `_as_int(...) not in protocolos` → `in protocolos` (condição invertida) | 12 failed / 9 passed — `test_filtra_somente_{tcp,udp,icmp}`, `test_uniao_multi_protocolo`, `test_protocolo_fora_do_conjunto_excluido`, `test_todos_os_tres_nao_equivale_a_sem_filtro`, `test_evento_sem_proto_excluido`, `test_evento_com_proto_nao_numerico_excluido`, `test_compoe_com_filtro_de_ip`, `test_um_protocolo_filtra_resultado`, `test_multi_protocolo_retorna_uniao`, `test_compoe_com_ip` | **KILLED** |
| b | `app/parsers/pcap_parser.py` | `if protocolos:` → `if False:` (filtro no-op) | 12 failed / 9 passed (mesmo conjunto de a) | **KILLED** |
| c | `app/parsers/pcap_parser.py` | `PROTOCOLO_NUMEROS` fixo com `tcp→17`, `udp→6` | 6 failed / 15 passed — `test_mapa_reverso_dos_tres_protocolos`, `test_converte_nomes_para_numeros`, `test_case_insensitive`, `test_deduplica_valores_repetidos`, `test_um_protocolo_filtra_resultado`, `test_compoe_com_ip` | **KILLED** |
| d | `app/schemas/flow.py` | Removida a checagem `if nome not in PROTOCOLO_NUMEROS: raise ValueError(...)` | 2 failed / 19 passed — `test_protocolo_invalido_rejeitado`, `test_protocolo_numerico_rejeitado` | **KILLED** |
| e | `app/schemas/flow.py` | `str(item).strip().lower()` → `str(item).strip()` (sem normalização) | 2 failed / 19 passed — `test_case_insensitive`, `test_deduplica_valores_repetidos` | **KILLED** |
| f | `app/services/flow_service.py` | Removido `protocolos=protocolos` da chamada a `pcap_event_matches` | 3 failed / 18 passed — `test_um_protocolo_filtra_resultado`, `test_multi_protocolo_retorna_uniao`, `test_compoe_com_ip` | **KILLED** |
| g *(extra, do verificador)* | `app/api/routes/flows.py` | Removido `protocolo=protocolo,` da construção do `FlowQuery` (rota ignora o param) | **21 passed** — nenhum teste falhou | **SURVIVED** |

**Placar: 6 KILLED / 1 SURVIVED (7 mutações).** Todas as mutações do núcleo especificado
(a–f) foram mortas. A sobrevivente (g) é da camada HTTP, declarada sem teste em `tasks.md:79`.

Após todas as reversões: gate quick 21 passed, gate full 60 passed, `git status` sem
resíduo de mutação.

---

## 4. Gaps ranqueados

| # | Sev | Gap | Evidência | Fix task sugerida |
| - | --- | --- | --------- | ----------------- |
| 1 | **Média** | Wiring da rota não é testado: remover `protocolo=protocolo` de `app/api/routes/flows.py:55` não quebra nenhum teste (MUT-G sobreviveu). O filtro poderia ser silenciosamente desligado em produção sem sinal na suíte. | MUT-G survived; `tasks.md:79` declara "Tests: none" | Teste de rota que instancia `listar_flows` (ou usa `TestClient` com `verificar_token_acesso` sobrescrito via `dependency_overrides`) e verifica que `protocolo=["tcp"]` chega ao `FlowService` — p.ex. mock do service capturando o `FlowQuery.protocolo`. Contorna a dívida de auth sem depender de `test_api.py`. |
| 2 | **Baixa** | PROTO-06 asserido só no schema: nenhum teste confirma **status 422** nem o corpo `{"erro": "Parametros invalidos"}` que a spec §AC8 exige literalmente. | `tests/test_flow_protocolo.py:124-130` asserta apenas `ValidationError`; caminho HTTP em `app/api/routes/flows.py:61-68` | Mesmo harness do gap #1: chamar a rota com `protocolo=["foo"]` e assertar `response.status_code == 422` e `response.json()["erro"] == "Parametros invalidos"`. |
| 3 | **Baixa (aceito)** | PROTO-08 e PROTO-09 sem cobertura automatizada (sem harness JS no projeto). Regressão na montagem da URL ou nas opções do `<select>` passaria despercebida. | `tasks.md:30` e `tasks.md:90` declaram verificação manual | Aceito para este ciclo. Verificação manual conforme spec §P2 Independent Test (marcar TCP+UDP e conferir `protocolo=tcp&protocolo=udp` na aba Network). Se um harness JS for introduzido, cobrir `buildUrl()`/`getSelectedProtocols()`. |
| 4 | **Informativo** | PROTO-07 tem assert dedicado só para AND com `ip`; AND com `porta` e `data` não tem assert próprio no arquivo de escopo. | `tests/test_flow_protocolo.py:85-89`, `:177-183` | Opcional: um caso adicional combinando `protocolo` + `porta` no `TestProtocoloMatcher`. Risco baixo — os filtros são independentes e sequenciais no matcher. |

---

## 5. Conclusão

O comportamento especificado em PROTO-01..05 e PROTO-07 está implementado e provado por
testes que discriminam: nenhuma das mutações de núcleo sobreviveu. PROTO-06 está
implementado corretamente e validado na borda do schema, faltando apenas o assert do
contrato HTTP. PROTO-08/09 permanecem como verificação manual declarada.

**Recomendação:** merge liberado; abrir os gaps #1 e #2 como follow-up (um único teste de
rota resolve ambos).

---

## Re-verificação (iteração 1 de 3) — gaps 1 e 2 fechados

Correção aplicada apenas em `tests/test_flow_protocolo.py` (nenhum código de produção alterado),
commit `470a70b`.

Novo harness `api_client`: `TestClient` com `dependency_overrides` de
`verificar_token_acesso` (contorna a dívida de auth de `tests/test_api.py`, sem tocá-la)
e de `get_flow_service` por um espião que captura o `FlowQuery` montado pela rota.

Testes adicionados (classe `TestProtocoloRota`):

| Teste | Fecha | Assert |
| ----- | ----- | ------ |
| `test_rota_repassa_protocolos_selecionados` | Gap 1 | `capturado["query"].protocolo == ["tcp","udp"]` e `protocolos_numericos() == {6,17}` |
| `test_rota_sem_protocolo_nao_filtra` | PROTO-03 na borda HTTP | `query.protocolo is None` |
| `test_rota_protocolo_invalido_retorna_422` | Gap 2 (PROTO-06 AC8) | `status_code == 422` e `json()["erro"] == "Parametros invalidos"` |

**Gate após correção:** quick **24 passed**; full **63 passed**.

**Sensor re-executado no mutante sobrevivente:**

| # | Mutação | Antes | Agora |
| - | ------- | ----- | ----- |
| g | `flows.py` deixa de passar `protocolo=protocolo` ao `FlowQuery` | SURVIVED (21 passed) | **KILLED** (2 failed) |

Working tree sem resíduo após reverter. **Veredito final: PASS** — 7/7 mutações mortas;
PROTO-06 agora com assert do contrato HTTP (422 + corpo). Permanecem como gaps aceitos:
PROTO-08/09 (frontend, verificados manualmente no browser — multi-select renderiza e a URL
recebe um `protocolo` por item marcado) e o item informativo sobre `porta`/`data` em PROTO-07.
