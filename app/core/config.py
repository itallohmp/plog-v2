import os

from dotenv import load_dotenv

load_dotenv()

API_PREFIX = os.getenv("PLOG_API_PREFIX", "/api")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "PLOG_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

# Origem dos flows (nfcapd + nfdump via SSH)
FLOW_ROUTE = os.getenv("PLOG_FLOW_ROUTE", "rj02bd01")
FLOW_REMOTE_DIR = os.getenv("PLOG_FLOW_REMOTE_DIR", f"/var/flows/{FLOW_ROUTE}").rstrip(
    "/"
)

# Estrutura remota: <FLOW_REMOTE_DIR>/<dia>/<hora>/<arquivos nfcapd>
FLOW_DAY_DIR_FORMAT = os.getenv("PLOG_FLOW_DAY_DIR_FORMAT", "%Y-%m-%d")

# Conexao SSH com o servidor de flows. Segredos somente via ambiente.
FLOW_SSH_HOST = os.getenv("PLOG_FLOW_SSH_HOST")
FLOW_SSH_PORT = int(os.getenv("PLOG_FLOW_SSH_PORT", "22"))
FLOW_SSH_USER = os.getenv("PLOG_FLOW_SSH_USER", "plog")
FLOW_SSH_KEY_PATH = os.getenv("PLOG_FLOW_SSH_KEY_PATH") or None
FLOW_SSH_PASSWORD = os.getenv("PLOG_FLOW_SSH_PASSWORD") or None
FLOW_SSH_KNOWN_HOSTS = os.getenv("PLOG_FLOW_SSH_KNOWN_HOSTS") or None
FLOW_SSH_TIMEOUT = int(os.getenv("PLOG_FLOW_SSH_TIMEOUT", "15"))

# Binario nfdump no servidor remoto e timeout de execucao.
NFDUMP_BIN = os.getenv("PLOG_NFDUMP_BIN", "nfdump")
NFDUMP_TIMEOUT = int(os.getenv("PLOG_NFDUMP_TIMEOUT", "120"))

FLOW_LOCAL_PATH = os.getenv("PLOG_FLOW_LOCAL_PATH") or None

# Resolucao de sessoes NAT abertas (create sem delete na janela consultada).
# Quando ligado, o service consulta o nfdump filtrado pelas chaves pendentes
# no range (dia seguinte -> hoje) para descobrir se ja fecharam. Desligavel
# porque a sintaxe de filtro NAT do nfdump varia por versao e precisa ser
# confirmada contra o binario do servidor antes de ser confiavel.
NAT_LOOKAHEAD_ATIVO = os.getenv("PLOG_NAT_LOOKAHEAD", "1") not in ("0", "false", "False")
# Teto de chaves pendentes por consulta, para nao gerar expressao gigante.
NAT_LOOKAHEAD_MAX_CHAVES = int(os.getenv("PLOG_NAT_LOOKAHEAD_MAX_CHAVES", "200"))
# Teto de dias verificados adiante. O nfdump 1.7.8 nao aceita range sobre
# diretorios de dia (`-R d1:d2`), entao o lookahead le um dia por vez com
# `-R <dia>` (filtrado, barato). O teto limita o custo; sessoes ainda abertas
# apos ele ficam com verificado_ate = ultimo dia checado.
NAT_LOOKAHEAD_MAX_DIAS = int(os.getenv("PLOG_NAT_LOOKAHEAD_MAX_DIAS", "3"))

NFDUMP_LOCAL_BIN = os.getenv("PLOG_NFDUMP_LOCAL_BIN", "nfdump")
FLOW_NFCAPD_PREFIX = os.getenv("PLOG_FLOW_NFCAPD_PREFIX", "nfcapd")

# Anomalia de blocos: IP local que mantem muitos blocos de porta ativos ao
# mesmo tempo pode ser sub-provedor / NAT atras de NAT. O normal e ~1 bloco por
# protocolo (~3 no total). LIMIAR = total de blocos simultaneos (pico) a partir
# do qual o IP entra no relatorio; ajustavel por env e por parametro na consulta.
ANOMALIA_LIMIAR = int(os.getenv("PLOG_ANOMALIA_LIMIAR", "6"))
# Teto de IPs retornados no ranking (os mais criticos primeiro).
ANOMALIA_TOP_N = int(os.getenv("PLOG_ANOMALIA_TOP_N", "100"))

FLOW_PLOG_SECRET_KEY = os.getenv("PLOG_SECRET_KEY")
FLOW_ALGORITHM = os.getenv("PLOG_ALGORITHM", "HS256")
_expire_raw = os.getenv("PLOG_ACCESS_TOKEN_EXPIRE_MINUTES")

if not FLOW_PLOG_SECRET_KEY:
    raise RuntimeError("PLOG_SECRET_KEY env var is required but not set.")
if _expire_raw is None:
    raise RuntimeError(
        "PLOG_ACCESS_TOKEN_EXPIRE_MINUTES env var is required but not set."
    )

FLOW_ACCESS_TOKEN_EXPIRE_MINUTES = int(_expire_raw)
