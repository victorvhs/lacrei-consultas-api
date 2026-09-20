from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Professional


class EnderecoSerializer(serializers.Serializer):
    logradouro = serializers.CharField(max_length=200)
    numero = serializers.CharField(max_length=20)
    complemento = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    bairro = serializers.CharField(max_length=100)
    cidade = serializers.CharField(max_length=100)
    uf = serializers.CharField(max_length=2)
    cep = serializers.CharField(max_length=9)


class ContatoSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254, required=False, allow_blank=True)
    telefone = serializers.CharField(max_length=20, required=False, allow_blank=True)


class ProfessionalSerializer(serializers.ModelSerializer):
    endereco = EnderecoSerializer(write_only=True, required=False)
    contato = ContatoSerializer(write_only=True, required=False)
    repasse_configurado = serializers.SerializerMethodField()

    class Meta:
        model = Professional
        fields = [
            "id",
            "nome_social",
            "profissao",
            "endereco",
            "contato",
            "repasse_configurado",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]

    def get_repasse_configurado(self, obj):
        return bool(obj.carteira_repasse_id)

    def to_representation(self, instance):
        rep = {
            "id": str(instance.id),
            "nome_social": instance.nome_social,
            "profissao": instance.profissao,
            "endereco": {
                "logradouro": instance.logradouro,
                "numero": instance.numero,
                "complemento": instance.complemento,
                "bairro": instance.bairro,
                "cidade": instance.cidade,
                "uf": instance.uf,
                "cep": instance.cep,
            },
            "contato": {
                "email": instance.email,
                "telefone": instance.telefone,
            },
            "repasse_configurado": bool(instance.carteira_repasse_id),
            "criado_em": instance.criado_em.isoformat(),
            "atualizado_em": instance.atualizado_em.isoformat(),
        }
        return rep

    def validate(self, attrs):
        contato = attrs.get("contato")
        if contato is None and self.instance:
            email = self.instance.email
            telefone = self.instance.telefone
        else:
            contato = contato or {}
            email = contato.get("email", "")
            telefone = contato.get("telefone", "")
        if not email and not telefone:
            raise serializers.ValidationError({"contato": {"email": ["Profissional precisa de email ou telefone."]}})
        return attrs

    def create(self, validated_data):
        endereco = validated_data.pop("endereco", {})
        contato = validated_data.pop("contato", {})

        validated_data["logradouro"] = endereco.get("logradouro", "")
        validated_data["numero"] = endereco.get("numero", "")
        validated_data["complemento"] = endereco.get("complemento", "")
        validated_data["bairro"] = endereco.get("bairro", "")
        validated_data["cidade"] = endereco.get("cidade", "")
        validated_data["uf"] = endereco.get("uf", "")
        validated_data["cep"] = endereco.get("cep", "")
        validated_data["email"] = contato.get("email", "")
        validated_data["telefone"] = contato.get("telefone", "")

        instance = Professional(**validated_data)
        try:
            instance.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        endereco = validated_data.pop("endereco", {})
        contato = validated_data.pop("contato", {})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if endereco:
            for attr, value in endereco.items():
                if hasattr(instance, attr):
                    setattr(instance, attr, value)

        if contato:
            for attr, value in contato.items():
                if hasattr(instance, attr):
                    setattr(instance, attr, value)

        try:
            instance.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        instance.save()
        return instance
