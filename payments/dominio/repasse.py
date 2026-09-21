from decimal import ROUND_HALF_EVEN, Decimal


def calcular_repasse(
    valor_cobranca: Decimal,
    percentual_repasse: Decimal,
    taxas_gateway: Decimal = Decimal("0"),
) -> Decimal:
    valor_liquido = valor_cobranca - taxas_gateway
    if valor_liquido < 0:
        valor_liquido = Decimal("0")
    repasse = (valor_liquido * percentual_repasse / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return repasse


def validar_percentual_repasse(percentual: Decimal) -> None:
    if percentual < Decimal("0") or percentual > Decimal("100"):
        from payments.dominio.excecoes import RegraPagamentoViolada

        raise RegraPagamentoViolada("Percentual de repasse deve estar entre 0 e 100.")


def validar_valor_consulta(valor: Decimal | None) -> None:
    if valor is None or valor <= 0:
        from payments.dominio.excecoes import RegraPagamentoViolada

        raise RegraPagamentoViolada("Consulta precisa de valor > 0.")
