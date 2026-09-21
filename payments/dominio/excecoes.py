class PagamentoError(Exception):
    pass


class GatewayIndisponivel(PagamentoError):
    pass


class ResultadoIncerto(PagamentoError):
    pass


class LimiteDeRequisicoes(PagamentoError):
    pass


class RequisicaoRecusada(PagamentoError):
    def __init__(self, motivo: str = ""):
        self.motivo = motivo
        super().__init__(motivo)


class CobrancaNaoEncontrada(PagamentoError):
    pass


class CredencialInvalida(PagamentoError):
    pass


class RegraPagamentoViolada(PagamentoError):
    pass
