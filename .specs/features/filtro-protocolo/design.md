# Design — Filtro por Protocolo

## Princípio

O filtro de protocolo é um **filtro de evento**, exatamente como `ip`, `porta` e `data`.
Portanto ele entra no mesmo ponto de decisão já existente — `pcap_event_matches()` — e
não cria um caminho novo. Nenhuma mudança na camada de repositório (SSH/nfdump): a
filtragem continua acontecendo depois do fetch, em memória.

## Fluxo

```
GET /api/flows?...&protocolo=tcp&protocolo=udp
      │
      ▼
routes/flows.py      protocolo: Optional[List[str]] = Query(None)
      │
      ▼
schemas/flow.py      FlowQuery.protocolo: Optional[List[str]]
      │              ├─ valida nomes contra PROTOCOLO_NUMEROS (422 se inválido)
      │              ├─ normaliza p/ minúsculo, deduplica
      │              └─ protocolos_numericos() -> Optional[Set[int]]
      ▼
services/flow_service.py   passa o conjunto de números ao matcher
      │
      ▼
parsers/pcap_parser.py     pcap_event_matches(..., protocolos: Optional[Set[int]])
                           evento entra se _as_int(event["proto"]) ∈ protocolos
```

## Decisões

| # | Decisão | Racional |
| - | ------- | -------- |
| D1 | O filtro vive em `pcap_event_matches`, junto de ip/porta/data | Um único ponto de verdade para "este evento casa os filtros?"; conjunção (AND) sai de graça (PROTO-07) |
| D2 | A conversão nome → número usa `PROTOCOLO_NUMEROS`, derivado de `PROTOCOLOS` já existente | Evita uma segunda tabela que possa divergir da usada na exibição (`_protocol_name`) |
| D3 | O matcher recebe **números** (`Set[int]`), não nomes | O evento traz `proto` numérico; converter uma vez no schema é mais barato e evita comparar strings por evento |
| D4 | A validação de nomes fica no schema (`FlowQuery`), não no matcher | Erro de entrada deve virar 422 na borda, como já ocorre com `ip` inválido; o matcher só executa a regra |
| D5 | `None` e lista vazia são equivalentes (sem filtro) | Consistente com `_validar_ip`, que já mapeia `""` → `None` (PROTO-03) |
| D6 | Evento sem `proto` ou com `proto` não numérico é **excluído** quando o filtro está ativo | `_as_int` devolve `None`, que nunca pertence ao conjunto; falha fechada evita falso positivo (PROTO-04) |
| D7 | UI usa `<select multiple>` com as três opções | Multi-seleção sem dependência nova; reaproveita o padrão de `<select>` do campo "Linhas" |

## Componentes tocados

| Arquivo | Mudança |
| ------- | ------- |
| `app/parsers/pcap_parser.py` | `PROTOCOLO_NUMEROS` (mapa reverso) + parâmetro `protocolos` em `pcap_event_matches` |
| `app/schemas/flow.py` | Campo `protocolo`, validador e `protocolos_numericos()` |
| `app/services/flow_service.py` | Repassa o conjunto ao matcher |
| `app/api/routes/flows.py` | Query param `protocolo` (multi-valor) |
| `static/plog.html` | Campo de múltipla seleção |
| `static/script.js` | Leitura da seleção e montagem dos params na URL |

## Riscos

- **Regressão nos filtros existentes:** mitigado por assinatura com default `None` em
  `pcap_event_matches` (chamadas atuais seguem válidas) e pela suíte existente de
  `test_pcap_parser` / `test_flow_interval`.
- **Divergência exibição × filtro:** mitigado por D2 (fonte única `PROTOCOLOS`).
