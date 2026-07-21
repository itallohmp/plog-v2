# Sintaxe de filtro do nfdump — a CONFIRMAR no servidor real

⚠️ **Pendência bloqueante (E6).** A expressão de filtro usada pelo pushdown (E7) depende da
versão do `nfdump` instalada no servidor de flows. O código monta a expressão por allowlist,
mas os **keywords** abaixo precisam ser confirmados contra o binário real antes de confiar na
resolução de sessões abertas. Enquanto não confirmados, o lookahead fica desligável por
`PLOG_NAT_LOOKAHEAD=0` e a feature degrada para "aberta até <fim da janela>".

## O que precisa ser verificado

Rodar no servidor, contra um dia com eventos NAT conhecidos, e confirmar que devolvem o delete
esperado:

```bash
# IP interno de origem
nfdump -R <dir> 'src ip 172.16.10.17' -o json | head

# IP publico traduzido (o keyword varia: 'nat ip', 'src nat ip', 'xlate src ip'...)
nfdump -R <dir> 'src nat ip 177.137.21.38' -o json | head

# Bloco de portas (keyword varia: 'pblock', 'nat port block'...)
nfdump -R <dir> 'pblock start 4096' -o json | head

# Evento de delete (pode ser por 'nat event' ou nao existir como filtro)
nfdump -R <dir> 'nat event delete' -o json | head
```

## Chave da consulta (o que a expressão precisa expressar)

Para cada sessão pendente, a pergunta é: *"existe um delete deste bloco depois da abertura?"*

Campos da chave (todos já tipados no código — IPs validados, inteiros de bloco):
- `src4_addr`  → filtro por IP interno de origem
- `src4_xlt_ip` → filtro por IP público traduzido
- `pblock_start` → filtro por início do bloco
- (opcional) `ip4_router` — se a expressão suportar, restringe ainda mais

## Registro da versão

| Item | Valor confirmado | Data |
| ---- | ---------------- | ---- |
| Versão do nfdump (`nfdump -V`) | _a preencher_ | |
| Keyword do IP público traduzido | _a preencher_ | |
| Keyword do bloco de portas | _a preencher_ | |
| Keyword/existência do filtro de evento | _a preencher_ | |
