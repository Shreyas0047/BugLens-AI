# Bug Lens-Ai

Intelligent Bug Report Analysis, Duplicate Detection and Severity Prediction System using NLP and AI.

An autonomous repository-level software quality and risk analysis platform: ingest a GitHub repo or
ZIP, run static analysis, detect duplicates/dead code, apply NLP semantics, and produce an
evidence-based risk report. It analyzes — it never modifies source code.

## Status: Phase 1 complete

- [x] Backend: FastAPI + SQLAlchemy + ARQ/Redis job queue (Python 3.12, pinned via uv)
- [x] Ingestion: GitHub URL (shallow clone, timeout, size caps) + ZIP upload (zip-slip/bomb guards)
- [x] Profiler: language detection (Python/JS/TS supported), manifests, framework hints, ignore rules
- [x] Worker: staged pipeline (ingest → profile → …) with per-stage progress + failure capture
- [x] API: repositories (create/upload/list/detail), runs (list/poll), health
- [ ] Static analysis (Phase 2) — next
- [ ] Redundancy / dead code (Phase 3)
- [ ] NLP layer (Phase 4)
- [ ] Risk engine (Phase 5)
- [ ] Risk graph + dashboard (Phases 6, 8)
- [ ] LLM explanations + evaluation (Phases 7, 9)

## Quick start

```bash
# 1. Redis (or your own redis-server)
docker run -d --name buglens-redis -p 6379:6379 --restart unless-stopped redis:7-alpine

# 2. Backend
cd backend
uv sync                        # Python 3.12 pinned via .python-version
uv run uvicorn app.main:app --reload --port 8000

# 3. Worker (separate terminal)
cd backend
uv run python -m workers.worker

# 4. Frontend (separate terminal)
cd frontend
npm install
npm run dev                    # http://localhost:5173 (proxies /api -> :8000)
```

## Security posture

Uploads and clones are treated as hostile: zip-slip/symlink rejection, compression-ratio bombs,
size/file-count caps, clone timeouts, per-run isolated workspaces, scrubbed subprocess env. The
target repository is never executed and its dependencies are never installed.

## Layout

```
backend/   FastAPI app, ARQ worker, ingestion/profiler services
frontend/  Vite + React + TypeScript + Tailwind SPA
ml/        dataset scripts + model training + evaluation (upcoming)
docs/      architecture + methodology + evaluation reports (upcoming)
```
