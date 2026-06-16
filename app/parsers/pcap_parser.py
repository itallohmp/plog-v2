import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional


PROTOCOLOS = {
    1: "ICMP",
    6: "TCP",
    17: "UDP",
}


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


def _port_block(event: Dict[str, Any]) -> str:
    start = event.get("pblock_start")
    end = event.get("pblock_end")
    if start in (None, "") and end in (None, ""):
        return ""
    if start == end or end in (None, ""):
        return str(start)
    return f"{start}-{end}"


def normalize_pcap_event(event: Dict[str, Any]) -> Dict[str, Any]:
    data = _first_value(event, ("t_first", "t_event", "t_received", "t_last"))
    origem = _first_value(event, ("src4_addr", "src_addr"))
    nat = _first_value(event, ("src4_xlt_ip", "src_xlt_ip"))
    destino = _first_value(event, ("dst4_addr", "dst_addr"))
    destino_final = _first_value(event, ("dst4_xlt_ip", "dst_xlt_ip"))

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


def iter_pcap_events(path: Path) -> Iterator[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except json.JSONDecodeError:
        yield from _iter_ndjson_events(path)
        return

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return

    if isinstance(payload, dict):
        records = payload.get("records") or payload.get("flows") or payload.get("data")
        if isinstance(records, list):
            for item in records:
                if isinstance(item, dict):
                    yield item
            return
        yield payload


def _iter_ndjson_events(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                yield item


def pcap_event_matches(
    event: Dict[str, Any],
    ip: Optional[str] = None,
    porta: Optional[str] = None,
    data: Optional[str] = None,
) -> bool:
    if ip and ip not in {
        str(event.get("src4_addr", "")),
        str(event.get("src4_xlt_ip", "")),
        str(event.get("dst4_addr", "")),
        str(event.get("dst4_xlt_ip", "")),
        str(event.get("ip4_router", "")),
    }:
        return False

    if data:
        event_date = _first_value(event, ("t_first", "t_event", "t_received", "t_last"))[:10]
        if event_date and event_date != data:
            return False

    port_number = _as_int(porta)
    if porta and port_number is None:
        return False

    if port_number is not None:
        direct_ports = {
            _as_int(event.get("src_port")),
            _as_int(event.get("dst_port")),
        }
        block_start = _as_int(event.get("pblock_start"))
        block_end = _as_int(event.get("pblock_end"))
        in_block = (
            block_start is not None
            and block_end is not None
            and block_start <= port_number <= block_end
        )

        if port_number not in direct_ports and not in_block:
            return False

    return True
