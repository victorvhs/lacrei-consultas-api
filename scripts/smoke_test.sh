#!/bin/bash
set -e

BASE_URL="${1:-http://localhost:8001}"

echo "Running smoke tests against $BASE_URL"

echo -n "Health live: "
curl -sf "$BASE_URL/health/live" && echo " OK" || { echo "FAIL"; exit 1; }

echo -n "Health ready: "
curl -sf "$BASE_URL/health/ready" && echo " OK" || { echo "FAIL"; exit 1; }

echo -n "Auth token endpoint: "
STATUS=$(curl -so /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/auth/token/" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}')
if [ "$STATUS" = "200" ] || [ "$STATUS" = "401" ]; then
  echo " OK ($STATUS)"
else
  echo "FAIL ($STATUS)"
  exit 1
fi

echo "All smoke tests passed."
