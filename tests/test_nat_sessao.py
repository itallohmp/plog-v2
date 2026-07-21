"""Testes de sessao NAT no nivel do service (correlacao ponta a ponta).

Derivados de .specs/features/sessoes-nat/spec.md (NAT-01, NAT-02).
"""

from datetime import date
from typing import Any, Dict, List
from unittest.mock import MagicMock

from app.repositories.flow_repository import FlowRepository
from app.schemas.flow import FlowQuery
from app.services.flow_service import FlowService

DIA = date(2026, 7, 15)

BLOCO = {
    "ip4_router": "172.16.2.1",
    "src4_addr": "172.16.10.17",
    "src4_xlt_ip": "177.137.21.38",
    "pblock_start": 4096,
    "pblock_size": 512,
    "proto": 6,
}


def _ev(hora: str, classe: str) -> Dict[str, Any]:
    nat_event = {
        "create": "NAT translation create",
        "delete": "NAT translation delete",
    }[classe]
    return dict(BLOCO, t_first=f"2026-07-15T{hora}", nat_event=nat_event)


def _service(eventos: List[Dict[str, Any]]) -> FlowService:
    repo = MagicMock(spec=FlowRepository)
    repo.fetch_raw_flows.return_value = eventos
    return FlowService(repo)


class TestSessaoService:
    def test_par_vira_uma_linha_fechada(self):
        """NAT-01: create + delete do mesmo bloco -> 1 sessao fechada com duracao."""
        svc = _service([_ev("18:48:41", "create"), _ev("18:48:51", "delete")])

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.total == 1
        registro = resp.registros[0]
        assert registro.status == "fechada"
        assert registro.duracao == "10s"
        assert registro.origem == "172.16.10.17"
        assert registro.nat == "177.137.21.38"
        assert registro.bloco_portas == "4096-4607"
        assert registro.eventos == 2

    def test_create_sem_delete_fica_aberta(self):
        """NAT-02: create sem delete na janela -> sessao aberta."""
        svc = _service([_ev("18:48:41", "create")])

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.total == 1
        assert resp.registros[0].status == "aberta"
        assert resp.registros[0].fechamento is None

    def test_protocolo_vem_do_evento_com_proto_valido(self):
        """Edge (spec): create com proto 0/ausente e delete com proto valido ->
        o protocolo exibido vem do delete."""
        create = dict(BLOCO, t_first="2026-07-15T10:00:00",
                      nat_event="NAT translation create", proto=0)
        delete = dict(BLOCO, t_first="2026-07-15T10:00:10",
                      nat_event="NAT translation delete", proto=6)
        svc = _service([create, delete])

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.registros[0].status == "fechada"
        assert resp.registros[0].protocolo == "TCP"

    def test_paginacao_conta_sessoes(self):
        """total e paginacao passam a contar sessoes, nao eventos crus."""
        eventos = [
            _ev("10:00:00", "create"),
            _ev("10:00:05", "delete"),  # sessao 1 (fechada)
            _ev("11:00:00", "create"),  # sessao 2 (aberta)
        ]
        svc = _service(eventos)

        resp = svc.buscar_flows(FlowQuery(data=DIA, tamanho_pagina=1))

        assert resp.total == 2  # 3 eventos -> 2 sessoes
        assert resp.total_paginas == 2
        assert len(resp.registros) == 1
