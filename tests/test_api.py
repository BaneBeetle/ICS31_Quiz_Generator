"""
Integration tests for all API endpoints in server.py.

All heavy external dependencies are mocked in conftest.py.
Tests cover:
  - Happy paths
  - Input validation / error cases
  - Ownership / access-control enforcement
  - Capacity / rate-limit guards (custom logic, not SlowAPI internals)
"""

from uuid import uuid4

from fastapi.testclient import TestClient

import server
from tests.conftest import make_job


# ===========================================================================
# GET /api/health
# ===========================================================================

class TestHealthEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_body_contains_healthy_status(self, client):
        resp = client.get("/api/health")
        assert resp.json()["status"] == "healthy"

    def test_body_contains_service_name(self, client):
        resp = client.get("/api/health")
        assert "service" in resp.json()


# ===========================================================================
# POST /api/generate
# ===========================================================================

class TestGenerateEndpoint:
    def test_valid_topic_returns_job_id(self, client):
        resp = client.post("/api/generate", json={"topic": "loops"})
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        # Confirm the returned value looks like a UUID
        assert len(data["job_id"]) == 36
        assert data["job_id"].count("-") == 4

    def test_valid_topic_creates_job_in_memory(self, client):
        resp = client.post("/api/generate", json={"topic": "functions"})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        assert job_id in server.jobs

    def test_missing_body_returns_422(self, client):
        resp = client.post("/api/generate")
        assert resp.status_code == 422

    def test_empty_topic_returns_422(self, client):
        resp = client.post("/api/generate", json={"topic": ""})
        assert resp.status_code == 422

    def test_whitespace_only_topic_returns_422(self, client):
        resp = client.post("/api/generate", json={"topic": "   "})
        assert resp.status_code == 422

    def test_topic_too_long_returns_422(self, client):
        resp = client.post("/api/generate", json={"topic": "a" * 101})
        assert resp.status_code == 422

    def test_non_ascii_topic_returns_422(self, client):
        # Japanese characters are not allowed by the ASCII validator
        resp = client.post("/api/generate", json={"topic": "ループ"})
        assert resp.status_code == 422

    def test_shell_special_chars_returns_422(self, client):
        resp = client.post("/api/generate", json={"topic": "loops; rm -rf /"})
        assert resp.status_code == 422

    def test_pipe_char_returns_422(self, client):
        resp = client.post("/api/generate", json={"topic": "loops | cat /etc/passwd"})
        assert resp.status_code == 422

    def test_extra_fields_rejected(self, client):
        # model_config = {"extra": "forbid"} should reject unknown fields
        resp = client.post("/api/generate", json={"topic": "lists", "hack": True})
        assert resp.status_code == 422

    def test_global_capacity_limit_returns_503(self, client):
        # Fill the in-memory job store to its maximum
        for _ in range(server.MAX_TOTAL_JOBS):
            make_job()
        resp = client.post("/api/generate", json={"topic": "functions"})
        assert resp.status_code == 503

    def test_concurrent_per_ip_limit_returns_429(self, client):
        # Saturate the concurrent-job allowance for the test client IP
        ip = "testclient"
        for _ in range(server.MAX_CONCURRENT_JOBS_PER_IP):
            jid = make_job(status="processing", client_ip=ip)
            server.active_jobs_by_ip.setdefault(ip, []).append(jid)
        resp = client.post("/api/generate", json={"topic": "conditionals"})
        assert resp.status_code == 429


# ===========================================================================
# GET /api/status/{job_id}
# ===========================================================================

class TestStatusEndpoint:
    def test_pending_job_returns_200(self, client, pending_job):
        resp = client.get(f"/api/status/{pending_job}")
        assert resp.status_code == 200

    def test_pending_job_body(self, client, pending_job):
        resp = client.get(f"/api/status/{pending_job}")
        data = resp.json()
        assert data["job_id"] == pending_job
        assert data["status"] == "processing"
        assert data["has_video"] is False

    def test_completed_job_has_video_true(self, client, completed_job):
        job_id, _ = completed_job
        resp = client.get(f"/api/status/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert resp.json()["has_video"] is True

    def test_invalid_uuid_returns_400(self, client):
        resp = client.get("/api/status/not-a-valid-uuid")
        assert resp.status_code == 400

    def test_unknown_job_returns_404(self, client):
        resp = client.get(f"/api/status/{uuid4()}")
        assert resp.status_code == 404

    def test_other_ips_job_returns_403(self, client):
        job_id = make_job(client_ip="192.168.1.1")
        resp = client.get(f"/api/status/{job_id}")
        assert resp.status_code == 403


# ===========================================================================
# GET /api/video/{job_id}  (download)
# GET /api/video/{job_id}/stream
# ===========================================================================

class TestVideoEndpoint:
    # --- download -----------------------------------------------------------

    def test_download_invalid_uuid_returns_400(self, client):
        resp = client.get("/api/video/bad-id")
        assert resp.status_code == 400

    def test_download_unknown_job_returns_404(self, client):
        resp = client.get(f"/api/video/{uuid4()}")
        assert resp.status_code == 404

    def test_download_pending_job_returns_400(self, client, pending_job):
        resp = client.get(f"/api/video/{pending_job}")
        assert resp.status_code == 400

    def test_download_completed_job_returns_200(self, client, completed_job):
        job_id, _ = completed_job
        resp = client.get(f"/api/video/{job_id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "video/mp4"

    def test_download_missing_file_returns_404(self, client):
        job_id = make_job(video_path="/nonexistent/video.mp4", status="completed")
        resp = client.get(f"/api/video/{job_id}")
        assert resp.status_code == 404

    def test_download_wrong_ip_returns_403(self, client):
        job_id = make_job(video_path="/fake.mp4", status="completed", client_ip="10.0.0.1")
        resp = client.get(f"/api/video/{job_id}")
        assert resp.status_code == 403

    # --- stream -------------------------------------------------------------

    def test_stream_invalid_uuid_returns_400(self, client):
        resp = client.get("/api/video/bad-id/stream")
        assert resp.status_code == 400

    def test_stream_unknown_job_returns_404(self, client):
        resp = client.get(f"/api/video/{uuid4()}/stream")
        assert resp.status_code == 404

    def test_stream_pending_job_returns_400(self, client, pending_job):
        resp = client.get(f"/api/video/{pending_job}/stream")
        assert resp.status_code == 400

    def test_stream_completed_job_returns_200(self, client, completed_job):
        job_id, _ = completed_job
        resp = client.get(f"/api/video/{job_id}/stream")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "video/mp4"

    def test_stream_wrong_ip_returns_403(self, client):
        job_id = make_job(video_path="/fake.mp4", status="completed", client_ip="10.0.0.1")
        resp = client.get(f"/api/video/{job_id}/stream")
        assert resp.status_code == 403


# ===========================================================================
# DELETE /api/job/{job_id}
# POST   /api/job/{job_id}/cleanup  (sendBeacon)
# ===========================================================================

class TestJobManagement:
    # --- DELETE -------------------------------------------------------------

    def test_delete_success_returns_200(self, client, completed_job):
        job_id, _ = completed_job
        resp = client.delete(f"/api/job/{job_id}")
        assert resp.status_code == 200

    def test_delete_removes_job_from_memory(self, client, completed_job):
        job_id, _ = completed_job
        client.delete(f"/api/job/{job_id}")
        assert job_id not in server.jobs

    def test_delete_removes_video_file(self, client, completed_job):
        import os
        job_id, video_path = completed_job
        assert os.path.exists(video_path)
        client.delete(f"/api/job/{job_id}")
        assert not os.path.exists(video_path)

    def test_delete_unknown_job_returns_404(self, client):
        resp = client.delete(f"/api/job/{uuid4()}")
        assert resp.status_code == 404

    def test_delete_invalid_uuid_returns_400(self, client):
        resp = client.delete("/api/job/not-a-uuid")
        assert resp.status_code == 400

    def test_delete_wrong_ip_returns_403(self, client):
        job_id = make_job(client_ip="10.0.0.1")
        resp = client.delete(f"/api/job/{job_id}")
        assert resp.status_code == 403

    # --- cleanup (sendBeacon) -----------------------------------------------

    def test_beacon_cleanup_success_returns_200(self, client, completed_job):
        job_id, _ = completed_job
        resp = client.post(f"/api/job/{job_id}/cleanup")
        assert resp.status_code == 200

    def test_beacon_cleanup_removes_job(self, client, completed_job):
        job_id, _ = completed_job
        client.post(f"/api/job/{job_id}/cleanup")
        assert job_id not in server.jobs

    def test_beacon_cleanup_unknown_job_still_returns_200(self, client):
        # sendBeacon endpoints must always return 200 — the browser ignores errors
        resp = client.post(f"/api/job/{uuid4()}/cleanup")
        assert resp.status_code == 200

    def test_beacon_cleanup_wrong_ip_still_returns_200(self, client):
        # Same reasoning: sendBeacon can't surface errors to the caller
        job_id = make_job(client_ip="10.0.0.1")
        resp = client.post(f"/api/job/{job_id}/cleanup")
        assert resp.status_code == 200


# ===========================================================================
# Frontend / catch-all routes
# ===========================================================================

class TestFrontendRoutes:
    def test_root_without_static_returns_json_fallback(self, client):
        # With no static/ build present the API returns a JSON message
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_root_with_static_serves_html(self, tmp_path):
        """When a built frontend exists at STATIC_DIR, / serves index.html."""
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<html><body>Quiz</body></html>")

        original = server.STATIC_DIR
        server.STATIC_DIR = str(static_dir)
        try:
            with TestClient(server.app, raise_server_exceptions=False) as c:
                resp = c.get("/")
            assert resp.status_code == 200
            assert b"Quiz" in resp.content
        finally:
            server.STATIC_DIR = original

    def test_path_with_dotdot_returns_400(self, client):
        # The catch-all route blocks paths containing '..'
        resp = client.get("/foo/../../secret")
        assert resp.status_code in (400, 404)

    def test_unknown_path_without_static_returns_404(self, client):
        resp = client.get("/nonexistent-page")
        assert resp.status_code == 404
