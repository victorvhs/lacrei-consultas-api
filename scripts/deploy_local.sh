#!/bin/bash
set -e

TAG="${1:-latest}"
PREVIOUS_TAG="${2:-previous}"

echo "Deploying version: $TAG"

APP_IMAGE="lacrei-saude:$TAG" docker compose -f docker-compose.release.yml up -d db
sleep 5

echo "Running migrations..."
APP_IMAGE="lacrei-saude:$TAG" docker compose -f docker-compose.release.yml run --rm migrate

echo "Starting API..."
APP_IMAGE="lacrei-saude:$TAG" docker compose -f docker-compose.release.yml up -d api
sleep 5

echo "Health check..."
for i in $(seq 1 10); do
  RESPONSE=$(curl -sf http://localhost:8001/health/live || echo "")
  if echo "$RESPONSE" | grep -q "$TAG"; then
    echo "Deploy successful: version $TAG is live"
    exit 0
  fi
  sleep 2
done

echo "Health check failed! Rolling back to $PREVIOUS_TAG..."
APP_IMAGE="lacrei-saude:$PREVIOUS_TAG" docker compose -f docker-compose.release.yml up -d api
echo "Rollback complete."
exit 1
