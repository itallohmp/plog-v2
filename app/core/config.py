import os

from dotenv import load_dotenv

load_dotenv()

API_PREFIX = os.getenv("PLOG_API_PREFIX", "/api")

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


# Origem dos flows (nfcapd + nfdump via SSH)
FLOW_REMOTE_DIR = os.getenv(
    "PLOG_FLOW_REMOTE_DIR", f"/var/flows/{os.getenv('PLOG_FLOW_ROUTE')}"
).rstrip("/")

# Estrutura remota: <FLOW_REMOTE_DIR>/<dia>/<hora>/<arquivos nfcapd>
FLOW_DAY_DIR_FORMAT = os.getenv("PLOG_FLOW_DAY_DIR_FORMAT", "%Y-%m-%d")

# Conexao SSH com o servidor de flows. Segredos somente via ambiente.
FLOW_SSH_HOST = os.getenv("PLOG_FLOW_SSH_HOST")
FLOW_SSH_PORT = int(os.getenv("PLOG_FLOW_SSH_PORT"))
FLOW_SSH_USER = os.getenv("PLOG_FLOW_SSH_USER", "plog")
FLOW_SSH_KEY_PATH = os.getenv("PLOG_FLOW_SSH_KEY_PATH") or None
FLOW_SSH_PASSWORD = os.getenv("PLOG_FLOW_SSH_PASSWORD") or None
FLOW_SSH_KNOWN_HOSTS = os.getenv("PLOG_FLOW_SSH_KNOWN_HOSTS") or None
FLOW_SSH_TIMEOUT = int(os.getenv("PLOG_FLOW_SSH_TIMEOUT", "15"))

# Binario nfdump no servidor remoto e timeout de execucao.
NFDUMP_BIN = os.getenv("PLOG_NFDUMP_BIN", "nfdump")
NFDUMP_TIMEOUT = int(os.getenv("PLOG_NFDUMP_TIMEOUT", "120"))

# Modo de teste local: se definido, le os flows de um arquivo/pasta local
# (arquivos nfcapd convertidos via nfdump ou JSON pronto) sem usar SSH.
# FLOW_LOCAL_PATH = (
#     os.getenv(
#         "PLOG_FLOW_LOCAL_PATH",
#         "C:\\Users\\Itallo Polito\\Desktop\\Projetos\\plog\\plog\\logs",
#     )
#     or None
# )

FLOW_LOCAL_PATH = None

# # Binario nfdump local usado para converter nfcapd em JSON no modo de teste.
# NFDUMP_LOCAL_BIN = os.getenv("PLOG_NFDUMP_LOCAL_BIN", "nfdump")
# # Prefixo dos arquivos nfcapd a procurar na pasta local.
# FLOW_NFCAPD_PREFIX = os.getenv("PLOG_FLOW_NFCAPD_PREFIX", "nfcapd")
