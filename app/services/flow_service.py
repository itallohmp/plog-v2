from math import ceil

from app.parsers.flow_parser import parse_flows
from app.parsers.pcap_parser import pcap_event_matches
from app.repositories.flow_repository import FlowRepository
from app.schemas.flow import FlowQuery, FlowResponse


class FlowService:
    def __init__(self, repository: FlowRepository):
        self.repository = repository

    def buscar_flows(self, query: FlowQuery) -> FlowResponse:
        data_iso = query.data.isoformat()
        porta = str(query.porta) if query.porta is not None else None

        brutos = self.repository.fetch_raw_flows(query.data, query.horas())

        filtrados = [
            evento
            for evento in brutos
            if pcap_event_matches(evento, ip=query.ip, porta=porta, data=data_iso)
        ]

        total = len(filtrados)
        total_paginas = max(1, ceil(total / query.tamanho_pagina)) if total else 1

        inicio = (query.pagina - 1) * query.tamanho_pagina
        fim = inicio + query.tamanho_pagina
        registros = parse_flows(filtrados[inicio:fim])

        return FlowResponse(
            data=data_iso,
            total=total,
            pagina=query.pagina,
            total_paginas=total_paginas,
            registros=registros,
        )
