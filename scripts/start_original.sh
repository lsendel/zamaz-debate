#!/bin/bash
echo "Starting original Zamaz Debate System on port 8000..."
cd "$(dirname "$0")/.."
python3 -m uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload
