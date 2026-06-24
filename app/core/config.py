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

NFDUMP_LOCAL_BIN = os.getenv("PLOG_NFDUMP_LOCAL_BIN", "nfdump")
FLOW_NFCAPD_PREFIX = os.getenv("PLOG_FLOW_NFCAPD_PREFIX", "nfcapd")

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
