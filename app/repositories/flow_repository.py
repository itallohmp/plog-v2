import json
import shlex
import subprocess
from datetime import date
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import paramiko
from app.core import config


def construir_filtro_nfdump(chaves: Sequence[Tuple]) -> str:
    """Monta a expressao de filtro do nfdump por allowlist de valores tipados.

    Cada chave e (roteador, origem, ip_nat, pblock_start, pblock_size). Somente
    IPs validos (ip_address) e inteiro de bloco entram na expressao; qualquer
    valor fora disso descarta a chave. Nunca ha string crua do usuario aqui —
    e a garantia contra injecao no shell do servidor de flows.

    NOTA: os keywords (`src nat ip`, `pblock start`) dependem da versao do
    nfdump e estao pendentes de confirmacao (ver nfdump-filtro.md).
    """
    partes: List[str] = []
    for chave in chaves:
        origem, nat, inicio = chave[1], chave[2], chave[3]
        try:
            ip_address(origem)
            ip_address(nat)
        except (ValueError, TypeError):
            continue
        if not isinstance(inicio, int) or isinstance(inicio, bool):
            continue
        partes.append(
            f"(src ip {origem} and src nat ip {nat} and pblock start {inicio})"
        )
    return " or ".join(partes)


class FlowNotFoundError(RuntimeError):
    """Diretorio da data/hora nao encontrado no servidor remoto."""


class FlowQueryError(RuntimeError):
    """Falha ao executar ou interpretar a consulta de flows."""


class FlowRepository:
    """Acesso aos flows nfcapd via SSH, exportando JSON com nfdump."""

    def _connect(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()

        if config.FLOW_SSH_KNOWN_HOSTS:
            client.load_host_keys(config.FLOW_SSH_KNOWN_HOSTS)
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs: Dict[str, Any] = {
            "hostname": config.FLOW_SSH_HOST,
            "port": config.FLOW_SSH_PORT,
            "username": config.FLOW_SSH_USER,
            "timeout": config.FLOW_SSH_TIMEOUT,
        }

        if config.FLOW_SSH_KEY_PATH:
            connect_kwargs["key_filename"] = config.FLOW_SSH_KEY_PATH
        elif config.FLOW_SSH_PASSWORD:
            connect_kwargs["password"] = config.FLOW_SSH_PASSWORD
            connect_kwargs["look_for_keys"] = False
            connect_kwargs["allow_agent"] = False
        else:
            raise FlowQueryError(
                "Credencial SSH ausente: defina PLOG_FLOW_SSH_KEY_PATH "
                "ou PLOG_FLOW_SSH_PASSWORD no ambiente."
            )

        try:
            client.connect(**connect_kwargs)
        except paramiko.SSHException as exc:
            raise FlowQueryError(f"Falha na conexao SSH: {exc}") from exc

        return client

    def fetch_raw_flows(self, dia: date, horas: Iterable[int]) -> List[Dict[str, Any]]:
        if config.FLOW_LOCAL_PATH:
            return self._fetch_local_flows(config.FLOW_LOCAL_PATH)

        day_dir = f"{config.FLOW_REMOTE_DIR}/{dia.strftime(config.FLOW_DAY_DIR_FORMAT)}"
        horas_alvo = set(horas)

        client = self._connect()
        try:
            hour_dirs = self._listar_pastas_hora(client, day_dir, horas_alvo)

            eventos: List[Dict[str, Any]] = []
            for hour_dir in hour_dirs:
                eventos.extend(self._run_nfdump(client, hour_dir))
            return eventos
        finally:
            client.close()

    def _listar_pastas_hora(
        self,
        client: paramiko.SSHClient,
        day_dir: str,
        horas_alvo: set,
    ) -> List[str]:
        sftp = client.open_sftp()
        try:
            try:
                entradas = sftp.listdir(day_dir)
            except IOError as exc:
                raise FlowNotFoundError(
                    f"Diretorio nao encontrado para a data indicada, verifique se a data e valida."  # {day_dir}
                ) from exc
        finally:
            sftp.close()

        pastas = []
        for nome in sorted(entradas):
            if nome.isdigit() and int(nome) in horas_alvo:
                pastas.append(f"{day_dir}/{nome}")

        if not pastas:
            raise FlowNotFoundError(
                f"Nenhuma pasta de hora encontrada em {day_dir} para as horas selecionadas."
            )

        return pastas

    def fetch_flows_por_chave(
        self, chaves: Sequence[Tuple], inicio: date, fim: date
    ) -> List[Dict[str, Any]]:
        """Consulta o nfdump filtrado pelas chaves de sessao, no range [inicio, fim].

        Usado para descobrir se sessoes abertas na janela fecharam depois dela,
        sem reler dias inteiros. A expressao vem de construir_filtro_nfdump
        (allowlist). Em modo local, delega ao acesso local (que ignora o range;
        o service filtra em memoria).
        """
        expr = construir_filtro_nfdump(chaves)
        if not expr:
            return []

        if config.FLOW_LOCAL_PATH:
            return self._fetch_local_flows(config.FLOW_LOCAL_PATH)

        base = config.FLOW_REMOTE_DIR
        dir_inicio = f"{base}/{inicio.strftime(config.FLOW_DAY_DIR_FORMAT)}"
        dir_fim = f"{base}/{fim.strftime(config.FLOW_DAY_DIR_FORMAT)}"
        range_arg = f"{dir_inicio}:{dir_fim}"

        comando = (
            f"{shlex.quote(config.NFDUMP_BIN)} -R {shlex.quote(range_arg)} "
            f"{shlex.quote(expr)} -o json"
        )

        client = self._connect()
        try:
            return self._exec_nfdump(client, comando, contexto=range_arg)
        finally:
            client.close()

    def _run_nfdump(
        self, client: paramiko.SSHClient, directory: str
    ) -> List[Dict[str, Any]]:
        comando = (
            f"{shlex.quote(config.NFDUMP_BIN)} " f"-R {shlex.quote(directory)} -o json"
        )
        return self._exec_nfdump(client, comando, contexto=directory)

    def _exec_nfdump(
        self, client: paramiko.SSHClient, comando: str, contexto: str
    ) -> List[Dict[str, Any]]:
        _, stdout, stderr = client.exec_command(comando, timeout=config.NFDUMP_TIMEOUT)

        saida = stdout.read().decode("utf-8", errors="ignore")
        erro = stderr.read().decode("utf-8", errors="ignore")
        status = stdout.channel.recv_exit_status()

        if status != 0:
            raise FlowQueryError(f"nfdump falhou em {contexto}: {erro.strip()}")

        return self._parse_nfdump_json(saida)

    def _fetch_local_flows(self, local_path: str) -> List[Dict[str, Any]]:
        caminho = Path(local_path)

        if not caminho.exists():
            raise FlowNotFoundError(
                f"Caminho local de flows nao encontrado: {local_path}"
            )

        if caminho.is_dir():
            json_files = sorted(caminho.glob("*.json"))
            nfcapd_files = sorted(caminho.glob(f"{config.FLOW_NFCAPD_PREFIX}*"))
        else:
            json_files = [caminho] if caminho.suffix.lower() == ".json" else []
            nfcapd_files = [] if caminho.suffix.lower() == ".json" else [caminho]

        eventos: List[Dict[str, Any]] = []

        for arquivo in json_files:
            conteudo = arquivo.read_text(encoding="utf-8", errors="ignore")
            eventos.extend(self._parse_nfdump_json(conteudo))

        for arquivo in nfcapd_files:
            eventos.extend(self._run_local_nfdump(arquivo))

        if not json_files and not nfcapd_files:
            raise FlowNotFoundError(
                f"Nenhum arquivo .json ou nfcapd encontrado em: {local_path}"
            )

        return eventos

    def _run_local_nfdump(self, arquivo: Path) -> List[Dict[str, Any]]:
        try:
            resultado = subprocess.run(
                [config.NFDUMP_LOCAL_BIN, "-r", str(arquivo), "-o", "json"],
                capture_output=True,
                text=True,
                timeout=config.NFDUMP_TIMEOUT,
            )
        except FileNotFoundError as exc:
            raise FlowQueryError(
                f"nfdump local nao encontrado ('{config.NFDUMP_LOCAL_BIN}'). "
                "Instale o nfdump ou defina PLOG_NFDUMP_LOCAL_BIN."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise FlowQueryError(f"nfdump local expirou ao ler {arquivo.name}") from exc

        if resultado.returncode != 0:
            raise FlowQueryError(
                f"nfdump local falhou em {arquivo.name}: {resultado.stderr.strip()}"
            )

        return self._parse_nfdump_json(resultado.stdout)

    @staticmethod
    def _parse_nfdump_json(payload: str) -> List[Dict[str, Any]]:
        conteudo = payload.strip()
        if not conteudo:
            return []

        try:
            dados = json.loads(conteudo)
        except json.JSONDecodeError:
            return FlowRepository._parse_ndjson(conteudo)

        if isinstance(dados, list):
            return [item for item in dados if isinstance(item, dict)]
        if isinstance(dados, dict):
            registros = dados.get("records") or dados.get("flows") or dados.get("data")
            if isinstance(registros, list):
                return [item for item in registros if isinstance(item, dict)]
            return [dados]
        return []

    @staticmethod
    def _parse_ndjson(conteudo: str) -> List[Dict[str, Any]]:
        eventos: List[Dict[str, Any]] = []
        for linha in conteudo.splitlines():
            linha = linha.strip()
            if not linha:
                continue
            try:
                item = json.loads(linha)
            except json.JSONDecodeError as exc:
                raise FlowQueryError(f"Saida do nfdump invalida: {exc}") from exc
            if isinstance(item, dict):
                eventos.append(item)
        return eventos
        return eventos
