from django.urls import include, path
from rest_framework.routers import DefaultRouter

from payments.api.views import (
    CriarPagamentoParaConsultaView,
    PagadorViewSet,
    PagamentoViewSet,
    SolicitarEstornoView,
    webhook_asaas,
)

router = DefaultRouter()
router.register("pagadores", PagadorViewSet, basename="pagador")
router.register("pagamentos", PagamentoViewSet, basename="pagamento")

urlpatterns = [
    path(
        "consultas/<uuid:consulta_id>/pagamentos/",
        CriarPagamentoParaConsultaView.as_view({"post": "create"}),
        name="criar-pagamento-consulta",
    ),
    path(
        "pagamentos/<uuid:pk>/estorno/",
        SolicitarEstornoView.as_view({"post": "create"}),
        name="solicitar-estorno",
    ),
    path("webhooks/asaas/", webhook_asaas, name="webhook-asaas"),
    path("", include(router.urls)),
]
