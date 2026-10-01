---
target: static/plog.html
total_score: 25
p0_count: 0
p1_count: 2
timestamp: 2026-07-21T15-37-04Z
slug: static-plog-html
---
# Critique — plog.html (25/40, Aceitável)
Dual-agent. Detector: 70 achados (1 warning Inter, 69 advisory drift — maioria tokens semânticos não capturados no DESIGN.md).
Heurísticas: Status 2, MundoReal 3, Controle 3, Consistência 2, PrevErro 3, Reconhecer 3, Flex 2, Minimalista 2, DiagErro 3, Ajuda 2.
P1: feedback de estado enfraquecido (setStatus no-op após remoção do selo); contraste 2.9:1 (eyebrow/asterisco laranja-texto).
P2: hero contradiz "sem hero"; faltam export auditável/sort/atalhos.
P3: chrome decorativo (grade de pontos, duplo glow, glass, dot pulsante).
Verificar: sticky header inerte (.table_wrap sem max-height).
Fortes: session_badge; larguras proporcionais; robustez async (AbortController, escapeHtml).
