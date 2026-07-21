# Sessões NAT: uma linha por sessão, com estado aberto/fechado

## Context

Hoje a tabela do PLOG mostra os eventos crus do nfdump: uma linha `NAT translation create`
e outra `NAT translation delete` para a **mesma** tradução. O analista precisa cruzar as
duas linhas mentalmente para responder a pergunta que importa — *"este bloco de portas ainda
está com o assinante?"*.

A feature colapsa o par numa **única linha de sessão**, com abertura, fechamento, duração e
um selo de estado: verde = aberta, vermelho = fechada.

A proposta inicial era usar o SQLite para comparar create/delete. Foi descartada: o par já
está no próprio log, e a comparação é uma varredura em memória. Gravar no banco e apagar
depois do uso adicionaria escrita, migration, concorrência entre analistas e a divergência
de URL do banco (`db.py:5` aponta para `app/database/plog.db`, `alembic.ini:89` para
`database/plog.db` — arquivos diferentes), **sem ganhar precisão alguma**. O SQLite continua
exclusivamente para usuários; o nfcapd segue como fonte única de verdade.

## Decisões

| # | Decisão | Motivo |
|---|---------|--------|
| D1 | Correlação **em memória**, sem banco | Mesmos dados, mesma janela; banco só agregaria custo |
| D2 | **Uma linha por sessão** | Responde direto "ainda aberta?", corta as linhas pela metade |
| D3 | Pareamento **cronológico com pilha por chave** | O bloco é realocado a outro assinante depois do delete; parear por chave global atribuiria tráfego ao assinante errado |
| D4 | Chave = `(roteador, origem, ip_nat, pblock_start, pblock_size)` — **sem `proto`** | Em alocação de bloco CGNAT o `proto` costuma vir 0/ausente |
| D5 | Evento não classificável → sessão **"indefinida"** de 1 evento | Nada some da tela; preserva todo o comportamento atual |
| D6 | Create sem par → resolvido por **consulta filtrada ao `nfdump`**, não relendo dias inteiros | Alocações duram até 6 meses; reler 180 dias × 24 horas seria ~4.300 execuções de nfdump. Uma consulta filtrada por chave, num único `-R range`, deixa o nfdump (C) achar o delete e devolver quase nada |
| D7 | Expressão de filtro do `nfdump` montada por **allowlist de valores tipados**, nunca por concatenação de string do usuário | Reabre a superfície de injeção que o projeto evitava; controlada porque os tokens são IPs já validados por `ip_address()` e inteiros de bloco, montados server-side |

## Abordagem

```
eventos da janela (já filtrados por IP/porta/protocolo/data)
        ↓  ordena por timestamp REAL (parseado, não string)
para cada evento:
    classe = create | delete | indefinido      (substring, case-insensitive)
    chave  = (roteador, origem, nat, pblock_start, pblock_size)

    create      → abre sessão, empilha em abertas[chave]
    delete      → desempilha o create mais recente ainda aberto  → sessão FECHADA
                  (pilha vazia = delete órfão → fechada, parcial=True)
    indefinido  → sessão isolada, status "indefinida"
        ↓
sobrou em `abertas` = pendentes → UMA consulta nfdump filtrada por chave,
                                   sobre um range amplo (dia seguinte → hoje)
        ↓
pagina SESSÕES (não eventos)
```

**Resolução de pendentes por pushdown (o núcleo da revisão).** Para cada create sem par
na janela, o backend pergunta ao `nfdump` diretamente: *"existe um delete deste bloco
(`ip4_router`, `src4_addr`, `src4_xlt_ip`, `pblock_start`) depois desta data?"*. O `nfdump`
lê o range num único `-R inicio:fim`, filtra em C e devolve pouquíssimos registros. Isso
funciona mesmo para alocações de 6 meses — o custo é proporcional ao que casa o filtro, não
ao volume total (~200 mil eventos/dia). Substitui a busca-adiante dia-a-dia, que era inviável.

Quando o filtro casa várias chaves pendentes de uma vez, agrupar numa expressão só
(`(chave1) or (chave2) or ...`), com teto de chaves por consulta para não gerar expressão
gigante.

**Por que pilha e não dicionário simples:** com `dict[chave] = create`, a sequência
`create A → delete A → create B → delete B` no mesmo bloco faria o delete de B fechar a
sessão de A. É o pior bug possível aqui — atribuição de tráfego ao assinante errado, num
sistema que responde ofício.

**Timestamp precisa ser parseado de verdade.** Ordenar `t_first` como string quebra em
silêncio se aparecer `" "` no lugar de `"T"`, sufixo `Z`, offset `-03:00` ou epoch — e ordem
errada aqui é exatamente o bug acima. Evento com timestamp ilegível vira "indefinido" em vez
de entrar na ordem no lugar errado.

## Arquivos

**Novos:** `app/parsers/nat_session.py`, `tests/unit/test_nat_session.py`,
`tests/test_nat_lookahead.py`, `.specs/features/sessoes-nat/spec.md`

**Alterados:** `app/services/flow_service.py`, `app/schemas/flow.py`, `app/core/config.py`,
`app/repositories/flow_repository.py` (novo método de consulta filtrada — ver E7),
`static/plog.html`, `static/script.js`, `static/style.css`, `.specs/STATE.md`

**Intocados:** `pcap_parser.py`, `flow_parser.py`, `routes/flows.py`, e **todos os testes
existentes**.

### Reuso (não reinventar)
- `_first_value`, `_as_int`, `_port_block_limits` — `app/parsers/pcap_parser.py:21,14,36`
- `normalize_pcap_event` (`pcap_parser.py:55`) alimenta os campos de exibição da sessão
- `parse_flows` / `FlowRecord` **permanecem** — usados por `tests/unit/test_flow_parser.py`
- Paleta verde/vermelha já existente em `style.css` (`#e7f8ee`/`#14703d`, `#fde8e8`/`#a11717`)
  e o padrão `.status_badge[data-state]` (`style.css:1105`)

## Etapas

Cada etapa é um commit atômico. Gate em todas: suíte verde, exceto as 7 falhas 401
pré-existentes de `tests/test_api.py` (dívida conhecida, fora de escopo).

**E1 — Spec.** `.specs/features/sessoes-nat/spec.md`, IDs `NAT-01..NN`, no formato de
`filtro-protocolo`.

**E2 — Primitivas puras** (`nat_session.py`): `classificar_evento`, `chave_sessao`,
`timestamp_evento`.
Testar: `create`/`delete` em `nat_event`, `event` e `type`; variações de caixa; `type:"EVENT"`
→ indefinido; string com create *e* delete → indefinido; chave `None` sem `src4_xlt_ip` /
sem `pblock_start` / sem `src4_addr`; timestamp com `T`, com espaço, `Z`, offset, epoch, lixo.

**E3 — Correlação.** `correlacionar(eventos)`.
Testar: par → 1 sessão fechada com duração; create sozinho → aberta; delete sozinho →
fechada + `parcial`; **realocação** (A create, A delete, B create, B delete na mesma chave →
2 sessões sem cruzamento); entrada fora de ordem → saída correta; indefinidos preservados 1:1.

**E4 — Schema `FlowSession`** (superset de `FlowRecord`): mantém `data`, `evento`, `protocolo`,
`origem`, `nat`, `bloco_portas`, `destino`, `roteador` com a mesma semântica, e acrescenta
`status`, `abertura`, `fechamento`, `duracao`, `duracao_segundos`, `verificado_ate`,
`parcial`, `eventos`. `FlowResponse.registros: List[FlowSession]`.

**E5 — Service correlaciona e pagina sessões.** Trocar a ordem em
`flow_service.py:52-57`: correlacionar sobre `filtrados` **completo**, depois fatiar.
Hoje a paginação corta antes do parse — se ficar assim, create e delete caem em páginas
diferentes e nunca se encontram. `total` passa a contar **sessões**.
Testar: suíte inteira verde + novo teste com par NAT real → `total == 1`, `status == "fechada"`.

**E6 — Verificar a sintaxe do `nfdump` no servidor real (pré-requisito, faça ANTES do E7).**
A sintaxe de filtro para NAT/bloco depende da versão do nfdump instalada — **não é conhecida
no código hoje**. Confirmar contra o binário real: como filtrar por `src ip`, pelo IP público
traduzido (algo como `nat ip` / `src nat ip`), pelo bloco de portas (`pblock start/size` ou
equivalente) e pelo evento de delete. Registrar a sintaxe verificada na spec. Config aqui:
`PLOG_NAT_LOOKAHEAD` (`1`/`0`, liga/desliga) e `PLOG_NAT_LOOKAHEAD_MAX_CHAVES` (teto de chaves
por consulta) em `app/core/config.py`.

**E7 — Consulta filtrada no repositório + resolução de pendentes no service.**
- `app/repositories/flow_repository.py`: novo método
  `fetch_flows_por_chave(chaves, inicio, fim) -> List[Dict]`, que monta a expressão de filtro
  **por allowlist** (só IPs já validados e inteiros de bloco; nada de string crua do usuário),
  faz `shlex.quote` na expressão inteira, e roda `nfdump -R <inicio:fim> '<expr>' -o json` numa
  única invocação. Reusa `_run_nfdump`/`_parse_nfdump_json` existentes.
- `app/services/flow_service.py`: terminada a correlação da janela, se sobrarem pendentes e
  `PLOG_NAT_LOOKAHEAD` ligado, chama o método acima (range = dia seguinte → hoje), fecha as
  sessões que casarem, marca `verificado_ate = hoje`. As que continuarem sem delete ficam
  `status="aberta"`.
- `FlowNotFoundError`/ausência de dados na consulta extra é engolida e **não** conta para
  `dias_encontrados` — contrato de 404 (RINT-03/04) intocado.
Testar (mock do repositório, molde `test_flow_interval.py::_service`): a expressão de filtro é
montada só com valores tipados (teste anti-injeção: chave com string maliciosa **não** é usada
crua — na prática a chave vem de campos numéricos/IP, o teste prova que valores não-IP/não-int
são rejeitados antes de entrar na expressão); pendente que casa delete no range → fechada;
pendente sem delete → aberta com `verificado_ate`; sem pendentes → **nenhuma** consulta extra
(assert de zero chamadas ao novo método); `PLOG_NAT_LOOKAHEAD=0` desliga; teto de chaves
respeitado.

**E8 — Frontend.** Colunas passam de 8 para: Status, Abertura, Fechamento, Duração,
Protocolo, Origem, NAT, Bloco Portas, Destino, Roteador.
⚠️ `colspan="8"` existe em **dois** lugares e ambos precisam mudar juntos:
`static/script.js:506` (`renderEmptyRow`) e `static/plog.html:135` (linha vazia estática).
Selo: verde `aberta`, vermelho `fechada`, cinza `indefinida`; tooltip mostra `verificado_ate`
no verde e o aviso de `parcial` no vermelho órfão.

**E9 — `.specs/STATE.md`.** `AD-004` (correlação em memória, chave sem `proto`, pilha
cronológica, `total` = sessões) e `AD-005` (lookahead: limite, filtro só por chave, dias
extras fora do 404). Handoff + lembrete de **reiniciar o backend** (AD-003).

## Verificação

0. **Pré-requisito (E6): sintaxe do `nfdump` confirmada no servidor real.** Rodar manualmente
   uma expressão de filtro por bloco/IP/evento contra o nfdump instalado e confirmar que
   devolve o delete esperado. Sem isso, o pushdown é chute — está marcado como incerto.
1. **Gate por etapa** (venv do Poetry):
   `python -m pytest tests/unit/test_nat_session.py tests/test_nat_lookahead.py tests/test_flow_protocolo.py tests/test_flow_interval.py tests/test_flow_service.py tests/unit -q`
2. **Sensor de discriminação** na etapa E3, obrigatório: trocar a pilha por
   `dict[chave] = create` e confirmar que o teste de realocação **falha**. Se sobreviver, o
   teste não protege o bug mais grave da feature.
3. **Frontend no browser**: servir `static/` e conferir as três classes de status com payload
   sintético; medir que a tabela não estoura na horizontal com as 10 colunas (hoje já tem
   `min-width: 980px`).
4. **Verificação end-to-end no ambiente real**: buscar um IP com par create/delete conhecido
   (como o do print: `172.16.10.17` → `177.137.21.38`, bloco `4096-4607`) e confirmar que as
   duas linhas viraram uma, fechada, com duração ~10s.
5. **Verifier independente** ao final (autor ≠ verificador), como nas features anteriores.

## Riscos

| Risco | Mitigação |
|-------|-----------|
| **Atribuição ao assinante errado** por realocação de bloco | Pilha cronológica + timestamp parseado + teste de realocação com sensor de mutação (item 2 da verificação) |
| Strings de evento não verificadas em código (só o seu print confirma `create`) | Classificação tolerante por substring sobre 3 campos; degradação é **segura** (vira "indefinida" e exibe como hoje, nada some) |
| **Sintaxe de filtro do nfdump desconhecida** (varia por versão) | E6 é pré-requisito bloqueante: confirmar contra o binário real antes de confiar; feature degrada para "aberta até <fim da janela>" se o pushdown falhar |
| **Injeção na expressão de filtro do nfdump** (superfície reaberta em D7) | Expressão montada só de valores tipados (IP validado por `ip_address()`, bloco como int); nunca string crua do usuário; `shlex.quote` na expressão; teste anti-injeção no E7 |
| **Custo do pushdown** | Uma consulta filtrada por lote de chaves, não releitura de dias inteiros; o custo escala com o que casa o filtro, não com os ~200 mil/dia; só roda com pendências, com teto de chaves por consulta |
| **Alocações de 6 meses / janela grande** | O pushdown resolve o "ainda aberto?" independentemente da idade da alocação. A janela de exibição em si ainda carrega tudo em memória (limite de 31 dias, comportamento pré-existente) — se janelas de meses virarem requisito de exibição, é outra frente (paginação server-side no nfdump) |
| `total` muda de significado (sessões, não eventos) | Campo `eventos` preserva a contagem crua; documentado em AD-004 |
| Perda da visão de evento cru | Aceito nesta versão; se fizer falta, um modo "eventos" volta como toggle |

## Fora de escopo

- Ingerir flows no SQLite (descartado — ver Context)
- Tokenizar a escala de espaçamento do CSS e o `z-index: 1000` do rodapé (dívida já mapeada)
- Corrigir as 7 falhas 401 de `tests/test_api.py` (dívida rastreada à parte)
- Corrigir a divergência de URL `db.py` × `alembic.ini` — não bloqueia esta feature, já que
  não mexemos no banco, mas vira mina terrestre na primeira migration futura
