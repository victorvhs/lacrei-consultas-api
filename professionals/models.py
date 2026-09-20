import re
import uuid

from django.core.validators import validate_email
from django.db import models


class Professional(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome_social = models.CharField(max_length=150)
    profissao = models.CharField(max_length=100)
    logradouro = models.CharField(max_length=200)
    numero = models.CharField(max_length=20)
    complemento = models.CharField(max_length=100, blank=True, default="")
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    cep = models.CharField(max_length=8)
    email = models.EmailField(max_length=254, blank=True, default="")
    telefone = models.CharField(max_length=11, blank=True, default="")
    carteira_repasse_id = models.CharField(max_length=64, blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.nome_social

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        if not self.email and not self.telefone:
            errors["email"] = "Profissional precisa de email ou telefone."

        if self.email:
            try:
                validate_email(self.email.lower())
            except Exception:
                errors["email"] = "Email inválido."
            self.email = self.email.lower().strip()

        if self.telefone:
            self.telefone = re.sub(r"\D", "", self.telefone)
            if len(self.telefone) not in (10, 11):
                errors["telefone"] = "Telefone deve ter 10 ou 11 dígitos."

        if self.cep:
            self.cep = re.sub(r"\D", "", self.cep)
            if len(self.cep) != 8:
                errors["cep"] = "CEP deve conter 8 dígitos."

        valid_ufs = [
            "AC",
            "AL",
            "AP",
            "AM",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MT",
            "MS",
            "MG",
            "PA",
            "PB",
            "PR",
            "PE",
            "PI",
            "RJ",
            "RN",
            "RS",
            "RO",
            "RR",
            "SC",
            "SP",
            "SE",
            "TO",
        ]
        if self.uf and self.uf.upper() not in valid_ufs:
            errors["uf"] = "UF inválida."
        self.uf = self.uf.upper() if self.uf else self.uf

        if self.nome_social:
            self.nome_social = self.nome_social.strip()
            if "<" in self.nome_social or ">" in self.nome_social:
                errors["nome_social"] = "Nome social não pode conter HTML."

        if errors:
            raise ValidationError(errors)
