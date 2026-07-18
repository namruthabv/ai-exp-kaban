#!/bin/sh
set -eu

unset DOCKER_DEFAULT_PLATFORM

if [ "${1:-}" = "--use-proxy" ]; then
  shift
else
  unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY
  echo "Starting with the native Docker platform and without inherited proxy settings."
fi

if [ "$#" -ne 0 ]; then
  echo "Usage: $0 [--use-proxy]" >&2
  exit 2
fi

cd "$(dirname "$0")/.."
docker compose up --build --detach

attempt=0
until curl --fail --silent http://localhost:8000/api/health >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 5 ]; then
    echo "The container started, but the health check did not become ready." >&2
    exit 1
  fi
  sleep 1
done

echo "Project Management MVP is available at http://localhost:8000"
