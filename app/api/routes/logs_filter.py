from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import glob
import json
import os
import re
import subprocess

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import (
    BASE_LOGS,
    FLOW_CACHE_DIR,
    FLOW_JSON_PATTERN,
    FLOW_REMOTE_DIR,
    FLOW_REMOTE_HOST,
    FLOW_REMOTE_USER,
    FLOW_ROUTE,
    SCRIPT_DOWNLOAD,
)
from app.parsers.log_parser import parse_log_line
from app.parsers.pcap_parser import (
    iter_pcap_events,
    normalize_pcap_event,
    pcap_event_matches,
)

router = APIRouter()


def _safe_route(route: str) -> bool:
    return not ("/" in route or "\\" in route or ".." in route)


def _date_parts(
    ano: Optional[str],
    mes: Optional[str],
    dia: Optional[str],
) -> tuple[str, str, str, str]:
    now = datetime.now()
    year = ano or f"{now.year}"
    month = (mes or f"{now.month}").zfill(2)
    day = (dia or f"{now.day}").zfill(2)
    return year, month, day, f"{year}-{month}-{day}"


def _flow_cache_path(ano: str, mes: str, dia: str) -> Path:
    return FLOW_CACHE_DIR / ano / mes / dia


def _json_files(path: Path) -> list[Path]:
    return sorted(path.glob(FLOW_JSON_PATTERN))


def _run_flow_download(ano: str, mes: str, dia: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "FLOW_REMOTE_HOST": FLOW_REMOTE_HOST,
            "FLOW_REMOTE_USER": FLOW_REMOTE_USER,
            "FLOW_REMOTE_DIR": str(FLOW_REMOTE_DIR),
            "FLOW_CACHE_DIR": str(FLOW_CACHE_DIR),
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT_DOWNLOAD), FLOW_ROUTE, ano, mes, dia],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        timeout=300,
    )


def _stream_pcap_logs(
    arquivos: Iterable[Path],
    ip: Optional[str],
    porta: Optional[str],
    data_iso: str,
    pagina: int,
    tamanho_pagina: int,
):
    indice_inicio = max(0, (pagina - 1) * tamanho_pagina)
    indice_fim = indice_inicio + tamanho_pagina
    contador_encontrados = 0

    for arquivo in arquivos:
        print("Lendo PCAP JSON:", arquivo)
        try:
            for event in iter_pcap_events(arquivo):
                if not pcap_event_matches(event, ip=ip, porta=porta, data=data_iso):
                    continue

                if indice_inicio <= contador_encontrados < indice_fim:
                    normalized = normalize_pcap_event(event)
                    normalized.pop("_raw", None)
                    yield json.dumps(normalized, ensure_ascii=False) + "\n"

                contador_encontrados += 1
                if contador_encontrados >= indice_fim:
                    return
        except Exception as exc:
            print(f"Erro ao ler JSON {arquivo}: {exc}")


def _legacy_log_files(route: str, ano: str, mes: str, dia: str) -> list[str]:
    caminho = os.path.join(BASE_LOGS, route, ano, mes, dia)
    arquivos = glob.glob(os.path.join(caminho, "*.log"))

    def chave_ordenacao_numerica(path: str):
        nome = os.path.basename(path)
        nums = re.findall(r"(\d+)", nome)
        return int(nums[-1]) if nums else nome

    return sorted(arquivos, key=chave_ordenacao_numerica)[:50]


def _stream_legacy_logs(
    arquivos: Iterable[str],
    ip_nat: Optional[str],
    porta_nat: Optional[str],
    pagina: int,
    tamanho_pagina: int,
):
    indice_inicio = max(0, (pagina - 1) * tamanho_pagina)
    indice_fim = indice_inicio + tamanho_pagina
    contador_encontrados = 0

    for arquivo in arquivos:
        try:
            with open(arquivo, "r", errors="ignore") as fh:
                for raw_line in fh:
                    line = raw_line.strip()
                    if not line:
                        continue

                    parseado = parse_log_line(line)
                    if not parseado:
                        continue

                    nat_field = parseado.get("nat", "")
                    nat_ip, _, nat_port = nat_field.partition(":")

                    if ip_nat and nat_ip != ip_nat:
                        continue
                    if porta_nat and nat_port != porta_nat:
                        continue

                    if indice_inicio <= contador_encontrados < indice_fim:
                        yield json.dumps(parseado, ensure_ascii=False) + "\n"

                    contador_encontrados += 1
                    if contador_encontrados >= indice_fim:
                        return
        except Exception as exc:
            print(f"Erro ao ler log legado {arquivo}: {exc}")


@router.get("/logs/filter")
def filter_logs(
    ip: Optional[str] = Query(None, description="IP para buscar nos flows"),
    porta: Optional[str] = Query(None, description="Porta para buscar nos flows"),
    ano: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    dia: Optional[str] = Query(None),
    pagina: int = Query(1, ge=1),
    tamanho_pagina: int = Query(100, ge=1, le=1000),
    ip_rota: Optional[str] = Query(None, description="Rota legada"),
    ip_nat: Optional[str] = Query(None, description="IP NAT legado"),
    porta_nat: Optional[str] = Query(None, description="Porta NAT legada"),
):
    ano, mes, dia, data_iso = _date_parts(ano, mes, dia)
    ip_filter = ip or ip_nat
    porta_filter = porta or porta_nat

    if ip_rota and not _safe_route(ip_rota):
        return JSONResponse({"erro": "Nome de rota inválido."}, status_code=400)

    try:
        caminho_json = _flow_cache_path(ano, mes, dia)
        arquivos_json = _json_files(caminho_json)

        if not arquivos_json:
            print("Flows JSON não encontrados localmente, executando download...")
            proc = _run_flow_download(ano, mes, dia)
            print("download returncode:", proc.returncode)
            print("download stderr:", proc.stderr)
            arquivos_json = _json_files(caminho_json)

            if proc.returncode != 0 and not arquivos_json:
                arquivos_legados = _legacy_log_files(ip_rota, ano, mes, dia) if ip_rota else []
                if not arquivos_legados:
                    return JSONResponse(
                        {
                            "erro": "Nenhum flow JSON encontrado após tentativa de download",
                            "detalhes": (proc.stderr or proc.stdout).strip(),
                        },
                        status_code=404,
                    )

        if arquivos_json:
            return StreamingResponse(
                _stream_pcap_logs(
                    arquivos_json,
                    ip=ip_filter,
                    porta=porta_filter,
                    data_iso=data_iso,
                    pagina=pagina,
                    tamanho_pagina=tamanho_pagina,
                ),
                media_type="application/x-ndjson",
            )

        if ip_rota:
            arquivos_legados = _legacy_log_files(ip_rota, ano, mes, dia)
            if arquivos_legados:
                return StreamingResponse(
                    _stream_legacy_logs(
                        arquivos_legados,
                        ip_nat=ip_filter,
                        porta_nat=porta_filter,
                        pagina=pagina,
                        tamanho_pagina=tamanho_pagina,
                    ),
                    media_type="application/x-ndjson",
                )

        return JSONResponse({"erro": "Nenhum log disponível"}, status_code=404)

    except subprocess.TimeoutExpired:
        return JSONResponse({"erro": "Processamento demorou demais"}, status_code=504)
    except Exception as exc:
        return JSONResponse({"erro": str(exc)}, status_code=500)