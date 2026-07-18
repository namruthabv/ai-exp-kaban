# Project Management MVP

## Run locally

Install a Docker-compatible runtime with Docker Compose, such as Rancher Desktop, Colima, Docker Desktop, or Docker Engine. Start that runtime, then run the script for your platform:

```bash
./scripts/start-mac.sh
./scripts/start-linux.sh
```

The macOS script uses Rancher Desktop's native platform and prevents inherited
proxy variables from reaching Docker. This affects only the script and the
commands it launches, not the parent terminal session. When Docker requires the
terminal's proxy configuration, run `./scripts/start-mac.sh --use-proxy`
instead.

```powershell
.\scripts\start-windows.ps1
```

Open <http://localhost:8000>. Stop the app with the matching `stop-*` script.
Sign in with username `user` and password `password`.

The container builds the Next.js frontend as static files and serves them with the FastAPI API from the same origin.

Set `SESSION_SECRET` in the root `.env` file to keep signed login sessions valid
across container restarts. When it is omitted, the backend safely generates a
temporary secret at startup for local use.

## Backend tests

```bash
cd backend
uv run pytest
```
