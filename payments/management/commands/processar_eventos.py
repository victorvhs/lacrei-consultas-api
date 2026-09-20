import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from payments.aplicacao.servicos import aplicar_transicao
from payments.dominio.estados import StatusPagamento, eh_alcancavel
from payments.dominio.excecoes import GatewayIndisponivel
from payments.models import EventoRecebido, Pagamento

logger = logging.getLogger(__name__)


def get_gateway():
    gateway_type = getattr(settings, "PAYMENT_GATEWAY", "fake")
    if gateway_type == "fake":
        from payments.adaptadores.fake import FakeGateway

        return FakeGateway()
    else:
        from payments.adaptadores.asaas.gateway import AsaasGateway

        return AsaasGateway(
            base_url=settings.ASAAS_BASE_URL,
            api_key=settings.ASAAS_API_KEY,
            webhook_tokens=settings.ASAAS_WEBHOOK_TOKENS,
        )


TIPOS_DE_INTERESSE = [
    "PAYMENT_CREATED",
    "PAYMENT_UPDATED",
    "PAYMENT_CONFIRMED",
    "PAYMENT_RECEIVED",
    "PAYMENT_OVERDUE",
    "PAYMENT_DELETED",
    "PAYMENT_REFUND_REQUESTED",
    "PAYMENT_REFUNDED",
    "PAYMENT_RECEIVED_IN_CASH",
    "PAYMENT_CHARGEBACK_REQUESTED",
    "PAYMENT_CHARGEBACK_DISPUTE",
]


class Command(BaseCommand):
    help = "Processa eventos recebidos (inbox)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--lote", type=int, default=10, help="Tamanho do lote"
        )

    def handle(self, *args, **options):
        lote_size = options["lote"]
        gateway = get_gateway()

        eventos = (
            EventoRecebido.objects.select_for_update(skip_locked=True)
            .filter(status="RECEBIDO")
            .order_by("recebido_em")[:lote_size]
        )

        with transaction.atomic():
            for evento in eventos:
                try:
                    self._processar_evento(gateway, evento)
                except Exception as e:
                    logger.error(
                        "erro_processar_evento",
                        extra={"erro": str(e), "event_id": evento.event_id},
                    )
                    evento.tentativas += 1
                    if evento.tentativas >= 5:
                        evento.status = "ERRO"
                    evento.save(update_fields=["tentativas", "status", "atualizado_em"])

    def _processar_evento(self, gateway, evento):
        if evento.tipo and evento.tipo not in TIPOS_DE_INTERESSE:
            evento.status = "IGNORADO"
            evento.processado_em = timezone.now()
            evento.save(update_fields=["status", "processado_em", "atualizado_em"])
            return

        referencia = evento.corpo.get("payment", {}).get("externalReference")
        id_externo = evento.corpo.get("payment", {}).get("id")

        pagamento = None
        if id_externo:
            try:
                pagamento = Pagamento.objects.get(id_externo=id_externo)
            except Pagamento.DoesNotExist:
                pass
        if pagamento is None and referencia:
            try:
                pagamento = Pagamento.objects.get(id=referencia)
            except (Pagamento.DoesNotExist, ValueError):
                pass

        if pagamento is None:
            evento.status = "IGNORADO"
            evento.processado_em = timezone.now()
            evento.save(update_fields=["status", "processado_em", "atualizado_em"])
            return

        try:
            cobranca = gateway.consultar_cobranca(
                pagamento.id_externo or id_externo or ""
            )
            novo_status = cobranca.status
        except (GatewayIndisponivel, Exception) as e:
            logger.warning("falha_consulta_gateway", extra={"erro": str(e)})
            raise

        status_atual = StatusPagamento(pagamento.status)

        if novo_status == status_atual:
            evento.status = "PROCESSADO"
            evento.processado_em = timezone.now()
            evento.save(update_fields=["status", "processado_em", "atualizado_em"])
            return

        if eh_alcancavel(status_atual, novo_status):
            aplicar_transicao(
                pagamento,
                novo_status,
                id_externo=cobranca.id_externo,
                url_pagamento=cobranca.url_pagamento,
            )
            evento.status = "PROCESSADO"
            evento.processado_em = timezone.now()
            evento.save(update_fields=["status", "processado_em", "atualizado_em"])
        else:
            logger.warning(
                "divergencia_estado",
                extra={
                    "pagamento_id": str(pagamento.id),
                    "status_atual": pagamento.status,
                    "novo_status": novo_status.value,
                },
            )
            evento.status = "IGNORADO"
            evento.processado_em = timezone.now()
            evento.save(update_fields=["status", "processado_em", "atualizado_em"])
