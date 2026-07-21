"""Correlacao de eventos NAT em sessoes (create + delete -> uma sessao).

Modulo puro, sem I/O. Interpreta o payload cru do nfdump, no mesmo papel de
pcap_parser.py. A correlacao propriamente dita (correlacionar) vem em seguida;
aqui ficam as tres primitivas: classificar o evento, extrair a chave de sessao
e obter o timestamp real.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

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
