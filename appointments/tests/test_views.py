import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from appointments.models import Appointment
from professionals.models import Professional


class AppointmentAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)

        self.professional = Professional.objects.create(
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

        self.future_date = (timezone.now() + timedelta(days=1)).isoformat()
        self.valid_data = {
            "profissional_id": str(self.professional.id),
            "data_hora": self.future_date,
            "valor": "150.00",
        }

    def test_create_appointment(self):
        response = self.client.post("/api/v1/consultas/", self.valid_data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["status"], "agendada")

    def test_create_appointment_without_valor(self):
        data = self.valid_data.copy()
        del data["valor"]

        response = self.client.post("/api/v1/consultas/", data, format="json")

        self.assertEqual(response.status_code, 201)

    def test_create_appointment_past_date(self):
        data = self.valid_data.copy()
        data["data_hora"] = (timezone.now() - timedelta(days=1)).isoformat()

        response = self.client.post("/api/v1/consultas/", data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_create_appointment_negative_valor(self):
        data = self.valid_data.copy()
        data["valor"] = "-10.00"

        response = self.client.post("/api/v1/consultas/", data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_create_appointment_zero_valor(self):
        data = self.valid_data.copy()
        data["valor"] = "0"

        response = self.client.post("/api/v1/consultas/", data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_create_appointment_nonexistent_professional(self):
        data = self.valid_data.copy()
        data["profissional_id"] = str(uuid.uuid4())

        response = self.client.post("/api/v1/consultas/", data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_create_appointment_invalid_professional_id(self):
        data = self.valid_data.copy()
        data["profissional_id"] = "not-a-uuid"

        response = self.client.post("/api/v1/consultas/", data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_create_appointment_duplicate_time(self):
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )

        response = self.client.post("/api/v1/consultas/", self.valid_data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_create_appointment_same_time_cancelled(self):
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="cancelada",
        )

        response = self.client.post("/api/v1/consultas/", self.valid_data, format="json")

        self.assertEqual(response.status_code, 201)

    def test_list_appointments(self):
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=2),
            status="realizada",
        )

        response = self.client.get("/api/v1/consultas/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_filter_by_profissional_id(self):
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )

        other_professional = Professional.objects.create(
            nome_social="Bruno Santos",
            profissao="Doctor",
            logradouro="Rua 2",
            numero="2",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="bruno@example.com",
        )
        Appointment.objects.create(
            profissional=other_professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )

        response = self.client.get(f"/api/v1/consultas/?profissional_id={self.professional.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_status(self):
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=2),
            status="realizada",
        )

        response = self.client.get("/api/v1/consultas/?status=agendada")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_date_range(self):
        date1 = timezone.now() + timedelta(days=1)
        date2 = timezone.now() + timedelta(days=5)
        date3 = timezone.now() + timedelta(days=10)

        Appointment.objects.create(profissional=self.professional, data_hora=date1, status="agendada")
        Appointment.objects.create(profissional=self.professional, data_hora=date2, status="agendada")
        Appointment.objects.create(profissional=self.professional, data_hora=date3, status="agendada")

        data_inicio = (timezone.now() + timedelta(days=2)).isoformat()
        data_fim = (timezone.now() + timedelta(days=6)).isoformat()

        response = self.client.get(f"/api/v1/consultas/?data_inicio={data_inicio}&data_fim={data_fim}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_filter_nonexistent_professional_returns_empty(self):
        fake_id = uuid.uuid4()
        response = self.client.get(f"/api/v1/consultas/?profissional_id={fake_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_retrieve_appointment(self):
        appointment = Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )

        response = self.client.get(f"/api/v1/consultas/{appointment.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "agendada")

    def test_retrieve_nonexistent_appointment(self):
        fake_id = uuid.uuid4()
        response = self.client.get(f"/api/v1/consultas/{fake_id}/")

        self.assertEqual(response.status_code, 404)

    def test_update_appointment_status(self):
        appointment = Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )

        data = {
            "profissional_id": str(self.professional.id),
            "data_hora": appointment.data_hora.isoformat(),
            "status": "realizada",
        }

        response = self.client.put(f"/api/v1/consultas/{appointment.id}/", data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "realizada")

    def test_update_cancelada_to_agendada_fails(self):
        appointment = Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="cancelada",
        )

        data = {
            "profissional_id": str(self.professional.id),
            "data_hora": appointment.data_hora.isoformat(),
            "status": "agendada",
        }

        response = self.client.put(f"/api/v1/consultas/{appointment.id}/", data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_update_realizada_to_agendada_fails(self):
        appointment = Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="realizada",
        )

        data = {
            "profissional_id": str(self.professional.id),
            "data_hora": appointment.data_hora.isoformat(),
            "status": "agendada",
        }

        response = self.client.put(f"/api/v1/consultas/{appointment.id}/", data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_patch_appointment_status(self):
        appointment = Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )

        response = self.client.patch(
            f"/api/v1/consultas/{appointment.id}/",
            {"status": "cancelada"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "cancelada")

    def test_delete_appointment(self):
        appointment = Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )

        response = self.client.delete(f"/api/v1/consultas/{appointment.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Appointment.objects.filter(id=appointment.id).exists())

    def test_unauthenticated_access_returns_401(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/v1/consultas/")

        self.assertEqual(response.status_code, 401)


class ProfessionalAppointmentsAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)

        self.professional = Professional.objects.create(
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

    def test_list_professional_appointments(self):
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=2),
            status="realizada",
        )

        response = self.client.get(f"/api/v1/profissionais/{self.professional.id}/consultas/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_professional_appointments_empty(self):
        response = self.client.get(f"/api/v1/profissionais/{self.professional.id}/consultas/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_list_appointments_nonexistent_professional(self):
        fake_id = uuid.uuid4()
        response = self.client.get(f"/api/v1/profissionais/{fake_id}/consultas/")

        self.assertEqual(response.status_code, 404)

    def test_list_appointments_invalid_professional_id(self):
        response = self.client.get("/api/v1/profissionais/not-a-uuid/consultas/")

        self.assertEqual(response.status_code, 404)
