from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from appointments.models import Appointment
from payments.dominio.excecoes import GatewayIndisponivel
from payments.models import Pagador, Pagamento


class PagadorAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)
        self.valid_data = {
            "nome": "Joao Silva",
            "documento": "52998224725",
            "email": "joao@example.com",
        }

    def test_criar_pagador(self):
        response = self.client.post("/api/v1/pagadores/", self.valid_data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["nome"], "Joao Silva")
        self.assertEqual(response.data["documento_mascarado"], "***.***.***-25")

    def test_criar_pagador_cpf_invalido(self):
        data = self.valid_data.copy()
        data["documento"] = "12345678901"
        response = self.client.post("/api/v1/pagadores/", data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_criar_pagador_cpf_todos_iguais(self):
        data = self.valid_data.copy()
        data["documento"] = "11111111111"
        response = self.client.post("/api/v1/pagadores/", data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_criar_pagador_cpf_com_digitos_invalidos(self):
        data = self.valid_data.copy()
        data["documento"] = "52998224724"
        response = self.client.post("/api/v1/pagadores/", data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_criar_pagador_cpf_curto(self):
        data = self.valid_data.copy()
        data["documento"] = "123"
        response = self.client.post("/api/v1/pagadores/", data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_listar_pagadores(self):
        Pagador.objects.create(nome="P1", documento_mascarado="***.***.***-12", email="p1@test.com")
        response = self.client.get("/api/v1/pagadores/")
        self.assertEqual(response.status_code, 200)

    def test_detalhar_pagador(self):
        pagador = Pagador.objects.create(nome="P1", documento_mascarado="***.***.***-12", email="p1@test.com")
        response = self.client.get(f"/api/v1/pagadores/{pagador.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["documento_mascarado"], "***.***.***-12")

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/pagadores/")
        self.assertEqual(response.status_code, 401)

    @patch("payments.adaptadores.fake.FakeGateway.registrar_pagador", side_effect=GatewayIndisponivel("offline"))
    def test_gateway_indisponivel(self, _register):
        response = self.client.post("/api/v1/pagadores/", self.valid_data, format="json")
        self.assertEqual(response.status_code, 500)


class PagamentoAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)

    def test_listar_pagamentos(self):
        response = self.client.get("/api/v1/pagamentos/")
        self.assertEqual(response.status_code, 200)

    def test_detalhar_pagamento_inexistente(self):
        fake_id = uuid4()
        response = self.client.get(f"/api/v1/pagamentos/{fake_id}/")
        self.assertEqual(response.status_code, 404)


class CriarPagamentoConsultaTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)

        from professionals.models import Professional

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

    def test_criar_pagamento_para_consulta(self):
        response = self.client.post(
            f"/api/v1/consultas/{self.consulta.id}/pagamentos/",
            {"pagador_id": str(self.pagador.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "AGUARDANDO_ENVIO")

    def test_criar_pagamento_consulta_sem_valor(self):
        consulta = Appointment.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=2),
            status="agendada",
        )
        response = self.client.post(
            f"/api/v1/consultas/{consulta.id}/pagamentos/",
            {"pagador_id": str(self.pagador.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 422)

    def test_criar_pagamento_consulta_cancelada(self):
        consulta = Appointment.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=2),
            status="cancelada",
            valor=Decimal("100.00"),
        )
        response = self.client.post(
            f"/api/v1/consultas/{consulta.id}/pagamentos/",
            {"pagador_id": str(self.pagador.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 422)

    def test_criar_pagamento_profissional_sem_carteira(self):
        from professionals.models import Professional

        prof_sem_carteira = Professional.objects.create(
            nome_social="Dr Bruno",
            profissao="Medico",
            logradouro="Rua 2",
            numero="200",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="bruno@test.com",
        )
        consulta = Appointment.objects.create(
            profissional=prof_sem_carteira,
            data_hora=timezone.now() + timedelta(days=3),
            status="agendada",
            valor=Decimal("100.00"),
        )
        response = self.client.post(
            f"/api/v1/consultas/{consulta.id}/pagamentos/",
            {"pagador_id": str(self.pagador.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 422)

    def test_criar_pagamento_consulta_inexistente(self):
        fake_id = uuid4()
        response = self.client.post(
            f"/api/v1/consultas/{fake_id}/pagamentos/",
            {"pagador_id": str(self.pagador.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 404)


class EstornoAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)

        from professionals.models import Professional

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
        self.pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("150.00"),
            status="CONFIRMADO",
            id_externo="pay_123",
        )

    def test_solicitar_estorno_confirmado(self):
        response = self.client.post(
            f"/api/v1/pagamentos/{self.pagamento.id}/estorno/",
            format="json",
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "ESTORNO_EM_ANDAMENTO")

    def test_solicitar_estorno_pendente_retorna_422(self):
        Pagamento.objects.filter(id=self.pagamento.id).update(status="CANCELADO")
        pagamento = Pagamento.objects.create(
            consulta=self.consulta,
            pagador=self.pagador,
            valor=Decimal("100.00"),
            status="PENDENTE",
            id_externo="pay_456",
        )
        response = self.client.post(
            f"/api/v1/pagamentos/{pagamento.id}/estorno/",
            format="json",
        )
        self.assertEqual(response.status_code, 422)

    def test_solicitar_estorno_pagamento_inexistente(self):
        fake_id = uuid4()
        response = self.client.post(
            f"/api/v1/pagamentos/{fake_id}/estorno/",
            format="json",
        )
        self.assertEqual(response.status_code, 404)


class WebhookAPITest(APITestCase):
    def test_webhook_payload_invalido_com_token(self):
        response = self.client.post(
            "/api/v1/webhooks/asaas/",
            {"status": "INVALID"},
            format="json",
            HTTP_ASAAS_ACCESS_TOKEN="token123",
        )
        self.assertEqual(response.status_code, 200)

    def test_webhook_sem_token_retorna_401(self):
        response = self.client.post(
            "/api/v1/webhooks/asaas/",
            {"payment": {"id": "pay_123"}},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_webhook_com_token_valido(self):
        response = self.client.post(
            "/api/v1/webhooks/asaas/",
            {
                "id": "evt_123",
                "type": "PAYMENT_RECEIVED",
                "payment": {
                    "id": "pay_123",
                    "status": "RECEIVED",
                    "externalReference": str(uuid4()),
                },
            },
            format="json",
            HTTP_ASAAS_ACCESS_TOKEN="token123",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["recebido"], True)

    def test_webhook_duplicado_idempotente(self):
        event_data = {
            "id": "evt_dup",
            "type": "PAYMENT_RECEIVED",
            "payment": {
                "id": "pay_dup",
                "status": "RECEIVED",
                "externalReference": str(uuid4()),
            },
        }
        response1 = self.client.post(
            "/api/v1/webhooks/asaas/",
            event_data,
            format="json",
            HTTP_ASAAS_ACCESS_TOKEN="token123",
        )
        response2 = self.client.post(
            "/api/v1/webhooks/asaas/",
            event_data,
            format="json",
            HTTP_ASAAS_ACCESS_TOKEN="token123",
        )
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

    def test_webhook_sem_dados_retorna_400(self):
        response = self.client.post(
            "/api/v1/webhooks/asaas/",
            data="",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
