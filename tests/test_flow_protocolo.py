"""Testes do filtro por protocolo (TCP / UDP / ICMP).

Derivados de .specs/features/filtro-protocolo/spec.md (PROTO-01..09).
Cada assert codifica o comportamento que a spec exige, nao o que o codigo faz.
"""

from typing import Any, Dict

from app.parsers.pcap_parser import PROTOCOLO_NUMEROS, pcap_event_matches

TCP, UDP, ICMP, GRE = 6, 17, 1, 47


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
