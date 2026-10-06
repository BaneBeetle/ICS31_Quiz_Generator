# ICS 31 Quiz Video Generator

[![CI](https://github.com/BaneBeetle/ICS31_Quiz_Generator/actions/workflows/ci.yml/badge.svg)](https://github.com/BaneBeetle/ICS31_Quiz_Generator/actions/workflows/ci.yml)

Turns a Python topic such as "Loops" or "Dictionaries" into a short, narrated, captioned
multiple-choice quiz video. An LLM writes the questions, a text-to-speech service narrates
them, and MoviePy/FFmpeg composites the narration, captions, a countdown sound and a
background clip into a vertical 576x1024 MP4.

**Demo:** [sample quiz video](https://www.youtube.com/shorts/uhuTbJ2Sr0c)

The project started as a command-line tool for UCI ICS 31 course staff and was later rebuilt
as a web app: a FastAPI backend with an asynchronous job API, a React frontend, Docker
packaging, deployment scripts for an Nginx + systemd server, and GitHub Actions CI. The
command-line entry point (`python main.py`) still works.

## How it works

### Video pipeline (`main.py`)

1. **Questions.** `gpt_api.generate_script()` asks the OpenAI Chat Completions API
   (`gpt-4o-mini`) for five multiple-choice questions on the topic as JSON (`question`,
   `choices` a-d, `correct`). The response is parsed and validated, topics that match simple
   prompt-injection patterns are rejected, and OpenAI errors are mapped to generic messages.
2. **Narration.** `tiktokvoice.tts()` synthesizes two intro lines, every question and every
   answer with the `en_us_001` voice through public TikTok TTS proxy endpoints (no API key).
   The clips are written to `temp/` and deleted when the job ends.
3. **Timeline.** Each question is followed by `clock.mp3` as a countdown. The question and its
   choices stay on screen for the narration plus the countdown, then the correct answer is
   read and shown. Optional background music is looped and mixed in at 15% volume.
4. **Render.** The background clip is resized to 576 px wide and looped or trimmed to the
   narration length. Captions are rendered by ImageMagick in Open Sans ExtraBold and
   composited on top, and the result is encoded as H.264/AAC (24 fps, `ultrafast` preset,
   CRF 28) to `videos/<uuid>.mp4`.

### Backend (`server.py`)

- **Async job API.** `POST /api/generate` validates the topic, creates a job with a UUID in an
  in-memory store, starts a background `threading.Thread` that runs the pipeline, and returns
  the job ID immediately.
- **Status polling.** The worker updates the job's `status` (`pending`, `processing`,
  `completed` or `failed`), `progress` (0-100) and `message` through a progress callback.
  Clients poll `GET /api/status/{job_id}`; the React app polls once per second.
- **Input validation.** Topics are NFKC-normalized, stripped of control characters, and must be
  2-100 ASCII characters from an allowlist of letters, digits, spaces and basic punctuation.
  Unknown request fields are rejected, and job IDs must be UUIDs.
- **Access control.** Each job records the client IP that created it. Status, video and delete
  requests from a different IP get `403`.
- **Limits.** SlowAPI rate limits per client (generate: 5/hour, status: 60/minute, other API
  endpoints: 30/minute), at most 2 active jobs per client IP (`429`), and at most 100 jobs in
  memory (`503`).
- **Cleanup.** A background task runs every 5 minutes and removes jobs and videos older than
  30 minutes and orphaned `temp/` files older than 1 hour. Leftover `.mp4` files in `videos/`
  are deleted at startup, and job videos at shutdown. The frontend deletes its job when the
  user starts a new quiz (`DELETE /api/job/{job_id}`) or closes the tab (`navigator.sendBeacon`
  to `POST /api/job/{job_id}/cleanup`).
- **Audit log.** Job starts, completions and failures, downloads, deletions, and rejected or
  denied requests are written as JSON lines to `logs/audit.log`.
- **Proxy support.** With `TRUST_PROXY=true` the client IP is taken from the first
  `X-Forwarded-For` entry (after validation); otherwise the socket peer address is used.
- **CORS and static files.** CORS is limited to `ALLOWED_ORIGINS` (GET, POST, DELETE). The
  production frontend is the React build copied to `static/` next to `server.py`: `/` returns
  `static/index.html`, `/static/...` serves the build's hashed JS and CSS bundles from
  `static/static/` (missing bundles are a `404`), and any other unmatched path returns the
  matching file from `static/`, falling back to `index.html`.

Job state lives in memory, so jobs do not survive a restart and the server is meant to run as
a single process.

### Frontend (`frontend/`)

A Create React App (React 18) page with three states: a topic form with suggestion chips and
client-side validation that mirrors the server rules, a progress screen driven by status
polling, and a player that streams the finished video with Download and Generate New Quiz
buttons. The production build calls the API on the origin it is served from (relative
`/api/...` URLs), so it works wherever FastAPI or Nginx serves it. The development server
(`npm start`, port 3000) calls `http://localhost:8000`. `REACT_APP_API_URL`, read at
build/start time, overrides both.

### Packaging and deployment

- **Docker.** The multi-stage `Dockerfile` builds the React app on `node:18-alpine`, then, on
  `python:3.12-slim`, installs FFmpeg, ImageMagick (with the policy change MoviePy needs to
  render text) and the Python dependencies, copies the backend modules and the React build
  (as `static/`), and runs `uvicorn server:app` on port 8000. `docker-compose.yml` runs that
  image with `OPENAI_API_KEY` taken from your environment or `.env`, mounts `videos/` and
  `temp/`, and defines a health check on `/api/health`. A `dev` profile adds the React dev
  server on port 3000.
- **Docker on EC2.** `deploy/ec2-setup.sh` installs Docker, Docker Compose and Git on Amazon
  Linux or Ubuntu, and `deploy/deploy.sh` pulls the repository, rebuilds the containers and
  checks `/api/health`. See [deploy/README.md](deploy/README.md).
- **Nginx + systemd on Ubuntu.** Run in this order:
  - `deploy/setup_server.sh` installs Python, Node.js 20, FFmpeg, ImageMagick, Nginx and a 2 GB
    swap file.
  - `deploy/install_app.sh` creates a virtualenv, installs the requirements and the font, and
    builds the frontend into `static/`.
  - `deploy/setup_service.sh` installs an `ics31-quiz` systemd unit that runs
    `python server.py` with the environment from `.env`. It sets `Restart=always` and
    sandboxing options (`NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome=read-only`,
    `PrivateTmp`).
  - `deploy/setup_nginx.sh` puts Nginx in front on port 80. It adds per-IP rate limits (1
    request/minute with a burst of 2 for `/api/generate`, 10 requests/second elsewhere), a 1 KB
    request-body limit, short client timeouts, security headers and unbuffered video
    proxying.
  - `deploy/logrotate.conf` rotates `logs/audit.log` daily.

  [DEPLOY.md](DEPLOY.md) walks through these steps.

## API

| Method | Path | Rate limit (per client) | Description |
| --- | --- | --- | --- |
| `GET` | `/api/health` | 30/minute | Health check |
| `POST` | `/api/generate` | 5/hour | Start a job. Body: `{"topic": "Loops"}`. Returns `job_id` and `message` |
| `GET` | `/api/status/{job_id}` | 60/minute | `job_id`, `status`, `progress`, `message`, `error`, `has_video` |
| `GET` | `/api/video/{job_id}/stream` | 30/minute | Finished MP4 for inline playback |
| `GET` | `/api/video/{job_id}` | 30/minute | Finished MP4 as a download |
| `DELETE` | `/api/job/{job_id}` | 30/minute | Delete the job and its video |
| `POST` | `/api/job/{job_id}/cleanup` | 30/minute | Same as `DELETE`, for `navigator.sendBeacon`; returns 200 even for unknown or foreign jobs |

Error responses: `400` malformed job ID or video not ready, `403` job created by a different
client IP, `404` unknown job or missing file, `422` invalid topic, `429` rate or concurrency
limit, `503` job store full. FastAPI's interactive docs are served at `/docs`.

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" -d '{"topic": "Loops"}'
curl http://localhost:8000/api/status/<job_id>
curl -o quiz.mp4 http://localhost:8000/api/video/<job_id>
```

## Getting started

### Requirements

- An OpenAI API key, and outbound internet access to OpenAI and the TTS endpoints.
- Python 3.12 (used by CI and the Docker image) and Node.js 20 (used by CI).
- ImageMagick, which MoviePy uses to render captions. `moviepy_config.py` looks for `magick` on
  `PATH` (and under Program Files on Windows) and sets `IMAGEMAGICK_BINARY`. On
  Debian/Ubuntu, ImageMagick's `policy.xml` must allow `@*` paths; the Dockerfile and
  `deploy/setup_server.sh` make that change.
- FFmpeg. By default MoviePy uses the binary that ships with the `imageio-ffmpeg` package; the
  Docker image and deploy scripts also install the system package.

### Media files (not included)

The repository includes the caption font but no audio or video. Supply files you have the
rights to use. `audio/`, `minecraft/` and all `.mp3`/`.mp4` files are git-ignored.

| File | Required | Where the code looks |
| --- | --- | --- |
| Background clip named `minecraft1*.mp4` | Yes | Anywhere under the project directory (recursive search), e.g. `minecraft/minecraft1.mp4` |
| `clock.mp3`, the countdown played after each question | Yes | Anywhere under the project directory, e.g. `audio/clock.mp3` |
| `wii_shop.mp3`, background music | No | Anywhere under the project directory, e.g. `audio/wii_shop.mp3` |
| `OpenSans-ExtraBold.ttf`, caption font | Included | Project root |

Don't put the background clip in `videos/`, because the server deletes `.mp4` files there on
startup. A 9:16 clip fills the frame; other clips are still scaled to 576 px wide.

The Docker image contains neither the media nor the font. Mount them, for example with a
`docker-compose.override.yml`:

```yaml
services:
  quiz-generator:
    volumes:
      - ./audio:/app/audio:ro
      - ./minecraft:/app/minecraft:ro
      - ./OpenSans-ExtraBold.ttf:/app/OpenSans-ExtraBold.ttf:ro
```

### Configuration

Copy `.env.example` to `.env`, which is git-ignored. Outside Docker, `gpt_api.py` loads it with
python-dotenv. Docker Compose reads it to fill in `OPENAI_API_KEY`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | none | Required for question generation |
| `PORT` | `8000` | Port used by `python server.py` |
| `DEBUG` | `false` | FastAPI debug mode and console audit logging |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated CORS origins |
| `TRUST_PROXY` | `false` | Trust `X-Forwarded-For`; enable only behind a reverse proxy |
| `REACT_APP_API_URL` | Same origin; `http://localhost:8000` under `npm start` | API base URL compiled into the frontend. Set it only if the API is on another origin |

`.env.example` sets `TRUST_PROXY=true` for the Nginx deployment. Set it to `false` when the app
is reachable directly.

### Run with Docker Compose

```bash
cp .env.example .env              # then set OPENAI_API_KEY
docker compose up --build         # http://localhost:8000
docker compose --profile dev up   # also starts the React dev server on :3000
```

### Run manually

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then set OPENAI_API_KEY
python server.py                  # API on http://localhost:8000, docs at /docs

# in a second terminal
cd frontend
npm ci
npm start                         # UI on http://localhost:3000
```

`make build` copies a production build of the frontend into `static/`, and `make help` lists
the other targets (`run`, `test`, `clean`, `deploy`).

### Command-line mode

`python main.py` prompts for a topic and writes the video to `videos/`.

## Tests and CI

`tests/test_api.py` contains 46 tests that exercise every API endpoint through FastAPI's
`TestClient`: happy paths, input validation, ownership checks, and the capacity and
concurrency limits. `tests/test_frontend.py` serves a stand-in React build and checks that
`index.html` and its JS/CSS bundles load. `tests/conftest.py` replaces `main`,
`moviepy_config` and `tiktokvoice` with mocks before importing the server, so the tests need no
API key, FFmpeg or ImageMagick.

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v                  # or: make test
```

GitHub Actions (`.github/workflows/ci.yml`) runs on pushes and pull requests to `main`. One job
runs the test suite on Python 3.12. The other runs `npm ci` and `npm run build` for the frontend
on Node.js 20, fails if the bundle hardcodes `http://localhost:8000`, and uploads the build as
an artifact for 7 days.

## Project layout

```
server.py               FastAPI app: job API, validation, limits, cleanup, audit log
main.py                 Video pipeline (also the CLI: python main.py)
gpt_api.py              OpenAI question generation
tiktokvoice.py          TikTok TTS client
moviepy_config.py       Finds ImageMagick for MoviePy on Windows
install_font.py         Installs the caption font for the current user
OpenSans-ExtraBold.ttf  Caption font (SIL Open Font License 1.1)
frontend/               React app (Create React App)
tests/                  pytest suite with mocked media and LLM dependencies
deploy/                 EC2, Docker, Nginx, systemd and logrotate scripts
Dockerfile, docker-compose.yml, Makefile, .github/workflows/ci.yml
```

## Credits

- `tiktokvoice.py` is a modified copy of GiorDior's TikTok-Voice-TTS script, which credits
  [oscie57/tiktok-voice](https://github.com/oscie57/tiktok-voice). It calls unofficial
  third-party TTS endpoints that may be rate limited or unavailable.
- Open Sans is Copyright 2020 The Open Sans Project Authors and is licensed under the
  [SIL Open Font License 1.1](https://openfontlicense.org).
