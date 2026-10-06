"""
Tests for serving the production frontend.

The Dockerfile, `make build` and deploy/install_app.sh copy the Create React
App build to static/ next to server.py: index.html is static/index.html, and
the bundles it loads from /static/js/... and /static/css/... live in
static/static/. Regression: /static was mounted on static/ itself, so every
bundle returned 404 and the page stayed blank.

server.py decides at import time whether to mount the bundles, so these tests
load a fresh copy of it from a temporary directory that contains such a build.
"""

import importlib.util
import logging
import re
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SERVER_PY = Path(__file__).resolve().parent.parent / "server.py"

INDEX_HTML = (
    '<!doctype html><html><head>'
    '<script defer="defer" src="/static/js/main.1a2b3c4d.js"></script>'
    '<link href="/static/css/main.5e6f7a8b.css" rel="stylesheet">'
    '</head><body><div id="root"></div></body></html>'
)


@pytest.fixture
def frontend_client(tmp_path):
    """A client for a copy of server.py whose static/ holds a CRA build."""
    shutil.copy(SERVER_PY, tmp_path / "server.py")
    build = tmp_path / "static"
    (build / "static" / "js").mkdir(parents=True)
    (build / "static" / "css").mkdir(parents=True)
    (build / "index.html").write_text(INDEX_HTML)
    (build / "static" / "js" / "main.1a2b3c4d.js").write_text("console.log('quiz');")
    (build / "static" / "css" / "main.5e6f7a8b.css").write_text("body { margin: 0; }")

    spec = importlib.util.spec_from_file_location("server_with_build", tmp_path / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        # No `with`: the startup hook isn't needed to serve files
        yield TestClient(module.app)
    finally:
        # The copy attached its own handler to the shared audit logger
        logging.getLogger("audit").removeHandler(module.audit_handler)
        module.audit_handler.close()


class TestBuiltFrontend:
    def test_index_and_its_bundles_load(self, frontend_client):
        index = frontend_client.get("/")
        assert index.status_code == 200
        assert index.headers["content-type"].startswith("text/html")

        assets = re.findall(r'(?:src|href)="(/static/[^"]+)"', index.text)
        assert assets == ["/static/js/main.1a2b3c4d.js", "/static/css/main.5e6f7a8b.css"]
        js, css = (frontend_client.get(path) for path in assets)
        assert js.status_code == 200
        assert "javascript" in js.headers["content-type"]
        assert js.text == "console.log('quiz');"
        assert css.status_code == 200
        assert css.headers["content-type"].startswith("text/css")

    def test_missing_bundle_returns_404_not_index_html(self, frontend_client):
        resp = frontend_client.get("/static/js/main.00000000.js")
        assert resp.status_code == 404

    def test_client_side_route_falls_back_to_index_html(self, frontend_client):
        resp = frontend_client.get("/quiz/loops")
        assert resp.status_code == 200
        assert 'id="root"' in resp.text

    def test_api_routes_still_take_precedence(self, frontend_client):
        resp = frontend_client.get("/api/health")
        assert resp.json()["status"] == "healthy"
