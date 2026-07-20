# Tasks — Filtro por Protocolo

## Execution Plan

| Fase | Tasks | Descrição |
| ---- | ----- | --------- |
| 1. Núcleo do filtro | T1, T2 | Mapa reverso + matcher; schema + validação |
| 2. Exposição na API | T3, T4 | Service repassa o filtro; rota aceita o param |
| 3. Interface | T5 | Controle de multi-seleção e montagem da URL |

3 fases → execução inline (sem delegação a sub-agentes).

## Gate Check Commands

Runner: venv do Poetry `plog-v2-9tTC8FC8-py3.12`.

| Nível | Comando |
| ----- | ------- |
| Quick | `python -m pytest tests/test_flow_protocolo.py -q` |
| Full  | `python -m pytest tests/test_flow_protocolo.py tests/test_flow_interval.py tests/test_flow_service.py tests/unit -q` |
| Build | `python -m pytest tests/test_flow_protocolo.py tests/test_flow_interval.py tests/test_flow_service.py tests/unit -q` (suíte completa exclui `test_api.py`, com 7 falhas 401 pré-existentes) |

## Test Coverage Matrix

| Camada | Cobre | Expectativa |
| ------ | ----- | ----------- |
| Parser (`pcap_event_matches`) | PROTO-01, 02, 03, 04, 07 | Assert 1:1 por AC; cada edge case listado tem teste dedicado |
| Schema (`FlowQuery`) | PROTO-03, 05, 06 | Normalização, dedup, rejeição de inválido |
| Service (`buscar_flows`) | PROTO-01, 02, 07 | Filtro de ponta a ponta sobre eventos brutos |
| Frontend | PROTO-08, 09 | Verificação manual (sem harness JS no projeto) |

---

## T1 — Mapa reverso + filtro de protocolo no matcher

**Arquivos:** `app/parsers/pcap_parser.py`, `tests/test_flow_protocolo.py`
**Depende de:** —
**Tests:** unit | **Gate:** quick
**Requisitos:** PROTO-01, PROTO-02, PROTO-03, PROTO-04, PROTO-07

**Done when:**
- `PROTOCOLO_NUMEROS` existe, derivado de `PROTOCOLOS` (D2), mapeando `"icmp"→1`, `"tcp"→6`, `"udp"→17`.
- `pcap_event_matches` aceita `protocolos: Optional[Set[int]] = None` (default preserva chamadas atuais).
- Com `protocolos` não vazio, o evento entra somente se `_as_int(event["proto"])` pertence ao conjunto.
- Com `protocolos` `None` ou vazio, nenhum filtro de protocolo é aplicado.
- Evento sem `proto` ou com `proto` não numérico é excluído quando o filtro está ativo.

## T2 — Campo `protocolo` no schema com validação

**Arquivos:** `app/schemas/flow.py`, `tests/test_flow_protocolo.py`
**Depende de:** T1 (usa `PROTOCOLO_NUMEROS`)
**Tests:** unit | **Gate:** quick
**Requisitos:** PROTO-03, PROTO-05, PROTO-06

**Done when:**
- `FlowQuery.protocolo: Optional[List[str]]`.
- Validador aceita nomes em qualquer capitalização, normaliza para minúsculo e deduplica.
- Nome fora de `PROTOCOLO_NUMEROS` levanta `ValidationError`.
- `None` e lista vazia resultam em "sem filtro".
- `protocolos_numericos()` devolve `Set[int]` correspondente, ou `None` quando sem filtro.

## T3 — Service repassa o filtro ao matcher

**Arquivos:** `app/services/flow_service.py`, `tests/test_flow_protocolo.py`
**Depende de:** T1, T2
**Tests:** unit | **Gate:** full
**Requisitos:** PROTO-01, PROTO-02, PROTO-07

**Done when:**
- `buscar_flows` obtém o conjunto via `query.protocolos_numericos()` e o repassa a `pcap_event_matches`.
- Busca com um protocolo retorna apenas eventos daquele protocolo.
- Busca com dois protocolos retorna a união e exclui os demais.
- Filtro de protocolo compõe por AND com `ip` e `data` (intervalo).

## T4 — Query param `protocolo` na rota

**Arquivos:** `app/api/routes/flows.py`
**Depende de:** T2
**Tests:** none (coberto por T2/T3; camada HTTP bloqueada pela dívida de auth) | **Gate:** full
**Requisitos:** PROTO-06

**Done when:**
- `protocolo: Optional[List[str]] = Query(None, description=...)` declarado e repassado ao `FlowQuery`.
- Valor inválido cai no `except ValidationError` já existente → 422 com `{"erro": "Parametros invalidos"}`.

## T5 — Multi-seleção na interface

**Arquivos:** `static/plog.html`, `static/script.js`, `static/style.css` (se necessário)
**Depende de:** T4
**Tests:** none (sem harness JS) | **Gate:** build
**Requisitos:** PROTO-08, PROTO-09

**Done when:**
- Campo de múltipla seleção com exatamente TCP, UDP e ICMP.
- Nenhum marcado → URL sem `protocolo`.
- N marcados → N params `protocolo` em minúsculo.
- Texto de ajuda do card de filtros menciona o protocolo como opcional.

---

## Validação final

Após T5: dispatch do Verifier (autor ≠ verificador) com spec-anchored check +
discrimination sensor sobre o filtro de protocolo. Relatório em `validation.md`.
