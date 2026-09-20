from django.core.exceptions import ValidationError
from django.test import TestCase

from professionals.models import Professional, contains_html, sanitize_text


class SanitizeTextTest(TestCase):
    def test_strips_whitespace(self):
        self.assertEqual(sanitize_text("  hello  "), "hello")

    def test_normalizes_unicode(self):
        import unicodedata

        value = unicodedata.normalize("NFD", "café")
        result = sanitize_text(value)
        self.assertEqual(result, "café")

    def test_handles_none(self):
        self.assertIsNone(sanitize_text(None))


class ContainsHtmlTest(TestCase):
    def test_detects_open_tag(self):
        self.assertTrue(contains_html("<script>alert('xss')</script>"))

    def test_detects_close_tag(self):
        self.assertTrue(contains_html("</div>"))

    def test_returns_false_for_clean_text(self):
        self.assertFalse(contains_html("Normal text"))

    def test_returns_false_for_empty(self):
        self.assertFalse(contains_html(""))
        self.assertFalse(contains_html(None))


class ProfessionalModelTest(TestCase):
    def test_create_valid_professional(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Setor Oeste",
            cidade="Goiânia",
            uf="GO",
            cep="74120-020",
            email="ana@example.com",
        )
        prof.clean()
        prof.save()

        self.assertIsNotNone(prof.id)
        self.assertEqual(prof.nome_social, "Ana Souza")
        self.assertEqual(prof.cep, "74120020")
        self.assertEqual(prof.uf, "GO")

    def test_requires_email_or_phone(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Setor Oeste",
            cidade="Goiânia",
            uf="GO",
            cep="74120020",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("email", ctx.exception.message_dict)

    def test_rejects_html_in_nome_social(self):
        prof = Professional(
            nome_social="<script>alert('xss')</script>",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="test@example.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("nome_social", ctx.exception.message_dict)

    def test_rejects_short_nome_social(self):
        prof = Professional(
            nome_social="A",
            profissao="Doctor",
            logradouro="Rua 1",
            numero="1",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="test@example.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("nome_social", ctx.exception.message_dict)

    def test_rejects_long_nome_social(self):
        prof = Professional(
            nome_social="A" * 151,
            profissao="Doctor",
            logradouro="Rua 1",
            numero="1",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="test@example.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("nome_social", ctx.exception.message_dict)

    def test_rejects_invalid_email(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="invalid-email",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("email", ctx.exception.message_dict)

    def test_rejects_invalid_phone(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            telefone="12345",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("telefone", ctx.exception.message_dict)

    def test_accepts_valid_phone_10_digits(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            telefone="(11) 1234-5678",
        )
        prof.clean()
        self.assertEqual(prof.telefone, "1112345678")

    def test_accepts_valid_phone_11_digits(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            telefone="(11) 99999-0000",
        )
        prof.clean()
        self.assertEqual(prof.telefone, "11999990000")

    def test_rejects_invalid_cep(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="1234",
            email="test@example.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("cep", ctx.exception.message_dict)

    def test_strips_cep_formatting(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="74120-020",
            email="test@example.com",
        )
        prof.clean()
        self.assertEqual(prof.cep, "74120020")

    def test_rejects_invalid_uf(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="XX",
            cep="01001000",
            email="test@example.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("uf", ctx.exception.message_dict)

    def test_normalizes_uf_to_uppercase(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="sp",
            cep="01001000",
            email="test@example.com",
        )
        prof.clean()
        self.assertEqual(prof.uf, "SP")

    def test_rejects_html_in_logradouro(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="<b>Rua 10</b>",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="test@example.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("logradouro", ctx.exception.message_dict)

    def test_rejects_html_in_bairro(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="<script>alert(1)</script>",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="test@example.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("bairro", ctx.exception.message_dict)

    def test_rejects_html_in_cidade(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="<img src=x>",
            uf="SP",
            cep="01001000",
            email="test@example.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("cidade", ctx.exception.message_dict)

    def test_rejects_html_in_profissao(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="<b>Doctor</b>",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="test@example.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            prof.clean()
        self.assertIn("profissao", ctx.exception.message_dict)

    def test_strips_whitespace_from_fields(self):
        prof = Professional(
            nome_social="  Ana Souza  ",
            profissao="  Psicóloga  ",
            logradouro="  Rua 10  ",
            numero="250",
            bairro="  Centro  ",
            cidade="  SP  ",
            uf="SP",
            cep="01001000",
            email="test@example.com",
        )
        prof.clean()
        self.assertEqual(prof.nome_social, "Ana Souza")
        self.assertEqual(prof.profissao, "Psicóloga")
        self.assertEqual(prof.logradouro, "Rua 10")

    def test_email_normalized_to_lowercase(self):
        prof = Professional(
            nome_social="Ana Souza",
            profissao="Psicóloga",
            logradouro="Rua 10",
            numero="250",
            bairro="Centro",
            cidade="SP",
            uf="SP",
            cep="01001000",
            email="TEST@EXAMPLE.COM",
        )
        prof.clean()
        self.assertEqual(prof.email, "test@example.com")

    def test_str_representation(self):
        prof = Professional(nome_social="Ana Souza")
        self.assertEqual(str(prof), "Ana Souza")
