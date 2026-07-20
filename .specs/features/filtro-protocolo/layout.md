# Revisão de layout — barra de filtros

Avaliação isolada em dois trilhos (avaliação visual e scan mecânico rodaram sem ver
o resultado um do outro, para o detector não ancorar o julgamento visual).

## Resultado dos dois trilhos

| Achado | Scan mecânico | Avaliação visual |
| ------ | ------------- | ---------------- |
| Grid monótono `repeat(4, minmax(150px,1fr))` | não detecta | **P0** — "Hora de" (2 chars) com a mesma largura de "IP" (15 chars); desperdício de até 6× |
| Botão na coluna errada | não detecta | **P0** — Protocolo ocupava a coluna `auto` destinada ao botão, deixando um vão à direita da ação primária |
| `select multiple` quebra a linha de base | não detecta | **P1** — ~92px de altura contra ~66px dos vizinhos |
| Espaçamento sem escala de tokens | 19 valores distintos; órfãos `13px`, `7px` | mesmo achado (gap único de 14px nos dois eixos → zero agrupamento) |
| `z-index: 1000` em `#rodape` | valor mágico, 100× acima do próximo nível | não detecta |

O detector com `--scope layout` retornou **zero achados**: um grid uniforme passa em
qualquer verificação mecânica. Isso é exatamente o que a avaliação visual existe para pegar.

## O que foi corrigido

1. **`.filtros` passou de Grid para Flex.** A barra de filtros é 1D (uma fila de controles
   que reflui), não 2D. Flex com `flex-wrap` dá largura por conteúdo e quebra natural, sem
   depender de breakpoints para recolocar itens.
2. **Larguras proporcionais ao conteúdo**, via modificadores: `--data` 152px, `--xs` 88px
   (horas), `--sm` 112px (porta, linhas), `--grow` (IP, único fluido). Todos com
   `flex-shrink: 0` — quando falta espaço a barra quebra a linha em vez de espremer campo.
3. **Protocolo virou grupo de checkboxes** com `min-height: 44px`, restaurando a linha de
   base horizontal da barra. Texto de ajuda "Nenhum = todos" removido: com os três estados
   visíveis, "nenhum marcado" é auto-evidente.
4. **Ordem reagrupada por significado**: quando (datas, horas) → o quê (IP, porta,
   protocolo) → exibição (linhas) → ação. Corrige também o pareamento em 2 colunas, onde
   "Hora de" e "Hora até" caíam em linhas diferentes.
5. **Botão ancorado à direita** (`margin-left: auto`), fechando a barra em vez de flutuar
   no meio.
6. **`row-gap` (20px) maior que `column-gap` (12px)**: quando a barra quebra, a separação
   entre linhas fica legível sem afastar campos vizinhos.
7. **Campo obrigatório marcado** — "Data de" é o único `required` e nada o indicava.

## Medições (sandbox de largura controlada)

| Container | Linhas | Altura do form | IP | Overflow horizontal |
| --------- | ------ | -------------- | -- | ------------------- |
| 1340px (desktop) | 1 | **66px** (antes ~250px em 2 linhas) | 218px | não |
| 1100px | 2 | 152px | 239px | não |
| 860px | 3 | 302px | 100% | não |
| 420px (mobile) | 5 | 474px | 100% | não |

Todos os controles medem **44px de altura** em todas as larguras (linha de base única).
No desktop a barra recuperou ~185px de altura, devolvidos à tabela de resultados — que é o
conteúdo real da tela.

## Fora de escopo (deliberado)

- **Tokenizar a escala de espaçamento.** O CSS tem 19 valores distintos sem tokens
  `--space-*`. É refatoração do site inteiro, com risco próprio; não cabia numa correção
  da barra de filtros. Mantive os valores já usados na área tocada para não criar uma
  terceira escala concorrente.
- **`z-index: 1000` do `#rodape`.** Vale revisar se o rodapé fixo deve mesmo vencer
  qualquer overlay futuro, mas nenhum modal existe hoje para colidir.
