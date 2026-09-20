import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('appointments', '0001_initial'),
        ('professionals', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pagador',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=200)),
                ('documento_mascarado', models.CharField(max_length=20)),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('id_externo', models.CharField(blank=True, default='', max_length=64)),
                ('gateway', models.CharField(default='fake', max_length=32)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='Pagamento',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('valor', models.DecimalField(decimal_places=2, max_digits=10)),
                ('forma', models.CharField(choices=[('PIX', 'PIX'), ('BOLETO', 'Boleto'), ('ESCOLHA_DO_PAGADOR', 'Escolha do Pagador')], default='PIX', max_length=32)),  # noqa: E501
                ('vencimento', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('AGUARDANDO_ENVIO', 'Aguardando Envio'), ('FALHA_ENVIO', 'Falha no Envio'), ('PENDENTE', 'Pendente'), ('CONFIRMADO', 'Confirmado'), ('PAGO', 'Pago'), ('VENCIDO', 'Vencido'), ('CANCELADO', 'Cancelado'), ('ESTORNO_EM_ANDAMENTO', 'Estorno em Andamento'), ('ESTORNADO', 'Estornado'), ('EM_DISPUTA', 'Em Disputa')], default='AGUARDANDO_ENVIO', max_length=32)),  # noqa: E501
                ('gateway', models.CharField(default='fake', max_length=32)),
                ('id_externo', models.CharField(blank=True, default='', max_length=64)),
                ('url_pagamento', models.URLField(blank=True, default='', max_length=500)),
                ('motivo_falha', models.TextField(blank=True, default='')),
                ('versao', models.IntegerField(default=1)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('consulta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos', to='appointments.appointment')),  # noqa: E501
                ('pagador', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos', to='payments.pagador')),  # noqa: E501
            ],
            options={
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddConstraint(
            model_name='pagamento',
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=['CANCELADO', 'ESTORNADO', 'FALHA_ENVIO'], _negated=True),
                fields=('consulta',),
                name='unico_pagamento_ativo_por_consulta',
            ),
        ),
        migrations.CreateModel(
            name='Repasse',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('carteira_id', models.CharField(max_length=64)),
                ('percentual', models.DecimalField(decimal_places=2, max_digits=5)),
                ('valor_estimado', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(choices=[('PENDENTE', 'Pendente'), ('AGUARDANDO_CREDITO', 'Aguardando Crédito'), ('CONCLUIDO', 'Concluído'), ('CANCELADO', 'Cancelado'), ('RECUSADO', 'Recusado')], default='PENDENTE', max_length=32)),  # noqa: E501
                ('motivo_recusa', models.TextField(blank=True, default='')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('pagamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repasses', to='payments.pagamento')),  # noqa: E501
                ('profissional', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='repasses', to='professionals.professional')),  # noqa: E501
            ],
            options={
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='OutboxMensagem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tipo', models.CharField(choices=[('CRIAR_COBRANCA', 'Criar Cobrança'), ('SOLICITAR_ESTORNO', 'Solicitar Estorno')], max_length=32)),  # noqa: E501
                ('versao_payload', models.IntegerField(default=1)),
                ('status', models.CharField(choices=[('PENDENTE', 'Pendente'), ('PROCESSANDO', 'Processando'), ('CONCLUIDA', 'Concluída'), ('FALHOU', 'Falhou')], default='PENDENTE', max_length=16)),  # noqa: E501
                ('tentativas', models.IntegerField(default=0)),
                ('proxima_tentativa_em', models.DateTimeField(blank=True, null=True)),
                ('ultimo_erro', models.TextField(blank=True, default='')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('pagamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outbox_mensagens', to='payments.pagamento')),  # noqa: E501
            ],
            options={
                'ordering': ['criado_em'],
            },
        ),
        migrations.AddIndex(
            model_name='outboxmensagem',
            index=models.Index(
                condition=models.Q(status__in=['PENDENTE', 'PROCESSANDO']),
                fields=['status', 'proxima_tentativa_em'],
                name='idx_outbox_pendente',
            ),
        ),
        migrations.CreateModel(
            name='EventoRecebido',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('gateway', models.CharField(default='fake', max_length=32)),
                ('event_id', models.CharField(max_length=128)),
                ('tipo', models.CharField(blank=True, default='', max_length=64)),
                ('corpo', models.JSONField(default=dict)),
                ('status', models.CharField(choices=[('RECEBIDO', 'Recebido'), ('PROCESSADO', 'Processado'), ('IGNORADO', 'Ignorado'), ('ERRO', 'Erro')], default='RECEBIDO', max_length=16)),  # noqa: E501
                ('tentativas', models.IntegerField(default=0)),
                ('recebido_em', models.DateTimeField(auto_now_add=True)),
                ('processado_em', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-recebido_em'],
            },
        ),
        migrations.AddConstraint(
            model_name='eventorecebido',
            constraint=models.UniqueConstraint(fields=('gateway', 'event_id'), name='unico_event_id_por_gateway'),
        ),
    ]
