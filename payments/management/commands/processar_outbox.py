import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from payments.aplicacao.servicos import aplicar_transicao
from payments.dominio.estados import StatusPagamento
from payments.dominio.excecoes import (
    GatewayIndisponivel,
    LimiteDeRequisicoes,
    RequisicaoRecusada,
    ResultadoIncerto,
)
from payments.models import OutboxMensagem, Repasse

logger = logging.getLogger(__name__)

MAX_TENTATIVAS = 8


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


class Command(BaseCommand):
    help = "Processa mensagens da outbox e envia para o gateway"

    def add_arguments(self, parser):
        parser.add_argument("--lote", type=int, default=10, help="Tamanho do lote")

    def handle(self, *args, **options):
        lote_size = options["lote"]
        gateway = get_gateway()

        now = timezone.now()
        mensagens = (
            OutboxMensagem.objects.select_for_update(skip_locked=True)
            .filter(
                status__in=["PENDENTE"],
                proxima_tentativa_em__lte=now,
            )
            .order_by("criado_em")[:lote_size]
        )

        processando = (
            OutboxMensagem.objects.select_for_update(skip_locked=True)
            .filter(
                status__in=["PROCESSANDO"],
                proxima_tentativa_em__lte=now,
            )
            .order_by("criado_em")
        )
        mensagens = list(mensagens) + list(processando)

        with transaction.atomic():
            for msg in mensagens:
                msg.status = "PROCESSANDO"
                msg.save(update_fields=["status", "atualizado_em"])

        for msg in mensagens:
            try:
                if msg.tipo == "CRIAR_COBRANCA":
                    self._processar_criar_cobranca(gateway, msg)
                elif msg.tipo == "SOLICITAR_ESTORNO":
                    self._processar_estorno(gateway, msg)
            except Exception as e:
                logger.error("erro_processar_outbox", extra={"erro": str(e), "msg_id": str(msg.id)})
                self._tratar_falha(msg, str(e))

    def _processar_criar_cobranca(self, gateway, msg):
        pagamento = msg.pagamento
        pagador = pagamento.pagador

        repasses = list(Repasse.objects.filter(pagamento=pagamento).select_related("profissional"))

        from payments.portas import PedidoCobranca, RepasseDTO

        repasse_dtos = [
            RepasseDTO(
                profissional_id=r.profissional.id,
                carteira_id=r.carteira_id,
                percentual=r.percentual,
                valor_estimado=r.valor_estimado,
            )
            for r in repasses
        ]

        pedido = PedidoCobranca(
            referencia=pagamento.id,
            pagador_id_externo=pagador.id_externo,
            valor=pagamento.valor,
            vencimento=str(pagamento.vencimento) if pagamento.vencimento else "",
            forma=pagamento.forma,
            repasses=repasse_dtos,
        )

        try:
            cobranca = gateway.criar_cobranca(pedido)
            aplicar_transicao(
                pagamento,
                cobranca.status,
                id_externo=cobranca.id_externo,
                url_pagamento=cobranca.url_pagamento,
            )
            msg.status = "CONCLUIDA"
            msg.save(update_fields=["status", "atualizado_em"])
        except ResultadoIncerto:
            try:
                cobranca = gateway.buscar_por_referencia(pagamento.id)
                if cobranca:
                    aplicar_transicao(
                        pagamento,
                        cobranca.status,
                        id_externo=cobranca.id_externo,
                        url_pagamento=cobranca.url_pagamento,
                    )
                    msg.status = "CONCLUIDA"
                    msg.save(update_fields=["status", "atualizado_em"])
                else:
                    raise GatewayIndisponivel("Resultado incerto e nao encontrado.")
            except GatewayIndisponivel:
                self._reagendar(msg, "Resultado incerto")
        except (GatewayIndisponivel, LimiteDeRequisicoes) as e:
            self._reagendar(msg, str(e))
        except RequisicaoRecusada as e:
            pagamento.status = StatusPagamento.FALHA_ENVIO.value
            pagamento.motivo_falha = e.motivo
            pagamento.save(update_fields=["status", "motivo_falha", "atualizado_em"])
            msg.status = "FALHOU"
            msg.ultimo_erro = e.motivo
            msg.save(update_fields=["status", "ultimo_erro", "atualizado_em"])

    def _processar_estorno(self, gateway, msg):
        pagamento = msg.pagamento
        if not pagamento.id_externo:
            msg.status = "FALHOU"
            msg.ultimo_erro = "Pagamento sem id_externo"
            msg.save(update_fields=["status", "ultimo_erro", "atualizado_em"])
            return

        try:
            gateway.solicitar_estorno(pagamento.id_externo)
            msg.status = "CONCLUIDA"
            msg.save(update_fields=["status", "atualizado_em"])
        except (GatewayIndisponivel, LimiteDeRequisicoes) as e:
            self._reagendar(msg, str(e))
        except RequisicaoRecusada as e:
            msg.status = "FALHOU"
            msg.ultimo_erro = e.motivo
            msg.save(update_fields=["status", "ultimo_erro", "atualizado_em"])

    def _reagendar(self, msg, erro):
        msg.tentativas += 1
        if msg.tentativas >= MAX_TENTATIVAS:
            msg.status = "FALHOU"
            msg.ultimo_erro = f"Tentativas esgotadas: {erro}"
            msg.pagamento.status = StatusPagamento.FALHA_ENVIO.value
            msg.pagamento.motivo_falha = erro
            msg.pagamento.save(update_fields=["status", "motivo_falha", "atualizado_em"])
        else:
            msg.status = "PENDENTE"
            msg.ultimo_erro = erro
            import random

            backoff = min(60 * (2**msg.tentativas), 3600)
            jitter = random.randint(0, 30)
            msg.proxima_tentativa_em = timezone.now() + timedelta(seconds=backoff + jitter)
        msg.save(
            update_fields=[
                "status",
                "tentativas",
                "ultimo_erro",
                "proxima_tentativa_em",
                "atualizado_em",
            ]
        )

    def _tratar_falha(self, msg, erro):
        msg.status = "FALHOU"
        msg.ultimo_erro = erro
        msg.save(update_fields=["status", "ultimo_erro", "atualizado_em"])
