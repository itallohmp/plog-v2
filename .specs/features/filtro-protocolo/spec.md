# Filtro por Protocolo (TCP / UDP / ICMP)

## Problem Statement

Hoje a busca de flows filtra por data, intervalo de datas, IP, porta e hora — mas não por
protocolo. O analista que investiga, por exemplo, apenas tráfego UDP precisa varrer
visualmente a coluna PROTOCOLO. Adicionar um filtro por protocolo reduz o ruído no
resultado e o volume de dados paginados.

## Goals

- [ ] Filtrar flows por um ou mais protocolos (TCP, UDP, ICMP) na API e na UI.
- [ ] Múltipla seleção: combinar protocolos numa mesma busca (ex.: TCP + UDP).
- [ ] Composição por AND com os filtros existentes (data, IP, porta, hora).

## Out of Scope

| Item | Motivo |
| ---- | ------ |
| Opção "Outros" (proto ≠ 1/6/17, ex.: GRE 47) | Decisão do usuário: filtro oferece apenas TCP/UDP/ICMP. |
| Filtrar por número de protocolo na UI (ex.: digitar `47`) | A UI expõe só os três nomes; API aceita apenas os nomes válidos. |
| Persistir o filtro escolhido entre sessões | Nenhum outro filtro persiste hoje; manteria consistência mas amplia escopo. |
| Corrigir os 7 testes 401 de `tests/test_api.py` | Dívida pré-existente, rastreada separadamente. |

---

## Assumptions & Open Questions

| Assumption / decisão | Default escolhido | Racional | Confirmado? |
| -------------------- | ----------------- | -------- | ----------- |
| Seleção múltipla de protocolos | `?protocolo=tcp&protocolo=udp` (query param repetido) | Escolha do usuário; padrão HTTP para multi-valor, suportado nativamente por `Query(None)` com `List[str]` no FastAPI | y |
| Apenas TCP/UDP/ICMP são válidos | Qualquer outro valor → erro de validação (422) | Escolha do usuário; evita filtro silenciosamente vazio por typo | y |
| Nomes aceitos sem diferenciar maiúsc./minúsc. | `TCP`, `tcp`, `Tcp` equivalentes | Reduz atrito de uso da API; a UI sempre envia minúsculo | y |
| Nenhum protocolo selecionado = todos | Ausência do parâmetro (ou lista vazia) desliga o filtro | Consistente com `ip`/`porta`, que já tratam vazio como "sem filtro" | y |
| Evento sem `proto` (ou não numérico) com filtro ativo | Excluído do resultado | Não é possível provar que casa o filtro; incluir seria falso positivo | y |
| Valores duplicados (`?protocolo=tcp&protocolo=tcp`) | Tratados como uma única seleção | Deduplicação natural via conjunto; sem efeito no resultado | y |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Filtrar flows por protocolo na API ⭐ MVP

**User Story**: Como analista de rede, quero restringir a busca de flows a um ou mais
protocolos, para investigar apenas o tráfego relevante sem varrer o resultado inteiro.

**Why P1**: É o núcleo da feature; a UI é apenas a porta de entrada para este comportamento.

**Acceptance Criteria**:

1. WHEN a consulta informa `protocolo=tcp` THEN o sistema SHALL retornar somente eventos com `proto` = 6.
2. WHEN a consulta informa `protocolo=udp` THEN o sistema SHALL retornar somente eventos com `proto` = 17.
3. WHEN a consulta informa `protocolo=icmp` THEN o sistema SHALL retornar somente eventos com `proto` = 1.
4. WHEN a consulta informa mais de um protocolo (ex.: `protocolo=tcp&protocolo=udp`) THEN o sistema SHALL retornar a união dos eventos desses protocolos (`proto` ∈ {6, 17}) e excluir os demais.
5. WHEN a consulta não informa `protocolo` (ou informa lista vazia) THEN o sistema SHALL não aplicar filtro de protocolo (retorna todos os protocolos).
6. WHEN o filtro de protocolo está ativo e um evento tem `proto` fora do conjunto selecionado (ex.: 47/GRE) THEN o sistema SHALL excluir esse evento.
7. WHEN o nome do protocolo é informado em qualquer capitalização (`TCP`, `tcp`) THEN o sistema SHALL tratá-los como equivalentes.
8. WHEN `protocolo` recebe um valor inválido (ex.: `foo`) THEN a API SHALL responder **422** com corpo `{"erro": "Parametros invalidos", ...}`.
9. WHEN o filtro de protocolo é combinado com IP, porta ou data THEN o sistema SHALL aplicar todos por conjunção (AND).

**Independent Test**: `pytest tests/test_flow_protocolo.py` verde; e `GET /api/flows?data=...&protocolo=tcp` retorna só TCP.

---

### P2: Selecionar protocolos na interface

**User Story**: Como analista, quero marcar os protocolos desejados no formulário de filtros,
para não precisar montar a URL manualmente.

**Why P2**: Depende do backend (P1); sem ele não há o que exibir.

**Acceptance Criteria**:

1. WHEN a tela de filtros é carregada THEN a UI SHALL exibir um controle de múltipla seleção com exatamente as opções TCP, UDP e ICMP.
2. WHEN nenhum protocolo está marcado THEN a busca SHALL ser enviada sem o parâmetro `protocolo` (equivale a todos).
3. WHEN N protocolos estão marcados THEN a URL da busca SHALL conter N parâmetros `protocolo`, um por protocolo marcado, em minúsculo.

**Independent Test**: marcar TCP+UDP e conferir na aba Network a URL com `protocolo=tcp&protocolo=udp`.

---

## Edge Cases

- WHEN o evento não possui a chave `proto` e o filtro está ativo THEN o sistema SHALL excluí-lo.
- WHEN o evento possui `proto` não numérico (ex.: `"abc"`) e o filtro está ativo THEN o sistema SHALL excluí-lo.
- WHEN o mesmo protocolo é informado mais de uma vez THEN o sistema SHALL tratá-lo como uma única seleção (resultado idêntico ao envio único).
- WHEN todos os três protocolos são selecionados THEN o resultado SHALL excluir eventos de outros protocolos (não equivale a "sem filtro").

---

## Requirement Traceability

| Requirement ID | Story | Fase | Status |
| -------------- | ----- | ---- | ------ |
| PROTO-01 | P1 AC1-AC3 (filtro por um protocolo) | Execute | Verified |
| PROTO-02 | P1 AC4 (união multi-protocolo) | Execute | Verified |
| PROTO-03 | P1 AC5 (ausente/vazio = sem filtro) | Execute | Verified |
| PROTO-04 | P1 AC6 + edges (proto fora do conjunto / ausente / inválido excluído) | Execute | Verified |
| PROTO-05 | P1 AC7 (case-insensitive) | Execute | Verified |
| PROTO-06 | P1 AC8 (valor inválido → 422) | Execute | Verified |
| PROTO-07 | P1 AC9 (AND com demais filtros) | Execute | Verified |
| PROTO-08 | P2 AC1 (controle multi-seleção na UI) | Execute | Verified |
| PROTO-09 | P2 AC2-AC3 (montagem da URL) | Execute | Verified |

**Coverage:** 9 requisitos, todos mapeados para tasks (ver `tasks.md`).

---

## Success Criteria

- [ ] Buscar com TCP marcado retorna apenas linhas com PROTOCOLO = TCP na tabela.
- [ ] Marcar TCP + UDP retorna as duas famílias e nenhuma outra.
- [ ] Suíte de testes do filtro verde; suíte pré-existente de flows sem regressão.
- [ ] Verifier confirma que os testes matam mutações do filtro de protocolo.
