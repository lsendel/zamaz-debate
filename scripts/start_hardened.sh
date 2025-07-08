#!/bin/bash
echo "Starting hardened Zamaz Debate System on port 8001..."
cd "$(dirname "$0")/.."
python3 -m uvicorn src.web.app_hardened:app --host 0.0.0.0 --port 8001 --reload
