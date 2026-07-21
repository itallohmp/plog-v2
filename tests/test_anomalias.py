"""Testes do relatorio de anomalias: IPs locais com muitos blocos ativos.

Cobre a varredura de pico (concorrencia real, nao acumulado) e a agregacao por
IP com o limiar.
"""

from datetime import date, datetime
from unittest.mock import MagicMock

from app.repositories.flow_repository import FlowRepository
from app.schemas.flow import FlowQuery
from app.services.flow_service import FlowService

PROTO = {"tcp": 6, "udp": 17, "icmp": 1}


def _ev(ts, classe, *, origem, pblock, proto="tcp", nat="177.137.21.38",
        roteador="172.16.2.1", size=512):
    nat_event = {
        "create": "NAT translation create",
        "delete": "NAT translation delete",
    }.get(classe, "EVENT")
    return {
        "t_first": f"2026-07-15T{ts}",
        "nat_event": nat_event,
        "ip4_router": roteador,
        "src4_addr": origem,
        "src4_xlt_ip": nat,
        "pblock_start": pblock,
        "pblock_size": size,
        "proto": PROTO[proto],
    }


def _service(eventos):
    repo = MagicMock(spec=FlowRepository)
    repo.fetch_raw_flows.return_value = eventos
    repo.fetch_flows_por_chave.return_value = []  # lookahead nao acha delete
    return FlowService(repo)


def _dt(minuto):
    return datetime(2026, 7, 15, 10, minuto, 0)


class TestPicoConcorrencia:
    def test_vazio(self):
        assert FlowService._pico_concorrencia([]) == 0

    def test_todos_sobrepostos(self):
        intervalos = [(_dt(0), _dt(5)), (_dt(1), _dt(5)), (_dt(2), _dt(5))]
        assert FlowService._pico_concorrencia(intervalos) == 3

    def test_pico_menor_que_total(self):
        # 3 blocos, mas no maximo 2 ao mesmo tempo: A e B se cruzam, C fica so.
        intervalos = [(_dt(0), _dt(2)), (_dt(1), _dt(3)), (_dt(10), _dt(11))]
        assert FlowService._pico_concorrencia(intervalos) == 2

    def test_borda_fecha_quando_outro_abre(self):
        # Um abre exatamente quando o outro fecha: nao sobrepoe (conservador).
        assert FlowService._pico_concorrencia([(_dt(0), _dt(2)), (_dt(2), _dt(4))]) == 1


class TestDetectarAnomalias:
    def test_ip_com_muitos_blocos_e_listado(self):
        eventos = []
        # IP suspeito: 4 blocos TCP + 3 UDP abertos (create sem delete) = 7.
        for i, pb in enumerate((1000, 2000, 3000, 4000)):
            eventos.append(_ev(f"10:0{i}:00", "create", origem="100.64.0.9",
                               pblock=pb, proto="tcp"))
        for i, pb in enumerate((5000, 6000, 7000)):
            eventos.append(_ev(f"10:1{i}:00", "create", origem="100.64.0.9",
                               pblock=pb, proto="udp"))
        # IP normal: 1 bloco TCP aberto e fechado.
        eventos.append(_ev("09:00:00", "create", origem="100.64.0.1", pblock=100))
        eventos.append(_ev("09:05:00", "delete", origem="100.64.0.1", pblock=100))

        resp = _service(eventos).detectar_anomalias(
            FlowQuery(data=date(2026, 7, 15)), limiar=6
        )

        assert resp.total_ips == 1
        item = resp.itens[0]
        assert item.origem == "100.64.0.9"
        assert item.total_abertas == 7
        assert item.total_pico == 7
        assert item.tcp.abertas == 4 and item.tcp.pico == 4
        assert item.udp.abertas == 3 and item.udp.pico == 3
        assert item.icmp.abertas == 0

    def test_ip_normal_fica_fora(self):
        eventos = [
            _ev("09:00:00", "create", origem="100.64.0.1", pblock=100),
            _ev("09:05:00", "delete", origem="100.64.0.1", pblock=100),
        ]
        resp = _service(eventos).detectar_anomalias(
            FlowQuery(data=date(2026, 7, 15)), limiar=6
        )
        assert resp.total_ips == 0
        assert resp.itens == []

    def test_pico_reflete_concorrencia_nao_acumulado(self):
        # 3 blocos TCP fechados, mas no maximo 2 simultaneos -> pico 2, nao 3.
        eventos = [
            _ev("10:00:00", "create", origem="100.64.0.5", pblock=200),
            _ev("10:02:00", "delete", origem="100.64.0.5", pblock=200),
            _ev("10:01:00", "create", origem="100.64.0.5", pblock=300),
            _ev("10:03:00", "delete", origem="100.64.0.5", pblock=300),
            _ev("10:10:00", "create", origem="100.64.0.5", pblock=400),
            _ev("10:11:00", "delete", origem="100.64.0.5", pblock=400),
        ]
        resp = _service(eventos).detectar_anomalias(
            FlowQuery(data=date(2026, 7, 15)), limiar=2
        )
        assert resp.total_ips == 1
        item = resp.itens[0]
        assert item.total_abertas == 0  # todos fechados
        assert item.tcp.pico == 2       # NAO 3
        assert item.total_pico == 2

    def test_buscar_flows_embute_anomalias(self):
        # A consulta normal ja traz o ranking (secao do dashboard), sem 2a passada.
        eventos = [
            _ev("10:00:00", "create", origem="100.64.9.9", pblock=pb)
            for pb in (10, 20, 30, 40, 50, 60, 70)
        ]
        resp = _service(eventos).buscar_flows(FlowQuery(data=date(2026, 7, 15)))
        assert resp.anomalias is not None
        assert resp.anomalias.total_ips == 1
        assert resp.anomalias.itens[0].origem == "100.64.9.9"
        assert resp.anomalias.itens[0].total_abertas == 7

    def test_dashboard_lista_maiores_mesmo_sem_anomalia(self):
        # IP com 3 blocos abertos (abaixo do limiar 6) entra no ranking do
        # dashboard, mas nao conta como anomalia. IP de 1 bloco fica de fora.
        eventos = [
            _ev("10:00:00", "create", origem="100.64.7.7", pblock=pb)
            for pb in (10, 20, 30)
        ]
        eventos += [
            _ev("09:00:00", "create", origem="100.64.7.1", pblock=1),
            _ev("09:05:00", "delete", origem="100.64.7.1", pblock=1),
        ]
        resp = _service(eventos).buscar_flows(FlowQuery(data=date(2026, 7, 15)))

        anom = resp.anomalias
        assert anom.total_ips == 0            # nenhum acima do limiar
        assert len(anom.itens) == 1           # mas o ranking mostra o maior
        assert anom.itens[0].origem == "100.64.7.7"
        assert anom.itens[0].total_pico == 3

    def test_ranking_ordena_por_pico_desc(self):
        eventos = []
        for pb in (10, 20, 30):  # IP A: 3 abertos
            eventos.append(_ev("10:00:00", "create", origem="100.64.0.2", pblock=pb))
        for pb in (40, 50, 60, 70, 80):  # IP B: 5 abertos
            eventos.append(_ev("10:00:00", "create", origem="100.64.0.3", pblock=pb))

        resp = _service(eventos).detectar_anomalias(
            FlowQuery(data=date(2026, 7, 15)), limiar=2
        )
        assert [i.origem for i in resp.itens] == ["100.64.0.3", "100.64.0.2"]
        assert resp.limiar == 2
