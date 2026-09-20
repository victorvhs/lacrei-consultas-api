from django.test import TestCase
from django.test.client import RequestFactory

from core.middleware import HealthCheckMiddleware, RequestIDMiddleware, AccessLogMiddleware


class HealthCheckMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_health_live(self):
        request = self.factory.get("/health/live")
        middleware = HealthCheckMiddleware(lambda r: None)
        response = middleware(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn(b"status", response.content)
        self.assertIn(b"ok", response.content)

    def test_health_ready_with_db(self):
        request = self.factory.get("/health/ready")
        middleware = HealthCheckMiddleware(lambda r: None)
        response = middleware(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn(b"ready", response.content)

    def test_health_ready_without_db(self):
        from unittest.mock import patch
        
        request = self.factory.get("/health/ready")
        
        with patch("django.db.connection.ensure_connection", side_effect=Exception("DB down")):
            middleware = HealthCheckMiddleware(lambda r: None)
            response = middleware(request)
        
        self.assertEqual(response.status_code, 503)
        self.assertIn(b"unavailable", response.content)

    def test_other_paths_pass_through(self):
        request = self.factory.get("/api/v1/test")
        
        def mock_response(r):
            from django.http import HttpResponse
            return HttpResponse("OK")
        
        middleware = HealthCheckMiddleware(mock_response)
        response = middleware(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")


class RequestIDMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_adds_request_id(self):
        request = self.factory.get("/test")
        middleware = RequestIDMiddleware(lambda r: __import__("django.http", fromlist=["HttpResponse"]).HttpResponse("OK"))
        response = middleware(request)
        
        self.assertTrue(hasattr(request, "request_id"))
        self.assertIn("X-Request-ID", response)

    def test_uses_existing_request_id(self):
        request = self.factory.get("/test", HTTP_X_REQUEST_ID="custom-id-123")
        middleware = RequestIDMiddleware(lambda r: __import__("django.http", fromlist=["HttpResponse"]).HttpResponse("OK"))
        response = middleware(request)
        
        self.assertEqual(request.request_id, "custom-id-123")
        self.assertEqual(response["X-Request-ID"], "custom-id-123")


class AccessLogMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_logs_request(self):
        request = self.factory.get("/test")
        request.request_id = "test-id"
        request.user = type("User", (), {"id": 1})()
        
        from django.http import HttpResponse
        middleware = AccessLogMiddleware(lambda r: HttpResponse("OK"))
        
        with self.assertLogs("access", level="INFO") as cm:
            middleware(request)
        
        self.assertTrue(any("test-id" in log for log in cm.output))
        self.assertTrue(any("GET" in log for log in cm.output))
        self.assertTrue(any("/test" in log for log in cm.output))
