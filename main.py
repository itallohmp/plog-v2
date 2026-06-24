from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.auth import router as auth_router
from app.api.routes.flows import router as flows_router
from app.api.routes.system import router as system_router
from app.core.config import ALLOWED_ORIGINS, API_PREFIX

app = FastAPI(title="PLOG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(system_router, prefix=API_PREFIX)
app.include_router(flows_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)

# Mount estatico por ultimo para nao sombrear as rotas da API.
app.mount("/", StaticFiles(directory="static", html=True), name="frontend")
