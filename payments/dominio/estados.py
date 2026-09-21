from enum import Enum


class StatusPagamento(str, Enum):
    AGUARDANDO_ENVIO = "AGUARDANDO_ENVIO"
    FALHA_ENVIO = "FALHA_ENVIO"
    PENDENTE = "PENDENTE"
    CONFIRMADO = "CONFIRMADO"
    PAGO = "PAGO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"
    ESTORNO_EM_ANDAMENTO = "ESTORNO_EM_ANDAMENTO"
    ESTORNADO = "ESTORNADO"
    EM_DISPUTA = "EM_DISPUTA"


class StatusRepasse(str, Enum):
    PENDENTE = "PENDENTE"
    AGUARDANDO_CREDITO = "AGUARDANDO_CREDITO"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"
    RECUSADO = "RECUSADO"


TRANSICOES_PERMITIDAS = {
    StatusPagamento.AGUARDANDO_ENVIO: [
        StatusPagamento.PENDENTE,
        StatusPagamento.FALHA_ENVIO,
    ],
    StatusPagamento.FALHA_ENVIO: [
        StatusPagamento.AGUARDANDO_ENVIO,
    ],
    StatusPagamento.PENDENTE: [
        StatusPagamento.CONFIRMADO,
        StatusPagamento.PAGO,
        StatusPagamento.VENCIDO,
        StatusPagamento.CANCELADO,
    ],
    StatusPagamento.VENCIDO: [
        StatusPagamento.PAGO,
        StatusPagamento.CANCELADO,
    ],
    StatusPagamento.CONFIRMADO: [
        StatusPagamento.PAGO,
        StatusPagamento.ESTORNO_EM_ANDAMENTO,
        StatusPagamento.EM_DISPUTA,
    ],
    StatusPagamento.PAGO: [
        StatusPagamento.ESTORNO_EM_ANDAMENTO,
        StatusPagamento.ESTORNADO,
        StatusPagamento.EM_DISPUTA,
    ],
    StatusPagamento.ESTORNO_EM_ANDAMENTO: [
        StatusPagamento.ESTORNADO,
    ],
    StatusPagamento.EM_DISPUTA: [
        StatusPagamento.PAGO,
        StatusPagamento.ESTORNADO,
    ],
}

ESTADOS_FINAIS = [
    StatusPagamento.CANCELADO,
    StatusPagamento.ESTORNADO,
]


def pode_transicionar(de: StatusPagamento, para: StatusPagamento) -> bool:
    if de == para:
        return True
    permitidos = TRANSICOES_PERMITIDAS.get(de, [])
    return para in permitidos


def eh_estado_final(status: StatusPagamento) -> bool:
    return status in ESTADOS_FINAIS


def eh_alcancavel(de: StatusPagamento, para: StatusPagamento) -> bool:
    if de == para:
        return True
    visitados = set()
    fila = [de]
    while fila:
        atual = fila.pop(0)
        if atual == para:
            return True
        if atual in visitados:
            continue
        visitados.add(atual)
        proximos = TRANSICOES_PERMITIDAS.get(atual, [])
        fila.extend(proximos)
    return False


def pode_estornar(status: StatusPagamento) -> bool:
    return status in (StatusPagamento.CONFIRMADO, StatusPagamento.PAGO)
