from __future__ import annotations

import hmac
import json
import logging
import uuid
from collections.abc import Mapping
from decimal import Decimal
from uuid import UUID

import httpx

from payments.dominio.estados import StatusPagamento
from payments.dominio.excecoes import (
    CobrancaNaoEncontrada,
    CredencialInvalida,
    GatewayIndisponivel,
    LimiteDeRequisicoes,
    RequisicaoRecusada,
    ResultadoIncerto,
)
from payments.portas import (
    CobrancaGateway,
    DadosPagador,
    NotificacaoGateway,
    PedidoCobranca,
)

logger = logging.getLogger(__name__)

MAPA_STATUS = {
    "PENDING": StatusPagamento.PENDENTE,
    "AWAITING_RISK_ANALYSIS": StatusPagamento.PENDENTE,
    "CONFIRMED": StatusPagamento.CONFIRMADO,
    "RECEIVED": StatusPagamento.PAGO,
    "RECEIVED_IN_CASH": StatusPagamento.PAGO,
    "OVERDUE": StatusPagamento.VENCIDO,
    "REFUND_REQUESTED": StatusPagamento.ESTORNO_EM_ANDAMENTO,
    "REFUND_IN_PROGRESS": StatusPagamento.ESTORNO_EM_ANDAMENTO,
    "REFUNDED": StatusPagamento.ESTORNADO,
    "CHARGEBACK_REQUESTED": StatusPagamento.EM_DISPUTA,
    "CHARGEBACK_DISPUTE": StatusPagamento.EM_DISPUTA,
    "AWAITING_CHARGEBACK_REVERSAL": StatusPagamento.EM_DISPUTA,
    "DUNNING_REQUESTED": StatusPagamento.EM_DISPUTA,
    "DUNNING_RECEIVED": StatusPagamento.EM_DISPUTA,
}

MAPA_EVENTO_STATUS = {
    "PAYMENT_CREATED": StatusPagamento.PENDENTE,
    "PAYMENT_UPDATED": None,
    "PAYMENT_CONFIRMED": StatusPagamento.CONFIRMADO,
    "PAYMENT_RECEIVED": StatusPagamento.PAGO,
    "PAYMENT_OVERDUE": StatusPagamento.VENCIDO,
    "PAYMENT_DELETED": StatusPagamento.CANCELADO,
    "PAYMENT_REFUND_REQUESTED": StatusPagamento.ESTORNO_EM_ANDAMENTO,
    "PAYMENT_REFUNDED": StatusPagamento.ESTORNADO,
    "PAYMENT_RECEIVED_IN_CASH": StatusPagamento.PAGO,
    "PAYMENT_CHARGEBACK_REQUESTED": StatusPagamento.EM_DISPUTA,
    "PAYMENT_CHARGEBACK_DISPUTE": StatusPagamento.EM_DISPUTA,
}


class AsaasGateway:
    def __init__(self, base_url: str, api_key: str, webhook_tokens: list[str]):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.webhook_tokens = webhook_tokens
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "access_token": self.api_key,
                "User-Agent": "LacreiSaude/1.0",
            },
            timeout=httpx.Timeout(connect=3.0, read=10.0, write=5.0, pool=3.0),
        )

    def _tratar_erro(self, response: httpx.Response) -> None:
        if response.status_code in (401, 403):
            raise CredencialInvalida(f"Credencial invalida: {response.status_code}")
        if response.status_code == 429:
            raise LimiteDeRequisicoes(f"Limite de requisicoes: {response.status_code}")
        if response.status_code == 404:
            raise CobrancaNaoEncontrada("Cobranca nao encontrada.")
        if 400 <= response.status_code < 500:
            try:
                body = response.json()
                motivo = body.get("errors", [{}])[0].get("description", response.text)
            except Exception:
                motivo = response.text
            raise RequisicaoRecusada(motivo)
        if response.status_code >= 500:
            raise GatewayIndisponivel(f"Gateway indisponivel: {response.status_code}")

    def _traduzir_status(self, status_str: str) -> StatusPagamento:
        status = MAPA_STATUS.get(status_str)
        if status is None:
            logger.warning("status_desconhecido", extra={"status": status_str})
            return StatusPagamento.PENDENTE
        return status

    def registrar_pagador(self, dados: DadosPagador) -> str:
        try:
            response = self.client.post(
                "/v3/customers",
                json={
                    "name": dados.nome,
                    "cpfCnpj": dados.documento,
                    "email": dados.email,
                },
            )
        except httpx.TimeoutException:
            raise GatewayIndisponivel("Timeout ao registrar pagador.")
        except httpx.ConnectError:
            raise GatewayIndisponivel("Erro de conexao ao registrar pagador.")
        self._tratar_erro(response)
        data = response.json()
        return data["id"]

    def criar_cobranca(self, pedido: PedidoCobranca) -> CobrancaGateway:
        payload = {
            "customer": pedido.pagador_id_externo,
            "billingType": pedido.forma,
            "value": str(pedido.valor),
            "dueDate": pedido.vencimento,
            "description": pedido.descricao,
            "externalReference": str(pedido.referencia),
        }
        if pedido.repasses:
            payload["split"] = [
                {
                    "walletId": r.carteira_id,
                    "percentual": float(r.percentual),
                    "value": float(r.valor_estimado),
                }
                for r in pedido.repasses
            ]
        try:
            response = self.client.post("/v3/payments", json=payload)
        except httpx.TimeoutException:
            raise ResultadoIncerto("Timeout ao criar cobranca.")
        except httpx.ConnectError:
            raise GatewayIndisponivel("Erro de conexao ao criar cobranca.")
        self._tratar_erro(response)
        data = response.json()
        return CobrancaGateway(
            id_externo=data["id"],
            status=self._traduzir_status(data.get("status", "PENDING")),
            valor=Decimal(str(data.get("value", pedido.valor))),
            url_pagamento=data.get("invoiceUrl", ""),
        )

    def buscar_por_referencia(self, referencia: UUID) -> CobrancaGateway | None:
        try:
            response = self.client.get(
                "/v3/payments",
                params={"externalReference": str(referencia)},
            )
        except (httpx.TimeoutException, httpx.ConnectError):
            raise GatewayIndisponivel("Erro ao buscar por referencia.")
        self._tratar_erro(response)
        data = response.json()
        results = data.get("data", [])
        if not results:
            return None
        item = results[0]
        return CobrancaGateway(
            id_externo=item["id"],
            status=self._traduzir_status(item.get("status", "PENDING")),
            valor=Decimal(str(item.get("value", 0))),
            url_pagamento=item.get("invoiceUrl", ""),
        )

    def consultar_cobranca(self, id_externo: str) -> CobrancaGateway:
        try:
            response = self.client.get(f"/v3/payments/{id_externo}")
        except httpx.TimeoutException:
            raise GatewayIndisponivel("Timeout ao consultar cobranca.")
        except httpx.ConnectError:
            raise GatewayIndisponivel("Erro de conexao ao consultar cobranca.")
        self._tratar_erro(response)
        data = response.json()
        return CobrancaGateway(
            id_externo=data["id"],
            status=self._traduzir_status(data.get("status", "PENDING")),
            valor=Decimal(str(data.get("value", 0))),
            url_pagamento=data.get("invoiceUrl", ""),
        )

    def solicitar_estorno(self, id_externo: str) -> None:
        try:
            response = self.client.post(f"/v3/payments/{id_externo}/refund")
        except httpx.TimeoutException:
            raise GatewayIndisponivel("Timeout ao solicitar estorno.")
        except httpx.ConnectError:
            raise GatewayIndisponivel("Erro de conexao ao solicitar estorno.")
        self._tratar_erro(response)

    def autenticar_notificacao(self, headers: Mapping[str, str]) -> bool:
        token = headers.get("asaas-access-token", "")
        for valido in self.webhook_tokens:
            if hmac.compare_digest(token, valido):
                return True
        return False

    def traduzir_notificacao(self, corpo: bytes) -> NotificacaoGateway:
        try:
            data = json.loads(corpo)
        except (json.JSONDecodeError, ValueError):
            from payments.dominio.excecoes import PagamentoError

            raise PagamentoError("Payload invalido.")
        event_type = data.get("type", "PAYMENT_UPDATED")
        event_id = data.get("id", str(uuid.uuid4()))
        payment = data.get("payment", {})
        status_str = payment.get("status", "")
        id_externo = payment.get("id")
        referencia_str = payment.get("externalReference")
        referencia = UUID(referencia_str) if referencia_str else None
        status = MAPA_EVENTO_STATUS.get(event_type)
        if status is None and status_str:
            status = self._traduzir_status(status_str)
        return NotificacaoGateway(
            event_id=event_id,
            tipo=event_type,
            referencia=referencia,
            id_externo=id_externo,
            status=status,
        )
