from datetime import date, timedelta
from ipaddress import ip_address
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_DIAS_INTERVALO = 31


class FlowQuery(BaseModel):
    """Parametros de consulta validados para a busca de flows."""

    model_config = ConfigDict(extra="ignore")

    data: date
    data_fim: Optional[date] = None
    ip: Optional[str] = None
    porta: Optional[int] = Field(default=None, ge=0, le=65535)
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


class FlowResponse(BaseModel):
    """Resposta paginada da consulta de flows."""

    data: str
    total: int
    pagina: int
    total_paginas: int
    registros: List[FlowRecord]
