from rest_framework import generics, status
from rest_framework.response import Response

from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer

from .models import Professional


class ProfessionalAppointmentsListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        profissional_id = self.kwargs["profissional_id"]
        try:
            Professional.objects.get(id=profissional_id)
        except (Professional.DoesNotExist, ValueError):
            return Appointment.objects.none()
        return Appointment.objects.filter(profissional_id=profissional_id).select_related("profissional")

    def list(self, request, *args, **kwargs):
        profissional_id = self.kwargs["profissional_id"]
        try:
            Professional.objects.get(id=profissional_id)
        except (Professional.DoesNotExist, ValueError):
            return Response(
                {"error": {"code": "not_found", "message": "Profissional não encontrado."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().list(request, *args, **kwargs)
