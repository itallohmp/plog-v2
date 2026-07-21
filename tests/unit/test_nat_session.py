"""Testes das primitivas de sessao NAT.

Derivados de .specs/features/sessoes-nat/spec.md (NAT-05, NAT-06 e a chave D4).
Cada assert codifica o comportamento que a spec exige, nao o que o codigo faz.
"""

from datetime import datetime, timezone

from app.parsers.nat_session import (
    classificar_evento,
    chave_sessao,
    timestamp_evento,
)


class TestClassificarEvento:
    def test_create_em_nat_event(self):
        assert classificar_evento({"nat_event": "NAT translation create"}) == "create"

    def test_delete_em_nat_event(self):
        assert classificar_evento({"nat_event": "NAT translation delete"}) == "delete"

    def test_create_em_event_e_type(self):
        assert classificar_evento({"event": "CREATE"}) == "create"
        assert classificar_evento({"type": "delete"}) == "delete"

    def test_case_insensitive(self):
        assert classificar_evento({"nat_event": "nAt TrAnSlAtIoN cReAtE"}) == "create"

    def test_type_event_generico_e_indefinido(self):
        # A fixture inteira do projeto cai neste caso (type == "EVENT").
        assert classificar_evento({"type": "EVENT"}) == "indefinido"

    def test_sem_campos_de_evento_e_indefinido(self):
        assert classificar_evento({"src4_addr": "10.0.0.1"}) == "indefinido"

    def test_ambiguo_create_e_delete_e_indefinido(self):
        assert classificar_evento({"nat_event": "create and delete"}) == "indefinido"


class TestChaveSessao:
    BLOCO = {
        "ip4_router": "172.16.2.1",
        "src4_addr": "172.16.10.17",
        "src4_xlt_ip": "177.137.21.38",
        "pblock_start": 4096,
        "pblock_size": 512,
    }

    def test_chave_completa(self):
        assert chave_sessao(self.BLOCO) == (
            "172.16.2.1",
            "172.16.10.17",
            "177.137.21.38",
            4096,
            512,
        )

    def test_create_e_delete_do_mesmo_bloco_tem_chave_identica(self):
        create = dict(self.BLOCO, nat_event="NAT translation create")
        delete = dict(self.BLOCO, nat_event="NAT translation delete")
        assert chave_sessao(create) == chave_sessao(delete)

    def test_sem_ip_nat_e_none(self):
        evento = dict(self.BLOCO)
        del evento["src4_xlt_ip"]
        assert chave_sessao(evento) is None

    def test_sem_pblock_start_e_none(self):
        evento = dict(self.BLOCO)
        del evento["pblock_start"]
        assert chave_sessao(evento) is None

    def test_sem_origem_e_none(self):
        evento = dict(self.BLOCO)
        del evento["src4_addr"]
        assert chave_sessao(evento) is None

    def test_evento_de_teste_existente_sem_nat_da_none(self):
        # Molde de tests/test_flow_interval.py::_evento: tem nat_event mas nao
        # tem src4_xlt_ip nem pblock_start -> chave None -> sessao indefinida.
        assert chave_sessao({"src4_addr": "100.64.18.210", "proto": 6}) is None


class TestTimestampEvento:
    def test_iso_com_t(self):
        assert timestamp_evento({"t_first": "2026-07-15T18:48:41.045"}) == datetime(
            2026, 7, 15, 18, 48, 41, 45000
        )

    def test_iso_com_espaco(self):
        assert timestamp_evento({"t_first": "2026-07-15 18:48:41"}) == datetime(
            2026, 7, 15, 18, 48, 41
        )

    def test_sufixo_z_vira_utc_naive(self):
        assert timestamp_evento({"t_first": "2026-07-15T18:48:41Z"}) == datetime(
            2026, 7, 15, 18, 48, 41
        )

    def test_offset_convertido_para_utc(self):
        # 18:48 em -03:00 == 21:48 UTC.
        assert timestamp_evento({"t_first": "2026-07-15T18:48:41-03:00"}) == datetime(
            2026, 7, 15, 21, 48, 41
        )

    def test_epoch_numerico(self):
        # 1_752_000_000 = 2025-07-08T19:20:00Z (referencia de sanidade).
        esperado = datetime.fromtimestamp(1752000000, timezone.utc).replace(tzinfo=None)
        assert timestamp_evento({"t_first": "1752000000"}) == esperado

    def test_lixo_vira_none(self):
        assert timestamp_evento({"t_first": "nao-e-data"}) is None

    def test_ausente_vira_none(self):
        assert timestamp_evento({}) is None

    def test_ordena_z_e_naive_coerentemente(self):
        # Um evento "Z" (UTC) e um naive devem ser comparaveis sem TypeError.
        a = timestamp_evento({"t_first": "2026-07-15T10:00:00Z"})
        b = timestamp_evento({"t_first": "2026-07-15T11:00:00"})
        assert a < b
