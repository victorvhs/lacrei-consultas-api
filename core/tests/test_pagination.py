from rest_framework.test import APITestCase


class StandardPaginationTest(APITestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        from professionals.models import Professional
        
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)
        
        for i in range(25):
            Professional.objects.create(
                nome_social=f"Professional {i}",
                profissao="Doctor",
                logradouro="Rua 1",
                numero="100",
                bairro="Centro",
                cidade="São Paulo",
                uf="SP",
                cep="01001000",
                email=f"prof{i}@example.com",
            )

    def test_default_page_size(self):
        response = self.client.get("/api/v1/profissionais/")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertEqual(response.data["count"], 25)

    def test_custom_page_size(self):
        response = self.client.get("/api/v1/profissionais/?page_size=10")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 10)

    def test_max_page_size(self):
        response = self.client.get("/api/v1/profissionais/?page_size=200")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 25)
