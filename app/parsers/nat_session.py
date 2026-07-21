"""Correlacao de eventos NAT em sessoes (create + delete -> uma sessao).

Modulo puro, sem I/O. Interpreta o payload cru do nfdump, no mesmo papel de
pcap_parser.py. A correlacao propriamente dita (correlacionar) vem em seguida;
aqui ficam as tres primitivas: classificar o evento, extrair a chave de sessao
e obter o timestamp real.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.parsers.pcap_parser import _as_int, _first_value

# Campos onde o tipo de evento pode aparecer, do mais especifico ao generico.
_CAMPOS_EVENTO = ("nat_event", "event", "type")
# Substrings que caracterizam cada classe (case-insensitive).
_TOKENS_CREATE = ("create", "add", "alloc")
_TOKENS_DELETE = ("delete", "destroy", "free", "release")

ChaveSessao = Tuple[Optional[str], str, str, int, Optional[int]]


def classificar_evento(evento: Dict[str, Any]) -> str:
    """Classifica o evento como 'create', 'delete' ou 'indefinido'.

    Concatena os tres campos de evento (em vez de "primeiro nao vazio") para
    ser imune a ordem: na fixture do projeto `type` == "EVENT" e em producao a
    informacao vem em `nat_event`. Ambiguo (create E delete) -> indefinido.
    """
    texto = " ".join(str(evento.get(campo, "")) for campo in _CAMPOS_EVENTO).lower()
    tem_create = any(token in texto for token in _TOKENS_CREATE)
    tem_delete = any(token in texto for token in _TOKENS_DELETE)

    if tem_create and not tem_delete:
        return "create"
    if tem_delete and not tem_create:
        return "delete"
    return "indefinido"


def chave_sessao(evento: Dict[str, Any]) -> Optional[ChaveSessao]:
    """Identidade da traducao: (roteador, origem, ip_nat, pblock_start, pblock_size).

    Sem `proto` de proposito: em alocacao de bloco CGNAT ele costuma vir 0 ou
    ausente. Retorna None quando falta origem, IP publico ou inicio de bloco —
    nesse caso o evento nao e correlacionavel e vira sessao indefinida.
    """
    origem = _first_value(evento, ("src4_addr", "src6_addr", "src_addr"))
    nat = _first_value(evento, ("src4_xlt_ip", "src_xlt_ip", "xlate_src_ip"))
    roteador = _first_value(evento, ("ip4_router", "router"))
    inicio = _as_int(evento.get("pblock_start"))
    tamanho = _as_int(evento.get("pblock_size"))

    if not origem or not nat or inicio is None:
        return None

    return (roteador or None, origem, nat, inicio, tamanho)


def timestamp_evento(evento: Dict[str, Any]) -> Optional[datetime]:
    """Timestamp do evento como datetime UTC-naive, ou None se ilegivel.

    Parse real (nao comparacao de string): ordenar `t_first` como texto quebra
    em silencio com espaco vs 'T', sufixo 'Z', offset ou epoch — e ordem errada
    aqui atribui trafego ao assinante errado. Evento ilegivel vira None, o que
    o torna indefinido em vez de entrar na ordem no lugar errado.
    """
    bruto = _first_value(evento, ("t_first", "t_event", "t_received", "t_last"))
    if not bruto:
        return None

    texto = bruto.strip().replace(" ", "T")
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"

    dt: Optional[datetime]
    try:
        dt = datetime.fromisoformat(texto)
    except ValueError:
        try:
            dt = datetime.fromtimestamp(float(bruto), tz=timezone.utc)
        except (TypeError, ValueError, OverflowError, OSError):
            return None

    if dt.tzinfo is not None:
        # Normaliza para UTC-naive: evita TypeError ao comparar naive vs aware.
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@dataclass
class Sessao:
    """Uma traducao NAT correlacionada (um ou dois eventos)."""

    chave: Optional[ChaveSessao]
    status: str  # "aberta" | "fechada" | "indefinida"
    ancora: Dict[str, Any]  # evento usado para os campos de exibicao
    abertura: Optional[datetime] = None
    fechamento: Optional[datetime] = None
    parcial: bool = False
    eventos: int = 1
    ordem: int = 0  # indice original do evento ancora, para ordenar a saida
    evento_create: Optional[Dict[str, Any]] = None
    evento_delete: Optional[Dict[str, Any]] = None

    @property
    def duracao_segundos(self) -> Optional[float]:
        if self.abertura is not None and self.fechamento is not None:
            return (self.fechamento - self.abertura).total_seconds()
        return None

    def fechar(self, fechamento: datetime, evento_delete: Dict[str, Any]) -> None:
        self.status = "fechada"
        self.fechamento = fechamento
        self.evento_delete = evento_delete
        self.eventos += 1


@dataclass
class CorrelacaoResultado:
    sessoes: List[Sessao] = field(default_factory=list)
    pendentes: List[Sessao] = field(default_factory=list)


def correlacionar(eventos: List[Dict[str, Any]]) -> CorrelacaoResultado:
    """Agrupa eventos NAT em sessoes, pareando create+delete cronologicamente.

    O pareamento usa uma PILHA por chave (LIFO): cada delete fecha o create mais
    recente ainda aberto daquela chave. Isso e o que impede misturar assinantes
    quando o mesmo bloco e realocado depois do delete — um dict[chave]=create
    faria o delete de um assinante fechar a sessao de outro.

    A saida (`sessoes`) fica ordenada pelo indice original do evento ancora;
    `pendentes` sao as sessoes que ficaram abertas (create sem delete na janela).
    """
    anotados = []
    for indice, evento in enumerate(eventos):
        classe = classificar_evento(evento)
        chave = chave_sessao(evento)
        ts = timestamp_evento(evento)
        pareavel = classe in ("create", "delete") and chave is not None and ts is not None
        anotados.append((indice, evento, classe, chave, ts, pareavel))

    # Ordem cronologica real para o pareamento; desempate estavel pelo indice.
    ordem_cronologica = sorted(anotados, key=lambda a: (a[4] or datetime.min, a[0]))

    sessoes: List[Sessao] = []
    abertas: Dict[ChaveSessao, List[Sessao]] = defaultdict(list)

    for indice, evento, classe, chave, ts, pareavel in ordem_cronologica:
        if not pareavel:
            sessoes.append(
                Sessao(
                    chave=chave,
                    status="indefinida",
                    ancora=evento,
                    abertura=ts,
                    ordem=indice,
                )
            )
            continue

        if classe == "create":
            sessao = Sessao(
                chave=chave,
                status="aberta",
                ancora=evento,
                abertura=ts,
                ordem=indice,
                evento_create=evento,
            )
            abertas[chave].append(sessao)
            sessoes.append(sessao)
        else:  # delete
            pilha = abertas.get(chave)
            if pilha:
                pilha.pop().fechar(ts, evento)
                if not pilha:
                    abertas.pop(chave, None)
            else:
                # Delete orfao: create ocorreu antes da janela consultada.
                sessoes.append(
                    Sessao(
                        chave=chave,
                        status="fechada",
                        ancora=evento,
                        abertura=None,
                        fechamento=ts,
                        parcial=True,
                        ordem=indice,
                        evento_delete=evento,
                    )
                )

    sessoes.sort(key=lambda s: s.ordem)
    pendentes = [sessao for pilha in abertas.values() for sessao in pilha]
    return CorrelacaoResultado(sessoes=sessoes, pendentes=pendentes)


def formatar_duracao(segundos: Optional[float]) -> Optional[str]:
    """Duracao legivel: '10s', '1m 5s', '2h 3m', '182d 4h'. None se indefinida."""
    if segundos is None:
        return None
    total = int(segundos)
    if total < 0:
        total = 0
    dias, resto = divmod(total, 86400)
    horas, resto = divmod(resto, 3600)
    minutos, segs = divmod(resto, 60)

    partes = []
    if dias:
        partes.append(f"{dias}d")
    if horas:
        partes.append(f"{horas}h")
    if minutos:
        partes.append(f"{minutos}m")
    if segs or not partes:
        partes.append(f"{segs}s")
    return " ".join(partes)
