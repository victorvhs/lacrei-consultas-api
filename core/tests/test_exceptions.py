from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory

from core.exceptions import custom_exception_handler


class CustomExceptionHandlerTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_handles_validation_error(self):
        request = self.factory.get("/test")
        request.request_id = "req-123"
        context = {"request": request}

        exc = ValidationError({"field": ["Error message"]})
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")

    def test_handles_401(self):
        from rest_framework.exceptions import NotAuthenticated

        request = self.factory.get("/test")
        request.request_id = "req-123"
        context = {"request": request}

        exc = NotAuthenticated()
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "not_authenticated")

    def test_handles_403(self):
        from rest_framework.exceptions import PermissionDenied

        request = self.factory.get("/test")
        request.request_id = "req-123"
        context = {"request": request}

        exc = PermissionDenied()
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"]["code"], "permission_denied")

    def test_handles_404(self):
        from rest_framework.exceptions import NotFound

        request = self.factory.get("/test")
        request.request_id = "req-123"
        context = {"request": request}

        exc = NotFound()
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "not_found")

    def test_handles_405(self):
        from rest_framework.exceptions import MethodNotAllowed

        request = self.factory.get("/test")
        request.request_id = "req-123"
        context = {"request": request}

        exc = MethodNotAllowed("GET")
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.data["error"]["code"], "method_not_allowed")

    def test_handles_409(self):

        request = self.factory.get("/test")
        request.request_id = "req-123"
        context = {"request": request}

        exc = Exception("Conflict")
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["error"]["code"], "internal_error")

    def test_handles_429(self):
        from rest_framework.exceptions import Throttled

        request = self.factory.get("/test")
        request.request_id = "req-123"
        context = {"request": request}

        exc = Throttled()
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["error"]["code"], "throttled")

    def test_handles_415(self):
        from rest_framework.exceptions import UnsupportedMediaType

        request = self.factory.get("/test")
        request.request_id = "req-123"
        context = {"request": request}

        exc = UnsupportedMediaType("text/plain")
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.data["error"]["code"], "unsupported_media_type")

    def test_handles_generic_exception(self):
        request = self.factory.get("/test")
        request.request_id = "req-123"
        context = {"request": request}

        exc = RuntimeError("Unexpected error")
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["error"]["code"], "internal_error")

    def test_includes_request_id(self):
        request = self.factory.get("/test")
        request.request_id = "unique-req-id"
        context = {"request": request}

        exc = ValidationError({"field": ["Error"]})
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.data["error"]["request_id"], "unique-req-id")
