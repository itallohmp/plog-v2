---
name: PLog
description: Painel institucional para consulta de flows de tradução NAT (CGNAT)
colors:
  azul-institucional: "#002c66"
  azul-institucional-light: "#06458f"
  laranja-sinal: "#ff6600"
  superficie: "#ffffff"
  fundo: "#f3f6fb"
  tinta: "#172033"
  neutro-texto: "#344054"
  neutro-muted: "#6b7280"
  borda: "#d9e2ef"
  aberta-fundo: "#e7f8ee"
  aberta-tinta: "#14703d"
  fechada-fundo: "#fde8e8"
  fechada-tinta: "#a11717"
  indefinida-fundo: "#edf0f5"
  indefinida-tinta: "#4b5563"
typography:
  heading:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "18px"
    fontWeight: 800
    lineHeight: 1.25
    letterSpacing: "normal"
  body:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0.06em"
  data:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
rounded:
  md: "12px"
  lg: "18px"
  pill: "999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "14px"
  lg: "24px"
  xl: "28px"
components:
  button-primary:
    backgroundColor: "{colors.azul-institucional}"
    textColor: "{colors.superficie}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "8px 20px"
    height: "44px"
  input:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
    height: "44px"
  badge-aberta:
    backgroundColor: "{colors.aberta-fundo}"
    textColor: "{colors.aberta-tinta}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  badge-fechada:
    backgroundColor: "{colors.fechada-fundo}"
    textColor: "{colors.fechada-tinta}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
---

# Design System: PLog

## 1. Overview

**Creative North Star: "O Painel Institucional"**

O PLog é o sistema oficial de um provedor para responder, em segundos, *"qual assinante usava
este IP nesta porta?"*. A interface deve transmitir a autoridade de um sistema corporativo — não
a leveza de um app de consumo. Azul-marinho institucional domina a moldura (cabeçalho, ação
primária, títulos); o laranja da marca aparece como **sinal**, nunca como decoração. O resultado
é sóbrio, ordenado e confiável: a tela de quem trabalha, não a vitrine de quem vende — embora
precise ser apresentável o bastante para uma demonstração comercial.

A densidade serve o plantão: cartões brancos limpos sobre um fundo azul-acinzentado, dados em
fonte monoespaçada para alinhar IPs e portas, e uma tabela que é o herói da tela. Tudo o mais —
filtros, cabeçalho, paginação — existe para servir a leitura desses dados. O sistema
explicitamente **rejeita** cara de blog (sem tipografia de display, sem hero), SaaS genérico
(sem gradientes decorativos, sem "big number" de vaidade, sem grades de cards repetidos) e dump
de terminal cru (apesar de técnico, tem hierarquia e respiro).

**Key Characteristics:**
- Azul institucional como moldura; laranja como sinal escasso.
- Dados sempre em monoespaçada; rótulos em Inter caixa-alta, curta e espaçada.
- A tabela é o herói; o chrome recua.
- Estado (aberta/fechada) legível por rótulo **e** cor, nunca só cor.
- Cartões brancos, cantos suaves, sombras difusas e discretas.

## 2. Colors

Uma base azul-institucional sóbria, neutros frios para estrutura, e um laranja de sinal usado com
extrema parcimônia; verde e vermelho reservados exclusivamente para o estado da sessão.

### Primary
- **Azul Institucional** (#002c66): a cor da autoridade. Cabeçalho, ação primária ("Buscar Logs"),
  títulos de seção, foco de teclado. É a moldura do sistema.
- **Azul Institucional Claro** (#06458f): segundo tom do azul, usado apenas no gradiente do botão
  primário (135°) e em realces de foco. Nunca sozinho como cor de texto.

### Secondary
- **Laranja Sinal** (#ff6600): a cor de ênfase da marca. Aparece como sinal — marcador de campo
  obrigatório, realce na borda esquerda da linha em hover, glow decorativo sutil. Uso ≤ 5% da tela.

### Neutral
- **Superfície** (#ffffff): fundo dos cartões e das linhas de dados.
- **Fundo** (#f3f6fb): plano de fundo azul-acinzentado da aplicação; separa os cartões.
- **Tinta** (#172033): corpo de texto principal (contraste ~13:1 sobre branco).
- **Neutro Texto** (#344054): rótulos de formulário e cabeçalhos de tabela.
- **Neutro Muted** (#6b7280): texto de apoio; usar com cautela — nunca para dado crítico.
- **Borda** (#d9e2ef): contornos de inputs, divisórias de tabela, molduras de cartão.

### Named Rules
**A Regra do Sinal.** O laranja (#ff6600) é sinal, não enfeite. Ele marca o que exige atenção
(campo obrigatório, estado, foco) e ocupa ≤ 5% de qualquer tela. Se o laranja está "preenchendo
espaço", está errado.

**A Regra do Estado por Cor + Rótulo.** Verde (#14703d) e vermelho (#a11717) são exclusivos do
estado da sessão (aberta/fechada) e **sempre** acompanham um rótulo de texto. Nunca comunicar
estado só por cor — daltonismo e monitores de plantão exigem o rótulo.

## 3. Typography

**Display/Heading Font:** Inter (com system-ui, -apple-system, sans-serif)
**Body Font:** Inter (mesma família, pesos variados)
**Label/Mono Font:** JetBrains Mono (com ui-monospace, monospace) — exclusiva para dados

**Character:** Uma única família humanista (Inter) carrega títulos, rótulos e corpo; a monoespaçada
(JetBrains Mono) entra só nos dados. O contraste é de função, não de família — sóbrio e legível,
sem pares tipográficos decorativos.

### Hierarchy
- **Heading** (800, 18px, 1.25): títulos de seção ("Filtros", "Resultados"). Curto e firme.
- **Body** (400, 15px, 1.5): texto de apoio, valores de input, mensagens.
- **Label** (700, 12px, caixa-alta, letter-spacing 0.06em): rótulos de campo e cabeçalhos de
  tabela. É o "carimbo" institucional da interface.
- **Data** (400, 13px, JetBrains Mono): toda célula de dado da tabela — IPs, portas, timestamps,
  blocos. Alinhamento monoespaçado é o que torna a varredura possível.

### Named Rules
**A Regra do Dado Monoespaçado.** Todo dado técnico (IP, porta, bloco, timestamp) é renderizado em
JetBrains Mono. O selo de Status é a única exceção na tabela: é rótulo, fica em Inter.

## 4. Elevation

Sistema quase-plano com sombras difusas e discretas. Profundidade vem da estratificação tonal
(cartão branco sobre fundo azul-acinzentado) mais uma sombra grande e suave que faz o cartão
"flutuar" sem drama. Nada de sombras duras ou bordas grossas.

### Shadow Vocabulary
- **Cartão** (`box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08)`): elevação principal dos cartões
  (filtros, resultados). Grande e translúcida.
- **Suave** (`box-shadow: 0 4px 24px rgba(0, 44, 102, 0.06)`): reforço curto na cor da marca,
  usado junto da sombra de cartão.
- **Glow** (`box-shadow: 0 0 60px rgba(255, 102, 0, 0.08)`): halo laranja decorativo raríssimo;
  atmosfera, nunca hierarquia.
- **Foco** (`box-shadow: 0 0 0 4px rgba(0, 44, 102, 0.1)`): anel de foco azul em inputs e selects.

### Named Rules
**A Regra Plana em Repouso.** Superfícies são planas por padrão; a única sombra permanente é a do
cartão. Qualquer sombra adicional é resposta a estado (foco, hover), não decoração.

## 5. Components

### Buttons
- **Shape:** cantos suaves (12px, `--radius-md`), altura mínima 44px.
- **Primary:** gradiente azul 135° (#002c66 → #06458f), texto branco, `padding: 8px 20px`, peso
  800. É a única superfície com gradiente no sistema — reservada à ação.
- **Hover / Focus:** micro-elevação por `transform` + sombra em 160ms ease; sem bounce.

### Chips (checkbox de filtro)
- **Style:** rótulo inline com checkbox nativo, `accent-color: #002c66`, texto 14px em Inter. Sem
  fundo nem borda — o próprio checkbox é o controle. Usados para Protocolo (TCP/UDP/ICMP) e Estado
  (Aberta/Fechada), agrupados lado a lado.
- **State:** marcado/desmarcado via checkbox nativo; foco com anel azul (`outline`).

### Cards / Containers
- **Corner Style:** cantos generosos (18px, `--radius-lg`).
- **Background:** superfície branca (#ffffff), às vezes translúcida (rgba branco .88) sobre o fundo.
- **Shadow Strategy:** sombra de Cartão + Suave (ver Elevation).
- **Border:** 1px sólida #d9e2ef quando precisa de contorno.
- **Internal Padding:** 22–30px.

### Inputs / Fields
- **Style:** fundo branco, borda 1px #d9e2ef, raio 12px, altura 44px, texto 15px.
- **Focus:** borda azul-clara + anel `0 0 0 4px rgba(0,44,102,0.1)`.
- **Larguras por conteúdo:** campos dimensionados pelo que recebem — horas estreitas (88px), datas
  médias (152px), IP fluido. Nunca todos com a mesma largura.

### Tabela de Sessões (signature)
- **Cabeçalho:** sticky, fundo #f0f4fa, rótulos 11px caixa-alta espaçada, cor #344054.
- **Linhas:** zebra sutil (par #fbfdff), hover #fff7ed com faixa laranja de 3px à esquerda no hover.
- **Dados:** JetBrains Mono 13px, cor #1e293b, exceto a 1ª coluna (Status).
- **Selo de Status:** pílula (999px) com dot; verde `aberta`, vermelho `fechada`, cinza
  `indefinida`; borda tracejada quando `parcial`. É o único elemento colorido por linha.

## 6. Do's and Don'ts

### Do:
- **Do** usar azul institucional (#002c66) para a moldura (cabeçalho, ação primária, títulos, foco).
- **Do** renderizar todo dado técnico em JetBrains Mono para alinhar IPs, portas e timestamps.
- **Do** acompanhar o estado da sessão de um rótulo de texto, sempre — verde/vermelho nunca sozinhos.
- **Do** manter contraste alto (corpo ≥ 4.5:1); tinta #172033 sobre branco é o padrão.
- **Do** dimensionar campos de filtro pela largura do conteúdo, não todos iguais.
- **Do** deixar a tabela ser o herói; o chrome recua.

### Don't:
- **Don't** parecer um **blog** ou peça editorial — sem fonte de display, sem hero, sem leitura longa.
- **Don't** cair em **SaaS genérico** — sem gradientes decorativos, sem "big number" de vaidade, sem
  grades de cards iguais repetidos.
- **Don't** virar **terminal cru** — dado técnico não é desculpa para ausência de hierarquia.
- **Don't** usar o laranja (#ff6600) como preenchimento; ele é sinal, ≤ 5% da tela.
- **Don't** usar `border-left`/`border-right` colorida > 1px como faixa decorativa em cards ou linhas.
- **Don't** aplicar gradiente em nada além do botão primário.
- **Don't** comunicar estado apenas por cor.
