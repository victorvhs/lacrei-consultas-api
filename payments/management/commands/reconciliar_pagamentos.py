import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from payments.aplicacao.servicos import aplicar_transicao
from payments.dominio.estados import StatusPagamento
from payments.models import Pagamento

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


STATUSES_NAO_FINAIS = [
    s.value
    for s in [
        StatusPagamento.AGUARDANDO_ENVIO,
        StatusPagamento.PENDENTE,
        StatusPagamento.CONFIRMADO,
        StatusPagamento.PAGO,
        StatusPagamento.ESTORNO_EM_ANDAMENTO,
        StatusPagamento.EM_DISPUTA,
    ]
]


class Command(BaseCommand):
    help = "Reconcilia pagamentos sem atualizacao recente"

    def add_arguments(self, parser):
        parser.add_argument(
            "--lote", type=int, default=20, help="Tamanho do lote"
        )
        parser.add_argument(
            "--minutos",
            type=int,
            default=30,
            help="Minutos sem atualizacao para considerar desatualizado",
        )

    def handle(self, *args, **options):
        lote_size = options["lote"]
        minutos = options["minutos"]
        gateway = get_gateway()

        cutoff = timezone.now() - timedelta(minutes=minutos)

        pagamentos = (
            Pagamento.objects.filter(
                status__in=STATUSES_NAO_FINAIS,
                atualizado_em__lt=cutoff,
            )
            .exclude(id_externo="")
            .order_by("atualizado_em")[:lote_size]
        )

        corrigidos = 0
        for pagamento in pagamentos:
            try:
                cobranca = gateway.consultar_cobranca(pagamento.id_externo)
                if aplicar_transicao(
                    pagamento,
                    cobranca.status,
                    id_externo=cobranca.id_externo,
                    url_pagamento=cobranca.url_pagamento,
                ):
                    corrigidos += 1
                    logger.info(
                        "pagamento_corrigido",
                        extra={"pagamento_id": str(pagamento.id)},
                    )
            except Exception as e:
                logger.warning(
                    "erro_reconciliacao",
                    extra={"erro": str(e), "pagamento_id": str(pagamento.id)},
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Reconciliacao concluida: {corrigidos} pagamentos corrigidos."
            )
        )
