from app.parsers.flow_parser import parse_flow_event, parse_flows


class TestFlowParser:
    def test_parse_flow_event_valida_campos(self, sample_events):
        registro = parse_flow_event(sample_events[0])

        assert registro.protocolo == "UDP"
        assert registro.origem == "100.64.11.204"
        assert registro.destino == "8.8.8.8"
        assert registro.porta_destino == "53"

    def test_parse_flows_retorna_lista(self, sample_events):
        registros = parse_flows(sample_events)

        assert len(registros) == 3
        assert all(registro.protocolo for registro in registros)

    def test_parse_flow_event_nao_inclui_raw(self, sample_events):
        registro = parse_flow_event(sample_events[0])

        assert not hasattr(registro, "_raw")
