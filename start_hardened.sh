#!/bin/bash
# Zamaz Debate System - Hardened Startup Script

echo "🚀 Starting Zamaz Debate System (Hardened)..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start the hardened web interface
echo "Starting web interface..."
python -m uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload --log-config logging.json

echo "✨ System started successfully!"
