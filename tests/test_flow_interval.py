"""Testes de regressao da busca de flows por intervalo de datas.

Derivados de .specs/features/regressao-intervalo-datas/spec.md (RINT-01..08).
A logica exercitada esta em FlowService.buscar_flows (iteracao dia-a-dia,
AD-001) e em FlowQuery (validacao de intervalo). Nenhum destes testes le a
implementacao para decidir o esperado: cada assert codifica o comportamento
que a spec exige.
"""

from datetime import date, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.repositories.flow_repository import FlowNotFoundError, FlowRepository
from app.schemas.flow import MAX_DIAS_INTERVALO, FlowQuery
from app.services.flow_service import FlowService

IP = "100.64.18.210"


def _evento(dia: date, ip: str = IP) -> Dict[str, Any]:
    """Evento minimo com t_first no dia informado e origem = ip."""
    return {
        "type": "EVENT",
        "t_first": f"{dia.isoformat()}T18:48:41.045",
        "proto": 6,
        "src4_addr": ip,
        "nat_event": "NAT translation delete",
    }


def _service(day_map: Dict[date, List[Dict[str, Any]]]) -> FlowService:
    """FlowService cujo repositorio varia o retorno por dia.

    Dias ausentes do mapa levantam FlowNotFoundError, reproduzindo o
    comportamento real de um diretorio de dia inexistente no servidor.
    """
    repo = MagicMock(spec=FlowRepository)

    def fetch(dia: date, horas):
        if dia in day_map:
            return day_map[dia]
        raise FlowNotFoundError(f"sem dados para {dia}")

    repo.fetch_raw_flows.side_effect = fetch
    return FlowService(repo)


class TestIntervaloService:
    def test_uniao_multi_dia(self):
        """RINT-01: intervalo retorna a uniao dos eventos que casam em todos os dias."""
        d14, d15 = date(2026, 7, 14), date(2026, 7, 15)
        svc = _service({d14: [_evento(d14)], d15: [_evento(d15)]})

        resp = svc.buscar_flows(FlowQuery(data=d14, data_fim=d15, ip=IP))

        assert resp.total == 2
        datas = sorted(r.data[:10] for r in resp.registros)
        assert datas == ["2026-07-14", "2026-07-15"]

    def test_evento_fora_do_filtro_excluido(self):
        """RINT-01 (clausula 'que casam o filtro'): dentro do dia consultado,
        eventos com IP diferente ou com data de outro dia sao excluidos.

        Discrimina o filtro intra-dia (pcap_event_matches com data=dia_iso):
        se o filtro por data ou por IP for removido, o ruido entra e o total sobe.
        """
        d14, d15 = date(2026, 7, 14), date(2026, 7, 15)
        ruido_ip = _evento(d15, ip="10.0.0.99")          # IP fora do filtro
        ruido_data = _evento(date(2026, 7, 13), ip=IP)   # data de outro dia
        svc = _service(
            {d14: [_evento(d14)], d15: [_evento(d15), ruido_ip, ruido_data]}
        )

        resp = svc.buscar_flows(FlowQuery(data=d14, data_fim=d15, ip=IP))

        assert resp.total == 2
        assert all(r.origem == IP for r in resp.registros)
        assert sorted(r.data[:10] for r in resp.registros) == [
            "2026-07-14",
            "2026-07-15",
        ]

    def test_dia_vazio_ignorado(self):
        """RINT-02: dia sem dados no intervalo e ignorado; dias com dados retornam.

        Caso exato do bug reportado: buscar de 14 a 15 com dados apenas no dia 15.
        """
        d14, d15 = date(2026, 7, 14), date(2026, 7, 15)
        svc = _service({d15: [_evento(d15)]})  # dia 14 levanta FlowNotFoundError

        resp = svc.buscar_flows(FlowQuery(data=d14, data_fim=d15, ip=IP))

        assert resp.total == 1
        assert resp.registros[0].data[:10] == "2026-07-15"
        assert resp.registros[0].origem == IP

    def test_todos_dias_vazios_levanta(self):
        """RINT-03: nenhum dia com dados no intervalo -> FlowNotFoundError."""
        d14, d15 = date(2026, 7, 14), date(2026, 7, 15)
        svc = _service({})  # ambos os dias levantam

        # A mensagem do fallback de intervalo distingue este caminho do
        # re-raise legado do dia unico (ver test_dia_unico_vazio_levanta).
        with pytest.raises(FlowNotFoundError, match="intervalo"):
            svc.buscar_flows(FlowQuery(data=d14, data_fim=d15, ip=IP))

    def test_dia_unico_vazio_levanta(self):
        """RINT-04: consulta de um unico dia sem dados preserva o erro legado."""
        d15 = date(2026, 7, 15)
        svc = _service({})

        # "Legado preservado" = re-raise do erro ORIGINAL do repositorio, e nao
        # o fallback de intervalo. O match ancora nessa distincao (RINT-04).
        with pytest.raises(FlowNotFoundError, match="sem dados para"):
            svc.buscar_flows(FlowQuery(data=d15, ip=IP))

    def test_label_intervalo(self):
        """RINT-05: campo data da resposta usa o formato 'inicio a fim'."""
        d14, d15 = date(2026, 7, 14), date(2026, 7, 15)
        svc = _service({d14: [_evento(d14)], d15: [_evento(d15)]})

        resp = svc.buscar_flows(FlowQuery(data=d14, data_fim=d15, ip=IP))

        assert resp.data == "2026-07-14 a 2026-07-15"


class TestIntervaloSchema:
    def test_schema_data_fim_menor_rejeita(self):
        """RINT-06: data_fim < data e rejeitado."""
        with pytest.raises(ValidationError):
            FlowQuery(data=date(2026, 7, 15), data_fim=date(2026, 7, 14))

    def test_schema_excede_maximo_rejeita(self):
        """RINT-07: intervalo com mais de MAX_DIAS_INTERVALO dias e rejeitado."""
        inicio = date(2026, 7, 1)
        # data_fim = inicio + MAX dias -> total de MAX+1 dias -> excede o limite
        excede = inicio + timedelta(days=MAX_DIAS_INTERVALO)
        with pytest.raises(ValidationError):
            FlowQuery(data=inicio, data_fim=excede)

    def test_schema_limite_maximo_aceito(self):
        """Edge: intervalo com exatamente MAX_DIAS_INTERVALO dias e aceito (limite inclusivo)."""
        inicio = date(2026, 7, 1)
        # total de exatamente MAX dias -> aceito
        limite = inicio + timedelta(days=MAX_DIAS_INTERVALO - 1)
        query = FlowQuery(data=inicio, data_fim=limite)
        assert len(query.dias()) == MAX_DIAS_INTERVALO

    def test_schema_dias_dia_unico(self):
        """RINT-08 (parte 1): data_fim == data (ou ausente) -> exatamente um dia."""
        d = date(2026, 7, 15)
        assert FlowQuery(data=d, data_fim=d).dias() == [d]
        assert FlowQuery(data=d).dias() == [d]

    def test_schema_dias_intervalo_ordenado(self):
        """RINT-08 (parte 2): intervalo de N dias -> N+1 datas em ordem crescente."""
        inicio = date(2026, 7, 14)
        fim = date(2026, 7, 16)
        assert FlowQuery(data=inicio, data_fim=fim).dias() == [
            date(2026, 7, 14),
            date(2026, 7, 15),
            date(2026, 7, 16),
        ]
