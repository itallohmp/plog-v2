"""Testes das primitivas de sessao NAT.

Derivados de .specs/features/sessoes-nat/spec.md (NAT-05, NAT-06 e a chave D4).
Cada assert codifica o comportamento que a spec exige, nao o que o codigo faz.
"""

from datetime import datetime, timezone

from app.parsers.nat_session import (
    classificar_evento,
    chave_sessao,
    correlacionar,
    timestamp_evento,
)


def _ev(dia_hora, classe, *, origem="172.16.10.17", nat="177.137.21.38",
        pblock_start=4096, roteador="172.16.2.1"):
    """Evento NAT com timestamp e chave completos (create/delete pareáveis)."""
    nat_event = {
        "create": "NAT translation create",
        "delete": "NAT translation delete",
    }.get(classe, "EVENT")
    return {
        "t_first": f"2026-07-15T{dia_hora}",
        "nat_event": nat_event,
        "ip4_router": roteador,
        "src4_addr": origem,
        "src4_xlt_ip": nat,
        "pblock_start": pblock_start,
        "pblock_size": 512,
    }


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


class TestCorrelacionar:
    def test_par_vira_sessao_fechada_com_duracao(self):
        """NAT-01: create + delete da mesma chave -> 1 sessao fechada com duracao."""
        eventos = [_ev("10:00:00", "create"), _ev("10:00:10", "delete")]
        r = correlacionar(eventos)

        assert len(r.sessoes) == 1
        s = r.sessoes[0]
        assert s.status == "fechada"
        assert s.duracao_segundos == 10.0
        assert s.eventos == 2
        assert r.pendentes == []

    def test_create_sozinho_fica_aberta(self):
        """NAT-02: create sem delete -> sessao aberta e pendente."""
        r = correlacionar([_ev("10:00:00", "create")])

        assert len(r.sessoes) == 1
        assert r.sessoes[0].status == "aberta"
        assert r.sessoes[0].fechamento is None
        assert len(r.pendentes) == 1
        assert r.pendentes[0] is r.sessoes[0]

    def test_delete_orfao_fica_fechada_parcial(self):
        """NAT-03: delete sem create na janela -> fechada, parcial, sem abertura."""
        r = correlacionar([_ev("10:00:10", "delete")])

        s = r.sessoes[0]
        assert s.status == "fechada"
        assert s.parcial is True
        assert s.abertura is None
        assert r.pendentes == []

    def test_realocacao_nao_cruza_assinantes(self):
        """NAT-04: create A, delete A, create B, delete B na MESMA chave ->
        duas sessoes independentes, sem o delete de B fechar a sessao de A.

        Este e o teste que o sensor de mutacao exercita: trocar a pilha por
        dict[chave]=create faz o delete de B fechar a sessao de A.
        """
        eventos = [
            _ev("10:00:00", "create"),  # A abre
            _ev("10:00:05", "delete"),  # A fecha (duracao 5s)
            _ev("11:00:00", "create"),  # B abre (mesma chave, realocado)
            _ev("11:00:20", "delete"),  # B fecha (duracao 20s)
        ]
        r = correlacionar(eventos)

        assert len(r.sessoes) == 2
        duracoes = sorted(s.duracao_segundos for s in r.sessoes)
        assert duracoes == [5.0, 20.0]
        assert all(s.status == "fechada" for s in r.sessoes)
        assert r.pendentes == []

    def test_indefinidos_preservados_um_a_um(self):
        """NAT-05: eventos sem chave/classe nao somem; viram sessoes indefinidas."""
        eventos = [
            {"type": "EVENT", "t_first": "2026-07-15T10:00:00", "src4_addr": "10.0.0.1"},
            {"type": "EVENT", "t_first": "2026-07-15T10:00:01", "src4_addr": "10.0.0.2"},
        ]
        r = correlacionar(eventos)

        assert len(r.sessoes) == 2
        assert all(s.status == "indefinida" for s in r.sessoes)
        assert r.pendentes == []

    def test_ordem_de_entrada_nao_importa(self):
        """NAT-06: delete que chega ANTES do create na lista ainda pareia pela
        ordem cronologica real (timestamp), nao pela ordem de entrada."""
        eventos = [_ev("10:00:10", "delete"), _ev("10:00:00", "create")]
        r = correlacionar(eventos)

        assert len(r.sessoes) == 1
        assert r.sessoes[0].status == "fechada"
        assert r.sessoes[0].duracao_segundos == 10.0
        assert r.sessoes[0].parcial is False

    def test_duas_abertas_mesma_chave_fecha_a_mais_recente(self):
        """Edge (LIFO): duas sessoes abertas na mesma chave -> o delete fecha a
        mais recente, deixando a antiga aberta."""
        eventos = [
            _ev("10:00:00", "create"),
            _ev("10:30:00", "create"),
            _ev("11:00:00", "delete"),
        ]
        r = correlacionar(eventos)

        assert len(r.sessoes) == 2
        fechadas = [s for s in r.sessoes if s.status == "fechada"]
        abertas = [s for s in r.sessoes if s.status == "aberta"]
        assert len(fechadas) == 1 and len(abertas) == 1
        # a fechada e a que abriu as 10:30 (duracao 30min = 1800s)
        assert fechadas[0].duracao_segundos == 1800.0

    def test_lista_vazia(self):
        r = correlacionar([])
        assert r.sessoes == []
        assert r.pendentes == []


class TestFormatarDuracao:
    def test_segundos(self):
        from app.parsers.nat_session import formatar_duracao
        assert formatar_duracao(10) == "10s"

    def test_zero(self):
        from app.parsers.nat_session import formatar_duracao
        assert formatar_duracao(0) == "0s"

    def test_composto(self):
        from app.parsers.nat_session import formatar_duracao
        assert formatar_duracao(3661) == "1h 1m 1s"

    def test_dias(self):
        from app.parsers.nat_session import formatar_duracao
        # 10 dias exatos
        assert formatar_duracao(10 * 86400) == "10d"

    def test_none(self):
        from app.parsers.nat_session import formatar_duracao
        assert formatar_duracao(None) is None
