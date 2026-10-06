# =============================================================================
# ICS31 Quiz Generator — Makefile
#
# Targets are designed for the Linux/macOS environment used in CI and on the
# EC2 server.  On Windows, run these commands inside WSL or Git Bash.
# =============================================================================

.DEFAULT_GOAL := help
.PHONY: help run build test clean deploy

# ---------------------------------------------------------------------------
# Help — list all targets with their descriptions
# ---------------------------------------------------------------------------
help: ## Show this help message
	@echo ""
	@echo "ICS31 Quiz Generator"
	@echo "--------------------"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# ---------------------------------------------------------------------------
# run — start the FastAPI development server
# ---------------------------------------------------------------------------
run: ## Start the backend server on port 8000
	python server.py

# ---------------------------------------------------------------------------
# build — compile the React frontend into static/
# ---------------------------------------------------------------------------
build: ## Build the React frontend and copy output to static/
	@echo "[build] Installing frontend dependencies..."
	cd frontend && npm ci
	@echo "[build] Building React app..."
	cd frontend && npm run build
	@echo "[build] Copying build output to static/..."
	mkdir -p static
	cp -r frontend/build/. static/
	@echo "[build] Done. Serve with: make run"

# ---------------------------------------------------------------------------
# test — run the pytest suite (no real API keys or media libs needed)
# ---------------------------------------------------------------------------
test: ## Run the pytest suite
	@echo "[test] Installing dev dependencies..."
	pip install -q -r requirements-dev.txt
	@echo "[test] Running tests..."
	pytest tests/ -v --tb=short

# ---------------------------------------------------------------------------
# clean — remove generated artifacts (does NOT touch source files)
# ---------------------------------------------------------------------------
clean: ## Remove generated videos, temp files, logs, and build artifacts
	@echo "[clean] Removing generated videos (videos/<uuid>.mp4)..."
	find videos/ -name '????????-????-????-????-????????????.mp4' -delete 2>/dev/null || true
	@echo "[clean] Removing temp files..."
	rm -rf temp/*
	@echo "[clean] Removing log files..."
	rm -f logs/*.log logs/*.log.*.gz
	@echo "[clean] Removing frontend build artifacts..."
	rm -rf frontend/build static/
	@echo "[clean] Removing Python cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache/
	@echo "[clean] Done."

# ---------------------------------------------------------------------------
# deploy — build and (re)start via Docker Compose
# ---------------------------------------------------------------------------
deploy: ## Deploy with Docker Compose (requires .env with OPENAI_API_KEY)
	@if [ ! -f .env ]; then \
		echo ""; \
		echo "ERROR: .env file not found."; \
		echo "  cp .env.example .env   # then fill in your OPENAI_API_KEY"; \
		echo ""; \
		exit 1; \
	fi
	@if ! grep -q "^OPENAI_API_KEY=sk-" .env; then \
		echo ""; \
		echo "WARNING: OPENAI_API_KEY does not look set in .env — deployment may fail."; \
		echo ""; \
	fi
	@echo "[deploy] Building and starting containers..."
	docker-compose up -d --build
	@echo "[deploy] Waiting for health check..."
	@sleep 5
	@curl -sf http://localhost:8000/api/health && echo " — service is healthy" || echo "WARNING: health check failed, check logs with: docker-compose logs -f"
