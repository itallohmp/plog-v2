"""Testes do filtro por estado da sessao (aberta / fechada).

Derivados de .specs/features/filtro-status/spec.md (STAT-01..07).
"""

from datetime import date
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.api.routes.flows import get_flow_service
from app.core.security import verificar_token_acesso
from app.repositories.flow_repository import FlowRepository
from app.schemas.flow import FlowQuery, FlowResponse
from app.services.flow_service import FlowService
from fastapi.testclient import TestClient
from main import app

DIA = date(2026, 7, 15)

BLOCO = {
    "ip4_router": "172.16.2.1",
    "src4_addr": "172.16.10.17",
    "src4_xlt_ip": "177.137.21.38",
    "pblock_size": 512,
    "proto": 6,
}


def _ev(hora: str, classe: str, pblock_start: int) -> Dict[str, Any]:
    nat_event = {
        "create": "NAT translation create",
        "delete": "NAT translation delete",
    }[classe]
    return dict(BLOCO, t_first=f"2026-07-15T{hora}", nat_event=nat_event,
                pblock_start=pblock_start)


def _service(eventos: List[Dict[str, Any]]) -> FlowService:
    repo = MagicMock(spec=FlowRepository)
    repo.fetch_raw_flows.return_value = eventos
    # Sem lookahead extra: pendentes ficam abertas.
    repo.fetch_flows_por_chave.return_value = []
    return FlowService(repo)


# Bloco 4096: par completo (fechada). Bloco 8192: create sozinho (aberta).
EVENTOS = [
    _ev("10:00:00", "create", 4096),
    _ev("10:00:10", "delete", 4096),
    _ev("11:00:00", "create", 8192),
]


class TestFiltroStatusSchema:
    def test_case_insensitive_e_dedup(self):
        """STAT-04: capitalizacao nao importa; duplicatas colapsam."""
        q = FlowQuery(data=DIA, status=["Aberta", "ABERTA"])
        assert q.estados_filtro() == {"aberta"}

    def test_sem_filtro(self):
        """STAT-03: ausente ou vazio -> None."""
        assert FlowQuery(data=DIA).estados_filtro() is None
        assert FlowQuery(data=DIA, status=[]).estados_filtro() is None

    def test_invalido_rejeitado(self):
        """STAT-05: valor fora do enum -> ValidationError."""
        with pytest.raises(ValidationError):
            FlowQuery(data=DIA, status=["meio-aberta"])


class TestFiltroStatusService:
    def test_so_fechada(self):
        """STAT-01: status=fechada retorna so a sessao fechada."""
        resp = _service(EVENTOS).buscar_flows(FlowQuery(data=DIA, status=["fechada"]))
        assert resp.total == 1
        assert resp.registros[0].status == "fechada"
        assert resp.registros[0].bloco_portas == "4096-4607"

    def test_so_aberta(self):
        """STAT-01: status=aberta retorna so a sessao aberta."""
        resp = _service(EVENTOS).buscar_flows(FlowQuery(data=DIA, status=["aberta"]))
        assert resp.total == 1
        assert resp.registros[0].status == "aberta"
        assert resp.registros[0].bloco_portas == "8192-8703"

    def test_uniao_aberta_fechada(self):
        """STAT-02: aberta+fechada retorna as duas."""
        resp = _service(EVENTOS).buscar_flows(
            FlowQuery(data=DIA, status=["aberta", "fechada"])
        )
        assert resp.total == 2
        assert sorted(r.status for r in resp.registros) == ["aberta", "fechada"]

    def test_sem_filtro_retorna_todas(self):
        """STAT-03: sem status -> todas as sessoes."""
        resp = _service(EVENTOS).buscar_flows(FlowQuery(data=DIA))
        assert resp.total == 2

    def test_compoe_com_protocolo(self):
        """STAT-08: status compoe por AND com protocolo."""
        resp = _service(EVENTOS).buscar_flows(
            FlowQuery(data=DIA, status=["fechada"], protocolo=["tcp"])
        )
        assert resp.total == 1
        assert resp.registros[0].protocolo == "TCP"


class TestFiltroStatusPosLookahead:
    def test_pendente_fechada_pelo_lookahead_conta_como_fechada(self):
        """STAT-06: o filtro roda APOS o lookahead. Uma pendente cujo delete e
        encontrado adiante conta como 'fechada', nao 'aberta'."""
        repo = MagicMock(spec=FlowRepository)
        repo.fetch_raw_flows.return_value = [_ev("10:00:00", "create", 4096)]
        # lookahead encontra o delete adiante
        repo.fetch_flows_por_chave.return_value = [
            dict(BLOCO, t_first="2026-07-16T09:00:00",
                 nat_event="NAT translation delete", pblock_start=4096)
        ]
        svc = FlowService(repo)

        # filtrando por "fechada", a sessao (que abriu na janela e fechou
        # adiante) deve aparecer
        resp = svc.buscar_flows(FlowQuery(data=DIA, status=["fechada"]))
        assert resp.total == 1
        assert resp.registros[0].status == "fechada"

        # e filtrando por "aberta" ela NAO deve aparecer
        resp2 = svc.buscar_flows(FlowQuery(data=DIA, status=["aberta"]))
        assert resp2.total == 0


@pytest.fixture
def api_client():
    capturado: Dict[str, Any] = {}

    class _ServiceEspiao:
        def buscar_flows(self, query: FlowQuery) -> FlowResponse:
            capturado["query"] = query
            return FlowResponse(
                data="2026-07-15", total=0, pagina=1, total_paginas=1, registros=[]
            )

    app.dependency_overrides[get_flow_service] = lambda: _ServiceEspiao()
    app.dependency_overrides[verificar_token_acesso] = lambda: object()
    with TestClient(app) as client:
        yield client, capturado
    app.dependency_overrides.clear()


class TestFiltroStatusRota:
    def test_rota_repassa_status(self, api_client):
        client, capturado = api_client
        r = client.get("/api/flows", params={"data": "2026-07-15", "status": ["aberta"]})
        assert r.status_code == 200
        assert capturado["query"].status == ["aberta"]

    def test_rota_status_invalido_422(self, api_client):
        """STAT-05 na borda HTTP."""
        client, _ = api_client
        r = client.get("/api/flows", params={"data": "2026-07-15", "status": "xyz"})
        assert r.status_code == 422
        assert r.json()["erro"] == "Parametros invalidos"
