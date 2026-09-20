from decimal import Decimal
from uuid import uuid4

import respx
from django.test import SimpleTestCase
from httpx import Response

from payments.adaptadores.asaas.gateway import AsaasGateway
from payments.dominio.estados import StatusPagamento
from payments.dominio.excecoes import (
    CobrancaNaoEncontrada,
    CredencialInvalida,
    GatewayIndisponivel,
    LimiteDeRequisicoes,
    RequisicaoRecusada,
)
from payments.portas import DadosPagador, PedidoCobranca


class AsaasGatewayTest(SimpleTestCase):
    def setUp(self):
        self.reference = uuid4()
        self.pedido = PedidoCobranca(
            referencia=self.reference,
            pagador_id_externo="cus_1",
            valor=Decimal("100.00"),
            vencimento="2026-12-01",
            forma="PIX",
            repasses=[],
        )

    @property
    def gateway(self):
        # Create the client inside each respx context so httpx is intercepted.
        return AsaasGateway("https://asaas.test", "api-key", ["token123"])

    @respx.mock
    def test_registrar_pagador(self):
        route = respx.post("https://asaas.test/v3/customers").mock(return_value=Response(200, json={"id": "cus_1"}))
        result = self.gateway.registrar_pagador(DadosPagador("Nome", "123", "n@example.com"))
        self.assertEqual(result, "cus_1")
        self.assertTrue(route.called)

    @respx.mock
    def test_criar_cobranca(self):
        respx.post("https://asaas.test/v3/payments").mock(
            return_value=Response(
                200,
                json={
                    "id": "pay_1",
                    "status": "PENDING",
                    "value": 100,
                    "invoiceUrl": "https://pay.test/1",
                },
            )
        )
        result = self.gateway.criar_cobranca(self.pedido)
        self.assertEqual(result.id_externo, "pay_1")
        self.assertEqual(result.status, StatusPagamento.PENDENTE)

    @respx.mock
    def test_buscar_e_consultar_cobranca(self):
        respx.get("https://asaas.test/v3/payments").mock(
            return_value=Response(200, json={"data": [{"id": "pay_1", "status": "RECEIVED", "value": 100}]})
        )
        result = self.gateway.buscar_por_referencia(self.reference)
        self.assertEqual(result.status, StatusPagamento.PAGO)

        respx.get("https://asaas.test/v3/payments/pay_1").mock(
            return_value=Response(200, json={"id": "pay_1", "status": "OVERDUE", "value": 100})
        )
        result = self.gateway.consultar_cobranca("pay_1")
        self.assertEqual(result.status, StatusPagamento.VENCIDO)

    @respx.mock
    def test_estorno(self):
        respx.post("https://asaas.test/v3/payments/pay_1/refund").mock(return_value=Response(200))
        self.gateway.solicitar_estorno("pay_1")

    def test_autenticacao_e_traducao_webhook(self):
        self.assertTrue(self.gateway.autenticar_notificacao({"asaas-access-token": "token123"}))
        self.assertFalse(self.gateway.autenticar_notificacao({"asaas-access-token": "bad"}))
        notification = self.gateway.traduzir_notificacao(
            b'{"id":"evt_1","type":"PAYMENT_RECEIVED","payment":{"id":"pay_1","status":"RECEIVED"}}'
        )
        self.assertEqual(notification.status, StatusPagamento.PAGO)

    @respx.mock
    def test_mapeia_erros_http(self):
        errors = (
            (401, CredencialInvalida),
            (429, LimiteDeRequisicoes),
            (404, CobrancaNaoEncontrada),
            (500, GatewayIndisponivel),
        )
        for code, exception in errors:
            respx.post("https://asaas.test/v3/payments").mock(return_value=Response(code))
            with self.assertRaises(exception):
                self.gateway.criar_cobranca(self.pedido)
            respx.reset()

    @respx.mock
    def test_mapeia_recusa_e_timeout(self):
        respx.post("https://asaas.test/v3/payments").mock(
            return_value=Response(422, json={"errors": [{"description": "invalid"}]})
        )
        with self.assertRaises(RequisicaoRecusada):
            self.gateway.criar_cobranca(self.pedido)

        route = respx.post("https://asaas.test/v3/payments").mock(side_effect=TimeoutError())
        with self.assertRaises(Exception):
            self.gateway.criar_cobranca(self.pedido)
        self.assertTrue(route.called)
