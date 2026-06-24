from datetime import date

import pytest
from app.parsers.pcap_parser import normalize_pcap_event, pcap_event_matches
from app.schemas.flow import FlowQuery
from pydantic import ValidationError


class TestNormalizePcapEvent:
    def test_normaliza_evento_udp(self, sample_events):
        normalizado = normalize_pcap_event(sample_events[0])

        assert normalizado["protocolo"] == "UDP"
        assert normalizado["origem"] == "100.64.11.204"
        assert normalizado["destino"] == "8.8.8.8"
        assert normalizado["porta_origem"] == 54321
        assert normalizado["porta_destino"] == 53
        assert normalizado["roteador"] == "10.0.0.1"

    def test_normaliza_evento_com_nat(self, sample_events):
        normalizado = normalize_pcap_event(sample_events[1])

        assert normalizado["protocolo"] == "TCP"
        assert normalizado["nat"] == "203.0.113.50"
        assert normalizado["origem"] == "192.168.1.10"

    def test_normaliza_bloco_portas(self, sample_events):
        normalizado = normalize_pcap_event(sample_events[2])

        assert normalizado["bloco_portas"] == "10000-10010"


class TestPcapEventMatches:
    def test_filtra_por_ip_origem(self, sample_events):
        assert pcap_event_matches(sample_events[0], ip="100.64.11.204") is True
        assert pcap_event_matches(sample_events[0], ip="8.8.8.8") is True
        assert pcap_event_matches(sample_events[0], ip="1.2.3.4") is False

    def test_filtra_por_ip_nat(self, sample_events):
        assert pcap_event_matches(sample_events[1], ip="203.0.113.50") is True

    def test_filtra_por_data(self, sample_events):
        assert pcap_event_matches(sample_events[0], data="2026-06-14") is True
        assert pcap_event_matches(sample_events[0], data="2026-06-15") is False

    def test_filtra_por_porta_direta(self, sample_events):
        assert pcap_event_matches(sample_events[0], porta="53") is True
        assert pcap_event_matches(sample_events[0], porta="54321") is True
        assert pcap_event_matches(sample_events[0], porta="9999") is False

    def test_filtra_por_bloco_portas(self, sample_events):
        assert pcap_event_matches(sample_events[2], porta="10005") is True
        assert pcap_event_matches(sample_events[2], porta="10011") is False


class TestFlowQuery:
    def test_horas_padrao_cobre_dia_inteiro(self):
        query = FlowQuery(data=date(2026, 6, 14))
        assert query.horas() == list(range(24))

    def test_horas_intervalo_simples(self):
        query = FlowQuery(data=date(2026, 6, 14), hora_de=8, hora_ate=10)
        assert query.horas() == [8, 9, 10]

    def test_horas_intervalo_cruza_meia_noite(self):
        query = FlowQuery(data=date(2026, 6, 14), hora_de=22, hora_ate=2)
        assert query.horas() == [22, 23, 0, 1, 2]

    def test_ip_invalido_rejeitado(self):
        with pytest.raises(ValidationError):
            FlowQuery(data=date(2026, 6, 14), ip="nao-e-ip")

    def test_ip_vazio_aceito(self):
        query = FlowQuery(data=date(2026, 6, 14), ip="")
        assert query.ip is None
