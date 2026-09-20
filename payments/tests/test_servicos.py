from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from appointments.models import Appointment
from payments.aplicacao.servicos import (
    aplicar_transicao,
    criar_pagamento,
    solicitar_estorno,
)
from payments.dominio.estados import StatusPagamento
from payments.dominio.excecoes import RegraPagamentoViolada
from payments.models import OutboxMensagem, Pagador, Pagamento, Repasse
from professionals.models import Professional


class CriarPagamentoTest(TestCase):
    def setUp(self):
        self.profissional = Professional.objects.create(
            nome_social="Dra Ana",
            profissao="Medica",
            logradouro="Rua 1",
            numero="100",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="ana@test.com",
            carteira_repasse_id="wallet_123",
        )
        self.consulta = Appointment.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
            valor=Decimal("150.00"),
        )
        self.pagador = Pagador.objects.create(
            nome="Paciente",
            documento_mascarado="***.***.***-12",
            email="pac@test.com",
            id_externo="cus_test",
        )

    def test_criar_pagamento_sucesso(self):
        pagamento = criar_pagamento(
            consulta_id=self.consulta.id,
            pagador_id=self.pagador.id,
        )
        self.assertEqual(pagamento.status, "AGUARDANDO_ENVIO")
        self.assertEqual(pagamento.valor, Decimal("150.00"))
        self.assertTrue(OutboxMensagem.objects.filter(pagamento=pagamento).exists())
        self.assertTrue(Repasse.objects.filter(pagamento=pagamento).exists())

    def test_criar_pagamento_consulta_cancelada(self):
        self.consulta.status = "cancelada"
        self.consulta.save()
        with self.assertRaises(RegraPagamentoViolada):
            criar_pagamento(
                consulta_id=self.consulta.id,
                pagador_id=self.pagador.id,
            )

    def test_criar_pagamento_sem_valor(self):
        consulta = Appointment.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=2),
            status="agendada",
        )
        with self.assertRaises(RegraPagamentoViolada):
            criar_pagamento(
                consulta_id=consulta.id,
                pagador_id=self.pagador.id,
            )

    def test_criar_pagamento_profissional_sem_carteira(self):
        prof = Professional.objects.create(
            nome_social="Dr Teste",
            profissao="Medico",
            logradouro="Rua 2",
            numero="200",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="test@test.com",
        )
        consulta = Appointment.objects.create(
            profissional=prof,
            data_hora=timezone.now() + timedelta(days=3),
            status="agendada",
            valor=Decimal("100.00"),
        )
        with self.assertRaises(RegraPagamentoViolada):
            criar_pagamento(
                consulta_id=consulta.id,
                pagador_id=self.pagador.id,
            )

    def test_repasse_criado_com_carteira_correta(self):
        pagamento = criar_pagamento(
            consulta_id=self.consulta.id,
            pagador_id=self.pagador.id,
        )
        repasse = Repasse.objects.get(pagamento=pagamento)
        self.assertEqual(repasse.carteira_id, "wallet_123")
        self.assertEqual(repasse.status, "PENDENTE")

    def test_outbox_mensagem_criada(self):
        pagamento = criar_pagamento(
            consulta_id=self.consulta.id,
            pagador_id=self.pagador.id,
        )
        msg = OutboxMensagem.objects.get(pagamento=pagamento)
        self.assertEqual(msg.tipo, "CRIAR_COBRANCA")
        self.assertEqual(msg.status, "PENDENTE")


class SolicitarEstornoTest(TestCase):
    def setUp(self):
        self.profissional = Professional.objects.create(
            nome_social="Dra Ana",
            profissao="Medica",
            logradouro="Rua 1",
            numero="100",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="ana@test.com",
            carteira_repasse_id="wallet_123",
        )
        self.consulta = Appointment.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
            valor=Decimal("150.00"),
        )
        self.pagador = Pagador.objects.create(
            nome="Paciente",
            documento_mascarado="***.***.***-12",
            email="pac@test.com",
            id_externo="cus_test",
        )

    def test_estorno_de_confirmado(self):
        pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("150.00"),
            status="CONFIRMADO",
            id_externo="pay_123",
        )
        Repasse.objects.create(
            pagamento=pagamento,
            profissional=self.profissional,
            carteira_id="wallet_123",
            percentual=Decimal("80"),
            valor_estimado=Decimal("120.00"),
        )
        resultado = solicitar_estorno(pagamento.id)
        self.assertEqual(resultado.status, "ESTORNO_EM_ANDAMENTO")
        self.assertTrue(OutboxMensagem.objects.filter(pagamento=pagamento, tipo="SOLICITAR_ESTORNO").exists())
        repasse = Repasse.objects.get(pagamento=pagamento)
        self.assertEqual(repasse.status, "CANCELADO")

    def test_estorno_de_pago(self):
        pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("150.00"),
            status="PAGO",
            id_externo="pay_123",
        )
        resultado = solicitar_estorno(pagamento.id)
        self.assertEqual(resultado.status, "ESTORNO_EM_ANDAMENTO")

    def test_estorno_de_pendente_retorna_erro(self):
        pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("150.00"),
            status="PENDENTE",
        )
        with self.assertRaises(RegraPagamentoViolada):
            solicitar_estorno(pagamento.id)


class AplicarTransicaoTest(TestCase):
    def setUp(self):
        self.profissional = Professional.objects.create(
            nome_social="Dra Ana",
            profissao="Medica",
            logradouro="Rua 1",
            numero="100",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="ana@test.com",
            carteira_repasse_id="wallet_123",
        )
        self.consulta = Appointment.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
            valor=Decimal("150.00"),
        )
        self.pagador = Pagador.objects.create(
            nome="Paciente",
            documento_mascarado="***.***.***-12",
            email="pac@test.com",
        )

    def test_transicao_valida(self):
        pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("150.00"),
            status="AGUARDANDO_ENVIO",
        )
        resultado = aplicar_transicao(pagamento, StatusPagamento.PENDENTE)
        self.assertTrue(resultado)
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, "PENDENTE")

    def test_transicao_mesmo_status(self):
        pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("150.00"),
            status="PENDENTE",
        )
        resultado = aplicar_transicao(pagamento, StatusPagamento.PENDENTE)
        self.assertFalse(resultado)

    def test_transicao_com_id_externo(self):
        pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("150.00"),
            status="AGUARDANDO_ENVIO",
        )
        aplicar_transicao(pagamento, StatusPagamento.PENDENTE, id_externo="pay_abc")
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.id_externo, "pay_abc")

    def test_transicao_confirmado_atualiza_repasse(self):
        pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("150.00"),
            status="PENDENTE",
            id_externo="pay_123",
        )
        Repasse.objects.create(
            pagamento=pagamento,
            profissional=self.profissional,
            carteira_id="wallet_123",
            percentual=Decimal("80"),
            valor_estimado=Decimal("120.00"),
        )
        aplicar_transicao(pagamento, StatusPagamento.CONFIRMADO)
        repasse = Repasse.objects.get(pagamento=pagamento)
        self.assertEqual(repasse.status, "CONCLUIDO")

    def test_transicao_invalida_retorna_false(self):
        pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("150.00"),
            status="CANCELADO",
        )
        resultado = aplicar_transicao(pagamento, StatusPagamento.PAGO)
        self.assertFalse(resultado)
