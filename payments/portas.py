from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from payments.dominio.estados import StatusPagamento


@dataclass(frozen=True)
class DadosPagador:
    nome: str
    documento: str
    email: str


@dataclass(frozen=True)
class RepasseDTO:
    profissional_id: UUID
    carteira_id: str
    percentual: Decimal
    valor_estimado: Decimal


@dataclass(frozen=True)
class PedidoCobranca:
    referencia: UUID
    pagador_id_externo: str
    valor: Decimal
    vencimento: str
    forma: str
    repasses: list[RepasseDTO]
    descricao: str = ""


@dataclass(frozen=True)
class CobrancaGateway:
    id_externo: str
    status: StatusPagamento
    valor: Decimal
    url_pagamento: str = ""


@dataclass(frozen=True)
class NotificacaoGateway:
    event_id: str
    tipo: str
    referencia: UUID | None
    id_externo: str | None
    status: StatusPagamento | None


class GatewayPagamento(Protocol):
    def registrar_pagador(self, dados: DadosPagador) -> str: ...

    def criar_cobranca(self, pedido: PedidoCobranca) -> CobrancaGateway: ...

    def buscar_por_referencia(self, referencia: UUID) -> CobrancaGateway | None: ...

    def consultar_cobranca(self, id_externo: str) -> CobrancaGateway: ...

    def solicitar_estorno(self, id_externo: str) -> None: ...

    def autenticar_notificacao(self, headers: Mapping[str, str]) -> bool: ...

    def traduzir_notificacao(self, corpo: bytes) -> NotificacaoGateway: ...
