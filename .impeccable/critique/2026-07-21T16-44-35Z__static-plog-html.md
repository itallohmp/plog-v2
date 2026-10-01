---
target: static/plog.html
total_score: 30
p0_count: 1
p1_count: 1
timestamp: 2026-07-21T16-44-35Z
slug: static-plog-html
---
# Critique — plog.html (2ª rodada) — 30/40, Sólido (B)
Dual-agent. Detector: 69 achados (1 warning Inter, 68 advisory drift de token). backdrop-filter restante só em login/index; plog limpo de glass.
Heurísticas: Status 3, MundoReal 3, Controle 3, Consistência 3, PrevErro 3, Reconhecer 4, Flex 2, Minimalista 4, DiagErro 3, Ajuda 2.
P0: "nenhum marcado = todos" invisível em protocolo/estado (filtro silenciosamente desligado; viola Estado-sempre-explícito).
P1: tabela sem ordenação + consulta sem estado na URL (não bookmarkável p/ ofício).
P2: estados indefinida/parcial só em title de hover (sem legenda); Estado(filtro) vs Status(coluna); th sem scope.
P3: seletor button{} global (gradiente/hover-laranja) + CSS morto (.status_badge, .filtros grid em flex).
Fortes: adesão ao DESIGN.md; export auditável; feedback (aria-live+dot+AbortController) + sticky correto.
Provocativas: só Data obrigatória (busca só-data = 10k linhas); onde os dashboards futuros vão morar.
