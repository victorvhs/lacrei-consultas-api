import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Professional",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("nome_social", models.CharField(max_length=150)),
                ("profissao", models.CharField(max_length=100)),
                ("logradouro", models.CharField(max_length=200)),
                ("numero", models.CharField(max_length=20)),
                ("complemento", models.CharField(blank=True, default="", max_length=100)),
                ("bairro", models.CharField(max_length=100)),
                ("cidade", models.CharField(max_length=100)),
                ("uf", models.CharField(max_length=2)),
                ("cep", models.CharField(max_length=8)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                ("telefone", models.CharField(blank=True, default="", max_length=11)),
                ("carteira_repasse_id", models.CharField(blank=True, default="", max_length=64)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-criado_em"],
            },
        ),
    ]
