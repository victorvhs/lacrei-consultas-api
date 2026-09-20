from django.test import SimpleTestCase

from payments.dominio.estados import (
    StatusPagamento,
    eh_alcancavel,
    eh_estado_final,
    pode_estornar,
    pode_transicionar,
)


class EstadosTest(SimpleTestCase):
    def test_pode_transicionar_aguardando_para_pendente(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.AGUARDANDO_ENVIO, StatusPagamento.PENDENTE)
        )

    def test_pode_transicionar_aguardando_para_falha(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.AGUARDANDO_ENVIO, StatusPagamento.FALHA_ENVIO)
        )

    def test_pode_transicionar_pendente_para_confirmado(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.PENDENTE, StatusPagamento.CONFIRMADO)
        )

    def test_pode_transicionar_pendente_para_pago(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.PENDENTE, StatusPagamento.PAGO)
        )

    def test_pode_transicionar_pendente_para_vencido(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.PENDENTE, StatusPagamento.VENCIDO)
        )

    def test_pode_transicionar_pendente_para_cancelado(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.PENDENTE, StatusPagamento.CANCELADO)
        )

    def test_pode_transicionar_confirmado_para_pago(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.CONFIRMADO, StatusPagamento.PAGO)
        )

    def test_pode_transicionar_confirmado_para_estorno_em_andamento(self):
        self.assertTrue(
            pode_transicionar(
                StatusPagamento.CONFIRMADO, StatusPagamento.ESTORNO_EM_ANDAMENTO
            )
        )

    def test_pode_transicionar_pago_para_estornado(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.PAGO, StatusPagamento.ESTORNADO)
        )

    def test_pode_transicionar_pago_para_em_disputa(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.PAGO, StatusPagamento.EM_DISPUTA)
        )

    def test_nao_pode_transicionar_cancelado_para_agendada(self):
        self.assertFalse(
            pode_transicionar(StatusPagamento.CANCELADO, StatusPagamento.AGUARDANDO_ENVIO)
        )

    def test_nao_pode_transicionar_estornado_para_pago(self):
        self.assertFalse(
            pode_transicionar(StatusPagamento.ESTORNADO, StatusPagamento.PAGO)
        )

    def test_mesmo_status_retorna_true(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.PENDENTE, StatusPagamento.PENDENTE)
        )

    def test_eh_estado_final_cancelado(self):
        self.assertTrue(eh_estado_final(StatusPagamento.CANCELADO))

    def test_eh_estado_final_estornado(self):
        self.assertTrue(eh_estado_final(StatusPagamento.ESTORNADO))

    def test_nao_eh_estado_final_pendente(self):
        self.assertFalse(eh_estado_final(StatusPagamento.PENDENTE))

    def test_nao_eh_estado_final_pago(self):
        self.assertFalse(eh_estado_final(StatusPagamento.PAGO))

    def test_eh_alcancavel_pendente_para_estornado(self):
        self.assertTrue(
            eh_alcancavel(StatusPagamento.PENDENTE, StatusPagamento.ESTORNADO)
        )

    def test_eh_alcancavel_aguardando_para_pago(self):
        self.assertTrue(
            eh_alcancavel(StatusPagamento.AGUARDANDO_ENVIO, StatusPagamento.PAGO)
        )

    def test_nao_eh_alcancavel_cancelado_para_pago(self):
        self.assertFalse(
            eh_alcancavel(StatusPagamento.CANCELADO, StatusPagamento.PAGO)
        )

    def test_eh_alcancavel_mesmo_status(self):
        self.assertTrue(
            eh_alcancavel(StatusPagamento.PENDENTE, StatusPagamento.PENDENTE)
        )

    def test_pode_estornar_confirmado(self):
        self.assertTrue(pode_estornar(StatusPagamento.CONFIRMADO))

    def test_pode_estornar_pago(self):
        self.assertTrue(pode_estornar(StatusPagamento.PAGO))

    def test_nao_pode_estornar_pendente(self):
        self.assertFalse(pode_estornar(StatusPagamento.PENDENTE))

    def test_nao_pode_estornar_cancelado(self):
        self.assertFalse(pode_estornar(StatusPagamento.CANCELADO))

    def test_nao_pode_estornar_aguardando_envio(self):
        self.assertFalse(pode_estornar(StatusPagamento.AGUARDANDO_ENVIO))

    def test_falha_envio_pode_voltar_para_aguardando(self):
        self.assertTrue(
            pode_transicionar(
                StatusPagamento.FALHA_ENVIO, StatusPagamento.AGUARDANDO_ENVIO
            )
        )

    def test_em_disputa_pode_ir_para_pago(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.EM_DISPUTA, StatusPagamento.PAGO)
        )

    def test_em_disputa_pode_ir_para_estornado(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.EM_DISPUTA, StatusPagamento.ESTORNADO)
        )

    def test_vencido_pode_ir_para_pago(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.VENCIDO, StatusPagamento.PAGO)
        )

    def test_vencido_pode_ir_para_cancelado(self):
        self.assertTrue(
            pode_transicionar(StatusPagamento.VENCIDO, StatusPagamento.CANCELADO)
        )
