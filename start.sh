#!/bin/sh
set -e

cd /app
# API listens internally; Next.js is the public entrypoint on $PORT
uvicorn src.main:app --host 127.0.0.1 --port 8180 --timeout-keep-alive 120 &
cd /app/frontend
exec npm start -- -p "${PORT:-3010}" -H 0.0.0.0
