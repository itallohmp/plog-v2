from collections import defaultdict
from datetime import date, datetime, timedelta
from math import ceil
from typing import Any, Dict, List

from app.core import config
from app.parsers.nat_session import (
    CorrelacaoResultado,
    Sessao,
    chave_sessao,
    classificar_evento,
    correlacionar,
    formatar_duracao,
    timestamp_evento,
)
from app.parsers.pcap_parser import normalize_pcap_event, pcap_event_matches
from app.repositories.flow_repository import (
    FlowNotFoundError,
    FlowQueryError,
    FlowRepository,
)
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
        verificado_ate=sessao.verificado_ate,
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
        self._resolver_pendentes(resultado, dias[-1])

        # Filtro por estado APOS a resolucao: uma pendente fechada pelo
        # lookahead ja conta como "fechada" aqui.
        sessoes = resultado.sessoes
        estados = query.estados_filtro()
        if estados is not None:
            sessoes = [s for s in sessoes if s.status in estados]

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

    def _resolver_pendentes(
        self, resultado: CorrelacaoResultado, ultimo_dia: date
    ) -> None:
        """Verifica, alem da janela, se as sessoes abertas ja fecharam.

        Consulta o nfdump filtrado pelas chaves pendentes no range (dia seguinte
        -> hoje). As que casarem um delete viram fechadas; as demais ficam
        abertas com verificado_ate = hoje. Desligavel por PLOG_NAT_LOOKAHEAD.
        """
        pendentes = resultado.pendentes
        if not pendentes or not config.NAT_LOOKAHEAD_ATIVO:
            return

        hoje = date.today()
        inicio = ultimo_dia + timedelta(days=1)
        # A janela consultada ja foi verificada ate o seu ultimo dia.
        verificado_ate = ultimo_dia

        if inicio <= hoje:
            max_dias = max(1, config.NAT_LOOKAHEAD_MAX_DIAS)
            fim = min(hoje, inicio + timedelta(days=max_dias - 1))

            chaves: List = []
            vistas = set()
            for sessao in pendentes:
                if sessao.chave not in vistas:
                    vistas.add(sessao.chave)
                    chaves.append(sessao.chave)
                if len(chaves) >= config.NAT_LOOKAHEAD_MAX_CHAVES:
                    break
            try:
                extras = self.repository.fetch_flows_por_chave(chaves, inicio, fim)
            except (FlowNotFoundError, FlowQueryError):
                # Falha no lookahead nunca derruba a consulta principal: as
                # sessoes apenas permanecem abertas ate o dia ja verificado.
                extras = []
            self._fechar_com_extras(pendentes, extras)
            verificado_ate = fim

        rotulo = verificado_ate.isoformat()
        for sessao in pendentes:
            if sessao.status == "aberta":
                sessao.verificado_ate = rotulo

    @staticmethod
    def _fechar_com_extras(
        pendentes: List[Sessao], extras: List[Dict[str, Any]]
    ) -> None:
        por_chave: Dict[Any, List[Sessao]] = defaultdict(list)
        for sessao in pendentes:
            por_chave[sessao.chave].append(sessao)

        deletes = []
        for evento in extras:
            if classificar_evento(evento) != "delete":
                continue
            chave = chave_sessao(evento)
            ts = timestamp_evento(evento)
            if ts is not None and chave in por_chave:
                deletes.append((ts, chave, evento))

        # Processa em ordem cronologica para casar cada delete com a sessao certa.
        deletes.sort(key=lambda d: d[0])
        for ts, chave, evento in deletes:
            candidatas = [
                s
                for s in por_chave[chave]
                if s.status == "aberta" and (s.abertura is None or s.abertura <= ts)
            ]
            if not candidatas:
                continue
            # LIFO, coerente com correlacionar: fecha a de abertura mais recente.
            alvo = max(candidatas, key=lambda s: s.abertura or datetime.min)
            alvo.fechar(ts, evento)
