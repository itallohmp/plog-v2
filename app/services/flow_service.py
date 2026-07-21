from math import ceil
from typing import Any, Dict, List

from app.parsers.nat_session import Sessao, correlacionar, formatar_duracao
from app.parsers.pcap_parser import normalize_pcap_event, pcap_event_matches
from app.repositories.flow_repository import FlowNotFoundError, FlowRepository
from app.schemas.flow import FlowQuery, FlowResponse, FlowSession

_PROTOCOLOS_NOMEADOS = {"ICMP", "TCP", "UDP"}


def _protocolo_da_sessao(sessao: Sessao, base_protocolo: str) -> str:
    """Prefere um protocolo nomeado entre create e delete.

    Em alocacao de bloco o create pode vir com proto 0/ausente; se o delete
    tiver um protocolo valido, usa o dele.
    """
    if base_protocolo in _PROTOCOLOS_NOMEADOS:
        return base_protocolo
    for evento in (sessao.evento_create, sessao.evento_delete):
        if evento is None:
            continue
        candidato = normalize_pcap_event(evento)["protocolo"]
        if candidato in _PROTOCOLOS_NOMEADOS:
            return candidato
    return base_protocolo


def _montar_sessao(sessao: Sessao) -> FlowSession:
    """Converte uma Sessao correlacionada no registro exibido (FlowSession)."""
    base = normalize_pcap_event(sessao.ancora)
    abertura = sessao.abertura.isoformat() if sessao.abertura else None
    fechamento = sessao.fechamento.isoformat() if sessao.fechamento else None

    return FlowSession(
        data=base["data"],
        evento=base["evento"],
        protocolo=_protocolo_da_sessao(sessao, base["protocolo"]),
        origem=base["origem"],
        nat=base["nat"],
        porta_origem=base["porta_origem"],
        porta_destino=base["porta_destino"],
        bloco_portas=base["bloco_portas"],
        destino=base["destino"],
        destino_final=base["destino_final"],
        roteador=base["roteador"],
        status=sessao.status,
        abertura=abertura,
        fechamento=fechamento,
        duracao=formatar_duracao(sessao.duracao_segundos),
        duracao_segundos=sessao.duracao_segundos,
        parcial=sessao.parcial,
        eventos=sessao.eventos,
    )


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

        # Correlaciona ANTES de paginar: create e delete de uma mesma sessao
        # precisam estar juntos, o que nao aconteceria se fatiassemos primeiro.
        resultado = correlacionar(filtrados)
        sessoes = resultado.sessoes

        total = len(sessoes)
        total_paginas = max(1, ceil(total / query.tamanho_pagina)) if total else 1

        inicio = (query.pagina - 1) * query.tamanho_pagina
        fim = inicio + query.tamanho_pagina
        registros = [_montar_sessao(s) for s in sessoes[inicio:fim]]

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
