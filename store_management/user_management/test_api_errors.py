import json

from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase

from store_management.error_middleware import ApiErrorMiddleware, build_error


class ApiErrorMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_validation_body_is_normalized(self):
        request = self.factory.post("/jensen/auth/login/")
        original = JsonResponse(
            {"username": ["This field is required."]},
            status=400,
        )
        response = ApiErrorMiddleware(lambda _request: original)(request)
        body = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "validation_error")
        self.assertEqual(body["message"], "username: This field is required.")
        self.assertEqual(body["errors"]["username"], ["This field is required."])
        self.assertEqual(body["username"], ["This field is required."])
        self.assertEqual(response["Content-Type"], "application/json")

    def test_detail_string_stays_readable(self):
        body = build_error(403, {"detail": "You do not have permission to perform this action."})

        self.assertEqual(body["code"], "permission_denied")
        self.assertEqual(body["detail"], "You do not have permission to perform this action.")
        self.assertEqual(body["errors"]["detail"], ["You do not have permission to perform this action."])

    def test_success_payload_is_unchanged(self):
        request = self.factory.get("/jensen/stock/goods/")
        original = JsonResponse({"count": 1, "result": []})
        response = ApiErrorMiddleware(lambda _request: original)(request)

        self.assertEqual(json.loads(response.content), {"count": 1, "result": []})

    def test_non_api_errors_are_unchanged(self):
        request = self.factory.get("/admin/login/")
        original = HttpResponse("nope", status=404, content_type="text/html")
        response = ApiErrorMiddleware(lambda _request: original)(request)

        self.assertEqual(response.content, b"nope")
        self.assertEqual(response.status_code, 404)

    def test_html_api_error_becomes_json(self):
        request = self.factory.get("/jensen/stock/missing/")
        original = HttpResponse("<h1>Not Found</h1>", status=404, content_type="text/html")
        response = ApiErrorMiddleware(lambda _request: original)(request)
        body = json.loads(response.content)

        self.assertEqual(body["code"], "not_found")
        self.assertEqual(body["message"], "That record was not found.")
        self.assertNotIn("<h1>", response.content.decode())

    def test_unhandled_exception_hides_internal_detail(self):
        request = self.factory.get("/jensen/stock/goods/")

        def explode(_request):
            raise RuntimeError("password=secret")

        response = ApiErrorMiddleware(explode)(request)
        body = json.loads(response.content)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["code"], "server_error")
        self.assertNotIn("secret", response.content.decode())

    def test_normalized_body_is_not_wrapped_again(self):
        request = self.factory.post("/jensen/order/create_order/")
        original = JsonResponse(
            build_error(400, {"customer_name": ["This field is required."]}),
            status=400,
        )
        response = ApiErrorMiddleware(lambda _request: original)(request)
        body = json.loads(response.content)

        self.assertEqual(body["errors"]["customer_name"], ["This field is required."])
        self.assertNotIn("errors", body["errors"])
