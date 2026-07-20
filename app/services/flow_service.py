from math import ceil
from typing import Any, Dict, List

from app.parsers.flow_parser import parse_flows
from app.parsers.pcap_parser import pcap_event_matches
from app.repositories.flow_repository import FlowNotFoundError, FlowRepository
from app.schemas.flow import FlowQuery, FlowResponse


class FlowService:
    def __init__(self, repository: FlowRepository):
        self.repository = repository

    def buscar_flows(self, query: FlowQuery) -> FlowResponse:
        porta = str(query.porta) if query.porta is not None else None
        protocolos = query.protocolos_numericos()
        dias = query.dias()
        horas = query.horas()

        filtrados: List[Dict[str, Any]] = []
        dias_encontrados = 0

        for dia in dias:
            try:
                brutos = self.repository.fetch_raw_flows(dia, horas)
            except FlowNotFoundError:
                # Em consultas por intervalo, dias sem dados sao ignorados;
                # a consulta so falha se nenhum dia tiver dados.
                if len(dias) == 1:
                    raise
                continue

            dias_encontrados += 1
            dia_iso = dia.isoformat()
            filtrados.extend(
                evento
                for evento in brutos
                if pcap_event_matches(
                    evento,
                    ip=query.ip,
                    porta=porta,
                    data=dia_iso,
                    protocolos=protocolos,
                )
            )

        if dias_encontrados == 0:
            raise FlowNotFoundError(
                "Nenhum dado encontrado para o intervalo de datas informado."
            )

        total = len(filtrados)
        total_paginas = max(1, ceil(total / query.tamanho_pagina)) if total else 1

        inicio = (query.pagina - 1) * query.tamanho_pagina
        fim = inicio + query.tamanho_pagina
        registros = parse_flows(filtrados[inicio:fim])

        data_label = query.data.isoformat()
        if query.data_fim and query.data_fim != query.data:
            data_label = f"{data_label} a {query.data_fim.isoformat()}"

        return FlowResponse(
            data=data_label,
            total=total,
            pagina=query.pagina,
            total_paginas=total_paginas,
            registros=registros,
        )
