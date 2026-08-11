#!/bin/bash
set -e

echo "Starting MarketTrust AI Backend on port 8000..."
cd /app/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &

echo "Starting MarketTrust AI Frontend on port 3000..."
cd /app/frontend
PORT=3000 npm start &

echo "Starting Nginx reverse proxy on port 7860..."
nginx -g "daemon off;"
