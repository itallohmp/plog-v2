# PLog

Ferramenta web para consultar **flows de tradução NAT (CGNAT)** de um provedor de forma
estruturada, sem depender de SSH + `nfdump` na linha de comando. O analista busca pela
interface; a API conecta por SSH ao servidor de flows, roda o `nfdump` sobre os arquivos
`nfcapd` da data, valida a saída JSON com Pydantic e exibe o resultado.

O problema que resolve: com CGNAT, um IP público é compartilhado por centenas de assinantes.
Responder *"qual assinante usava este IP nesta porta, neste instante?"* (ordem judicial,
resposta a abuso, troubleshooting) exigia varredura manual dos logs. O PLog transforma isso
numa busca de segundos, acessível a qualquer pessoa do NOC.

## Principais recursos

- **Busca de flows** por data, **intervalo de datas** (até 31 dias), IP, porta e faixa de horas.
- **Filtro por protocolo** (TCP / UDP / ICMP, múltipla seleção).
- **Sessões NAT correlacionadas**: cada par `create` + `delete` da mesma tradução vira **uma
  linha** com estado **aberta** (verde) / **fechada** (vermelho) / indefinida, com abertura,
  fechamento e duração.
- **Filtro por estado** da sessão (aberta / fechada).
- **Resolução de sessões abertas** além da janela consultada, via consulta `nfdump` filtrada
  por chave (para alocações longas que fecham depois do período buscado).
- **Autenticação JWT** (access + refresh) com senhas em Argon2; usuários em SQLite.
- Paginação, tratamento de erros semântico e frontend estático servido pela própria API.

## Arquitetura

Camadas com responsabilidade única — `routes → services → repositories → parsers`:

| Camada | Papel |
| ------ | ----- |
| `app/api/routes/` | Endpoints FastAPI (`/flows`, `/auth/*`, `/health`), validação de entrada |
| `app/services/` | Regra de negócio: correlação de sessões, filtros, paginação |
| `app/repositories/` | Único lugar que sabe de SSH/`nfdump` (via Paramiko); isola o acesso |
| `app/parsers/` | Interpretação do JSON cru do `nfdump` e correlação de eventos NAT |
| `app/schemas/` | Modelos Pydantic (validação de consulta e resposta) |
| `app/core/` | Config por ambiente e segurança (JWT, hashing) |
| `app/database/`, `app/models/` | SQLAlchemy + SQLite (apenas usuários) |

O isolamento do SSH no `FlowRepository` deixa toda a lógica testável com mocks, sem rede — foi
o que permitiu adicionar filtros e a correlação de sessões sem tocar na camada de transporte.

### Sessões NAT (create/delete)

O `nfdump` emite dois eventos por tradução: `NAT translation create` e `... delete`. O
`app/parsers/nat_session.py` os correlaciona por uma **chave**
`(roteador, origem, ip_nat, pblock_start, pblock_size)`, pareando cronologicamente com uma
**pilha por chave**: cada `delete` fecha o `create` mais recente ainda aberto. Isso evita
atribuir tráfego ao assinante errado quando um bloco de portas é realocado.

Sessões que ficam abertas na janela são verificadas adiante (dia a dia, filtrado por chave) até
`PLOG_NAT_LOOKAHEAD_MAX_DIAS`. O lookahead é desligável e nunca derruba a consulta principal.

## Configuração (variáveis de ambiente)

Nenhuma credencial fica no código. A aplicação **não sobe** sem `PLOG_SECRET_KEY` e
`PLOG_ACCESS_TOKEN_EXPIRE_MINUTES`.

**Autenticação / segurança**
- `PLOG_SECRET_KEY` (obrigatória) — segredo de assinatura do JWT
- `PLOG_ALGORITHM` (padrão `HS256`)
- `PLOG_ACCESS_TOKEN_EXPIRE_MINUTES` (obrigatória)

**Servidor de flows (SSH + nfdump)**
- `PLOG_FLOW_SSH_HOST`, `PLOG_FLOW_SSH_PORT`, `PLOG_FLOW_SSH_USER`
- `PLOG_FLOW_SSH_KEY_PATH` (recomendado) **ou** `PLOG_FLOW_SSH_PASSWORD`
- `PLOG_FLOW_SSH_KNOWN_HOSTS` (recomendado — valida o host, evita `AutoAddPolicy`)
- `PLOG_FLOW_REMOTE_DIR`, `PLOG_FLOW_DAY_DIR_FORMAT` (padrão `%Y-%m-%d`)
- `PLOG_NFDUMP_BIN` (padrão `nfdump`), `PLOG_NFDUMP_TIMEOUT`

**Lookahead de sessões abertas**
- `PLOG_NAT_LOOKAHEAD` (`1`/`0`, padrão ligado)
- `PLOG_NAT_LOOKAHEAD_MAX_DIAS` (padrão `3`) — teto de dias verificados adiante
- `PLOG_NAT_LOOKAHEAD_MAX_CHAVES` (padrão `200`) — teto de chaves por consulta

**Modo local (dev, sem VPN)**
- `PLOG_FLOW_LOCAL_PATH` — arquivo `.json`/`nfcapd` ou pasta; quando definido, lê daqui em vez
  de conectar por SSH
- `PLOG_NFDUMP_LOCAL_BIN`, `PLOG_FLOW_NFCAPD_PREFIX`

**API**
- `PLOG_API_PREFIX` (padrão `/api`), `PLOG_ALLOWED_ORIGINS`

## Como rodar

```bash
poetry install
# defina as variáveis de ambiente (ver acima), ex.: em um arquivo .env
poetry run alembic upgrade head          # cria a tabela de usuários
poetry run python create_user.py         # cria o primeiro usuário admin
poetry run uvicorn main:app --host 0.0.0.0 --port 8000
```

A interface fica em `http://<host>:8000/`. Docs da API em `/api/docs`.

> **Deploy:** todo deploy que altera código Python **exige reiniciar o processo**
> (`systemctl restart plog-v2.service`). O frontend é servido do disco a cada request, mas as
> rotas ficam em memória desde o boot — sem restart, JS novo + rota antiga ignoram parâmetros
> novos em silêncio.

## Testes

A suíte roda no virtualenv do Poetry (que contém as dependências do app):

```bash
poetry run pytest
```

## Endpoints

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| `GET`  | `/api/health` | Verificação de saúde |
| `GET`  | `/api/flows` | Consulta de flows/sessões (data, intervalo, IP, porta, protocolo, estado, horas, paginação) |
| `POST` | `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout` | Autenticação |
| `GET`  | `/api/auth/me`, `/api/auth/usuarios` | Perfil e listagem (admin) |
| `POST`/`PATCH`/`DELETE` | `/api/auth/usuarios...` | Gestão de usuários (admin) |

Erros: **404** (sem dados na data), **502** (falha SSH/`nfdump`), **422** (parâmetros inválidos),
**401/403** (autenticação/autorização).

## Convenção de commits

Commits seguem **[Conventional Commits](https://www.conventionalcommits.org/)** com o assunto
**em inglês**: `<type>(<scope>): <description>`.

Um hook de `commit-msg` versionado (`.githooks/`) valida isso. Ative uma vez por clone:

```bash
git config core.hooksPath .githooks
```

Ele rejeita commits fora do formato ou com o assunto em português (acentos ou palavras comuns).
Exemplo válido: `feat(flows): add session state filter`.

## Estrutura do projeto

```
.
├── main.py                     # app FastAPI, CORS, monta rotas e /static
├── app/
│   ├── api/routes/             # flows, auth, system
│   ├── services/               # flow_service (correlação, filtros, paginação)
│   ├── repositories/           # flow_repository (SSH + nfdump)
│   ├── parsers/                # pcap_parser, nat_session, flow_parser
│   ├── schemas/                # flow, auth (Pydantic)
│   ├── core/                   # config, security (JWT)
│   ├── database/ , models/     # SQLAlchemy + SQLite (usuários)
├── alembic/                    # migrations
├── static/                     # frontend (HTML/CSS/JS)
├── tests/                      # pytest (unit + integração)
├── .githooks/commit-msg        # valida Conventional Commits em inglês
└── README.md
```

## Tecnologias

Python · FastAPI · Pydantic · Paramiko · SQLAlchemy + Alembic · python-jose (JWT) · pwdlib
(Argon2) · pytest · HTML/CSS/JavaScript.
