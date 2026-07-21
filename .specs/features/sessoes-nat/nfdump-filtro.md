# Sintaxe de filtro do nfdump — CONFIRMADA no servidor real

✅ **Verificado em 2026-07-21** contra o servidor de flows (`10.10.10.53`, rota `rj02bd01`),
via VPN, com dados de produção reais. A pendência do E6 está resolvida.

## Ambiente confirmado

| Item | Valor |
| ---- | ----- |
| Versão do nfdump | **1.7.8** (`nfdump: Version: 1.7.8-e198c8b options: lz4`) |
| Estrutura de diretórios | `/<base>/<YYYY-MM-DD>/<HH>/nfcapd*` (dia → hora → arquivos) |
| Valores de `nat_event` | exatamente `"NAT translation create"` e `"NAT translation delete"` |
| Campos por evento | `nat_event`, `src4_addr`, `src4_xlt_ip`, `pblock_start`, `pblock_size`, `pblock_end`(=0), `ip4_router`, `proto`, `t_event`, `type` |

## Filtros testados (com valores reais)

| Expressão | Resultado |
| --------- | --------- |
| `src ip <ip>` | ✅ funciona |
| `src nat ip <ip>` | ✅ funciona (IP público traduzido) |
| `nat event delete` | ✅ funciona |
| `nat event create` | ❌ inválido — o keyword é `ADD`, não `create` |
| `nat src ip` / `xlate src ip` | ❌ syntax error |
| **`pblock start <n>`** | ❌ **syntax error — nfdump 1.7.8 não tem filtro de bloco** |

## Decisão de implementação

`construir_filtro_nfdump` gera `(src ip <origem> and src nat ip <ip_nat>)` — **sem** cláusula
de bloco, porque o `pblock` não é filtrável nesta versão. O bloco de portas exato é casado
**em Python** (`FlowService._fechar_com_extras`, via `chave_sessao`), então a resolução
continua precisa. A expressão real gerada foi validada no servidor:

```
(src ip 100.64.18.249 and src nat ip 177.137.21.8)  -> status 0, retornou create + delete
```

Não usamos filtro por `nat event` na expressão (a classe é decidida em Python), o que também
evita a divergência do keyword `create`/`ADD`.

## Validação end-to-end

`FlowService.buscar_flows` sobre o assinante real `100.64.18.249` (2026-07-21, hora 00)
retornou **6 sessões fechadas** com durações reais (~30s). O bloco `20992-21503` apareceu
3 vezes (realocado ao longo da hora), cada ocorrência pareada como sessão independente —
confirmando o pareamento cronológico por pilha sobre dados de produção.
