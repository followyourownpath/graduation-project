#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/home/interndev/bread}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

cd "$APP_DIR"

if [[ ! -f .env ]]; then
  echo "Missing $APP_DIR/.env. Copy deploy/production.env.example and provide production values." >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" config --quiet
docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans

if ! curl --fail --silent --show-error \
  --retry 12 --retry-delay 5 --retry-all-errors \
  http://127.0.0.1:5001/api/v1/health >/dev/null; then
  docker compose -f "$COMPOSE_FILE" logs --tail=100 backend frontend
  exit 1
fi

curl --fail --silent --show-error \
  --retry 12 --retry-delay 5 --retry-all-errors \
  http://127.0.0.1:3001/bread/login >/dev/null

echo "Bread deployment is healthy."
