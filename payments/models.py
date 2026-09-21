import uuid

from django.db import models

from appointments.models import Appointment
from professionals.models import Professional


class Pagador(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=200)
    documento_mascarado = models.CharField(max_length=20)
    email = models.EmailField(max_length=254, blank=True, default="")
    id_externo = models.CharField(max_length=64, blank=True, default="")
    gateway = models.CharField(max_length=32, default="fake")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome} ({self.documento_mascarado})"


class Pagamento(models.Model):
    STATUS_CHOICES = [
        ("AGUARDANDO_ENVIO", "Aguardando Envio"),
        ("FALHA_ENVIO", "Falha no Envio"),
        ("PENDENTE", "Pendente"),
        ("CONFIRMADO", "Confirmado"),
        ("PAGO", "Pago"),
        ("VENCIDO", "Vencido"),
        ("CANCELADO", "Cancelado"),
        ("ESTORNO_EM_ANDAMENTO", "Estorno em Andamento"),
        ("ESTORNADO", "Estornado"),
        ("EM_DISPUTA", "Em Disputa"),
    ]

    FORMA_CHOICES = [
        ("PIX", "PIX"),
        ("BOLETO", "Boleto"),
        ("ESCOLHA_DO_PAGADOR", "Escolha do Pagador"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consulta = models.ForeignKey(Appointment, on_delete=models.PROTECT, related_name="pagamentos")
    pagador = models.ForeignKey(Pagador, on_delete=models.PROTECT, related_name="pagamentos")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    forma = models.CharField(max_length=32, choices=FORMA_CHOICES, default="PIX")
    vencimento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="AGUARDANDO_ENVIO")
    gateway = models.CharField(max_length=32, default="fake")
    id_externo = models.CharField(max_length=64, blank=True, default="")
    url_pagamento = models.URLField(max_length=500, blank=True, default="")
    motivo_falha = models.TextField(blank=True, default="")
    versao = models.IntegerField(default=1)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["consulta"],
                condition=~models.Q(status__in=["CANCELADO", "ESTORNADO", "FALHA_ENVIO"]),
                name="unico_pagamento_ativo_por_consulta",
            ),
        ]

    def __str__(self):
        return f"Pagamento {self.id} - {self.status}"


class Repasse(models.Model):
    STATUS_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("AGUARDANDO_CREDITO", "Aguardando Crédito"),
        ("CONCLUIDO", "Concluído"),
        ("CANCELADO", "Cancelado"),
        ("RECUSADO", "Recusado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pagamento = models.ForeignKey(Pagamento, on_delete=models.CASCADE, related_name="repasses")
    profissional = models.ForeignKey(Professional, on_delete=models.PROTECT, related_name="repasses")
    carteira_id = models.CharField(max_length=64)
    percentual = models.DecimalField(max_digits=5, decimal_places=2)
    valor_estimado = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="PENDENTE")
    motivo_recusa = models.TextField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Repasse {self.id} - {self.status}"


class OutboxMensagem(models.Model):
    TIPO_CHOICES = [
        ("CRIAR_COBRANCA", "Criar Cobrança"),
        ("SOLICITAR_ESTORNO", "Solicitar Estorno"),
    ]

    STATUS_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("PROCESSANDO", "Processando"),
        ("CONCLUIDA", "Concluída"),
        ("FALHOU", "Falhou"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=32, choices=TIPO_CHOICES)
    pagamento = models.ForeignKey(Pagamento, on_delete=models.CASCADE, related_name="outbox_mensagens")
    versao_payload = models.IntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDENTE")
    tentativas = models.IntegerField(default=0)
    proxima_tentativa_em = models.DateTimeField(null=True, blank=True)
    ultimo_erro = models.TextField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["criado_em"]
        indexes = [
            models.Index(
                fields=["status", "proxima_tentativa_em"],
                condition=models.Q(status__in=["PENDENTE", "PROCESSANDO"]),
                name="idx_outbox_pendente",
            ),
        ]

    def __str__(self):
        return f"Outbox {self.id} - {self.tipo} - {self.status}"


class EventoRecebido(models.Model):
    STATUS_CHOICES = [
        ("RECEBIDO", "Recebido"),
        ("PROCESSADO", "Processado"),
        ("IGNORADO", "Ignorado"),
        ("ERRO", "Erro"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gateway = models.CharField(max_length=32, default="fake")
    event_id = models.CharField(max_length=128)
    tipo = models.CharField(max_length=64, blank=True, default="")
    corpo = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="RECEBIDO")
    tentativas = models.IntegerField(default=0)
    recebido_em = models.DateTimeField(auto_now_add=True)
    processado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-recebido_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["gateway", "event_id"],
                name="unico_event_id_por_gateway",
            ),
        ]

    def __str__(self):
        return f"Evento {self.event_id} - {self.status}"
