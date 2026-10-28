"""Turn /jensen/ error responses into one JSON shape.

Success responses are left unchanged. Clients should read ``message`` for a
short explanation and ``errors`` for field lists. Original keys are kept so
older clients that read ``detail`` or a field name still work.
"""

import json
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse

logger = logging.getLogger(__name__)

API_PREFIX = "/jensen/"
ENVELOPE_KEYS = {"success", "status", "code", "message", "errors"}
PLAIN_KEYS = {"detail", "non_field_errors"}

STATUS_CODES = {
    400: "bad_request",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    415: "unsupported_media_type",
    429: "throttled",
    500: "server_error",
}

DEFAULT_MESSAGES = {
    400: "The request could not be processed.",
    401: "Sign in to continue.",
    403: "You do not have permission to do that.",
    404: "That record was not found.",
    405: "That action is not allowed.",
    500: "Something went wrong. Try again.",
}


def is_api_path(path):
    return (path or "").startswith(API_PREFIX)


def build_error(status, payload=None):
    status = int(status or 500)
    errors = _field_errors(payload)
    messages = _messages(errors)
    body = {
        "success": False,
        "status": status,
        "code": _code_for(status, errors),
        "message": "; ".join(messages[:4]) if messages else _default_message(status),
        "errors": errors,
    }
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key not in body:
                body[key] = value
    elif isinstance(payload, list) and payload:
        body["detail"] = payload
    return body


class ApiErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Exception:
            if not is_api_path(getattr(request, "path", "")):
                raise
            logger.exception("Unhandled API error on %s", request.path)
            return JsonResponse(build_error(500), status=500)
        return self._normalize(request, response)

    def process_exception(self, request, exception):
        if not is_api_path(getattr(request, "path", "")):
            return None
        logger.exception("Unhandled API error on %s", request.path)
        return JsonResponse(build_error(500), status=500)

    def _normalize(self, request, response):
        if not is_api_path(getattr(request, "path", "")):
            return response
        status = getattr(response, "status_code", 200) or 200
        if status < 400 or getattr(response, "streaming", False):
            return response

        payload = _read_payload(response)
        if payload is None and not _should_wrap(response):
            return response
        if _already_normalized(payload):
            payload["status"] = status
            return _write_json(response, payload, status)
        return _write_json(response, build_error(status, payload), status)


def _code_for(status, errors):
    if status == 400 and set(errors) - PLAIN_KEYS:
        return "validation_error"
    return STATUS_CODES.get(status, "error")


def _default_message(status):
    return DEFAULT_MESSAGES.get(status, "The request could not be completed.")


def _field_errors(payload):
    if isinstance(payload, dict):
        source = payload.get("errors")
        if not isinstance(source, dict):
            source = {
                key: value
                for key, value in payload.items()
                if key not in ENVELOPE_KEYS
            }
        errors = {}
        for key, value in source.items():
            messages = _collect(value)
            if messages:
                errors[str(key)] = messages
        return errors
    if isinstance(payload, list):
        messages = _collect(payload)
        return {"non_field_errors": messages} if messages else {}
    if isinstance(payload, str):
        text = payload.strip()
        if text and not text.startswith("<"):
            return {"detail": [text]}
    return {}


def _collect(value):
    messages = []
    if isinstance(value, str):
        text = value.strip()
        if text and not text.startswith("<"):
            messages.append(text)
    elif isinstance(value, list):
        for item in value:
            messages.extend(_collect(item))
    elif isinstance(value, dict):
        for item in value.values():
            messages.extend(_collect(item))
    elif value is not None:
        text = str(value).strip()
        if text:
            messages.append(text)
    return messages


def _messages(errors):
    messages = []
    for key, items in errors.items():
        for item in items:
            if key in PLAIN_KEYS:
                messages.append(item)
            else:
                messages.append(f"{key.replace('_', ' ')}: {item}")
    return messages


def _already_normalized(payload):
    return (
        isinstance(payload, dict)
        and payload.get("success") is False
        and isinstance(payload.get("message"), str)
        and isinstance(payload.get("errors"), dict)
        and isinstance(payload.get("code"), str)
    )


def _read_payload(response):
    content = getattr(response, "content", b"") or b""
    if content:
        if _looks_like_html(response, content):
            return None
        content_type = response.get("Content-Type", "")
        if "json" in content_type or content[:1] in (b"{", b"["):
            try:
                return json.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
        return None
    data = getattr(response, "data", None)
    if isinstance(data, (dict, list, str)):
        return data
    return None


def _looks_like_html(response, content):
    content_type = response.get("Content-Type", "")
    if "text/html" in content_type:
        return True
    return bool(content) and content[:1] == b"<"


def _should_wrap(response):
    content = getattr(response, "content", b"") or b""
    if not content:
        return True
    return _looks_like_html(response, content)


def _write_json(response, body, status):
    encoded = json.dumps(body, cls=DjangoJSONEncoder).encode("utf-8")
    if hasattr(response, "data"):
        response.data = body
    response.status_code = status
    response.content = encoded
    response["Content-Type"] = "application/json"
    response["Content-Length"] = str(len(encoded))
    return response
