from rest_framework import serializers

from payments.models import (
    Pagador,
    Pagamento,
    Repasse,
)


class PagadorSerializer(serializers.ModelSerializer):
    documento = serializers.CharField(write_only=True)

    class Meta:
        model = Pagador
        fields = [
            "id",
            "nome",
            "documento",
            "documento_mascarado",
            "email",
            "gateway",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = [
            "id",
            "documento_mascarado",
            "gateway",
            "criado_em",
            "atualizado_em",
        ]

    def validate_documento(self, value):
        cpf = value.replace(".", "").replace("-", "").strip()
        if len(cpf) != 11 or not cpf.isdigit():
            raise serializers.ValidationError("CPF deve conter 11 dígitos.")
        if cpf == cpf[0] * 11:
            raise serializers.ValidationError("CPF inválido.")
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        d1 = (11 - (soma % 11)) % 10
        if int(cpf[9]) != d1:
            raise serializers.ValidationError("CPF inválido.")
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        d2 = (11 - (soma % 11)) % 10
        if int(cpf[10]) != d2:
            raise serializers.ValidationError("CPF inválido.")
        return cpf

    def create(self, validated_data):
        cpf = validated_data.pop("documento")
        validated_data["documento_mascarado"] = f"***.***.***-{cpf[-2:]}"
        return super().create(validated_data)


class RepasseSerializer(serializers.ModelSerializer):
    profissional_id = serializers.UUIDField(source="profissional.id", read_only=True)

    class Meta:
        model = Repasse
        fields = [
            "id",
            "profissional_id",
            "carteira_id",
            "percentual",
            "valor_estimado",
            "status",
            "motivo_recusa",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = fields


class PagamentoSerializer(serializers.ModelSerializer):
    repasses = RepasseSerializer(many=True, read_only=True)
    consulta_id = serializers.UUIDField(source="consulta.id", read_only=True)
    pagador_id = serializers.UUIDField(source="pagador.id", read_only=True)

    class Meta:
        model = Pagamento
        fields = [
            "id",
            "consulta_id",
            "pagador_id",
            "valor",
            "forma",
            "vencimento",
            "status",
            "gateway",
            "id_externo",
            "url_pagamento",
            "motivo_falha",
            "repasses",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["valor"] = str(instance.valor)
        data["links"] = {
            "self": f"/api/v1/pagamentos/{instance.id}/",
        }
        return data


class CriarPagamentoSerializer(serializers.Serializer):
    pagador_id = serializers.UUIDField()
    forma = serializers.ChoiceField(
        choices=["PIX", "BOLETO", "ESCOLHA_DO_PAGADOR"],
        default="PIX",
    )
    vencimento = serializers.CharField(required=False, default="")


class EstornoSerializer(serializers.Serializer):
    motivo = serializers.CharField(required=False, default="")
