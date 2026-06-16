from pathlib import Path

ROOT_PATH = "/api"

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

BASE_LOGS = Path("/home/plog/venv/logs")
SCRIPT_DOWNLOAD = BASE_LOGS / "modulos" / "script-download-logs.sh"
SCRIPT_DESCOMPACTA = BASE_LOGS / "modulos" / "script-descompacta-log.sh"

FLOW_ROUTE = "rj02bd01"
FLOW_REMOTE_HOST = "10.10.10.53"
FLOW_REMOTE_USER = "plog"
FLOW_REMOTE_DIR = Path("/var/flows") / FLOW_ROUTE
FLOW_CACHE_DIR = BASE_LOGS / "flows" / FLOW_ROUTE
FLOW_JSON_PATTERN = "*.json"
FLOW_PASSWORD_ENV = "PLOG_FLOW_SFTP_PASSWORD"

SSH_HOSTNAME = "10.10.10.208"
SSH_USERNAME = "plog"
SSH_PRIVATE_KEY_PATH = Path("/home/plog/.ssh/id_rsa")