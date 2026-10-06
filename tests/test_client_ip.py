"""Client IP resolution: forwarded headers from the client must not be trusted."""

from starlette.requests import Request

import server


def _request(client, headers=()):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/health",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers],
    }
    if client:
        scope["client"] = (client, 50000)
    return Request(scope)


def test_spoofed_forwarded_for_is_ignored():
    request = _request("203.0.113.7", [("X-Forwarded-For", "6.6.6.6"), ("X-Real-IP", "6.6.6.6")])
    assert server.get_client_ip(request) == "203.0.113.7"


def test_missing_client_is_unknown():
    assert server.get_client_ip(_request(None)) == "unknown"
