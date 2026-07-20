from typing import Any, Dict, Iterable, Optional, Set

PROTOCOLOS = {
    1: "ICMP",
    6: "TCP",
    17: "UDP",
}

# Mapa reverso usado pelo filtro por protocolo. Derivado de PROTOCOLOS para
# que exibicao e filtro nunca divirjam.
PROTOCOLO_NUMEROS = {nome.lower(): numero for numero, nome in PROTOCOLOS.items()}


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_value(event: Dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = event.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _protocol_name(value: Any) -> str:
    proto_number = _as_int(value)
    if proto_number is None:
        return str(value or "")
    return PROTOCOLOS.get(proto_number, str(proto_number))


def _port_block_limits(event: Dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    start = _as_int(event.get("pblock_start"))
    size = _as_int(event.get("pblock_size"))

    if start is not None and size is not None:
        return start, start + size - 1

    return start, _as_int(event.get("pblock_end"))


def _port_block(event: Dict[str, Any]) -> str:
    start, end = _port_block_limits(event)
    if start is None and end is None:
        return ""
    if start == end or end is None:
        return str(start)
    return f"{start}-{end}"


def normalize_pcap_event(event: Dict[str, Any]) -> Dict[str, Any]:
    data = _first_value(event, ("t_first", "t_event", "t_received", "t_last"))
    origem = _first_value(event, ("src4_addr", "src6_addr", "src_addr"))
    nat = _first_value(event, ("src4_xlt_ip", "src_xlt_ip", "xlate_src_ip"))
    destino = _first_value(event, ("dst4_addr", "dst6_addr", "dst_addr"))
    destino_final = _first_value(event, ("dst4_xlt_ip", "dst_xlt_ip", "xlate_dst_ip"))

    return {
        "data": data,
        "evento": _first_value(event, ("nat_event", "event", "type")),
        "protocolo": _protocol_name(event.get("proto")),
        "origem": origem,
        "nat": nat,
        "porta_origem": event.get("src_port", ""),
        "porta_destino": event.get("dst_port", ""),
        "bloco_portas": _port_block(event),
        "destino": destino,
        "destino_final": destino_final,
        "roteador": _first_value(event, ("ip4_router", "router")),
        "_raw": event,
    }


def pcap_event_matches(
    event: Dict[str, Any],
    ip: Optional[str] = None,
    porta: Optional[str] = None,
    data: Optional[str] = None,
    protocolos: Optional[Set[int]] = None,
) -> bool:
    if ip:
        ip_candidates = {
            str(event.get(key, ""))
            for key in (
                "src4_addr",
                "src6_addr",
                "src_addr",
                "src4_xlt_ip",
                "src_xlt_ip",
                "xlate_src_ip",
                "dst4_addr",
                "dst6_addr",
                "dst_addr",
                "dst4_xlt_ip",
                "dst_xlt_ip",
                "xlate_dst_ip",
                "ip4_router",
            )
        }
        if ip not in ip_candidates:
            return False

    if data:
        event_date = _first_value(
            event, ("t_first", "t_event", "t_received", "t_last")
        )[:10]
        if event_date and event_date != data:
            return False

    if protocolos:
        # Evento sem proto (ou com proto nao numerico) da None, que nunca
        # pertence ao conjunto: falha fechada quando o filtro esta ativo.
        if _as_int(event.get("proto")) not in protocolos:
            return False

    port_number = _as_int(porta)
    if porta and port_number is None:
        return False

    if port_number is not None:
        direct_ports = {
            _as_int(event.get("src_port")),
            _as_int(event.get("dst_port")),
            _as_int(event.get("src_xlt_port")),
            _as_int(event.get("dst_xlt_port")),
        }
        block_start, block_end = _port_block_limits(event)
        in_block = (
            block_start is not None
            and block_end is not None
            and block_start <= port_number <= block_end
        )

        if port_number not in direct_ports and not in_block:
            return False

    return True
