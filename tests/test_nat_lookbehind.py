"""Testes da resolucao PARA TRAS de deletes orfaos (lookbehind).

Espelho de test_nat_lookahead.py: quando um delete aparece na janela sem o
create par (create ocorreu antes do primeiro dia), o service consulta os dias
anteriores filtrado pela chave e completa a sessao (abertura + duracao).
"""

from datetime import date, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock

from app.core import config
from app.repositories.flow_repository import FlowQueryError, FlowRepository
from app.schemas.flow import FlowQuery
from app.services.flow_service import FlowService

# Janela de um dia; os dias anteriores (para o lookbehind) existem sempre.
DIA = date(2020, 1, 10)

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


class TestCasarOrfaosParaTras:
    def test_completa_sessao_com_create_anterior(self):
        """Delete na janela + create no dia anterior -> fechada COM abertura."""
        svc, repo = _service(
            janela=[_ev("2020-01-10T10:00:00", "delete")],
            extras=[_ev("2020-01-08T09:00:00", "create")],
        )

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.total == 1
        reg = resp.registros[0]
        assert reg.status == "fechada"
        assert reg.abertura == "2020-01-08T09:00:00"
        assert reg.fechamento == "2020-01-10T10:00:00"
        assert reg.parcial is False
        assert reg.duracao_segundos is not None  # abertura+fechamento -> duracao

    def test_consulta_os_dias_anteriores_a_janela(self):
        """O lookbehind pede o range [primeiro_dia - MAX, primeiro_dia - 1]."""
        svc, repo = _service(
            janela=[_ev("2020-01-10T10:00:00", "delete")],
            extras=[_ev("2020-01-08T09:00:00", "create")],
        )

        svc.buscar_flows(FlowQuery(data=DIA))

        repo.fetch_flows_por_chave.assert_called_once()
        _, inicio, fim = repo.fetch_flows_por_chave.call_args.args
        assert inicio == DIA - timedelta(days=config.NAT_LOOKBEHIND_MAX_DIAS)
        assert fim == DIA - timedelta(days=1)

    def test_sem_create_anterior_fica_parcial(self):
        """Nada nos dias anteriores -> segue fechada parcial, sem abertura."""
        svc, repo = _service(
            janela=[_ev("2020-01-10T10:00:00", "delete")],
            extras=[],
        )

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        reg = resp.registros[0]
        assert reg.status == "fechada"
        assert reg.abertura is None
        assert reg.parcial is True

    def test_falha_no_lookbehind_nao_derruba_query(self):
        """Erro no nfdump extra degrada: sessao segue parcial, nunca 502."""
        svc, repo = _service(
            janela=[_ev("2020-01-10T10:00:00", "delete")],
            extras=[],
        )
        repo.fetch_flows_por_chave.side_effect = FlowQueryError("nfdump falhou")

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.total == 1
        assert resp.registros[0].parcial is True

    def test_sem_orfaos_nao_consulta(self):
        """Par completo na janela -> nenhuma consulta extra pra tras."""
        svc, repo = _service(
            janela=[
                _ev("2020-01-10T10:00:00", "create"),
                _ev("2020-01-10T10:00:10", "delete"),
            ],
            extras=[],
        )

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.registros[0].status == "fechada"
        repo.fetch_flows_por_chave.assert_not_called()

    def test_desligavel_por_env(self, monkeypatch):
        """PLOG_NAT_LOOKBEHIND=0 -> nao consulta; delete orfao segue parcial."""
        monkeypatch.setattr(config, "NAT_LOOKBEHIND_ATIVO", False)
        svc, repo = _service(
            janela=[_ev("2020-01-10T10:00:00", "delete")],
            extras=[_ev("2020-01-08T09:00:00", "create")],
        )

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.registros[0].parcial is True
        assert resp.registros[0].abertura is None
        repo.fetch_flows_por_chave.assert_not_called()

    def test_lifo_dois_orfaos_dois_creates(self):
        """Dois deletes na janela + dois creates antes: casa LIFO.

        O delete mais antigo (D1) fecha o create mais recente (C2); o delete
        seguinte (D2) fecha o create mais antigo (C1) — mesma regra do
        correlacionar, para nao trocar assinantes."""
        svc, repo = _service(
            janela=[
                _ev("2020-01-10T10:00:00", "delete"),  # D1 (mais antigo)
                _ev("2020-01-10T11:00:00", "delete"),  # D2
            ],
            extras=[
                _ev("2020-01-08T08:00:00", "create"),  # C1 (mais antigo)
                _ev("2020-01-08T09:00:00", "create"),  # C2 (mais recente)
            ],
        )

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.total == 2
        # registros ordenados pelo indice original: [D1, D2].
        assert resp.registros[0].abertura == "2020-01-08T09:00:00"  # D1 <- C2
        assert resp.registros[1].abertura == "2020-01-08T08:00:00"  # D2 <- C1
        assert all(r.parcial is False for r in resp.registros)
