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
    endereco = EnderecoSerializer(source="*", write_only=True)
    contato = ContatoSerializer(source="*", write_only=True)
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
        rep = super().to_representation(instance)
        rep.pop("endereco", None)
        rep.pop("contato", None)
        rep["endereco"] = {
            "logradouro": instance.logradouro,
            "numero": instance.numero,
            "complemento": instance.complemento,
            "bairro": instance.bairro,
            "cidade": instance.cidade,
            "uf": instance.uf,
            "cep": instance.cep,
        }
        rep["contato"] = {
            "email": instance.email,
            "telefone": instance.telefone,
        }
        return rep

    def validate(self, attrs):
        email = attrs.get("email", "")
        telefone = attrs.get("telefone", "")
        if not email and not telefone:
            raise serializers.ValidationError({"email": "Profissional precisa de email ou telefone."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("endereco", None)
        validated_data.pop("contato", None)
        instance = super().create(validated_data)
        instance.clean()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        validated_data.pop("endereco", None)
        validated_data.pop("contato", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.clean()
        instance.save()
        return instance
