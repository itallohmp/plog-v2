from datetime import date

from app.repositories.flow_repository import FlowNotFoundError, FlowQueryError
from app.schemas.flow import FlowQuery


class TestFlowService:
    def test_retorna_todos_os_registros(self, flow_service, mock_repository):
        query = FlowQuery(data=date(2026, 6, 14))
        resposta = flow_service.buscar_flows(query)

        assert resposta.total == 2
        assert len(resposta.registros) == 2
        assert resposta.data == "2026-06-14"
        mock_repository.fetch_raw_flows.assert_called_once_with(
            date(2026, 6, 14), list(range(24))
        )

    def test_filtra_por_ip(self, flow_service):
        query = FlowQuery(data=date(2026, 6, 14), ip="100.64.11.204")
        resposta = flow_service.buscar_flows(query)

        assert resposta.total == 1
        assert resposta.registros[0].origem == "100.64.11.204"

    def test_filtra_por_data(self, flow_service):
        query = FlowQuery(data=date(2026, 6, 15))
        resposta = flow_service.buscar_flows(query)

        assert resposta.total == 1
        assert resposta.registros[0].origem == "10.10.10.100"

    def test_paginacao(self, flow_service):
        query = FlowQuery(data=date(2026, 6, 14), pagina=2, tamanho_pagina=1)
        resposta = flow_service.buscar_flows(query)

        assert resposta.total == 2
        assert resposta.pagina == 2
        assert resposta.total_paginas == 2
        assert len(resposta.registros) == 1

    def test_sem_resultados_mantem_total_paginas(self, flow_service):
        query = FlowQuery(data=date(2026, 6, 14), ip="0.0.0.0")
        resposta = flow_service.buscar_flows(query)

        assert resposta.total == 0
        assert resposta.total_paginas == 1
        assert resposta.registros == []

    def test_resumo_agrega_o_filtro(self, flow_service):
        query = FlowQuery(data=date(2026, 6, 14))
        resposta = flow_service.buscar_flows(query)

        resumo = resposta.resumo
        assert resumo is not None
        assert resumo.total == 2
        assert resumo.indefinidas == 2
        assert resumo.abertas == 0
        assert resumo.fechadas == 0
        # Eventos avulsos (indefinidos) nao tem duracao.
        assert resumo.duracao_media is None
        assert resumo.duracao_media_segundos is None
        assert resumo.por_protocolo == {"UDP": 1, "TCP": 1}

    def test_resumo_cobre_alem_da_pagina(self, flow_service):
        # O ponto da feature: o resumo reflete TODAS as sessoes do filtro,
        # mesmo quando a pagina exibe apenas uma.
        query = FlowQuery(data=date(2026, 6, 14), pagina=1, tamanho_pagina=1)
        resposta = flow_service.buscar_flows(query)

        assert len(resposta.registros) == 1
        assert resposta.resumo.total == 2

    def test_resumo_respeita_filtro_de_estado(self, flow_service):
        query = FlowQuery(data=date(2026, 6, 14), status=["aberta"])
        resposta = flow_service.buscar_flows(query)

        # Nenhuma sessao aberta nas fixtures -> resumo zerado, coerente com a
        # tabela filtrada.
        assert resposta.resumo.total == 0
        assert resposta.resumo.por_protocolo == {}

    def test_sem_resultados_resumo_zerado(self, flow_service):
        query = FlowQuery(data=date(2026, 6, 14), ip="0.0.0.0")
        resposta = flow_service.buscar_flows(query)

        assert resposta.resumo is not None
        assert resposta.resumo.total == 0

    def test_propaga_erro_do_repository(self, flow_service, mock_repository):
        mock_repository.fetch_raw_flows.side_effect = FlowNotFoundError(
            "nao encontrado"
        )

        query = FlowQuery(data=date(2026, 6, 14))

        try:
            flow_service.buscar_flows(query)
            raise AssertionError("esperava FlowNotFoundError")
        except FlowNotFoundError as exc:
            assert str(exc) == "nao encontrado"

    def test_propaga_erro_de_consulta(self, flow_service, mock_repository):
        mock_repository.fetch_raw_flows.side_effect = FlowQueryError("falha ssh")

        query = FlowQuery(data=date(2026, 6, 14))

        try:
            flow_service.buscar_flows(query)
            raise AssertionError("esperava FlowQueryError")
        except FlowQueryError as exc:
            assert str(exc) == "falha ssh"
