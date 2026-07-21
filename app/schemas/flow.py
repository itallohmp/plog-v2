from datetime import date, timedelta
from ipaddress import ip_address
from typing import Dict, List, Optional, Set

from app.parsers.pcap_parser import PROTOCOLO_NUMEROS
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_DIAS_INTERVALO = 31

# Estados possiveis de uma sessao NAT (ver app/parsers/nat_session.py).
ESTADOS_SESSAO = frozenset({"aberta", "fechada", "indefinida"})


class FlowQuery(BaseModel):
    """Parametros de consulta validados para a busca de flows."""

    model_config = ConfigDict(extra="ignore")

    data: date
    data_fim: Optional[date] = None
    ip: Optional[str] = None
    porta: Optional[int] = Field(default=None, ge=0, le=65535)
    protocolo: Optional[List[str]] = None
    status: Optional[List[str]] = None
    hora_de: Optional[int] = Field(default=None, ge=0, le=23)
    hora_ate: Optional[int] = Field(default=None, ge=0, le=23)
    pagina: int = Field(default=1, ge=1)
    tamanho_pagina: int = Field(default=100, ge=1, le=1000)

    @field_validator("ip")
    @classmethod
    def _validar_ip(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None or valor == "":
            return None
        try:
            ip_address(valor)
        except ValueError as exc:
            raise ValueError("IP invalido") from exc
        return valor

    @field_validator("protocolo")
    @classmethod
    def _validar_protocolo(cls, valor: Optional[List[str]]) -> Optional[List[str]]:
        if not valor:
            return None

        normalizados: List[str] = []
        for item in valor:
            nome = str(item).strip().lower()
            if nome not in PROTOCOLO_NUMEROS:
                validos = ", ".join(sorted(PROTOCOLO_NUMEROS))
                raise ValueError(f"Protocolo invalido: use um de {validos}")
            if nome not in normalizados:
                normalizados.append(nome)
        return normalizados

    @field_validator("status")
    @classmethod
    def _validar_status(cls, valor: Optional[List[str]]) -> Optional[List[str]]:
        if not valor:
            return None

        normalizados: List[str] = []
        for item in valor:
            estado = str(item).strip().lower()
            if estado not in ESTADOS_SESSAO:
                validos = ", ".join(sorted(ESTADOS_SESSAO))
                raise ValueError(f"Estado invalido: use um de {validos}")
            if estado not in normalizados:
                normalizados.append(estado)
        return normalizados

    @model_validator(mode="after")
    def _validar_intervalo_datas(self) -> "FlowQuery":
        if self.data_fim is None:
            return self
        if self.data_fim < self.data:
            raise ValueError("Data final deve ser maior ou igual a data inicial")
        if (self.data_fim - self.data).days + 1 > MAX_DIAS_INTERVALO:
            raise ValueError(
                f"Intervalo maximo de {MAX_DIAS_INTERVALO} dias por consulta"
            )
        return self

    def dias(self) -> List[date]:
        fim = self.data_fim or self.data
        total = (fim - self.data).days + 1
        return [self.data + timedelta(days=i) for i in range(total)]

    def protocolos_numericos(self) -> Optional[Set[int]]:
        """Numeros IANA dos protocolos selecionados, ou None quando sem filtro."""
        if not self.protocolo:
            return None
        return {PROTOCOLO_NUMEROS[nome] for nome in self.protocolo}

    def estados_filtro(self) -> Optional[Set[str]]:
        """Estados de sessao selecionados, ou None quando sem filtro."""
        if not self.status:
            return None
        return set(self.status)

    def horas(self) -> List[int]:
        if self.hora_de is None and self.hora_ate is None:
            return list(range(24))

        inicio = self.hora_de if self.hora_de is not None else 0
        fim = self.hora_ate if self.hora_ate is not None else 23

        if inicio <= fim:
            return list(range(inicio, fim + 1))
        return list(range(inicio, 24)) + list(range(0, fim + 1))


class FlowRecord(BaseModel):
    """Registro de flow normalizado para exibicao no frontend."""

    model_config = ConfigDict(extra="ignore")

    data: Optional[str] = None
    evento: Optional[str] = None
    protocolo: Optional[str] = None
    origem: Optional[str] = None
    nat: Optional[str] = None
    porta_origem: Optional[str] = None
    porta_destino: Optional[str] = None
    bloco_portas: Optional[str] = None
    destino: Optional[str] = None
    destino_final: Optional[str] = None
    roteador: Optional[str] = None

    @field_validator("*", mode="before")
    @classmethod
    def _coercao_texto(cls, valor):
        if valor is None:
            return None
        return str(valor)


class FlowSession(BaseModel):
    """Sessao NAT correlacionada (superset de FlowRecord).

    Mantem os mesmos campos de exibicao de FlowRecord, com a mesma semantica
    (preenchidos a partir do evento ancora), e acrescenta o estado da sessao.
    """

    model_config = ConfigDict(extra="ignore")

    # --- compatibilidade com FlowRecord (mesma semantica de exibicao) ---
    data: Optional[str] = None
    evento: Optional[str] = None
    protocolo: Optional[str] = None
    origem: Optional[str] = None
    nat: Optional[str] = None
    porta_origem: Optional[str] = None
    porta_destino: Optional[str] = None
    bloco_portas: Optional[str] = None
    destino: Optional[str] = None
    destino_final: Optional[str] = None
    roteador: Optional[str] = None

    # --- estado da sessao ---
    status: str = "indefinida"  # aberta | fechada | indefinida
    abertura: Optional[str] = None
    fechamento: Optional[str] = None
    duracao: Optional[str] = None
    duracao_segundos: Optional[float] = None
    verificado_ate: Optional[str] = None  # so quando status == "aberta"
    parcial: bool = False  # delete orfao (create fora da janela)
    eventos: int = 1

    @field_validator(
        "data",
        "evento",
        "protocolo",
        "origem",
        "nat",
        "porta_origem",
        "porta_destino",
        "bloco_portas",
        "destino",
        "destino_final",
        "roteador",
        "abertura",
        "fechamento",
        "duracao",
        "verificado_ate",
        mode="before",
    )
    @classmethod
    def _coercao_texto(cls, valor):
        if valor is None:
            return None
        return str(valor)


class FlowResumo(BaseModel):
    """Agregado das sessoes que casam o filtro inteiro (nao apenas a pagina).

    Calculado sobre todas as sessoes correlacionadas, depois do filtro por
    estado. Permite ao painel refletir o conjunto completo, e nao so a pagina
    carregada na tabela.
    """

    total: int = 0
    abertas: int = 0
    fechadas: int = 0
    indefinidas: int = 0
    parciais: int = 0
    duracao_media_segundos: Optional[float] = None
    duracao_media: Optional[str] = None
    por_protocolo: Dict[str, int] = Field(default_factory=dict)


class FlowResponse(BaseModel):
    """Resposta paginada da consulta de flows."""

    data: str
    total: int
    pagina: int
    total_paginas: int
    registros: List[FlowSession]
    resumo: Optional[FlowResumo] = None
    # Ranking compacto de IPs com muitos blocos ativos, para o dashboard.
    anomalias: Optional["AnomaliaResponse"] = None


class AnomaliaProtocolo(BaseModel):
    """Blocos de um protocolo para um IP: abertos agora e pico simultaneo."""

    abertas: int = 0
    pico: int = 0


class AnomaliaIP(BaseModel):
    """Um IP local e sua contagem de blocos, por protocolo e no total.

    `abertas` = blocos sem fechamento (ainda em uso). `pico` = maximo de blocos
    que estiveram ativos ao mesmo tempo na janela (concorrencia real).
    """

    origem: str
    nat: Optional[str] = None
    roteador: Optional[str] = None
    tcp: AnomaliaProtocolo = Field(default_factory=AnomaliaProtocolo)
    udp: AnomaliaProtocolo = Field(default_factory=AnomaliaProtocolo)
    icmp: AnomaliaProtocolo = Field(default_factory=AnomaliaProtocolo)
    total_abertas: int = 0
    total_pico: int = 0


class AnomaliaResponse(BaseModel):
    """Ranking de IPs locais com blocos ativos acima do limiar."""

    data: str
    limiar: int
    total_ips: int
    itens: List[AnomaliaIP]


class SeriePonto(BaseModel):
    """Um ponto da curva de concorrencia: blocos ativos ao mesmo tempo em `t`.

    Cada ponto e um instante em que a contagem mudou (abertura ou fechamento de
    bloco). Entre dois pontos o valor e constante — a serie e uma funcao degrau.
    `total` e a soma dos tres protocolos no instante.
    """

    t: str  # ISO do instante da mudanca
    total: int = 0
    tcp: int = 0
    udp: int = 0
    icmp: int = 0


class SeriePico(BaseModel):
    """Maximo da serie e o instante em que ocorreu (para marcar no grafico)."""

    total: int = 0
    instante: Optional[str] = None


class SerieResponse(BaseModel):
    """Serie temporal da alocacao de blocos de um IP local, para o modal de picos.

    `pontos` e a curva de concorrencia (funcao degrau) na janela consultada; seu
    maximo (`pico.total`) coincide com o `total_pico` do ranking. `truncada`
    sinaliza que a serie foi reamostrada por ter pontos demais (picos preservados).
    """

    ip: str
    data: str
    inicio: Optional[str] = None
    fim: Optional[str] = None
    limiar: int
    pico: SeriePico = Field(default_factory=SeriePico)
    pontos: List[SeriePonto] = Field(default_factory=list)
    truncada: bool = False


# FlowResponse referencia AnomaliaResponse (definido depois): resolve o forward.
FlowResponse.model_rebuild()
