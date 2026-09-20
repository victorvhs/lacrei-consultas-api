from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from django.db import transaction

from appointments.models import Appointment
from payments.dominio.estados import (
    StatusPagamento,
    StatusRepasse,
    pode_estornar,
    pode_transicionar,
)
from payments.dominio.excecoes import RegraPagamentoViolada
from payments.dominio.repasse import calcular_repasse, validar_percentual_repasse, validar_valor_consulta
from payments.models import (
    OutboxMensagem,
    Pagador,
    Pagamento,
    Repasse,
)

if TYPE_CHECKING:
    pass


def criar_pagamento(
    consulta_id: UUID,
    pagador_id: UUID,
    forma: str = "PIX",
    vencimento: str = "",
    percentual_repasse: int = 80,
) -> Pagamento:
    consulta = Appointment.objects.select_related("profissional").get(id=consulta_id)

    if consulta.status == "cancelada":
        raise RegraPagamentoViolada("Consulta cancelada nao gera cobranca.")

    validar_valor_consulta(consulta.valor)

    pagador = Pagador.objects.get(id=pagador_id)

    profissional = consulta.profissional
    if not profissional.carteira_repasse_id:
        raise RegraPagamentoViolada("Profissional precisa de carteira_repasse_id.")

    validar_percentual_repasse(Decimal(str(percentual_repasse)))

    valor_estimado = calcular_repasse(
        consulta.valor, Decimal(str(percentual_repasse))
    )

    with transaction.atomic():
        pagamento = Pagamento.objects.create(
            consulta=consulta,
            pagador=pagador,
            valor=consulta.valor,
            forma=forma,
            vencimento=vencimento or None,
            status=StatusPagamento.AGUARDANDO_ENVIO.value,
        )

        Repasse.objects.create(
            pagamento=pagamento,
            profissional=profissional,
            carteira_id=profissional.carteira_repasse_id,
            percentual=Decimal(str(percentual_repasse)),
            valor_estimado=valor_estimado,
            status=StatusRepasse.PENDENTE.value,
        )

        OutboxMensagem.objects.create(
            tipo="CRIAR_COBRANCA",
            pagamento=pagamento,
        )

    return pagamento


def solicitar_estorno(pagamento_id: UUID) -> Pagamento:
    pagamento = Pagamento.objects.get(id=pagamento_id)
    status_atual = StatusPagamento(pagamento.status)

    if not pode_estornar(status_atual):
        raise RegraPagamentoViolada(
            "Estorno apenas de pagamento CONFIRMADO ou PAGO."
        )

    with transaction.atomic():
        pagamento.status = StatusPagamento.ESTORNO_EM_ANDAMENTO.value
        pagamento.save(update_fields=["status", "atualizado_em"])

        OutboxMensagem.objects.create(
            tipo="SOLICITAR_ESTORNO",
            pagamento=pagamento,
        )

        Repasse.objects.filter(pagamento=pagamento).update(
            status=StatusRepasse.CANCELADO.value
        )

    return pagamento


def aplicar_transicao(
    pagamento: Pagamento,
    novo_status: StatusPagamento,
    id_externo: str = "",
    url_pagamento: str = "",
) -> bool:
    status_atual = StatusPagamento(pagamento.status)

    if status_atual == novo_status:
        return False

    if not pode_transicionar(status_atual, novo_status):
        from payments.dominio.estados import eh_alcancavel

        if eh_alcancavel(status_atual, novo_status):
            pagamento.status = novo_status.value
        else:
            return False
    else:
        pagamento.status = novo_status.value

    if id_externo and not pagamento.id_externo:
        pagamento.id_externo = id_externo
    if url_pagamento and not pagamento.url_pagamento:
        pagamento.url_pagamento = url_pagamento

    pagamento.save(
        update_fields=["status", "id_externo", "url_pagamento", "atualizado_em"]
    )

    if novo_status in (StatusPagamento.CONFIRMADO, StatusPagamento.PAGO):
        Repasse.objects.filter(pagamento=pagamento).update(
            status=StatusRepasse.CONCLUIDO.value
        )

    return True
