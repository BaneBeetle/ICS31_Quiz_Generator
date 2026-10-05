"""
Pytest configuration and shared fixtures for ICS31 Quiz Generator.

Heavy external dependencies (MoviePy, TikTok TTS, OpenAI) are replaced with
MagicMock objects *before* server.py is imported, so the full test suite runs
without real API keys, FFmpeg, or ImageMagick installed.
"""

import sys
from datetime import datetime
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Intercept heavy dependencies BEFORE server.py is imported.
#
# server.py does `from main import generate` at module level.  main.py in turn
# imports moviepy, tiktokvoice, and gpt_api — none of which should execute
# during unit/integration tests.
# ---------------------------------------------------------------------------
_mock_main = MagicMock()
_mock_main.generate = MagicMock(return_value="/fake/videos/test-video.mp4")

sys.modules.setdefault("main", _mock_main)
sys.modules.setdefault("moviepy_config", MagicMock())
sys.modules.setdefault("tiktokvoice", MagicMock())

# These imports must follow the sys.modules patches above.
from fastapi.testclient import TestClient  # noqa: E402
import server  # noqa: E402


# ---------------------------------------------------------------------------
# Helper — not a fixture so tests can call it freely
# ---------------------------------------------------------------------------

def make_job(
    job_id: str = None,
    status: str = "completed",
    video_path: str = None,
    client_ip: str = "testclient",
) -> str:
    """Insert a synthetic job into server.jobs and return its ID.

    Uses 'testclient' as the default IP because that is what Starlette's
    TestClient reports as request.client.host for every request.
    """
    from uuid import uuid4

    if job_id is None:
        job_id = str(uuid4())

    server.jobs[job_id] = {
        "job_id": job_id,
        "status": status,
        "progress": 100 if status == "completed" else 0,
        "message": "Done" if status == "completed" else "Pending",
        "video_path": video_path,
        "created_at": datetime.now().isoformat(),
        "error": None,
        "topic": "loops",
        "client_ip": client_ip,
    }
    return job_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_server_state():
    """Clear shared mutable state between tests to prevent leakage."""
    server.jobs.clear()
    server.active_jobs_by_ip.clear()
    yield
    server.jobs.clear()
    server.active_jobs_by_ip.clear()


@pytest.fixture
def client():
    """Fresh TestClient for each test.  raise_server_exceptions=False so that
    5xx responses are returned as HTTP responses rather than raised exceptions,
    which lets us assert on status codes for error paths."""
    with TestClient(server.app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def completed_job(tmp_path):
    """A completed job whose video file actually exists on disk."""
    video_file = tmp_path / "output.mp4"
    video_file.write_bytes(b"\x00" * 16)  # minimal fake MP4 bytes
    job_id = make_job(video_path=str(video_file), status="completed")
    return job_id, str(video_file)


@pytest.fixture
def pending_job():
    """A job that is still processing."""
    return make_job(status="processing", video_path=None)
