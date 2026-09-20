import json
import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from appointments.models import Appointment
from payments.api.serializers import (
    CriarPagamentoSerializer,
    PagadorSerializer,
    PagamentoSerializer,
)
from payments.aplicacao.servicos import criar_pagamento, solicitar_estorno
from payments.dominio.excecoes import (
    GatewayIndisponivel,
    RegraPagamentoViolada,
)
from payments.models import EventoRecebido, Pagador, Pagamento

logger = logging.getLogger(__name__)


class PagadorViewSet(viewsets.ModelViewSet):
    queryset = Pagador.objects.all()
    serializer_class = PagadorSerializer
    lookup_field = "id"
    http_method_names = ["post", "get"]

    def perform_create(self, serializer):
        gateway = getattr(settings, "PAYMENT_GATEWAY", "fake")
        if gateway == "fake":
            from payments.adaptadores.fake import FakeGateway

            gw = FakeGateway()
        else:
            from payments.adaptadores.asaas.gateway import AsaasGateway

            gw = AsaasGateway(
                base_url=settings.ASAAS_BASE_URL,
                api_key=settings.ASAAS_API_KEY,
                webhook_tokens=settings.ASAAS_WEBHOOK_TOKENS,
            )

        validated_data = serializer.validated_data
        cpf = validated_data.pop("documento")

        from payments.portas import DadosPagador

        dados = DadosPagador(
            nome=validated_data["nome"],
            documento=cpf,
            email=validated_data.get("email", ""),
        )

        try:
            id_externo = gw.registrar_pagador(dados)
        except GatewayIndisponivel:
            from rest_framework.exceptions import APIException

            raise APIException(
                detail="Gateway de pagamento indisponivel.",
                code="gateway_unavailable",
            )

        validated_data["documento_mascarado"] = f"***.***.***-{cpf[-2:]}"
        validated_data["id_externo"] = id_externo
        validated_data["gateway"] = gateway

        Pagador.objects.create(**validated_data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        pagador = Pagador.objects.latest("criado_em")
        output = PagadorSerializer(pagador).data
        return Response(output, status=status.HTTP_201_CREATED)


class PagamentoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pagamento.objects.select_related("consulta", "pagador").prefetch_related(
        "repasses", "repasses__profissional"
    ).all()
    serializer_class = PagamentoSerializer
    lookup_field = "id"


@method_decorator(csrf_exempt, name="dispatch")
class CriarPagamentoParaConsultaView(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request, consulta_id=None):
        try:
            Appointment.objects.get(id=consulta_id)
        except (Appointment.DoesNotExist, ValueError):
            return Response(
                {"error": {"code": "not_found", "message": "Consulta nao encontrada."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CriarPagamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pagamento = criar_pagamento(
                consulta_id=consulta_id,
                pagador_id=serializer.validated_data["pagador_id"],
                forma=serializer.validated_data.get("forma", "PIX"),
                vencimento=serializer.validated_data.get("vencimento", ""),
                percentual_repasse=settings.REPASSE_PERCENTUAL_PADRAO,
            )
        except RegraPagamentoViolada as e:
            return Response(
                {
                    "error": {
                        "code": "business_rule_violation",
                        "message": str(e),
                        "details": {},
                    }
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Pagamento.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "conflict",
                        "message": "Ja existe um pagamento ativo para esta consulta.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        output = PagamentoSerializer(pagamento).data
        return Response(output, status=status.HTTP_202_ACCEPTED)


@method_decorator(csrf_exempt, name="dispatch")
class SolicitarEstornoView(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request, pk=None):
        try:
            pagamento = Pagamento.objects.get(id=pk)
        except Pagamento.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Pagamento nao encontrado."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            pagamento = solicitar_estorno(pagamento.id)
        except RegraPagamentoViolada as e:
            return Response(
                {
                    "error": {
                        "code": "business_rule_violation",
                        "message": str(e),
                        "details": {},
                    }
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        output = PagamentoSerializer(pagamento).data
        return Response(output, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@permission_classes([AllowAny])
def webhook_asaas(request):
    if not request.data:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    gateway_type = getattr(settings, "PAYMENT_GATEWAY", "fake")
    if gateway_type == "fake":
        from payments.adaptadores.fake import FakeGateway

        gw = FakeGateway()
    else:
        from payments.adaptadores.asaas.gateway import AsaasGateway

        gw = AsaasGateway(
            base_url=settings.ASAAS_BASE_URL,
            api_key=settings.ASAAS_API_KEY,
            webhook_tokens=settings.ASAAS_WEBHOOK_TOKENS,
        )

    if not gw.autenticar_notificacao(request.headers):
        logger.warning("webhook_token_invalido")
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    corpo_bytes = json.dumps(request.data).encode()

    try:
        notificacao = gw.traduzir_notificacao(corpo_bytes)
    except Exception:
        EventoRecebido.objects.create(
            gateway=gateway_type,
            event_id="unknown",
            tipo="UNKNOWN",
            corpo=request.data,
            status="ERRO",
        )
        return Response({"recebido": True}, status=status.HTTP_200_OK)

    event_id = notificacao.event_id

    _, created = EventoRecebido.objects.get_or_create(
        gateway=gateway_type,
        event_id=event_id,
        defaults={
            "tipo": notificacao.tipo,
            "corpo": request.data,
            "status": "RECEBIDO",
        },
    )

    return Response({"recebido": True}, status=status.HTTP_200_OK)
