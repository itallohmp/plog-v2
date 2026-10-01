---
name: PLog
description: Console técnico para consulta de flows de tradução NAT (CGNAT)
colors:
  fundo: "#040d1f"
  superficie: "#0a1730"
  superficie-2: "#0f1f3d"
  linha-alternada: "#0c1a35"
  input: "#06112a"
  borda: "#1c2f55"
  borda-forte: "#2a4270"
  texto: "#e6eefc"
  texto-2: "#9fb3d4"
  muted: "#7d93b8"
  apagado: "#4f6690"
  azul-marca: "#002c66"
  azul-eletrico: "#3b8cff"
  laranja-sinal: "#ff6600"
  laranja-texto: "#ff9a54"
  aberta: "#3ddc84"
  fechada: "#ff5c5c"
  fechada-texto: "#ff7a7a"
typography:
  heading:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "18px"
    fontWeight: 800
    lineHeight: 1.25
  body:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0.08em"
  data:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: "8px"
  md: "12px"
  pill: "999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "18px"
  lg: "24px"
  xl: "28px"
components:
  button-primary:
    backgroundColor: "{colors.laranja-sinal}"
    textColor: "#ffffff"
    typography: "JetBrains Mono 700 15px"
    rounded: "10px"
    height: "48px"
  button-ghost:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.texto}"
    border: "1px {colors.borda}"
    rounded: "{rounded.sm}"
    height: "38px"
  input:
    backgroundColor: "{colors.input}"
    textColor: "{colors.texto}"
    border: "1px {colors.borda}"
    focus: "borda {colors.azul-eletrico} + anel 4px rgba(59,140,255,.22)"
    rounded: "{rounded.sm}"
    height: "44px"
  badge-aberta:
    backgroundColor: "rgba(61,220,132,.12)"
    textColor: "{colors.aberta}"
    rounded: "{rounded.pill}"
  badge-fechada:
    backgroundColor: "rgba(255,92,92,.12)"
    textColor: "{colors.fechada-texto}"
    rounded: "{rounded.pill}"
---

# Design System: PLog

## 1. Overview

**Norte criativo: "O Console do NOC"**

O PLog responde, em segundos, *"qual assinante usava este IP nesta porta?"*. A interface tem cara
de ferramenta de TI: tema escuro único, grade técnica discreta no fundo, dados em monoespaçada e
um acento azul elétrico. O laranja da marca é a cor da **ação** (botão primário) e do **sinal**
(anomalia, item ativo). Tudo serve à leitura dos dados — a tabela continua sendo o herói.

O visual técnico vem da estrutura (grade, mono, bordas finas, terminal e topologia nas páginas
públicas), **não de ornamentos de texto**. Ficam proibidos colchetes decorativos (`[ SEÇÃO ]`),
prompts falsos (`~/plog $`), comentários de código como subtítulo (`// …`) e legendas do tipo
"FIG.01". Esses recursos parecem gerados, não projetados.

**Características:**
- Fundo `#040d1f` com grade de 48px; cartões `#0a1730` com borda `#1c2f55`.
- Azul elétrico (`#3b8cff`) para foco, seleção, links e realces.
- Laranja (`#ff6600`) para a ação primária e sinais de anomalia.
- Rótulos e dados em JetBrains Mono; títulos e corpo em Inter.
- Estado da sessão sempre por cor **e** rótulo.

## 2. Colors

### Base
- **Fundo** (#040d1f): plano da aplicação, com grade azul a 7% de opacidade.
- **Superfície** (#0a1730) / **Superfície 2** (#0f1f3d): cartões / cabeçalhos de tabela e realces.
- **Input** (#06112a): campos de formulário.
- **Borda** (#1c2f55): contornos, divisórias e linhas de tabela.

### Texto
- **Texto** (#e6eefc) para conteúdo; **Texto 2** (#9fb3d4) para rótulos secundários;
  **Muted** (#7d93b8) para apoio; **Apagado** (#4f6690) só para placeholders.

### Acentos
- **Azul elétrico** (#3b8cff): foco, chips selecionados, links e a página atual da paginação.
- **Laranja sinal** (#ff6600): botão primário, item ativo do menu, pico acima do limiar.

### Named Rules
**A Regra do Estado por Cor + Rótulo.** Verde (#3ddc84) e vermelho (#ff5c5c) são exclusivos do
estado da sessão (aberta/fechada) e **sempre** acompanham o texto do rótulo.

**A Regra do Laranja.** Laranja marca ação ou anomalia. No mapa de calor do ranking, laranja = no
limiar ou acima; azul = morno (3+). A linha de limiar do gráfico de picos é laranja, nunca vermelha.

## 3. Typography

- **Heading** (Inter 800, 18–24px): títulos de página e de cartão. Sem subtítulo decorativo.
- **Body** (Inter 400, 15px): textos de apoio e mensagens.
- **Label** (JetBrains Mono 700, 11px, caixa-alta, 0.08em): rótulos de campo e cabeçalhos de tabela.
- **Data** (JetBrains Mono 400, 12.5–13px): IPs, portas, timestamps, blocos, contagens.

**A Regra do Dado Monoespaçado.** Todo dado técnico é JetBrains Mono. O selo de Status é rótulo
e fica em Inter.

## 4. Elevation

Profundidade por camadas tonais (fundo → superfície → superfície 2) e bordas finas. Sombras são
escuras e difusas (`0 12px 32px rgba(0,0,0,.3)`); brilhos azuis/laranja só no terminal da home,
no modal e no botão primário.

## 5. Components

- **Botão primário:** laranja, texto branco em mono 700, 48px, raio 10px, brilho laranja suave.
- **Botão fantasma:** superfície + borda; hover com borda e fundo azul elétrico a 14%.
- **Inputs:** fundo `#06112a`, borda `#1c2f55`, raio 8px; foco com borda azul e anel de 4px.
  No login, o campo tem um `>` à esquerda que acende em azul no foco.
- **Chips (Protocolo/Estado):** pílulas de checkbox sempre visíveis; selecionado = borda azul,
  fundo azul 14% e ícone de check.
- **Cartões:** raio 12px, padding 28px, título 18px.
- **Tabela de sessões (signature):** cabeçalho sticky em mono, zebra `#0c1a35`, hover azul 7%,
  dados em mono, selo de status em pílula com dot.
- **Panorama:** total em mono grande, barra aberta × fechada, blocos de estado e lista de métricas.
- **Menu lateral:** `#06112a`, item ativo com fundo branco 10% e ponto laranja; vira drawer < 1000px.

## 6. Do's and Don'ts

### Do:
- **Do** usar a grade, a mono e as bordas finas para dar o tom técnico.
- **Do** renderizar todo dado técnico em JetBrains Mono.
- **Do** acompanhar o estado da sessão de um rótulo de texto, sempre.
- **Do** manter contraste alto: texto `#e6eefc` sobre `#0a1730`.

### Don't:
- **Don't** usar colchetes, prompts, `//` ou legendas "FIG." como enfeite de texto.
- **Don't** pôr subtítulos genéricos sob títulos; só textos com dado real (ex.: "Mostrando 100 de…").
- **Don't** usar laranja como preenchimento decorativo.
- **Don't** comunicar estado apenas por cor.
