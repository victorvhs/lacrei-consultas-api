from django.db.models import Q
from rest_framework import status, viewsets
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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.appointments.exists():
            return Response(
                {"error": {"code": "conflict", "message": "Não é possível excluir profissional com consultas."}},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)
