from typing import Any, Dict, Iterable, List

from app.parsers.pcap_parser import normalize_pcap_event
from app.schemas.flow import FlowRecord


def parse_flow_event(event: Dict[str, Any]) -> FlowRecord:
    """Normaliza e valida um unico evento de flow do nfdump."""
    normalizado = normalize_pcap_event(event)
    normalizado.pop("_raw", None)
    return FlowRecord.model_validate(normalizado)


def parse_flows(raw_events: Iterable[Dict[str, Any]]) -> List[FlowRecord]:
    """Converte eventos brutos do nfdump em registros validados."""
    return [parse_flow_event(event) for event in raw_events]
