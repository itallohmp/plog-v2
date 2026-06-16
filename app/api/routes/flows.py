from datetime import date
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.repositories.flow_repository import (
    FlowNotFoundError,
    FlowQueryError,
    FlowRepository,
)
from app.schemas.flow import FlowQuery, FlowResponse
from app.services.flow_service import FlowService

router = APIRouter()
service = FlowService(FlowRepository())


@router.get("/flows", response_model=FlowResponse)
def listar_flows(
    data: date = Query(..., description="Data dos flows (YYYY-MM-DD)"),
    ip: Optional[str] = Query(None, description="IP para filtrar"),
    porta: Optional[int] = Query(None, ge=0, le=65535),
    hora_de: Optional[int] = Query(None, ge=0, le=23),
    hora_ate: Optional[int] = Query(None, ge=0, le=23),
    pagina: int = Query(1, ge=1),
    tamanho_pagina: int = Query(100, ge=1, le=1000),
):
    try:
        query = FlowQuery(
            data=data,
            ip=ip,
            porta=porta,
            hora_de=hora_de,
            hora_ate=hora_ate,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
        )
    except ValidationError as exc:
        return JSONResponse(
            {"erro": "Parametros invalidos", "detalhes": exc.errors()},
            status_code=422,
        )

    try:
        return service.buscar_flows(query)
    except FlowNotFoundError as exc:
        return JSONResponse({"erro": str(exc)}, status_code=404)
    except FlowQueryError as exc:
        return JSONResponse(
            {"erro": "Falha ao consultar flows", "detalhes": str(exc)},
            status_code=502,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"erro": str(exc)}, status_code=500)
