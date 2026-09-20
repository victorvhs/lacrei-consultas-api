import re
import unicodedata
import uuid

from django.core.validators import validate_email
from django.db import models


def sanitize_text(value):
    if value is None:
        return value
    value = unicodedata.normalize("NFC", str(value))
    value = value.strip()
    return value


def contains_html(value):
    if not value:
        return False
    return "<" in value or ">" in value


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

        self.nome_social = sanitize_text(self.nome_social)
        if not self.nome_social or len(self.nome_social) < 2:
            errors["nome_social"] = "Nome social deve ter entre 2 e 150 caracteres."
        elif len(self.nome_social) > 150:
            errors["nome_social"] = "Nome social deve ter entre 2 e 150 caracteres."
        elif contains_html(self.nome_social):
            errors["nome_social"] = "Nome social não pode conter HTML."

        self.profissao = sanitize_text(self.profissao)
        if contains_html(self.profissao):
            errors["profissao"] = "Profissão não pode conter HTML."

        if not self.email and not self.telefone:
            errors["email"] = "Profissional precisa de email ou telefone."

        if self.email:
            self.email = sanitize_text(self.email).lower()
            try:
                validate_email(self.email)
            except Exception:
                errors["email"] = "Email inválido."

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
        if self.uf:
            self.uf = self.uf.upper()
            if self.uf not in valid_ufs:
                errors["uf"] = "UF inválida."

        self.logradouro = sanitize_text(self.logradouro)
        self.bairro = sanitize_text(self.bairro)
        self.cidade = sanitize_text(self.cidade)
        self.complemento = sanitize_text(self.complemento) or ""

        if contains_html(self.logradouro):
            errors["logradouro"] = "Logradouro não pode conter HTML."
        if contains_html(self.bairro):
            errors["bairro"] = "Bairro não pode conter HTML."
        if contains_html(self.cidade):
            errors["cidade"] = "Cidade não pode conter HTML."

        if errors:
            raise ValidationError(errors)
