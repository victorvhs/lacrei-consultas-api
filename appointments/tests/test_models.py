from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from appointments.models import Appointment
from professionals.models import Professional


class AppointmentModelTest(TestCase):
    def setUp(self):
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

    def test_create_valid_appointment(self):
        appointment = Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
            valor=150.00,
        )
        appointment.clean()
        
        self.assertIsNotNone(appointment.id)
        self.assertEqual(appointment.status, "agendada")

    def test_rejects_past_date_on_create(self):
        appointment = Appointment(
            profissional=self.professional,
            data_hora=timezone.now() - timedelta(days=1),
            status="agendada",
        )
        
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            appointment.clean()
        self.assertIn("data_hora", ctx.exception.message_dict)

    def test_rejects_negative_valor(self):
        appointment = Appointment(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
            valor=-10.00,
        )
        
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            appointment.clean()
        self.assertIn("valor", ctx.exception.message_dict)

    def test_rejects_zero_valor(self):
        appointment = Appointment(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
            valor=0,
        )
        
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            appointment.clean()
        self.assertIn("valor", ctx.exception.message_dict)

    def test_accepts_none_valor(self):
        appointment = Appointment.objects.create(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
            status="agendada",
        )
        appointment.clean()
        
        self.assertIsNone(appointment.valor)

    def test_rejects_duplicate_non_cancelled(self):
        time = timezone.now() + timedelta(days=1)
        
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=time,
            status="agendada",
        )
        
        duplicate = Appointment(
            profissional=self.professional,
            data_hora=time,
            status="agendada",
        )
        
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            duplicate.clean()
        self.assertIn("data_hora", ctx.exception.message_dict)

    def test_allows_duplicate_if_cancelled(self):
        time = timezone.now() + timedelta(days=1)
        
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=time,
            status="cancelada",
        )
        
        new_appointment = Appointment(
            profissional=self.professional,
            data_hora=time,
            status="agendada",
        )
        new_appointment.clean()
        
    def test_allows_same_time_different_professional(self):
        time = timezone.now() + timedelta(days=1)
        
        Appointment.objects.create(
            profissional=self.professional,
            data_hora=time,
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
        
        new_appointment = Appointment(
            profissional=other_professional,
            data_hora=time,
            status="agendada",
        )
        new_appointment.clean()

    def test_can_transition_agendada_to_realizada(self):
        appointment = Appointment(status="agendada")
        self.assertTrue(appointment.can_transition_to("realizada"))

    def test_can_transition_agendada_to_cancelada(self):
        appointment = Appointment(status="agendada")
        self.assertTrue(appointment.can_transition_to("cancelada"))

    def test_cannot_transition_cancelada_to_agendada(self):
        appointment = Appointment(status="cancelada")
        self.assertFalse(appointment.can_transition_to("agendada"))

    def test_cannot_transition_realizada_to_agendada(self):
        appointment = Appointment(status="realizada")
        self.assertFalse(appointment.can_transition_to("agendada"))

    def test_can_transition_to_same_status(self):
        appointment = Appointment(status="agendada")
        self.assertTrue(appointment.can_transition_to("agendada"))

    def test_str_representation(self):
        appointment = Appointment(
            profissional=self.professional,
            data_hora=timezone.now() + timedelta(days=1),
        )
        expected = f"{self.professional} - {appointment.data_hora}"
        self.assertEqual(str(appointment), expected)
