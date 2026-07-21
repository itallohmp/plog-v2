from datetime import date
from typing import List, Optional

from app.core.security import verificar_token_acesso
from app.models.user import User
from app.repositories.flow_repository import (
    FlowNotFoundError,
    FlowQueryError,
    FlowRepository,
)
from app.schemas.flow import (
    AnomaliaResponse,
    FlowQuery,
    FlowResponse,
    SerieResponse,
)
from app.services.flow_service import FlowService
from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

router = APIRouter()


def get_flow_repository() -> FlowRepository:
    return FlowRepository()


def get_flow_service(
    repository: FlowRepository = Depends(get_flow_repository),
) -> FlowService:
    return FlowService(repository)


@router.get("/flows", response_model=FlowResponse)
def listar_flows(
    data: date = Query(..., description="Data inicial dos flows (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(
        None, description="Data final do intervalo (YYYY-MM-DD, opcional)"
    ),
    ip: Optional[str] = Query(None, description="IP para filtrar"),
    porta: Optional[int] = Query(None, ge=0, le=65535),
    protocolo: Optional[List[str]] = Query(
        None, description="Protocolos: tcp, udp e/ou icmp (repetivel; vazio = todos)"
    ),
    status: Optional[List[str]] = Query(
        None, description="Estados: aberta, fechada e/ou indefinida (repetivel)"
    ),
    hora_de: Optional[int] = Query(None, ge=0, le=23),
    hora_ate: Optional[int] = Query(None, ge=0, le=23),
    pagina: int = Query(1, ge=1),
    tamanho_pagina: int = Query(100, ge=1, le=1000),
    service: FlowService = Depends(get_flow_service),
    usuario: User = Depends(verificar_token_acesso),
):
    try:
        query = FlowQuery(
            data=data,
            data_fim=data_fim,
            ip=ip,
            porta=porta,
            protocolo=protocolo,
            status=status,
            hora_de=hora_de,
            hora_ate=hora_ate,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
        )
    except ValidationError as exc:
        return JSONResponse(
            {
                "erro": "Parametros invalidos",
                "detalhes": jsonable_encoder(exc.errors()),
            },
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


@router.get("/flows/anomalias", response_model=AnomaliaResponse)
def listar_anomalias(
    data: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data final (opcional)"),
    ip: Optional[str] = Query(None, description="Filtra por um IP de origem"),
    hora_de: Optional[int] = Query(None, ge=0, le=23),
    hora_ate: Optional[int] = Query(None, ge=0, le=23),
    limiar: Optional[int] = Query(
        None, ge=1, description="Blocos simultaneos minimos para listar o IP"
    ),
    service: FlowService = Depends(get_flow_service),
    usuario: User = Depends(verificar_token_acesso),
):
    try:
        # Sem filtro de protocolo/estado: o relatorio conta todos os blocos.
        query = FlowQuery(
            data=data,
            data_fim=data_fim,
            ip=ip,
            hora_de=hora_de,
            hora_ate=hora_ate,
        )
    except ValidationError as exc:
        return JSONResponse(
            {
                "erro": "Parametros invalidos",
                "detalhes": jsonable_encoder(exc.errors()),
            },
            status_code=422,
        )

    try:
        return service.detectar_anomalias(query, limiar=limiar)
    except FlowNotFoundError as exc:
        return JSONResponse({"erro": str(exc)}, status_code=404)
    except FlowQueryError as exc:
        return JSONResponse(
            {"erro": "Falha ao consultar flows", "detalhes": str(exc)},
            status_code=502,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"erro": str(exc)}, status_code=500)


@router.get("/flows/anomalias/serie", response_model=SerieResponse)
def serie_anomalia(
    ip: str = Query(..., description="IP local para a serie de picos"),
    data: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data final (opcional)"),
    hora_de: Optional[int] = Query(None, ge=0, le=23),
    hora_ate: Optional[int] = Query(None, ge=0, le=23),
    service: FlowService = Depends(get_flow_service),
    usuario: User = Depends(verificar_token_acesso),
):
    """Curva de alocacao de blocos de um IP na janela (modal do ranking).

    Mesmo filtro do ranking (sem protocolo/estado): conta todos os blocos do IP.
    """
    try:
        query = FlowQuery(
            data=data,
            data_fim=data_fim,
            ip=ip,
            hora_de=hora_de,
            hora_ate=hora_ate,
        )
    except ValidationError as exc:
        return JSONResponse(
            {
                "erro": "Parametros invalidos",
                "detalhes": jsonable_encoder(exc.errors()),
            },
            status_code=422,
        )

    try:
        return service.serie_ip(query, ip)
    except FlowNotFoundError as exc:
        return JSONResponse({"erro": str(exc)}, status_code=404)
    except FlowQueryError as exc:
        return JSONResponse(
            {"erro": "Falha ao consultar flows", "detalhes": str(exc)},
            status_code=502,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"erro": str(exc)}, status_code=500)
