import uuid

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from professionals.models import Professional


class ProfessionalAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)
        self.valid_data = {
            "nome_social": "Ana Souza",
            "profissao": "Psicóloga",
            "endereco": {
                "logradouro": "Rua 10",
                "numero": "250",
                "complemento": "Sala 3",
                "bairro": "Setor Oeste",
                "cidade": "Goiânia",
                "uf": "GO",
                "cep": "74120-020",
            },
            "contato": {
                "email": "ana@example.com",
                "telefone": "(62) 99999-0000",
            },
        }

    def test_create_professional(self):
        response = self.client.post("/api/v1/profissionais/", self.valid_data, format="json")
        
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["nome_social"], "Ana Souza")
        self.assertEqual(response.data["endereco"]["cep"], "74120020")
        self.assertFalse(response.data["repasse_configurado"])

    def test_create_professional_missing_email_and_phone(self):
        data = self.valid_data.copy()
        data["contato"] = {}
        
        response = self.client.post("/api/v1/profissionais/", data, format="json")
        
        self.assertEqual(response.status_code, 400)

    def test_create_professional_only_email(self):
        data = self.valid_data.copy()
        data["contato"] = {"email": "test@example.com"}
        
        response = self.client.post("/api/v1/profissionais/", data, format="json")
        
        self.assertEqual(response.status_code, 201)

    def test_create_professional_only_phone(self):
        data = self.valid_data.copy()
        data["contato"] = {"telefone": "(11) 99999-0000"}
        
        response = self.client.post("/api/v1/profissionais/", data, format="json")
        
        self.assertEqual(response.status_code, 201)

    def test_create_professional_html_injection(self):
        data = self.valid_data.copy()
        data["nome_social"] = "<script>alert('xss')</script>"
        
        response = self.client.post("/api/v1/profissionais/", data, format="json")
        
        self.assertEqual(response.status_code, 400)

    def test_create_professional_invalid_cep(self):
        data = self.valid_data.copy()
        data["endereco"]["cep"] = "123"
        
        response = self.client.post("/api/v1/profissionais/", data, format="json")
        
        self.assertEqual(response.status_code, 400)

    def test_create_professional_invalid_uf(self):
        data = self.valid_data.copy()
        data["endereco"]["uf"] = "XX"
        
        response = self.client.post("/api/v1/profissionais/", data, format="json")
        
        self.assertEqual(response.status_code, 400)

    def test_create_professional_invalid_email(self):
        data = self.valid_data.copy()
        data["contato"]["email"] = "not-an-email"
        
        response = self.client.post("/api/v1/profissionais/", data, format="json")
        
        self.assertEqual(response.status_code, 400)

    def test_create_professional_invalid_phone(self):
        data = self.valid_data.copy()
        data["contato"]["telefone"] = "123"
        
        response = self.client.post("/api/v1/profissionais/", data, format="json")
        
        self.assertEqual(response.status_code, 400)

    def test_list_professionals(self):
        Professional.objects.create(
            nome_social="Prof 1",
            profissao="Doctor",
            logradouro="Rua 1",
            numero="1",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="prof1@example.com",
        )
        Professional.objects.create(
            nome_social="Prof 2",
            profissao="Nurse",
            logradouro="Rua 2",
            numero="2",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="prof2@example.com",
        )
        
        response = self.client.get("/api/v1/profissionais/")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_filter_by_name(self):
        Professional.objects.create(
            nome_social="Ana Silva",
            profissao="Doctor",
            logradouro="Rua 1",
            numero="1",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="ana@example.com",
        )
        Professional.objects.create(
            nome_social="Bruno Santos",
            profissao="Nurse",
            logradouro="Rua 2",
            numero="2",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="bruno@example.com",
        )
        
        response = self.client.get("/api/v1/profissionais/?nome=Ana")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["nome_social"], "Ana Silva")

    def test_retrieve_professional(self):
        prof = Professional.objects.create(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="ana@example.com",
        )
        
        response = self.client.get(f"/api/v1/profissionais/{prof.id}/")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["nome_social"], "Ana Souza")

    def test_retrieve_nonexistent_professional(self):
        fake_id = uuid.uuid4()
        response = self.client.get(f"/api/v1/profissionais/{fake_id}/")
        
        self.assertEqual(response.status_code, 404)

    def test_update_professional_put(self):
        prof = Professional.objects.create(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="ana@example.com",
        )
        
        data = {
            "nome_social": "Ana Souza Updated",
            "profissao": "Psiquiatra",
            "endereco": {
                "logradouro": "Rua Nova",
                "numero": "100",
                "bairro": "Novo Bairro",
                "cidade": "Rio de Janeiro",
                "uf": "RJ",
                "cep": "20000000",
            },
            "contato": {
                "email": "ana.updated@example.com",
            },
        }
        
        response = self.client.put(f"/api/v1/profissionais/{prof.id}/", data, format="json")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["nome_social"], "Ana Souza Updated")

    def test_update_professional_patch(self):
        prof = Professional.objects.create(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="ana@example.com",
        )
        
        data = {"nome_social": "Ana Souza Updated"}
        
        response = self.client.patch(f"/api/v1/profissionais/{prof.id}/", data, format="json")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["nome_social"], "Ana Souza Updated")

    def test_delete_professional_without_appointments(self):
        prof = Professional.objects.create(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="ana@example.com",
        )
        
        response = self.client.delete(f"/api/v1/profissionais/{prof.id}/")
        
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Professional.objects.filter(id=prof.id).exists())

    def test_delete_professional_with_appointments_returns_409(self):
        from appointments.models import Appointment
        from django.utils import timezone
        from datetime import timedelta
        
        prof = Professional.objects.create(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="ana@example.com",
        )
        
        Appointment.objects.create(
            profissional=prof,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )
        
        response = self.client.delete(f"/api/v1/profissionais/{prof.id}/")
        
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "conflict")

    def test_unauthenticated_access_returns_401(self):
        self.client.force_authenticate(user=None)
        
        response = self.client.get("/api/v1/profissionais/")
        
        self.assertEqual(response.status_code, 401)

    def test_repasse_configurado_true_when_carteira_set(self):
        prof = Professional.objects.create(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="ana@example.com",
            carteira_repasse_id="wallet123",
        )
        
        response = self.client.get(f"/api/v1/profissionais/{prof.id}/")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["repasse_configurado"])
