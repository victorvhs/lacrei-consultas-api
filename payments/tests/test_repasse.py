from decimal import Decimal

from django.test import SimpleTestCase

from payments.dominio.excecoes import RegraPagamentoViolada
from payments.dominio.repasse import (
    calcular_repasse,
    validar_percentual_repasse,
    validar_valor_consulta,
)


class RepasseTest(SimpleTestCase):
    def test_calcular_repasse_basico(self):
        resultado = calcular_repasse(Decimal("150.00"), Decimal("80"))
        self.assertEqual(resultado, Decimal("120.00"))

    def test_calcular_repasse_com_taxas(self):
        resultado = calcular_repasse(
            Decimal("150.00"), Decimal("80"), taxas_gateway=Decimal("5.00")
        )
        self.assertEqual(resultado, Decimal("116.00"))

    def test_calcular_repasse_taxas_maior_que_valor(self):
        resultado = calcular_repasse(
            Decimal("10.00"), Decimal("80"), taxas_gateway=Decimal("15.00")
        )
        self.assertEqual(resultado, Decimal("0.00"))

    def test_calcular_repasse_zero_taxas(self):
        resultado = calcular_repasse(Decimal("100.00"), Decimal("50"))
        self.assertEqual(resultado, Decimal("50.00"))

    def test_calcular_repasse_100_por_cento(self):
        resultado = calcular_repasse(Decimal("200.00"), Decimal("100"))
        self.assertEqual(resultado, Decimal("200.00"))

    def test_calcular_repasse_zero_por_cento(self):
        resultado = calcular_repasse(Decimal("200.00"), Decimal("0"))
        self.assertEqual(resultado, Decimal("0.00"))

    def test_calcular_repasse_rounding(self):
        resultado = calcular_repasse(Decimal("99.99"), Decimal("80"))
        self.assertEqual(resultado, Decimal("80.00"))

    def test_calcular_repasse_valor_pequeno(self):
        resultado = calcular_repasse(Decimal("0.01"), Decimal("50"))
        self.assertEqual(resultado, Decimal("0.01"))

    def test_validar_percentual_valido(self):
        validar_percentual_repasse(Decimal("80"))
        validar_percentual_repasse(Decimal("0"))
        validar_percentual_repasse(Decimal("100"))
        validar_percentual_repasse(Decimal("50.5"))

    def test_validar_percentual_negativo(self):
        with self.assertRaises(RegraPagamentoViolada):
            validar_percentual_repasse(Decimal("-1"))

    def test_validar_percentual_acima_100(self):
        with self.assertRaises(RegraPagamentoViolada):
            validar_percentual_repasse(Decimal("101"))

    def test_validar_valor_consulta_valido(self):
        validar_valor_consulta(Decimal("150.00"))

    def test_validar_valor_consulta_zero(self):
        with self.assertRaises(RegraPagamentoViolada):
            validar_valor_consulta(Decimal("0"))

    def test_validar_valor_consulta_negativo(self):
        with self.assertRaises(RegraPagamentoViolada):
            validar_valor_consulta(Decimal("-10"))

    def test_validar_valor_consulta_none(self):
        with self.assertRaises(RegraPagamentoViolada):
            validar_valor_consulta(None)
