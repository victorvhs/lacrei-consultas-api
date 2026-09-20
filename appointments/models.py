import uuid

from django.db import models

from professionals.models import Professional


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("agendada", "Agendada"),
        ("realizada", "Realizada"),
        ("cancelada", "Cancelada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profissional = models.ForeignKey(
        Professional, on_delete=models.PROTECT, related_name="appointments"
    )
    data_hora = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="agendada")
    valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_hora"]

    def __str__(self):
        return f"{self.profissional} - {self.data_hora}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone

        errors = {}

        if not self.pk and self.data_hora <= timezone.now():
            errors["data_hora"] = "data_hora deve ser no futuro."

        if self.valor is not None and self.valor <= 0:
            errors["valor"] = "valor deve ser maior que zero."

        duplicate = Appointment.objects.filter(
            profissional=self.profissional,
            data_hora=self.data_hora,
        ).exclude(status="cancelada")
        if self.pk:
            duplicate = duplicate.exclude(pk=self.pk)
        if duplicate.exists():
            errors["data_hora"] = "Já existe consulta não cancelada neste horário."

        if errors:
            raise ValidationError(errors)
