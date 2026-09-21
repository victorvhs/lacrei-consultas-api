import json
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from payments.adaptadores.fake import FakeGateway
from payments.dominio.estados import StatusPagamento
from payments.dominio.excecoes import CobrancaNaoEncontrada, CredencialInvalida
from payments.portas import DadosPagador, PedidoCobranca


class FakeGatewayTest(SimpleTestCase):
    def setUp(self):
        self.gw = FakeGateway()

    def test_registrar_pagador(self):
        dados = DadosPagador(nome="Teste", documento="12345678901", email="test@test.com")
        id_ext = self.gw.registrar_pagador(dados)
        self.assertTrue(id_ext.startswith("cus_"))
        self.assertIn(id_ext, self.gw.pagadores)

    def test_criar_cobranca(self):
        pedido = PedidoCobranca(
            referencia=uuid4(),
            pagador_id_externo="cus_test",
            valor=Decimal("150.00"),
            vencimento="2026-12-01",
            forma="PIX",
            repasses=[],
        )
        cobranca = self.gw.criar_cobranca(pedido)
        self.assertTrue(cobranca.id_externo.startswith("pay_"))
        self.assertEqual(cobranca.status, StatusPagamento.PENDENTE)
        self.assertEqual(cobranca.valor, Decimal("150.00"))

    def test_buscar_por_referencia(self):
        ref = uuid4()
        pedido = PedidoCobranca(
            referencia=ref,
            pagador_id_externo="cus_test",
            valor=Decimal("100.00"),
            vencimento="",
            forma="PIX",
            repasses=[],
        )
        self.gw.criar_cobranca(pedido)
        resultado = self.gw.buscar_por_referencia(ref)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.valor, Decimal("100.00"))

    def test_buscar_por_referencia_nao_encontrada(self):
        resultado = self.gw.buscar_por_referencia(uuid4())
        self.assertIsNone(resultado)

    def test_consultar_cobranca(self):
        pedido = PedidoCobranca(
            referencia=uuid4(),
            pagador_id_externo="cus_test",
            valor=Decimal("100.00"),
            vencimento="",
            forma="PIX",
            repasses=[],
        )
        cobranca = self.gw.criar_cobranca(pedido)
        resultado = self.gw.consultar_cobranca(cobranca.id_externo)
        self.assertEqual(resultado.id_externo, cobranca.id_externo)

    def test_consultar_cobranca_nao_encontrada(self):
        with self.assertRaises(CobrancaNaoEncontrada):
            self.gw.consultar_cobranca("pay_nao_existe")

    def test_solicitar_estorno(self):
        pedido = PedidoCobranca(
            referencia=uuid4(),
            pagador_id_externo="cus_test",
            valor=Decimal("100.00"),
            vencimento="",
            forma="PIX",
            repasses=[],
        )
        cobranca = self.gw.criar_cobranca(pedido)
        self.gw.solicitar_estorno(cobranca.id_externo)
        resultado = self.gw.consultar_cobranca(cobranca.id_externo)
        self.assertEqual(resultado.status, StatusPagamento.ESTORNADO)

    def test_solicitar_estorno_nao_encontrada(self):
        with self.assertRaises(CobrancaNaoEncontrada):
            self.gw.solicitar_estorno("pay_nao_existe")

    def test_autenticar_notificacao_valida(self):
        self.assertTrue(self.gw.autenticar_notificacao({"asaas-access-token": "fake-token"}))

    def test_autenticar_notificacao_invalida(self):
        self.assertFalse(self.gw.autenticar_notificacao({"asaas-access-token": "wrong"}))

    def test_autenticar_notificacao_sem_token(self):
        self.assertFalse(self.gw.autenticar_notificacao({}))

    def test_traduzir_notificacao(self):
        corpo = json.dumps(
            {
                "event_id": "evt_123",
                "tipo": "PAYMENT_UPDATED",
                "referencia": str(uuid4()),
                "id_externo": "pay_123",
                "status": "PENDENTE",
            }
        ).encode()
        notificacao = self.gw.traduzir_notificacao(corpo)
        self.assertEqual(notificacao.event_id, "evt_123")
        self.assertEqual(notificacao.tipo, "PAYMENT_UPDATED")

    def test_traduzir_notificacao_invalido(self):
        from payments.dominio.excecoes import PagamentoError

        with self.assertRaises(PagamentoError):
            self.gw.traduzir_notificacao(b"invalid json")

    def test_programar_erro(self):
        self.gw.programar_erro(CredencialInvalida("erro"))
        dados = DadosPagador(nome="Teste", documento="123", email="t@t.com")
        with self.assertRaises(CredencialInvalida):
            self.gw.registrar_pagador(dados)

    def test_programar_status(self):
        self.gw.programar_status(StatusPagamento.CONFIRMADO)
        pedido = PedidoCobranca(
            referencia=uuid4(),
            pagador_id_externo="cus_test",
            valor=Decimal("100.00"),
            vencimento="",
            forma="PIX",
            repasses=[],
        )
        cobranca = self.gw.criar_cobranca(pedido)
        self.assertEqual(cobranca.status, StatusPagamento.CONFIRMADO)

    def test_marcar_como_paga(self):
        pedido = PedidoCobranca(
            referencia=uuid4(),
            pagador_id_externo="cus_test",
            valor=Decimal("100.00"),
            vencimento="",
            forma="PIX",
            repasses=[],
        )
        cobranca = self.gw.criar_cobranca(pedido)
        self.gw.marcar_como_paga(cobranca.id_externo)
        resultado = self.gw.consultar_cobranca(cobranca.id_externo)
        self.assertEqual(resultado.status, StatusPagamento.PAGO)

    def test_marcar_como_paga_nao_encontrada(self):
        with self.assertRaises(CobrancaNaoEncontrada):
            self.gw.marcar_como_paga("pay_nao_existe")

    def test_erro_desaparece_apos_uma_chamada(self):
        self.gw.programar_erro(CredencialInvalida("erro"))
        dados = DadosPagador(nome="Teste", documento="123", email="t@t.com")
        with self.assertRaises(CredencialInvalida):
            self.gw.registrar_pagador(dados)
        id_ext = self.gw.registrar_pagador(dados)
        self.assertTrue(id_ext.startswith("cus_"))
