from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from professionals.models import Professional

from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related("profissional").all()
    serializer_class = AppointmentSerializer
    lookup_field = "id"

    def get_queryset(self):
        qs = super().get_queryset()
        profissional_id = self.request.query_params.get("profissional_id")
        status_filter = self.request.query_params.get("status")
        data_inicio = self.request.query_params.get("data_inicio")
        data_fim = self.request.query_params.get("data_fim")

        if profissional_id:
            try:
                Professional.objects.get(id=profissional_id)
            except (Professional.DoesNotExist, ValueError):
                return Appointment.objects.none()
            qs = qs.filter(profissional_id=profissional_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if data_inicio:
            qs = qs.filter(data_hora__gte=data_inicio)
        if data_fim:
            qs = qs.filter(data_hora__lte=data_fim)

        return qs

    @action(detail=False, methods=["get"], url_path="por-profissional/(?P<profissional_id>[^/.]+)")
    def por_profissional(self, request, profissional_id=None):
        try:
            professional = Professional.objects.get(id=profissional_id)
        except (Professional.DoesNotExist, ValueError):
            return Response(
                {"error": {"code": "not_found", "message": "Profissional não encontrado."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        appointments = Appointment.objects.filter(profissional=professional)
        page = self.paginate_queryset(appointments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)
