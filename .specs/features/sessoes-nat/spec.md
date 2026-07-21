# Sessões NAT — uma linha por sessão (aberto/fechado)

## Problem Statement

A tabela de flows mostra os eventos crus do nfdump: uma linha `NAT translation create` e
outra `NAT translation delete` para a MESMA tradução. O analista precisa cruzar as duas
linhas para responder a pergunta que importa — *"este bloco de portas ainda está com o
assinante?"*. Esta feature colapsa o par numa única linha de sessão, com abertura,
fechamento, duração e um selo de estado (verde = aberta, vermelho = fechada).

## Goals

- [ ] Correlacionar create+delete da mesma tradução numa única sessão.
- [ ] Exibir estado colorido: aberta / fechada / indefinida.
- [ ] Resolver create sem par via consulta filtrada ao nfdump (alocações duram até 6 meses).
- [ ] Zero regressão nos filtros e testes existentes.

## Out of Scope

| Item | Motivo |
| ---- | ------ |
| Ingerir flows no SQLite | O par já está no log; banco só agregaria custo e uma 2ª fonte de verdade. Banco segue só com usuários. |
| Exibir janelas de meses de sessões de uma vez | A janela de exibição carrega tudo em memória (limite de 31 dias já existente). Paginação server-side no nfdump é outra frente. |
| Modo "eventos crus" (toggle) | Aceito perder a visão crua nesta versão; volta como toggle se fizer falta. |
| Corrigir divergência de URL `db.py` × `alembic.ini` | Não tocamos no banco; vira dívida separada. |

---

## Assumptions & Open Questions

| Assumption / decisão | Default escolhido | Racional | Confirmado? |
| -------------------- | ----------------- | -------- | ----------- |
| Correlação em memória, sem banco | Varredura cronológica sobre os eventos já carregados | Mesmos dados, mesma janela | y |
| Chave de sessão | `(roteador, origem, ip_nat, pblock_start, pblock_size)`, sem `proto` | Em alocação de bloco CGNAT o `proto` vem 0/ausente | y |
| Pareamento | Cronológico, pilha (LIFO) por chave | Bloco é realocado a outro assinante após o delete; chave global misturaria assinantes | y |
| Evento não classificável / sem chave / sem timestamp | Vira sessão "indefinida" de 1 evento | Nada some da tela; preserva comportamento atual | y |
| Strings de evento | `create`/`delete` reconhecidos por substring, case-insensitive, em `nat_event`/`event`/`type` | Só o print de produção confirma os valores; degradação é segura | y |
| Create sem par na janela | Consulta filtrada ao nfdump (dia seguinte → hoje) | Alocações de 6 meses inviabilizam reler dias inteiros | y |
| Expressão de filtro do nfdump | Montada por allowlist de valores tipados + `shlex.quote` | Reabre superfície de injeção; controlada por IP validado | y |
| **Sintaxe de filtro do nfdump** | `(src ip <origem> and src nat ip <nat>)`; bloco casado em Python | **Confirmada no nfdump 1.7.8** (ver nfdump-filtro.md): `pblock` não é filtrável nessa versão | **y — verificado 2026-07-21** |

**Open questions:** none — a sintaxe do nfdump foi confirmada contra o servidor real
(nfdump 1.7.8) e validada end-to-end com dados de produção.

---

## User Stories

### P1: Uma linha por sessão com estado ⭐ MVP

**User Story**: Como analista, quero ver cada tradução NAT como uma linha com estado
aberto/fechado, para responder direto se um bloco ainda está alocado.

**Acceptance Criteria**:

1. WHEN existem um create e um delete da mesma chave na janela THEN o sistema SHALL emitir UMA sessão com status `fechada`, `abertura` = t do create, `fechamento` = t do delete e `duracao` calculada.
2. WHEN existe um create sem delete correspondente THEN o sistema SHALL emitir a sessão com status `aberta`.
3. WHEN existe um delete sem create na janela THEN o sistema SHALL emitir sessão `fechada` com `parcial = true` e `abertura = null`.
4. WHEN a mesma chave é realocada (create A, delete A, create B, delete B) THEN o sistema SHALL emitir DUAS sessões sem cruzar o delete de B com o create de A.
5. WHEN o evento não é classificável, não tem chave completa ou tem timestamp ilegível THEN o sistema SHALL emitir sessão `indefinida` de 1 evento, sem descartá-lo.
6. WHEN os eventos chegam fora de ordem cronológica THEN o sistema SHALL correlacionar pela ordem temporal real (timestamp parseado), não pela ordem de entrada.

**Independent Test**: `pytest tests/unit/test_nat_session.py` verde; par create/delete → `total == 1`, `status == "fechada"`.

---

### P2: Resolver sessões abertas antigas via nfdump

**User Story**: Como analista, quero que um create sem delete na janela seja verificado além
dela, para não ver "aberta" numa sessão que fechou meses depois.

**Acceptance Criteria**:

1. WHEN sobram sessões pendentes após a correlação e o lookahead está ligado THEN o sistema SHALL consultar o nfdump filtrado pelas chaves pendentes no range (dia seguinte → hoje).
2. WHEN a consulta encontra o delete THEN a sessão SHALL virar `fechada` com o `fechamento` real.
3. WHEN a consulta não encontra delete THEN a sessão SHALL permanecer `aberta` com `verificado_ate` = hoje.
4. WHEN não há sessões pendentes THEN o sistema SHALL NÃO fazer nenhuma consulta extra.
5. WHEN `PLOG_NAT_LOOKAHEAD=0` THEN o sistema SHALL pular a resolução e deixar as pendentes como `aberta`.
6. WHEN a expressão de filtro é montada THEN ela SHALL conter apenas valores tipados (IP validado, inteiros de bloco), nunca string crua.

**Independent Test**: `pytest tests/test_nat_lookahead.py` verde.

---

### P3: Exibição na interface

**User Story**: Como analista, quero ver o estado colorido e as colunas de abertura/duração
na tabela.

**Acceptance Criteria**:

1. WHEN a tabela é renderizada THEN cada linha SHALL mostrar um selo verde (`aberta`), vermelho (`fechada`) ou cinza (`indefinida`).
2. WHEN a sessão está aberta THEN o selo SHALL indicar `verificado até <data>` (tooltip).
3. WHEN a sessão é `parcial` THEN a UI SHALL sinalizar que a abertura ocorreu antes da janela.

**Independent Test**: verificação manual no browser com payload das três classes.

---

## Edge Cases

- WHEN duas sessões da mesma chave estão abertas ao mesmo tempo (anomalia) THEN o delete SHALL fechar a mais recente (LIFO).
- WHEN o timestamp vem com `T`, espaço, sufixo `Z`, offset `-03:00` ou epoch THEN o sistema SHALL parseá-lo corretamente; lixo → sessão indefinida.
- WHEN a lista de eventos é vazia THEN o resultado SHALL ser `[]` sem consulta extra.
- WHEN o create tem `proto` 0/ausente e o delete tem proto válido THEN o protocolo exibido SHALL vir do que for válido.

---

## Requirement Traceability

| Requirement ID | Story | Fase | Status |
| -------------- | ----- | ---- | ------ |
| NAT-01 | P1 AC1 (par → fechada + duração) | Execute | Verified |
| NAT-02 | P1 AC2 (create sozinho → aberta) | Execute | Verified |
| NAT-03 | P1 AC3 (delete órfão → parcial) | Execute | Verified |
| NAT-04 | P1 AC4 (realocação sem cruzamento) | Execute | Verified |
| NAT-05 | P1 AC5 (indefinido preservado) | Execute | Verified |
| NAT-06 | P1 AC6 (ordem cronológica real) | Execute | Verified |
| NAT-07 | P2 AC1-AC3 (lookahead nfdump) | Execute | Verified |
| NAT-08 | P2 AC4 (sem pendentes = sem consulta) | Execute | Verified |
| NAT-09 | P2 AC5 (desligável por env) | Execute | Verified |
| NAT-10 | P2 AC6 (filtro por allowlist) | Execute | Verified |
| NAT-11 | P3 AC1-AC3 (UI de status) | Execute | Verified |

**Coverage:** 11 requisitos, todos mapeados para etapas (ver plano aprovado).

---

## Success Criteria

- [ ] Par create/delete conhecido vira uma linha fechada com duração correta.
- [ ] Realocação de bloco nunca atribui tráfego ao assinante errado (teste + sensor de mutação).
- [ ] Suíte existente sem regressão (exceto as 7 falhas 401 pré-existentes).
- [ ] Verifier independente confirma que os testes matam mutações da correlação.
