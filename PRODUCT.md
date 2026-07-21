# Product

## Register

product

## Platform

web

## Users

Analistas e equipe de suporte (N1/NOC) de um provedor de internet, operando muitas vezes em
plantão noturno. Chegam ao PLog com uma pergunta específica e urgente — normalmente disparada
por ordem judicial, denúncia de abuso ou troubleshooting: *"qual assinante estava usando este
IP público nesta porta, neste instante?"*. Com CGNAT, um IP público é compartilhado por
centenas de assinantes, e a resposta só existe nos logs de tradução NAT. Antes do PLog, só uma
pessoa conseguia extrair isso via SSH + `nfdump`; o objetivo é que qualquer pessoa do NOC faça
em segundos.

## Product Purpose

Tornar consultável, por uma interface web, o log de tradução NAT (nfcapd/NetFlow) de um
provedor: buscar por data/IP/porta/protocolo/estado, correlacionar os eventos `create`/`delete`
em sessões com estado (aberta/fechada) e apresentar o resultado de forma legível e paginada.

Sucesso hoje = a informação certa, rápida e sem ambiguidade, já que a saída pode virar resposta
formal a um ofício. Direção futura = evoluir de ferramenta interna para **produto comercial**
vendável a outros provedores, incorporando dashboards. As decisões de design devem manter o
sistema apresentável e consistente o suficiente para demonstração/venda, sem sacrificar a
densidade que o plantão exige.

## Brand Personality

Institucional, sóbrio e corporativo. Voz técnica e direta, sem marketing nem firula. A
interface deve transmitir precisão e confiabilidade — cara de sistema oficial do provedor, não
de app de consumo. Calma e ordem acima de energia visual.

## Anti-references

- **Não é um blog / peça editorial**: sem tipografia de display, sem hero, sem conteúdo de
  leitura longa. É uma ferramenta de trabalho.
- **Não é SaaS genérico**: sem gradientes decorativos, sem "big number" de vaidade, sem grades
  de cards iguais repetidos.
- **Não é terminal cru**: apesar de técnico, não deve parecer um dump sem hierarquia; precisa
  de organização e legibilidade.
- O produto crescerá para **dashboards** — o layout deve comportar isso sem virar um painel
  sobrecarregado de widgets competindo por atenção.

## Design Principles

- **A tabela é o produto.** O resultado da busca é o herói da tela; filtros, cabeçalho e chrome
  existem para servir a leitura dos dados, não para competir com eles.
- **Correto acima de bonito.** A saída pode virar prova. Nunca exibir um estado
  plausível-porém-errado (ex.: filtro silenciosamente desligado, sessão "aberta" que já fechou).
  Ambiguidade é pior que um erro visível.
- **Estado sempre explícito.** Aberta/fechada/indefinida devem ser legíveis por rótulo, não só
  por cor — protege daltônicos e mantém a leitura inequívoca sob qualquer contraste.
- **Densidade a serviço do plantão.** Poucos cliques, alto contraste, varredura rápida; a tela
  precisa render bem em monitores variados e sob a luz irregular de um plantão noturno.
- **Pronto para virar produto.** Consistência de componentes e acabamento suficientes para
  demonstrar/vender; nada de solução descartável que envergonhe numa demo.

## Accessibility & Inclusion

- **Alto contraste** como requisito explícito: corpo de texto ≥ 4.5:1, selos/labels legíveis em
  monitores diversos e sob luz variável do plantão.
- **Não depender só de cor** para o estado da sessão (aberta/fechada) — sempre acompanhar de
  texto/rótulo (já adotado nos selos de status).
- Alvo prático: **WCAG 2.1 AA** para contraste e para foco de teclado no formulário de filtros e
  na paginação, à medida que a ferramenta caminha para produto.
