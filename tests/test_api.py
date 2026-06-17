from app.repositories.flow_repository import FlowNotFoundError, FlowQueryError


class TestHealthEndpoint:
    def test_health_retorna_ok(self, client):
        resposta = client.get("/api/health")

        assert resposta.status_code == 200
        assert resposta.json() == {"status": "ok"}


class TestFlowsEndpoint:
    def test_lista_flows_com_sucesso(self, client):
        resposta = client.get("/api/flows", params={"data": "2026-06-14"})

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["total"] == 2
        assert corpo["data"] == "2026-06-14"
        assert len(corpo["registros"]) == 2

    def test_filtra_por_ip(self, client):
        resposta = client.get(
            "/api/flows",
            params={"data": "2026-06-14", "ip": "100.64.11.204"},
        )

        assert resposta.status_code == 200
        assert resposta.json()["total"] == 1

    def test_data_obrigatoria(self, client):
        resposta = client.get("/api/flows")

        assert resposta.status_code == 422

    def test_ip_invalido(self, client):
        resposta = client.get(
            "/api/flows",
            params={"data": "2026-06-14", "ip": "invalido"},
        )

        assert resposta.status_code == 422
        assert resposta.json()["erro"] == "Parametros invalidos"

    def test_nao_encontrado(self, client, mock_repository):
        mock_repository.fetch_raw_flows.side_effect = FlowNotFoundError(
            "Diretorio nao encontrado"
        )

        resposta = client.get("/api/flows", params={"data": "2026-06-14"})

        assert resposta.status_code == 404
        assert "nao encontrado" in resposta.json()["erro"].lower()

    def test_falha_consulta(self, client, mock_repository):
        mock_repository.fetch_raw_flows.side_effect = FlowQueryError("SSH indisponivel")

        resposta = client.get("/api/flows", params={"data": "2026-06-14"})

        assert resposta.status_code == 502
        corpo = resposta.json()
        assert corpo["erro"] == "Falha ao consultar flows"
        assert "SSH indisponivel" in corpo["detalhes"]

    def test_paginacao(self, client):
        resposta = client.get(
            "/api/flows",
            params={"data": "2026-06-14", "pagina": 2, "tamanho_pagina": 1},
        )

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["pagina"] == 2
        assert len(corpo["registros"]) == 1
