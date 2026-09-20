from django.db.models import Q
from rest_framework import viewsets
from rest_framework.response import Response

from .models import Professional
from .serializers import ProfessionalSerializer


class ProfessionalViewSet(viewsets.ModelViewSet):
    queryset = Professional.objects.all()
    serializer_class = ProfessionalSerializer
    lookup_field = "id"

    def get_queryset(self):
        qs = super().get_queryset()
        nome = self.request.query_params.get("nome")
        if nome:
            qs = qs.filter(Q(nome_social__icontains=nome))
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.clean()
        instance.save()

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.clean()
        instance.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.appointments.exists():
            return Response(
                {"error": {"code": "conflict", "message": "Não é possível excluir profissional com consultas."}},
                status=409,
            )
        return super().destroy(request, *args, **kwargs)
