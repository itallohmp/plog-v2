"""Testes do filtro por protocolo (TCP / UDP / ICMP).

Derivados de .specs/features/filtro-protocolo/spec.md (PROTO-01..09).
Cada assert codifica o comportamento que a spec exige, nao o que o codigo faz.
"""

from datetime import date
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.parsers.pcap_parser import PROTOCOLO_NUMEROS, pcap_event_matches
from app.repositories.flow_repository import FlowRepository
from app.schemas.flow import FlowQuery
from app.services.flow_service import FlowService

TCP, UDP, ICMP, GRE = 6, 17, 1, 47
DIA = date(2026, 7, 15)


def _evento(proto: Any) -> Dict[str, Any]:
    """Evento minimo com o campo proto informado."""
    return {"t_first": "2026-07-15T18:48:41.045", "src4_addr": "100.64.18.210", "proto": proto}


class TestProtocoloMatcher:
    def test_mapa_reverso_dos_tres_protocolos(self):
        """PROTO-01: nomes mapeiam para os numeros IANA corretos."""
        assert PROTOCOLO_NUMEROS == {"icmp": 1, "tcp": 6, "udp": 17}

    def test_filtra_somente_tcp(self):
        """PROTO-01 (AC1): protocolo=tcp retorna somente proto 6."""
        assert pcap_event_matches(_evento(TCP), protocolos={TCP}) is True
        assert pcap_event_matches(_evento(UDP), protocolos={TCP}) is False
        assert pcap_event_matches(_evento(ICMP), protocolos={TCP}) is False

    def test_filtra_somente_udp(self):
        """PROTO-01 (AC2): protocolo=udp retorna somente proto 17."""
        assert pcap_event_matches(_evento(UDP), protocolos={UDP}) is True
        assert pcap_event_matches(_evento(TCP), protocolos={UDP}) is False

    def test_filtra_somente_icmp(self):
        """PROTO-01 (AC3): protocolo=icmp retorna somente proto 1."""
        assert pcap_event_matches(_evento(ICMP), protocolos={ICMP}) is True
        assert pcap_event_matches(_evento(TCP), protocolos={ICMP}) is False

    def test_uniao_multi_protocolo(self):
        """PROTO-02 (AC4): dois protocolos retornam a uniao e excluem os demais."""
        selecao = {TCP, UDP}
        assert pcap_event_matches(_evento(TCP), protocolos=selecao) is True
        assert pcap_event_matches(_evento(UDP), protocolos=selecao) is True
        assert pcap_event_matches(_evento(ICMP), protocolos=selecao) is False

    def test_sem_filtro_aceita_todos(self):
        """PROTO-03 (AC5): None ou conjunto vazio nao aplica filtro de protocolo."""
        for proto in (TCP, UDP, ICMP, GRE):
            assert pcap_event_matches(_evento(proto), protocolos=None) is True
            assert pcap_event_matches(_evento(proto), protocolos=set()) is True

    def test_protocolo_fora_do_conjunto_excluido(self):
        """PROTO-04 (AC6): proto fora da selecao (ex.: 47/GRE) e excluido."""
        assert pcap_event_matches(_evento(GRE), protocolos={TCP, UDP, ICMP}) is False

    def test_todos_os_tres_nao_equivale_a_sem_filtro(self):
        """Edge: selecionar os tres ainda exclui outros protocolos."""
        todos = set(PROTOCOLO_NUMEROS.values())
        assert pcap_event_matches(_evento(GRE), protocolos=todos) is False
        assert pcap_event_matches(_evento(GRE), protocolos=None) is True

    def test_evento_sem_proto_excluido(self):
        """Edge: evento sem a chave proto e excluido quando o filtro esta ativo."""
        evento = {"t_first": "2026-07-15T18:48:41.045", "src4_addr": "100.64.18.210"}
        assert pcap_event_matches(evento, protocolos={TCP}) is False
        assert pcap_event_matches(evento, protocolos=None) is True

    def test_evento_com_proto_nao_numerico_excluido(self):
        """Edge: proto nao numerico e excluido quando o filtro esta ativo."""
        assert pcap_event_matches(_evento("abc"), protocolos={TCP}) is False

    def test_compoe_com_filtro_de_ip(self):
        """PROTO-07 (AC9): protocolo compoe por AND com os demais filtros."""
        evento = _evento(TCP)
        assert pcap_event_matches(evento, ip="100.64.18.210", protocolos={TCP}) is True
        # protocolo casa, IP nao -> excluido
        assert pcap_event_matches(evento, ip="10.0.0.1", protocolos={TCP}) is False
        # IP casa, protocolo nao -> excluido
        assert pcap_event_matches(evento, ip="100.64.18.210", protocolos={UDP}) is False


class TestProtocoloSchema:
    def test_converte_nomes_para_numeros(self):
        """PROTO-01/02: nomes selecionados viram o conjunto numerico correspondente."""
        assert FlowQuery(data=DIA, protocolo=["tcp"]).protocolos_numericos() == {TCP}
        assert FlowQuery(data=DIA, protocolo=["tcp", "udp"]).protocolos_numericos() == {
            TCP,
            UDP,
        }
        assert FlowQuery(data=DIA, protocolo=["icmp"]).protocolos_numericos() == {ICMP}

    def test_case_insensitive(self):
        """PROTO-05 (AC7): capitalizacao nao altera o resultado."""
        assert FlowQuery(data=DIA, protocolo=["TCP"]).protocolos_numericos() == {TCP}
        assert FlowQuery(data=DIA, protocolo=["Udp"]).protocolos_numericos() == {UDP}
        assert FlowQuery(data=DIA, protocolo=["iCmP"]).protocolos_numericos() == {ICMP}

    def test_ausente_ou_vazio_sem_filtro(self):
        """PROTO-03 (AC5): None ou lista vazia desliga o filtro."""
        assert FlowQuery(data=DIA).protocolos_numericos() is None
        assert FlowQuery(data=DIA, protocolo=[]).protocolos_numericos() is None

    def test_deduplica_valores_repetidos(self):
        """Edge: valor repetido equivale a uma unica selecao."""
        assert FlowQuery(data=DIA, protocolo=["tcp", "tcp"]).protocolos_numericos() == {
            TCP
        }
        assert FlowQuery(data=DIA, protocolo=["tcp", "TCP"]).protocolos_numericos() == {
            TCP
        }

    def test_protocolo_invalido_rejeitado(self):
        """PROTO-06 (AC8): valor fora de TCP/UDP/ICMP e rejeitado na borda."""
        with pytest.raises(ValidationError):
            FlowQuery(data=DIA, protocolo=["foo"])

    def test_protocolo_numerico_rejeitado(self):
        """PROTO-06: a API aceita apenas os nomes, nao o numero do protocolo."""
        with pytest.raises(ValidationError):
            FlowQuery(data=DIA, protocolo=["6"])


def _service(eventos):
    """FlowService cujo repositorio devolve sempre os eventos informados."""
    repo = MagicMock(spec=FlowRepository)
    repo.fetch_raw_flows.return_value = eventos
    return FlowService(repo)


class TestProtocoloService:
    """Filtro de ponta a ponta: do FlowQuery ate os registros retornados."""

    EVENTOS = [_evento(TCP), _evento(UDP), _evento(ICMP), _evento(GRE)]

    def test_um_protocolo_filtra_resultado(self):
        """PROTO-01: buscar com um protocolo retorna somente aquele protocolo."""
        svc = _service(self.EVENTOS)

        resp = svc.buscar_flows(FlowQuery(data=DIA, protocolo=["tcp"]))

        assert resp.total == 1
        assert [r.protocolo for r in resp.registros] == ["TCP"]

    def test_multi_protocolo_retorna_uniao(self):
        """PROTO-02: dois protocolos retornam a uniao e excluem os demais."""
        svc = _service(self.EVENTOS)

        resp = svc.buscar_flows(FlowQuery(data=DIA, protocolo=["tcp", "udp"]))

        assert resp.total == 2
        assert sorted(r.protocolo for r in resp.registros) == ["TCP", "UDP"]

    def test_sem_protocolo_retorna_todos(self):
        """PROTO-03: sem o filtro, todos os protocolos (inclusive GRE) retornam."""
        svc = _service(self.EVENTOS)

        resp = svc.buscar_flows(FlowQuery(data=DIA))

        assert resp.total == 4
        assert sorted(r.protocolo for r in resp.registros) == ["47", "ICMP", "TCP", "UDP"]

    def test_compoe_com_ip(self):
        """PROTO-07: protocolo e IP sao aplicados por conjuncao (AND)."""
        outro_ip = dict(_evento(TCP), src4_addr="10.0.0.1")
        svc = _service([_evento(TCP), outro_ip, _evento(UDP)])

        resp = svc.buscar_flows(
            FlowQuery(data=DIA, ip="100.64.18.210", protocolo=["tcp"])
        )

        assert resp.total == 1
        assert resp.registros[0].protocolo == "TCP"
        assert resp.registros[0].origem == "100.64.18.210"
