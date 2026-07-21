"""Testes da resolucao de sessoes pendentes via consulta filtrada ao nfdump.

Derivados de .specs/features/sessoes-nat/spec.md (NAT-07..10).
"""

from datetime import date
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from app.core import config
from app.repositories.flow_repository import FlowRepository, construir_filtro_nfdump
from app.schemas.flow import FlowQuery
from app.services.flow_service import FlowService

# Dia claramente no passado, para o range (dia seguinte -> hoje) existir sempre.
DIA = date(2020, 1, 1)

BLOCO = {
    "ip4_router": "172.16.2.1",
    "src4_addr": "172.16.10.17",
    "src4_xlt_ip": "177.137.21.38",
    "pblock_start": 4096,
    "pblock_size": 512,
    "proto": 6,
}


def _ev(data_iso: str, classe: str) -> Dict[str, Any]:
    nat_event = {
        "create": "NAT translation create",
        "delete": "NAT translation delete",
    }[classe]
    return dict(BLOCO, t_first=data_iso, nat_event=nat_event)


def _service(janela: List[Dict[str, Any]], extras: List[Dict[str, Any]]):
    repo = MagicMock(spec=FlowRepository)
    repo.fetch_raw_flows.return_value = janela
    repo.fetch_flows_por_chave.return_value = extras
    return FlowService(repo), repo


class TestConstruirFiltro:
    def test_monta_expressao_com_ips(self):
        """Filtra por src ip + src nat ip (sintaxe confirmada no nfdump 1.7.8)."""
        chave = ("172.16.2.1", "172.16.10.17", "177.137.21.38", 4096, 512)
        expr = construir_filtro_nfdump([chave])
        assert "src ip 172.16.10.17" in expr
        assert "src nat ip 177.137.21.38" in expr

    def test_bloco_nao_entra_na_expressao(self):
        """O nfdump 1.7.8 nao tem filtro pblock; o bloco e casado em Python."""
        chave = ("172.16.2.1", "172.16.10.17", "177.137.21.38", 4096, 512)
        expr = construir_filtro_nfdump([chave])
        assert "pblock" not in expr and "4096" not in expr

    def test_anti_injecao_descarta_chave_com_ip_malicioso(self):
        """NAT-10: valor que nao e IP valido nunca entra na expressao."""
        maliciosa = ("172.16.2.1", "1.2.3.4; rm -rf /", "177.137.21.38", 4096, 512)
        assert construir_filtro_nfdump([maliciosa]) == ""

    def test_anti_injecao_descarta_nat_malicioso(self):
        ruim = ("172.16.2.1", "172.16.10.17", "$(reboot)", 4096, 512)
        assert construir_filtro_nfdump([ruim]) == ""

    def test_mistura_valida_e_invalida_mantem_so_a_valida(self):
        boa = ("172.16.2.1", "172.16.10.17", "177.137.21.38", 4096, 512)
        ruim = ("172.16.2.1", "nao-ip", "177.137.21.38", 8192, 512)
        expr = construir_filtro_nfdump([boa, ruim])
        assert "172.16.10.17" in expr and "nao-ip" not in expr


class TestResolverPendentes:
    def test_fecha_sessao_com_delete_posterior(self):
        """NAT-07: create sem par na janela, delete encontrado adiante -> fechada."""
        svc, repo = _service(
            janela=[_ev("2020-01-01T10:00:00", "create")],
            extras=[_ev("2020-01-05T10:00:00", "delete")],
        )

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.total == 1
        assert resp.registros[0].status == "fechada"
        assert resp.registros[0].fechamento[:10] == "2020-01-05"
        repo.fetch_flows_por_chave.assert_called_once()

    def test_sem_delete_fica_aberta_com_verificado_ate(self):
        """NAT-07: pendente sem delete no range -> aberta, verificado ate hoje."""
        svc, repo = _service(
            janela=[_ev("2020-01-01T10:00:00", "create")],
            extras=[],
        )

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.registros[0].status == "aberta"
        assert resp.registros[0].verificado_ate == date.today().isoformat()

    def test_sem_pendentes_nao_consulta(self):
        """NAT-08: janela ja com par completo -> nenhuma consulta extra."""
        svc, repo = _service(
            janela=[
                _ev("2020-01-01T10:00:00", "create"),
                _ev("2020-01-01T10:00:10", "delete"),
            ],
            extras=[],
        )

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.registros[0].status == "fechada"
        repo.fetch_flows_por_chave.assert_not_called()

    def test_desligavel_por_env(self, monkeypatch):
        """NAT-09: PLOG_NAT_LOOKAHEAD=0 -> nao consulta; pendente fica aberta."""
        monkeypatch.setattr(config, "NAT_LOOKAHEAD_ATIVO", False)
        svc, repo = _service(
            janela=[_ev("2020-01-01T10:00:00", "create")],
            extras=[_ev("2020-01-05T10:00:00", "delete")],
        )

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.registros[0].status == "aberta"
        assert resp.registros[0].verificado_ate is None
        repo.fetch_flows_por_chave.assert_not_called()
