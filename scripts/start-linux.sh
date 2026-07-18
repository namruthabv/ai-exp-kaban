#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
docker compose up --build --detach

attempt=0
until curl --fail --silent http://localhost:8000/api/health >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "The container started, but the health check did not become ready." >&2
    exit 1
  fi
  sleep 1
done

echo "Project Management MVP is available at http://localhost:8000"
