# Validation — Sessões NAT (feature/sessoes-nat)

**Verifier independente (fresh-eyes, autor ≠ verificador).** Cobertura re-derivada do zero a
partir de `spec.md`, regra *evidence-or-zero* (só conta como coberto quando há `file:line` +
a expressão do assert, e o valor asserido bate com a spec).

**Range de commits:** `ed125d0^..HEAD` (9 commits — `ed125d0` spec/plan → `e8b5e1e` STATE/handoff).

---

## Veredito: **PASS**

- Gate: **108 passed** (0 falhas no escopo).
- Cobertura: **11/11 ACs** (NAT-01..10 automatizados; NAT-11 = UI, verificação manual).
- Sensor de discriminação: **5/5 mutações KILLED**, 0 sobreviventes.
- `git status` ao final: limpo no escopo da feature (só `app/core/security.py` M e `Roteiro.pdf`
  untracked — alheios, pré-existentes).

---

## 1. Gate

Comando (venv Poetry):
```
pytest tests/unit tests/test_flow_service.py tests/test_flow_interval.py \
       tests/test_flow_protocolo.py tests/test_nat_sessao.py tests/test_nat_lookahead.py -q
```
Resultado: **108 passed, 1 warning** (StarletteDeprecationWarning, inócuo).
`tests/test_api.py` NÃO rodado (7 falhas 401 pré-existentes, fora de escopo, conforme instrução).

---

## 2. Cobertura ancorada na spec (evidence-or-zero)

| AC | Descrição (spec) | Teste — file:line | Assert (expressão) | Esperado bate? | Status |
|----|------------------|-------------------|--------------------|----------------|--------|
| NAT-01 | par create+delete → 1 sessão `fechada` + duração | `tests/unit/test_nat_session.py:150-153` | `len(r.sessoes)==1`; `s.status=="fechada"`; `s.duracao_segundos==10.0`; `s.eventos==2` | sim | ✅ |
| NAT-01 | idem no nível service (`total==1`, duração legível) | `tests/test_nat_sessao.py:47-54` | `resp.total==1`; `registro.status=="fechada"`; `registro.duracao=="10s"`; `bloco_portas=="4096-4607"`; `eventos==2` | sim | ✅ |
| NAT-02 | create sem delete → `aberta` (e pendente) | `tests/unit/test_nat_session.py:161-165` | `r.sessoes[0].status=="aberta"`; `fechamento is None`; `len(r.pendentes)==1` | sim | ✅ |
| NAT-02 | idem service | `tests/test_nat_sessao.py:62-64` | `resp.total==1`; `status=="aberta"`; `fechamento is None` | sim | ✅ |
| NAT-03 | delete órfão → `fechada`, `parcial=True`, `abertura=None` | `tests/unit/test_nat_session.py:171-175` | `s.status=="fechada"`; `s.parcial is True`; `s.abertura is None`; `r.pendentes==[]` | sim | ✅ |
| NAT-04 | realocação (A/A/B/B mesma chave) → 2 sessões sem cruzar | `tests/unit/test_nat_session.py:190-196` | `len(r.sessoes)==2`; `sorted(duracoes)==[5.0,20.0]`; `all status=="fechada"` | sim | ✅ |
| NAT-05 | não classificável → sessão `indefinida` 1:1, sem descartar | `tests/unit/test_nat_session.py:204-208` | `len(r.sessoes)==2`; `all status=="indefinida"`; `r.pendentes==[]` | sim | ✅ |
| NAT-06 | fora de ordem → correlaciona por timestamp real | `tests/unit/test_nat_session.py:216-219` | `len==1`; `status=="fechada"`; `duracao_segundos==10.0`; `parcial is False` | sim | ✅ |
| NAT-07 | lookahead: pendente + delete no range → `fechada` c/ fechamento real | `tests/test_nat_lookahead.py:77-80` | `resp.total==1`; `status=="fechada"`; `fechamento[:10]=="2020-01-05"`; `fetch_flows_por_chave.assert_called_once()` | sim | ✅ |
| NAT-07 | lookahead: pendente sem delete → `aberta`, `verificado_ate=hoje` | `tests/test_nat_lookahead.py:91-92` | `status=="aberta"`; `verificado_ate==date.today().isoformat()` | sim | ✅ |
| NAT-08 | sem pendentes → nenhuma consulta extra | `tests/test_nat_lookahead.py:106-107` | `status=="fechada"`; `fetch_flows_por_chave.assert_not_called()` | sim | ✅ |
| NAT-09 | `PLOG_NAT_LOOKAHEAD=0` → pula resolução, fica `aberta` | `tests/test_nat_lookahead.py:119-121` | `status=="aberta"`; `verificado_ate is None`; `assert_not_called()` | sim | ✅ |
| NAT-10 | filtro montado só com valores tipados (anti-injeção) | `tests/test_nat_lookahead.py:54,58,63-64` | `construir_filtro_nfdump([maliciosa])==""`; bloco não-int → `""`; mistura mantém só a válida (`"4096" in expr and "8192" not in expr`) | sim | ✅ |
| NAT-11 | UI: selo verde/vermelho/cinza, tooltip `verificado_ate`, aviso `parcial` | `static/script.js:350-361` + `static/style.css:1288-1303` | `data-state` por status; tooltip `Sem fechamento até …` (aberta) / aviso órfão (parcial); classes `.session_badge[data-state=aberta|fechada|indefinida]` | código presente | ⚠️ manual (sem harness JS) |

**Cobertura de edge cases (spec §Edge Cases) — suporte adicional, não-AC:**
- LIFO (duas abertas mesma chave → fecha a mais recente): `tests/unit/test_nat_session.py:229-236`.
- Timestamp `T`/espaço/`Z`/offset/epoch/lixo: `tests/unit/test_nat_session.py:104-141` (classe `TestTimestampEvento`).
- Lista vazia → `[]`: `tests/unit/test_nat_session.py:238-241`.
- Chave incompleta (sem nat / sem pblock / sem origem) → `None`: `tests/unit/test_nat_session.py:83-101`.

---

## 3. Sensor de discriminação (mutações de comportamento)

Cada mutação injetada isoladamente, testes rodados, revertida com `git checkout --` imediatamente.
Código commitado → checkout restaura corretamente.

| # | Arquivo | Mutação | Testes que FALHARAM (amostra) | Resultado |
|---|---------|---------|-------------------------------|-----------|
| a | `app/parsers/nat_session.py` | pilha → dict: `abertas[chave].append` → `= [sessao]` **e** `pilha.pop()` → `pilha[-1]` | `test_realocacao_nao_cruza_assinantes`, `test_par_vira_sessao_fechada_com_duracao` | **KILLED** |
| b | `nat_session.py` `timestamp_evento` | retorna sempre `None` | 19 falhas (correlação + service + lookahead: `test_par…`, `test_ordem…`, `test_delete_orfao…`, todos os `TestResolverPendentes`) | **KILLED** |
| c | `nat_session.py` `classificar_evento` | retorna sempre `"indefinido"` | 17 falhas (`test_par…`, `test_create_sozinho…`, `test_delete_orfao…`, service, lookahead) | **KILLED** |
| d | `app/repositories/flow_repository.py` `construir_filtro_nfdump` | remove validação `ip_address`/int (aceita qualquer string) | `test_anti_injecao_descarta_chave_com_ip_malicioso`, `test_anti_injecao_descarta_bloco_nao_inteiro`, `test_mistura_valida_e_invalida_mantem_so_a_valida` | **KILLED** |
| e | `app/services/flow_service.py` `_resolver_pendentes` | `return` imediato (no-op) | `test_fecha_sessao_com_delete_posterior`, `test_sem_delete_fica_aberta_com_verificado_ate` | **KILLED** |

**Sobreviventes: 0.** O teste de realocação (NAT-04) — o bug mais grave da feature (atribuição
ao assinante errado) — é morto pela mutação (a), confirmando que a suíte protege a pilha LIFO.

Pós-sensor: `git status` limpo no escopo; gate re-rodado = **108 passed**.

---

## 4. Gaps ranqueados (fix tasks)

PASS limpo. Nenhum gap bloqueante. Itens advisory (não afetam veredito):

1. **[baixa] NAT-11 sem cobertura automatizada.** A UI (selo, tooltip, `parcial`) é verificada
   só manualmente no browser — sem harness JS no projeto. Aceito pela spec (P3 Independent Test =
   "verificação manual"). Risco residual: regressão silenciosa em `statusBadge`/CSS.
2. **[baixa] Edge case "protocolo do par" sem teste direto.** `_protocolo_da_sessao`
   (`flow_service.py:23-37`) implementa "create proto 0/ausente + delete válido → usa o do delete",
   mas nenhum teste exercita o caso create-inválido/delete-válido diretamente (fixtures usam
   `proto:6` em ambos). Edge case da spec §Edge Cases, não um AC numerado.
3. **[informativo] Sintaxe do filtro nfdump ainda pendente (E6).** Keywords `src nat ip`/
   `pblock start` dependem da versão do binário real (marcado na spec como pendência E6 e em
   `construir_filtro_nfdump`). Não testável em unidade; a montagem por allowlist (NAT-10) está
   coberta, a sintaxe exata é validação de ambiente.

---

*Verificado por: Verifier independente. Data: 2026-07-21.*
