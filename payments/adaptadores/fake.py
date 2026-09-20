from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from uuid import UUID

from payments.dominio.estados import StatusPagamento
from payments.dominio.excecoes import CobrancaNaoEncontrada
from payments.portas import (
    CobrancaGateway,
    DadosPagador,
    NotificacaoGateway,
    PedidoCobranca,
)


class FakeGateway:
    def __init__(self):
        self.pagadores: dict[str, DadosPagador] = {}
        self.cobrancas: dict[str, dict] = {}
        self.tokens_validos: list[str] = ["fake-token"]
        self._proximo_erro: Exception | None = None
        self._proximo_status: StatusPagamento | None = None

    def programar_erro(self, erro: Exception) -> None:
        self._proximo_erro = erro

    def programar_status(self, status: StatusPagamento) -> None:
        self._proximo_status = status

    def registrar_pagador(self, dados: DadosPagador) -> str:
        if self._proximo_erro:
            erro = self._proximo_erro
            self._proximo_erro = None
            raise erro
        id_externo = f"cus_{uuid.uuid4().hex[:16]}"
        self.pagadores[id_externo] = dados
        return id_externo

    def criar_cobranca(self, pedido: PedidoCobranca) -> CobrancaGateway:
        if self._proximo_erro:
            erro = self._proximo_erro
            self._proximo_erro = None
            raise erro
        id_externo = f"pay_{uuid.uuid4().hex[:16]}"
        status = self._proximo_status or StatusPagamento.PENDENTE
        self._proximo_status = None
        self.cobrancas[id_externo] = {
            "referencia": pedido.referencia,
            "status": status,
            "valor": pedido.valor,
            "url_pagamento": f"https://fake.gateway/pay/{id_externo}",
        }
        return CobrancaGateway(
            id_externo=id_externo,
            status=status,
            valor=pedido.valor,
            url_pagamento=f"https://fake.gateway/pay/{id_externo}",
        )

    def buscar_por_referencia(self, referencia: UUID) -> CobrancaGateway | None:
        for id_ext, dados in self.cobrancas.items():
            if dados["referencia"] == referencia:
                return CobrancaGateway(
                    id_externo=id_ext,
                    status=dados["status"],
                    valor=dados["valor"],
                    url_pagamento=dados.get("url_pagamento", ""),
                )
        return None

    def consultar_cobranca(self, id_externo: str) -> CobrancaGateway:
        if id_externo not in self.cobrancas:
            raise CobrancaNaoEncontrada(f"Cobranca {id_externo} nao encontrada.")
        dados = self.cobrancas[id_externo]
        return CobrancaGateway(
            id_externo=id_externo,
            status=dados["status"],
            valor=dados["valor"],
            url_pagamento=dados.get("url_pagamento", ""),
        )

    def solicitar_estorno(self, id_externo: str) -> None:
        if id_externo not in self.cobrancas:
            raise CobrancaNaoEncontrada(f"Cobranca {id_externo} nao encontrada.")
        self.cobrancas[id_externo]["status"] = StatusPagamento.ESTORNADO

    def autenticar_notificacao(self, headers: Mapping[str, str]) -> bool:
        token = headers.get("asaas-access-token", "")
        return token in self.tokens_validos

    def traduzir_notificacao(self, corpo: bytes) -> NotificacaoGateway:
        try:
            data = json.loads(corpo)
        except (json.JSONDecodeError, ValueError):
            from payments.dominio.excecoes import PagamentoError

            raise PagamentoError("Payload invalido.")
        return NotificacaoGateway(
            event_id=data.get("event_id", str(uuid.uuid4())),
            tipo=data.get("tipo", "PAYMENT_UPDATED"),
            referencia=UUID(data["referencia"]) if data.get("referencia") else None,
            id_externo=data.get("id_externo"),
            status=StatusPagamento(data["status"]) if data.get("status") else None,
        )

    def marcar_como_paga(self, id_externo: str) -> None:
        if id_externo not in self.cobrancas:
            raise CobrancaNaoEncontrada(f"Cobranca {id_externo} nao encontrada.")
        self.cobrancas[id_externo]["status"] = StatusPagamento.PAGO
