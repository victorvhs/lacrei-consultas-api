#!/bin/bash
set -e

TAG="${1:?Usage: rollback_local.sh <tag>}"

echo "Rolling back to version: $TAG"

APP_IMAGE="lacrei-saude:$TAG" docker compose -f docker-compose.release.yml up -d api

echo "Waiting for health check..."
for i in $(seq 1 10); do
  if curl -sf http://localhost:8001/health/live; then
    echo "Rollback successful: version $TAG is live"
    exit 0
  fi
  sleep 2
done

echo "Rollback health check failed!"
exit 1
