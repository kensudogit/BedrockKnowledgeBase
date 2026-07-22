#!/bin/sh
set -e

cd /app
# API listens internally; Next.js is the public entrypoint on $PORT
export INTERNAL_API_URL="${INTERNAL_API_URL:-http://127.0.0.1:8180}"
uvicorn src.main:app --host 127.0.0.1 --port 8180 --timeout-keep-alive 120 &
# Wait until API accepts connections before Next starts proxying
i=0
while [ "$i" -lt 30 ]; do
  if curl -fsS "${INTERNAL_API_URL}/health" >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 0.3
done
cd /app/frontend
exec npm start -- -p "${PORT:-3010}" -H 0.0.0.0
