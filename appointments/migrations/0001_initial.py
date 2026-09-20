import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("professionals", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Appointment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("data_hora", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[("agendada", "Agendada"), ("realizada", "Realizada"), ("cancelada", "Cancelada")],
                        default="agendada",
                        max_length=20,
                    ),
                ),  # noqa: E501
                ("valor", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "profissional",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="appointments",
                        to="professionals.professional",
                    ),
                ),  # noqa: E501
            ],
            options={
                "ordering": ["-data_hora"],
            },
        ),
    ]
