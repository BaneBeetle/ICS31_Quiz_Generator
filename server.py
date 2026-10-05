"""
ICS31 Quiz Generator API Server
Security-hardened with rate limiting, input validation, audit logging, and secure configuration.
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import re
import json
import logging
import threading
import asyncio
from uuid import uuid4
from typing import Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from main import generate

# =============================================================================
# LOGGING CONFIGURATION (STRIDE: Repudiation - Audit Trail)
# =============================================================================

# Configure structured audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# File handler for audit logs (JSON format for easy parsing)
audit_handler = logging.FileHandler(
    os.path.join(LOGS_DIR, "audit.log"),
    encoding="utf-8"
)
audit_handler.setFormatter(logging.Formatter("%(message)s"))
audit_logger.addHandler(audit_handler)

# Also log to console in development
if os.getenv("DEBUG", "false").lower() == "true":
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("[AUDIT] %(message)s"))
    audit_logger.addHandler(console_handler)


def log_audit(
    action: str,
    request: Request,
    job_id: str = None,
    success: bool = True,
    details: dict = None
):
    """
    Log security-relevant events for audit trail.

    STRIDE: Addresses Repudiation by maintaining evidence of who did what and when.
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action,
        "client_ip": get_client_ip(request),
        "user_agent": request.headers.get("User-Agent", "unknown")[:200],  # Truncate long UAs
        "job_id": job_id,
        "success": success,
        "method": request.method,
        "path": str(request.url.path),
        "details": details or {}
    }
    audit_logger.info(json.dumps(log_entry))


# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Rate limiting configuration (OWASP: Protect against brute force/DoS)
RATE_LIMIT_GENERATE = "5/hour"       # Max 5 video generations per IP per hour
RATE_LIMIT_STATUS = "60/minute"       # Status polling during generation
RATE_LIMIT_DEFAULT = "30/minute"      # General endpoints

# Input validation limits (OWASP: Input validation)
TOPIC_MIN_LENGTH = 2
TOPIC_MAX_LENGTH = 100
ALLOWED_TOPIC_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.,!?\'"()]+$')

# Job ID validation (prevent path traversal/injection)
UUID_PATTERN = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')

# Auto-cleanup configuration
VIDEO_MAX_AGE_MINUTES = 30
CLEANUP_INTERVAL_SECONDS = 300
# [ADDED] Orphaned temp files (e.g. from crashed jobs) older than this are purged
TEMP_MAX_AGE_HOURS = 1

# CORS configuration
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

# Maximum concurrent jobs per IP
MAX_CONCURRENT_JOBS_PER_IP = 2

# Maximum total jobs in memory (prevent memory exhaustion)
MAX_TOTAL_JOBS = 100

# STRIDE: Spoofing - Only trust X-Forwarded-For when behind a known proxy
# Set TRUST_PROXY=true when deploying behind Nginx/load balancer
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"

# =============================================================================
# RATE LIMITER SETUP
# =============================================================================

limiter = Limiter(key_func=get_remote_address)

# Track active jobs per IP
active_jobs_by_ip: dict[str, list[str]] = {}

# =============================================================================
# INPUT VALIDATION MODELS (OWASP: Schema-based validation)
# =============================================================================

class GenerateRequest(BaseModel):
    """Validated request model for video generation."""
    topic: str = Field(
        ...,
        min_length=TOPIC_MIN_LENGTH,
        max_length=TOPIC_MAX_LENGTH,
        description="Python topic for quiz generation"
    )
    model_config = {"extra": "forbid"}

    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v: str) -> str:
        # Security: Normalize unicode to prevent homoglyph attacks
        import unicodedata
        v = unicodedata.normalize('NFKC', v)

        # Security: Remove null bytes and control characters
        v = ''.join(char for char in v if ord(char) >= 32 or char in '\t\n')
        v = v.replace('\x00', '')  # Explicitly remove null bytes

        v = v.strip()
        if not v:
            raise ValueError("Topic cannot be empty or whitespace only")

        # Security: Check for non-ASCII characters (only allow basic Latin)
        if not v.isascii():
            raise ValueError(
                "Topic must contain only ASCII characters. "
                "Please use English letters and numbers."
            )

        if not ALLOWED_TOPIC_PATTERN.match(v):
            raise ValueError(
                "Topic contains invalid characters. "
                "Only letters, numbers, spaces, and basic punctuation allowed."
            )
        v = ' '.join(v.split())
        return v


class JobStatus(BaseModel):
    """Response model for job status - no sensitive data exposed."""
    job_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    message: str
    error: Optional[str] = None
    has_video: bool = False


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def validate_job_id(job_id: str) -> bool:
    """Validate job ID format to prevent injection attacks."""
    return bool(UUID_PATTERN.match(job_id.lower()))


def get_client_ip(request: Request) -> str:
    """
    Extract client IP with secure proxy handling.

    STRIDE: Addresses Spoofing by only trusting X-Forwarded-For when
    explicitly configured (behind a trusted reverse proxy like Nginx).
    """
    if TRUST_PROXY:
        # Only trust proxy headers when configured
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP (original client) from the chain
            ip = forwarded.split(",")[0].strip()
            # Validate IP format to prevent injection
            if _is_valid_ip(ip):
                return ip
            # Fall back to direct connection if invalid
            return request.client.host if request.client else "unknown"

    # Direct connection - use actual client IP
    return request.client.host if request.client else "unknown"


def _is_valid_ip(ip: str) -> bool:
    """Validate IP address format (IPv4 or IPv6)."""
    import ipaddress
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def verify_job_ownership(request: Request, job_id: str) -> bool:
    """
    Verify the requesting client owns this job.

    STRIDE: Addresses Information Disclosure by preventing users from
    accessing other users' job data.
    """
    if job_id not in jobs:
        return False

    job = jobs[job_id]
    client_ip = get_client_ip(request)

    # Job owner is the IP that created it
    return job.get("client_ip") == client_ip


def check_concurrent_job_limit(client_ip: str) -> bool:
    """Check if client has reached concurrent job limit."""
    if client_ip not in active_jobs_by_ip:
        return True

    # Clean up completed jobs for this IP
    active_jobs_by_ip[client_ip] = [
        jid for jid in active_jobs_by_ip[client_ip]
        if jid in jobs and jobs[jid]["status"] in ("pending", "processing")
    ]

    return len(active_jobs_by_ip[client_ip]) < MAX_CONCURRENT_JOBS_PER_IP


def track_job_for_ip(client_ip: str, job_id: str):
    """Track a new job for rate limiting purposes."""
    if client_ip not in active_jobs_by_ip:
        active_jobs_by_ip[client_ip] = []
    active_jobs_by_ip[client_ip].append(job_id)


def cleanup_old_jobs():
    """Remove jobs and video files older than VIDEO_MAX_AGE_MINUTES."""
    now = datetime.now()
    jobs_to_delete = []

    for job_id, job in jobs.items():
        try:
            created_at = datetime.fromisoformat(job["created_at"])
            age = now - created_at

            if age > timedelta(minutes=VIDEO_MAX_AGE_MINUTES):
                if job.get("video_path") and os.path.exists(job["video_path"]):
                    try:
                        os.remove(job["video_path"])
                        print(f"[Cleanup] Deleted video: {job['video_path']}")
                    except Exception as e:
                        print(f"[Cleanup] Failed to delete video: {e}")

                jobs_to_delete.append(job_id)
        except Exception as e:
            print(f"[Cleanup] Error processing job {job_id}: {e}")

    for job_id in jobs_to_delete:
        del jobs[job_id]
        print(f"[Cleanup] Removed job: {job_id}")

    if jobs_to_delete:
        print(f"[Cleanup] Cleaned up {len(jobs_to_delete)} old jobs")


# [ADDED] Purge orphaned files from temp/ that are older than TEMP_MAX_AGE_HOURS.
# main.py calls cleanup_temp_files() on normal completion, but if a job crashes
# or the process is killed mid-generation those TTS/scratch files are never
# removed.  This function catches them on a scheduled basis.
def cleanup_temp_dir():
    """Remove orphaned files in temp/ that are older than TEMP_MAX_AGE_HOURS."""
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    if not os.path.exists(temp_dir):
        return

    now = datetime.now()
    cutoff = timedelta(hours=TEMP_MAX_AGE_HOURS)
    removed = 0

    for filename in os.listdir(temp_dir):
        filepath = os.path.join(temp_dir, filename)
        try:
            if os.path.isfile(filepath):
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if now - mtime > cutoff:
                    os.remove(filepath)
                    removed += 1
        except Exception as e:
            print(f"[TempCleanup] Could not remove {filepath}: {e}")

    if removed:
        print(f"[TempCleanup] Removed {removed} orphaned temp file(s) older than {TEMP_MAX_AGE_HOURS}h")


async def periodic_cleanup():
    """Background task for periodic video cleanup."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        cleanup_old_jobs()
        cleanup_temp_dir()  # [ADDED] also purge orphaned temp files


# =============================================================================
# APPLICATION LIFECYCLE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle manager."""
    cleanup_task = asyncio.create_task(periodic_cleanup())

    print(f"[Startup] Auto-cleanup enabled: videos expire after {VIDEO_MAX_AGE_MINUTES} minutes")
    print(f"[Startup] Rate limits: generate={RATE_LIMIT_GENERATE}, status={RATE_LIMIT_STATUS}")
    print(f"[Startup] Trust proxy: {TRUST_PROXY}")
    print(f"[Startup] Audit logging to: {LOGS_DIR}/audit.log")

    # Clean up leftover videos from previous runs
    videos_dir = os.path.join(os.path.dirname(__file__), "videos")
    if os.path.exists(videos_dir):
        for filename in os.listdir(videos_dir):
            if filename.endswith(".mp4"):
                filepath = os.path.join(videos_dir, filename)
                try:
                    os.remove(filepath)
                    print(f"[Startup] Cleaned up leftover video: {filename}")
                except Exception as e:
                    print(f"[Startup] Failed to clean up {filename}: {e}")

    yield

    cleanup_task.cancel()
    print("[Shutdown] Cleaning up all videos...")
    for job_id, job in list(jobs.items()):
        if job.get("video_path") and os.path.exists(job["video_path"]):
            try:
                os.remove(job["video_path"])
            except Exception:
                pass


# =============================================================================
# APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="ICS31 Quiz Generator API",
    description="Generate educational quiz videos for ICS 31 Python topics",
    version="1.0.0",
    lifespan=lifespan,
    debug=os.getenv("DEBUG", "false").lower() == "true"
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Serve static frontend files in production
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# CORS middleware with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

# In-memory storage for job status
jobs = {}


# =============================================================================
# VIDEO GENERATION
# =============================================================================

def process_video_generation(job_id: str, topic: str, client_ip: str):
    """Background task to generate video."""
    def progress_callback(progress: int, message: str):
        if job_id in jobs:
            jobs[job_id]["progress"] = progress
            jobs[job_id]["message"] = message

    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["message"] = "Starting video generation..."

        video_path = generate(topic, progress_callback)

        if job_id in jobs:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["message"] = "Video generation complete!"
            jobs[job_id]["video_path"] = video_path

            # Log successful generation
            audit_logger.info(json.dumps({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "video_generated",
                "client_ip": client_ip,
                "job_id": job_id,
                "success": True,
                "details": {"topic": topic}
            }))

    except Exception as e:
        if job_id in jobs:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "Video generation failed. Please try again."
            jobs[job_id]["message"] = "Generation failed"

            # Log failure (with actual error for debugging)
            audit_logger.info(json.dumps({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "video_generation_failed",
                "client_ip": client_ip,
                "job_id": job_id,
                "success": False,
                "details": {"topic": topic, "error": str(e)}
            }))

            print(f"[Error] Job {job_id} failed: {str(e)}")


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/api/health")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def health_check(request: Request):
    """Health check endpoint."""
    return {"status": "healthy", "service": "ICS31 Quiz Generator"}


@app.post("/api/generate")
@limiter.limit(RATE_LIMIT_GENERATE)
async def start_generation(request: Request, payload: GenerateRequest):
    """
    Start video generation for a topic.
    Rate limited and input validated.
    """
    client_ip = get_client_ip(request)

    # Check global job limit (prevent memory exhaustion)
    if len(jobs) >= MAX_TOTAL_JOBS:
        log_audit("generate_rejected", request, details={"reason": "global_limit"})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is at capacity. Please try again later."
        )

    # Check concurrent job limit per IP
    if not check_concurrent_job_limit(client_ip):
        log_audit("generate_rejected", request, details={"reason": "concurrent_limit"})
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum {MAX_CONCURRENT_JOBS_PER_IP} concurrent jobs allowed. "
                   "Please wait for your current job to complete."
        )

    job_id = str(uuid4())

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "message": "Job queued",
        "video_path": None,
        "created_at": datetime.now().isoformat(),
        "error": None,
        "topic": payload.topic,
        "client_ip": client_ip  # Store for ownership verification
    }

    # Track this job for concurrent limit
    track_job_for_ip(client_ip, job_id)

    # Audit log: job started
    log_audit("generate_started", request, job_id=job_id, details={"topic": payload.topic})

    # Start background thread for video generation
    thread = threading.Thread(
        target=process_video_generation,
        args=(job_id, payload.topic, client_ip)
    )
    thread.start()

    return {"job_id": job_id, "message": "Video generation started"}


@app.get("/api/status/{job_id}")
@limiter.limit(RATE_LIMIT_STATUS)
async def get_status(request: Request, job_id: str):
    """Get the status of a video generation job."""
    if not validate_job_id(job_id):
        log_audit("status_check", request, job_id=job_id, success=False,
                  details={"reason": "invalid_job_id"})
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    # STRIDE: Verify ownership to prevent information disclosure
    if not verify_job_ownership(request, job_id):
        log_audit("status_check", request, job_id=job_id, success=False,
                  details={"reason": "ownership_denied"})
        raise HTTPException(status_code=403, detail="Access denied")

    job = jobs[job_id]
    return JobStatus(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        error=job["error"],
        has_video=job["video_path"] is not None
    )


@app.get("/api/video/{job_id}")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_video(request: Request, job_id: str):
    """Download the generated video."""
    if not validate_job_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    # STRIDE: Verify ownership
    if not verify_job_ownership(request, job_id):
        log_audit("video_download", request, job_id=job_id, success=False,
                  details={"reason": "ownership_denied"})
        raise HTTPException(status_code=403, detail="Access denied")

    job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready yet")

    if not job["video_path"] or not os.path.exists(job["video_path"]):
        raise HTTPException(status_code=404, detail="Video file not found")

    # Audit log: video download
    log_audit("video_download", request, job_id=job_id)

    # Sanitize filename
    safe_topic = re.sub(r'[^a-zA-Z0-9_\-]', '_', job['topic'])[:50]
    filename = f"quiz_{safe_topic}_{job_id[:8]}.mp4"

    return FileResponse(
        path=job["video_path"],
        media_type="video/mp4",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store"
        }
    )


@app.get("/api/video/{job_id}/stream")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def stream_video(request: Request, job_id: str):
    """Stream the generated video for playback."""
    if not validate_job_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    # STRIDE: Verify ownership
    if not verify_job_ownership(request, job_id):
        log_audit("video_stream", request, job_id=job_id, success=False,
                  details={"reason": "ownership_denied"})
        raise HTTPException(status_code=403, detail="Access denied")

    job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready yet")

    if not job["video_path"] or not os.path.exists(job["video_path"]):
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        path=job["video_path"],
        media_type="video/mp4",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store"
        }
    )


@app.delete("/api/job/{job_id}")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def delete_job(request: Request, job_id: str):
    """Delete a job and its associated video file."""
    if not validate_job_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    # STRIDE: Verify ownership
    if not verify_job_ownership(request, job_id):
        log_audit("job_delete", request, job_id=job_id, success=False,
                  details={"reason": "ownership_denied"})
        raise HTTPException(status_code=403, detail="Access denied")

    job = jobs[job_id]

    if job["video_path"] and os.path.exists(job["video_path"]):
        try:
            os.remove(job["video_path"])
        except Exception:
            pass

    del jobs[job_id]

    log_audit("job_delete", request, job_id=job_id)

    return {"message": "Job deleted successfully"}


@app.post("/api/job/{job_id}/cleanup")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def cleanup_job(request: Request, job_id: str):
    """Cleanup endpoint for sendBeacon (browser unload events)."""
    if not validate_job_id(job_id):
        return {"message": "Invalid job ID"}

    if job_id not in jobs:
        return {"message": "Job not found or already cleaned"}

    # STRIDE: Verify ownership (but don't fail - sendBeacon can't handle errors)
    if not verify_job_ownership(request, job_id):
        log_audit("beacon_cleanup", request, job_id=job_id, success=False,
                  details={"reason": "ownership_denied"})
        return {"message": "Access denied"}

    job = jobs[job_id]

    if job.get("video_path") and os.path.exists(job["video_path"]):
        try:
            os.remove(job["video_path"])
        except Exception as e:
            print(f"[Beacon Cleanup] Failed to remove video: {e}")

    del jobs[job_id]

    log_audit("beacon_cleanup", request, job_id=job_id)

    return {"message": "Job cleaned up successfully"}


# =============================================================================
# FRONTEND ROUTES
# =============================================================================

@app.get("/")
async def serve_frontend():
    """Serve the React frontend."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "ICS31 Quiz Generator API", "docs": "/docs"}


@app.get("/{path:path}")
async def catch_all(path: str):
    """Catch-all route for React Router (SPA support)."""
    # Security: Prevent path traversal
    if ".." in path or path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    static_file = os.path.join(STATIC_DIR, path)

    # Verify path is within STATIC_DIR
    try:
        resolved = os.path.realpath(static_file)
        static_resolved = os.path.realpath(STATIC_DIR)
        if not resolved.startswith(static_resolved):
            raise HTTPException(status_code=400, detail="Invalid path")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    if os.path.exists(static_file) and os.path.isfile(static_file):
        return FileResponse(static_file)

    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Not found")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        # Security: Don't expose server version
        server_header=False,
        # Security: Connection timeouts (STRIDE: DoS protection)
        timeout_keep_alive=5,          # Close idle connections after 5s
        # Security: Limit concurrent connections for t3.small
        limit_concurrency=10,
        limit_max_requests=1000,       # Restart worker after 1000 requests (memory leak protection)
    )
