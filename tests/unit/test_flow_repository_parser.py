import pytest

from app.repositories.flow_repository import FlowQueryError, FlowRepository


class TestParseNfdumpJson:
    def test_lista_json(self):
        payload = '[{"src4_addr": "1.1.1.1"}, {"src4_addr": "2.2.2.2"}]'
        resultado = FlowRepository._parse_nfdump_json(payload)

        assert len(resultado) == 2
        assert resultado[0]["src4_addr"] == "1.1.1.1"

    def test_objeto_com_chave_records(self):
        payload = '{"records": [{"src4_addr": "1.1.1.1"}]}'
        resultado = FlowRepository._parse_nfdump_json(payload)

        assert len(resultado) == 1

    def test_ndjson(self):
        payload = '{"src4_addr": "1.1.1.1"}\n{"src4_addr": "2.2.2.2"}'
        resultado = FlowRepository._parse_nfdump_json(payload)

        assert len(resultado) == 2

    def test_payload_vazio(self):
        assert FlowRepository._parse_nfdump_json("") == []
        assert FlowRepository._parse_nfdump_json("   ") == []

    def test_ndjson_invalido_levanta_erro(self):
        with pytest.raises(FlowQueryError, match="Saida do nfdump invalida"):
            FlowRepository._parse_nfdump_json('{"ok": true}\nnao-e-json')
