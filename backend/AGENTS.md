# Backend development guide

This folder contains the FastAPI application and its tests. Follow the repository-root `AGENTS.md` in addition to this file.

- Keep API routes under `/api` so static frontend routes cannot shadow them.
- Keep route handlers thin and place reusable behavior in focused modules as it becomes necessary.
- Manage Python dependencies with `uv`; commit `uv.lock` and use locked installs in Docker.
- Validate behavior through FastAPI's `TestClient` and isolated test data.
- Never read or expose `OPENROUTER_API_KEY` in browser-facing code, API responses, or logs.
- The production process serves both the API and static frontend from one FastAPI application.

Run backend tests from this directory with `uv run pytest` when `uv` is installed, or run them through the Docker build from the repository root.
