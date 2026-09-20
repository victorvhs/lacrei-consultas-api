from rest_framework import serializers

from professionals.models import Professional

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    profissional_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "profissional_id",
            "data_hora",
            "status",
            "valor",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]

    def validate_profissional_id(self, value):
        try:
            Professional.objects.get(id=value)
        except (Professional.DoesNotExist, ValueError):
            raise serializers.ValidationError("Profissional não encontrado.")
        return value

    def validate(self, attrs):
        profissional_id = attrs.get("profissional_id")
        data_hora = attrs.get("data_hora")

        if profissional_id and data_hora:
            from django.utils import timezone

            if not self.instance and data_hora <= timezone.now():
                raise serializers.ValidationError({"data_hora": "data_hora deve ser no futuro."})

            duplicate = Appointment.objects.filter(
                profissional_id=profissional_id,
                data_hora=data_hora,
            ).exclude(status="cancelada")
            if self.instance:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError({"data_hora": "Já existe consulta não cancelada neste horário."})

        valor = attrs.get("valor")
        if valor is not None and valor <= 0:
            raise serializers.ValidationError({"valor": "valor deve ser maior que zero."})

        return attrs

    def create(self, validated_data):
        profissional_id = validated_data.pop("profissional_id")
        validated_data["profissional_id"] = profissional_id
        instance = Appointment.objects.create(**validated_data)
        instance.clean()
        return instance

    def update(self, instance, validated_data):
        profissional_id = validated_data.pop("profissional_id", None)
        if profissional_id:
            validated_data["profissional_id"] = profissional_id

        new_status = validated_data.get("status")
        if new_status and not instance.can_transition_to(new_status):
            raise serializers.ValidationError(
                {"status": "Transição de status inválida. Cancelada/Realizada não voltam para Agendada."}
            )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.clean()
        instance.save()
        return instance
