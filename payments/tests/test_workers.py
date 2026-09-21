from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from appointments.models import Appointment
from payments.adaptadores.fake import FakeGateway
from payments.dominio.estados import StatusPagamento
from payments.dominio.excecoes import (
    GatewayIndisponivel,
    LimiteDeRequisicoes,
    RequisicaoRecusada,
    ResultadoIncerto,
)
from payments.models import EventoRecebido, OutboxMensagem, Pagador, Pagamento, Repasse
from professionals.models import Professional


class WorkerFixture(TestCase):
    def setUp(self):
        self.profissional = Professional.objects.create(
            nome_social="Dra. Worker",
            profissao="Medica",
            logradouro="Rua 1",
            numero="10",
            bairro="Centro",
            cidade="Sao Paulo",
            uf="SP",
            cep="01001000",
            email="worker@example.com",
            carteira_repasse_id="wallet-worker",
        )
        self.consulta = Appointment.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
            valor=Decimal("100.00"),
        )
        self.pagador = Pagador.objects.create(
            nome="Pagador Worker",
            documento_mascarado="***.***.***-25",
            email="payer@example.com",
            id_externo="cus-worker",
        )
        self.pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("100.00"),
            status=StatusPagamento.AGUARDANDO_ENVIO.value,
        )
        self.repasse = Repasse.objects.create(
            pagamento=self.pagamento,
            profissional=self.profissional,
            carteira_id="wallet-worker",
            percentual=Decimal("80.00"),
            valor_estimado=Decimal("80.00"),
        )

    def outbox(self, tipo="CRIAR_COBRANCA", status="PENDENTE"):
        return OutboxMensagem.objects.create(
            tipo=tipo,
            pagamento=self.pagamento,
            status=status,
            proxima_tentativa_em=timezone.now() - timedelta(minutes=1),
        )


class OutboxWorkerTest(WorkerFixture):
    @patch("payments.management.commands.processar_outbox.settings.PAYMENT_GATEWAY", "asaas")
    @patch("payments.adaptadores.asaas.gateway.AsaasGateway")
    def test_factory_asaas(self, gateway_class):
        from payments.management.commands.processar_outbox import get_gateway

        get_gateway()
        gateway_class.assert_called_once()

    @patch("payments.management.commands.processar_outbox.get_gateway")
    def test_processa_cobranca_com_sucesso(self, get_gateway):
        gateway = FakeGateway()
        get_gateway.return_value = gateway
        mensagem = self.outbox()

        call_command("processar_outbox")

        mensagem.refresh_from_db()
        self.pagamento.refresh_from_db()
        self.assertEqual(mensagem.status, "CONCLUIDA")
        self.assertEqual(self.pagamento.status, StatusPagamento.PENDENTE.value)
        self.assertTrue(self.pagamento.id_externo.startswith("pay_"))

    @patch("payments.management.commands.processar_outbox.get_gateway")
    def test_reagenda_gateway_indisponivel(self, get_gateway):
        gateway = MagicMock()
        gateway.criar_cobranca.side_effect = GatewayIndisponivel("offline")
        get_gateway.return_value = gateway
        mensagem = self.outbox()

        call_command("processar_outbox")

        mensagem.refresh_from_db()
        self.assertEqual(mensagem.status, "PENDENTE")
        self.assertEqual(mensagem.tentativas, 1)
        self.assertIsNotNone(mensagem.proxima_tentativa_em)

    @patch("payments.management.commands.processar_outbox.get_gateway")
    def test_reagenda_limite_de_requisicoes(self, get_gateway):
        gateway = MagicMock()
        gateway.criar_cobranca.side_effect = LimiteDeRequisicoes("429")
        get_gateway.return_value = gateway
        mensagem = self.outbox()

        call_command("processar_outbox")

        mensagem.refresh_from_db()
        self.assertEqual(mensagem.status, "PENDENTE")

    @patch("payments.management.commands.processar_outbox.get_gateway")
    def test_timeout_com_cobranca_encontrada(self, get_gateway):
        gateway = FakeGateway()
        pedido = self._pedido()
        pedido = pedido.__class__(
            referencia=self.pagamento.id,
            pagador_id_externo=pedido.pagador_id_externo,
            valor=pedido.valor,
            vencimento=pedido.vencimento,
            forma=pedido.forma,
            repasses=pedido.repasses,
        )
        gateway.criar_cobranca(pedido)
        gateway.criar_cobranca = MagicMock(side_effect=ResultadoIncerto("timeout"))
        get_gateway.return_value = gateway
        mensagem = self.outbox()

        call_command("processar_outbox")

        mensagem.refresh_from_db()
        self.assertEqual(mensagem.status, "CONCLUIDA")

    @patch("payments.management.commands.processar_outbox.get_gateway")
    def test_timeout_sem_cobranca_reagenda(self, get_gateway):
        gateway = MagicMock()
        gateway.criar_cobranca.side_effect = ResultadoIncerto("timeout")
        gateway.buscar_por_referencia.return_value = None
        get_gateway.return_value = gateway
        mensagem = self.outbox()

        call_command("processar_outbox")

        mensagem.refresh_from_db()
        self.assertEqual(mensagem.status, "PENDENTE")

    @patch("payments.management.commands.processar_outbox.get_gateway")
    def test_recusa_marca_falha_sem_retry(self, get_gateway):
        gateway = MagicMock()
        gateway.criar_cobranca.side_effect = RequisicaoRecusada("wallet invalida")
        get_gateway.return_value = gateway
        mensagem = self.outbox()

        call_command("processar_outbox")

        mensagem.refresh_from_db()
        self.pagamento.refresh_from_db()
        self.assertEqual(mensagem.status, "FALHOU")
        self.assertEqual(self.pagamento.status, StatusPagamento.FALHA_ENVIO.value)

    @patch("payments.management.commands.processar_outbox.get_gateway")
    def test_processa_estorno(self, get_gateway):
        gateway = MagicMock()
        get_gateway.return_value = gateway
        self.pagamento.status = StatusPagamento.ESTORNO_EM_ANDAMENTO.value
        self.pagamento.id_externo = "pay-refund"
        self.pagamento.save()
        mensagem = self.outbox("SOLICITAR_ESTORNO")

        call_command("processar_outbox")

        mensagem.refresh_from_db()
        gateway.solicitar_estorno.assert_called_once_with("pay-refund")
        self.assertEqual(mensagem.status, "CONCLUIDA")

    def test_estorno_sem_id_externo_falha(self):
        mensagem = self.outbox("SOLICITAR_ESTORNO")
        call_command("processar_outbox")
        mensagem.refresh_from_db()
        self.assertEqual(mensagem.status, "FALHOU")

    @patch("payments.management.commands.processar_outbox.get_gateway")
    def test_estorno_recusado_falha(self, get_gateway):
        gateway = MagicMock()
        gateway.solicitar_estorno.side_effect = RequisicaoRecusada("recusado")
        get_gateway.return_value = gateway
        self.pagamento.status = StatusPagamento.ESTORNO_EM_ANDAMENTO.value
        self.pagamento.id_externo = "pay-refund"
        self.pagamento.save()
        message = self.outbox("SOLICITAR_ESTORNO")
        call_command("processar_outbox")
        message.refresh_from_db()
        self.assertEqual(message.status, "FALHOU")

    def test_reagendamento_esgota_tentativas(self):
        from payments.management.commands.processar_outbox import Command

        mensagem = self.outbox()
        mensagem.tentativas = 7
        mensagem.save()
        Command()._reagendar(mensagem, "offline")
        mensagem.refresh_from_db()
        self.pagamento.refresh_from_db()
        self.assertEqual(mensagem.status, "FALHOU")
        self.assertEqual(self.pagamento.status, StatusPagamento.FALHA_ENVIO.value)

    def _pedido(self):
        from payments.portas import PedidoCobranca

        return PedidoCobranca(
            referencia=uuid4(),
            pagador_id_externo="cus-worker",
            valor=Decimal("100.00"),
            vencimento="",
            forma="PIX",
            repasses=[],
        )


class EventWorkerTest(WorkerFixture):
    @patch("payments.management.commands.processar_eventos.settings.PAYMENT_GATEWAY", "asaas")
    @patch("payments.adaptadores.asaas.gateway.AsaasGateway")
    def test_factory_asaas(self, gateway_class):
        from payments.management.commands.processar_eventos import get_gateway

        get_gateway()
        gateway_class.assert_called_once()

    def event(self, tipo="PAYMENT_RECEIVED", body=None):
        return EventoRecebido.objects.create(
            event_id=str(uuid4()),
            tipo=tipo,
            corpo=body or {"payment": {"id": self.pagamento.id_externo}},
        )

    @patch("payments.management.commands.processar_eventos.get_gateway")
    def test_ignora_tipo_desconhecido(self, get_gateway):
        event = self.event("UNKNOWN")
        get_gateway.return_value = FakeGateway()
        call_command("processar_eventos")
        event.refresh_from_db()
        self.assertEqual(event.status, "IGNORADO")

    @patch("payments.management.commands.processar_eventos.get_gateway")
    def test_ignora_pagamento_inexistente(self, get_gateway):
        event = self.event(body={"payment": {"id": "pay-missing"}})
        get_gateway.return_value = FakeGateway()
        call_command("processar_eventos")
        event.refresh_from_db()
        self.assertEqual(event.status, "IGNORADO")

    @patch("payments.management.commands.processar_eventos.get_gateway")
    def test_reagenda_evento_com_erro(self, get_gateway):
        gateway = MagicMock()
        gateway.consultar_cobranca.side_effect = GatewayIndisponivel("offline")
        get_gateway.return_value = gateway
        self.pagamento.id_externo = "pay-error"
        self.pagamento.save()
        event = self.event()
        call_command("processar_eventos")
        event.refresh_from_db()
        self.assertEqual(event.tentativas, 1)

    @patch("payments.management.commands.processar_eventos.get_gateway")
    def test_processa_estado_confirmado(self, get_gateway):
        gateway = MagicMock()
        gateway.consultar_cobranca.return_value = MagicMock(
            status=StatusPagamento.PAGO,
            id_externo="pay-worker",
            url_pagamento="https://pay.test",
        )
        self.pagamento.id_externo = "pay-worker"
        self.pagamento.status = StatusPagamento.PENDENTE.value
        self.pagamento.save()
        get_gateway.return_value = gateway
        event = self.event()

        call_command("processar_eventos")

        event.refresh_from_db()
        self.pagamento.refresh_from_db()
        self.assertEqual(event.status, "PROCESSADO")
        self.assertEqual(self.pagamento.status, StatusPagamento.PAGO.value)

    @patch("payments.management.commands.processar_eventos.get_gateway")
    def test_processa_evento_com_mesmo_estado(self, get_gateway):
        gateway = MagicMock()
        gateway.consultar_cobranca.return_value = MagicMock(
            status=StatusPagamento.AGUARDANDO_ENVIO,
            id_externo="pay-worker",
            url_pagamento="",
        )
        self.pagamento.id_externo = "pay-worker"
        self.pagamento.save()
        get_gateway.return_value = gateway
        event = self.event()
        call_command("processar_eventos")
        event.refresh_from_db()
        self.assertEqual(event.status, "PROCESSADO")

    @patch("payments.management.commands.processar_eventos.get_gateway")
    def test_ignora_divergencia_de_estado(self, get_gateway):
        gateway = MagicMock()
        gateway.consultar_cobranca.return_value = MagicMock(
            status=StatusPagamento.PAGO,
            id_externo="pay-worker",
            url_pagamento="",
        )
        self.pagamento.status = StatusPagamento.CANCELADO.value
        self.pagamento.id_externo = "pay-worker"
        self.pagamento.save()
        get_gateway.return_value = gateway
        event = self.event()
        call_command("processar_eventos")
        event.refresh_from_db()
        self.assertEqual(event.status, "IGNORADO")


class ReconciliationWorkerTest(WorkerFixture):
    @patch("payments.management.commands.reconciliar_pagamentos.settings.PAYMENT_GATEWAY", "asaas")
    @patch("payments.adaptadores.asaas.gateway.AsaasGateway")
    def test_factory_asaas(self, gateway_class):
        from payments.management.commands.reconciliar_pagamentos import get_gateway

        get_gateway()
        gateway_class.assert_called_once()

    @patch("payments.management.commands.reconciliar_pagamentos.get_gateway")
    def test_corrige_pagamento_antigo(self, get_gateway):
        gateway = MagicMock()
        gateway.consultar_cobranca.return_value = MagicMock(
            status=StatusPagamento.PAGO,
            id_externo="pay-reconcile",
            url_pagamento="",
        )
        self.pagamento.status = StatusPagamento.PENDENTE.value
        self.pagamento.id_externo = "pay-reconcile"
        self.pagamento.save()
        Pagamento.objects.filter(id=self.pagamento.id).update(atualizado_em=timezone.now() - timedelta(hours=1))
        get_gateway.return_value = gateway

        call_command("reconciliar_pagamentos", minutos=30)

        self.pagamento.refresh_from_db()
        self.assertEqual(self.pagamento.status, StatusPagamento.PAGO.value)

    @patch("payments.management.commands.reconciliar_pagamentos.get_gateway")
    def test_reconciliacao_ignora_erro_do_gateway(self, get_gateway):
        gateway = MagicMock()
        gateway.consultar_cobranca.side_effect = GatewayIndisponivel("offline")
        self.pagamento.id_externo = "pay-reconcile"
        self.pagamento.save()
        Pagamento.objects.filter(id=self.pagamento.id).update(atualizado_em=timezone.now() - timedelta(hours=1))
        get_gateway.return_value = gateway
        call_command("reconciliar_pagamentos")
        self.pagamento.refresh_from_db()
        self.assertEqual(self.pagamento.status, StatusPagamento.AGUARDANDO_ENVIO.value)


class ExpungeWorkerTest(WorkerFixture):
    def test_expurga_eventos_antigos(self):
        event = EventoRecebido.objects.create(event_id="old-event", corpo={})
        EventoRecebido.objects.filter(id=event.id).update(recebido_em=timezone.now() - timedelta(days=100))
        call_command("expurgar_eventos", dias=90)
        self.assertFalse(EventoRecebido.objects.filter(id=event.id).exists())
