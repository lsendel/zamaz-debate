# Zamaz Debate System Makefile
# Run various commands for the debate system

.PHONY: help install setup run stop test clean debate evolve check-env web logs status

# Default target - show help
help:
	@echo "Zamaz Debate System - Available Commands:"
	@echo "==========================================="
	@echo "  make install    - Install Python dependencies"
	@echo "  make setup      - Initial setup (venv, deps, directories)"
	@echo "  make run        - Start the web interface"
	@echo "  make stop       - Stop the web interface"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean up generated files"
	@echo "  make debate     - Run a test debate"
	@echo "  make evolve     - Trigger system evolution"
	@echo "  make check-env  - Verify environment setup"
	@echo "  make web        - Open web interface in browser"
	@echo "  make logs       - Show web interface logs"
	@echo "  make status     - Check system status"
	@echo "  make dev        - Run in development mode (with logs)"

# Check if virtual environment exists
VENV_EXISTS := $(shell test -d venv && echo 1 || echo 0)

# Install dependencies
install:
ifeq ($(VENV_EXISTS), 0)
	@echo "Creating virtual environment..."
	python3 -m venv venv
endif
	@echo "Installing dependencies..."
	./venv/bin/pip install -r requirements.txt
	@echo "✓ Dependencies installed"

# Initial setup
setup: install
	@echo "Setting up Zamaz Debate System..."
	@mkdir -p data/{debates,evolutions,decisions,pr_drafts,pr_history,ai_cache,localhost_checks}
	@if [ ! -f .env ]; then \
		echo "Creating .env from example..."; \
		cp .env.example .env; \
		echo "⚠️  Please edit .env and add your API keys"; \
	fi
	@echo "✓ Setup complete"

# Check environment
check-env:
	@echo "Checking environment..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@if grep -q "your-anthropic-api-key-here" .env; then \
		echo "❌ Anthropic API key not configured"; \
		exit 1; \
	fi
	@if grep -q "your-google-api-key-here" .env; then \
		echo "❌ Google API key not configured"; \
		exit 1; \
	fi
	@echo "✓ Environment configured"

# Run the web interface
run: check-env
	@echo "Starting Zamaz Debate System..."
	@pkill -f "src/web/app.py" || true
	@sleep 1
	@if [ -d "venv" ]; then \
		nohup ./venv/bin/python src/web/app.py > web_interface.log 2>&1 & \
	else \
		echo "❌ Virtual environment not found. Run 'make setup' first"; \
		exit 1; \
	fi
	@sleep 2
	@echo "✓ Web interface started at http://localhost:8000"
	@echo "  Run 'make logs' to view logs"

# Run in development mode (foreground with logs)
dev: check-env
	@echo "Starting in development mode..."
	./venv/bin/python src/web/app.py

# Stop the web interface
stop:
	@echo "Stopping web interface..."
	@pkill -f "src/web/app.py" || echo "No process to stop"
	@echo "✓ Stopped"

# Run tests
test:
	@echo "Running tests..."
	./venv/bin/pytest -v

# Run a simple test debate
debate: check-env
	@echo "Running test debate..."
	@./venv/bin/python -c "import sys; sys.path.append('.'); import asyncio; from src.core.nucleus import DebateNucleus; \
		nucleus = DebateNucleus(); \
		result = asyncio.run(nucleus.decide( \
			'Should we add logging to track decision performance?', \
			'Consider debugging needs and performance overhead' \
		)); \
		print(f\"Decision: {result['decision'][:100]}...\"); \
		print(f\"Method: {result['method']}, Rounds: {result['rounds']}\")"

# Trigger system evolution
evolve: check-env
	@echo "Triggering system evolution..."
	@curl -X POST http://localhost:8000/evolve 2>/dev/null | python3 -m json.tool || \
		echo "❌ Web interface not running. Run 'make run' first."

# Simple evolve - triggers evolution once
evolve-once:
	@./venv/bin/python scripts/evolve_once.py || python3 scripts/evolve_once.py

# Open web interface in browser
web:
	@echo "Opening web interface..."
	@open http://localhost:8000 || xdg-open http://localhost:8000 || echo "Please open http://localhost:8000"

# View logs
logs:
	@echo "=== Web Interface Logs ==="
	@tail -f web_interface.log

# Check system status
status:
	@echo "=== System Status ==="
	@ps aux | grep -E "web_interface.py" | grep -v grep > /dev/null && \
		echo "✓ Web interface: Running" || echo "✗ Web interface: Stopped"
	@echo ""
	@echo "=== Statistics ==="
	@curl -s http://localhost:8000/stats 2>/dev/null | python3 -m json.tool || \
		echo "Unable to fetch stats (web interface not running)"
	@echo ""
	@echo "=== Recent Debates ==="
	@ls -lt debates/*.json 2>/dev/null | head -5 || echo "No debates found"

# Clean up generated files
clean:
	@echo "Cleaning up..."
	@rm -rf __pycache__ */__pycache__ */*/__pycache__
	@rm -rf .pytest_cache
	@rm -f web_interface.log
	@echo "✓ Cleaned up"

# Deep clean (including data)
clean-all: clean
	@echo "⚠️  This will delete all debates and evolutions!"
	@read -p "Are you sure? [y/N] " confirm; \
	if [ "$$confirm" = "y" ]; then \
		rm -rf debates/* evolutions/* decisions/* pr_drafts/* pr_history/*; \
		echo "✓ All data cleaned"; \
	else \
		echo "Cancelled"; \
	fi

# Run with specific PR creation enabled
run-with-pr: check-env
	@echo "Starting with PR creation enabled..."
	@pkill -f web_interface.py || true
	@sleep 1
	@CREATE_PR_FOR_DECISIONS=true nohup ./venv/bin/python src/web/app.py > web_interface.log 2>&1 &
	@sleep 2
	@echo "✓ Started with PR creation enabled"

# Check localhost with puppeteer
check-localhost:
	@echo "Checking localhost with Puppeteer..."
	./venv/bin/python check_localhost.py

# Create a complex decision (for testing)
test-decision:
	@echo "Creating test decision..."
	@curl -X POST http://localhost:8000/decide \
		-H "Content-Type: application/json" \
		-d '{ \
			"question": "Should we implement caching for debate results?", \
			"context": "To improve performance and reduce API calls" \
		}' | python3 -m json.tool

# View PR drafts
pr-drafts:
	@echo "=== PR Drafts ==="
	@ls -la pr_drafts/*.json 2>/dev/null || echo "No PR drafts found"
	@echo ""
	@if ls pr_drafts/*.json 2>/dev/null | head -1 > /dev/null; then \
		echo "Latest PR draft:"; \
		ls -t pr_drafts/*.json | head -1 | xargs cat | python3 -m json.tool | head -20; \
	fi

# Install development dependencies
dev-install: install
	@echo "Installing development dependencies..."
	./venv/bin/pip install black flake8 mypy
	@echo "✓ Development dependencies installed"

# Format code
format:
	@echo "Formatting code..."
	./venv/bin/black src/

# Lint code
lint:
	@echo "Linting code..."
	./venv/bin/flake8 src/ --max-line-length=100

# Security check
security:
	@echo "Running security audit..."
	@./scripts/security_check.sh

# Setup git hooks
setup-hooks:
	@echo "Setting up git hooks..."
	@git config core.hooksPath .githooks
	@echo "✓ Git hooks configured"

# Pre-commit checks (runs security + tests)
pre-commit: security lint
	@echo "✓ Pre-commit checks passed"

# Run in mock mode (no API calls)
run-mock:
	@echo "Starting in mock mode (no API calls)..."
	@pkill -f web_interface.py || true
	@sleep 1
	@USE_MOCK_AI=true nohup ./venv/bin/python web_interface.py > web_interface.log 2>&1 &
	@sleep 2
	@echo "✓ Started in mock mode - no API costs!"

# Run with caching enabled
run-cached:
	@echo "Starting with response caching..."
	@pkill -f web_interface.py || true
	@sleep 1
	@USE_CACHED_RESPONSES=true nohup ./venv/bin/python web_interface.py > web_interface.log 2>&1 &
	@sleep 2
	@echo "✓ Started with caching - responses will be reused!"

# Clear AI cache
clear-cache:
	@echo "Clearing AI response cache..."
	@rm -rf ai_cache/*
	@echo "✓ Cache cleared"

# Show API usage estimate
usage:
	@echo "=== API Usage Summary ==="
	@echo "Cached responses: $$(find ai_cache -name "*.json" 2>/dev/null | wc -l)"
	@echo "Cache size: $$(du -sh ai_cache 2>/dev/null | cut -f1)"
	@echo "Manual debates: $$(ls debates/manual_* 2>/dev/null | wc -l)"
	@echo ""
	@echo "Current mode: $$(grep AI_MODE .env | cut -d= -f2)"
	@echo "Mock AI: $$(grep USE_MOCK_AI .env | cut -d= -f2)"
	@echo "Caching: $$(grep USE_CACHED_RESPONSES .env | cut -d= -f2)"
	@echo ""
	@echo "💰 Estimated API savings: $$$(( ($$(find ai_cache -name "*.json" 2>/dev/null | wc -l) + $$(ls debates/manual_* 2>/dev/null | wc -l)) * 3 )) cents"

# Create manual debate from claude.ai
manual-debate:
	@echo "🤖 Creating manual debate from claude.ai..."
	@./scripts/manual_debate.py

# Open claude.ai in browser
claude-ai:
	@echo "Opening claude.ai..."
	@open https://claude.ai || xdg-open https://claude.ai || echo "Please open https://claude.ai"

# Run auto-evolution script
auto-evolve:
	@echo "🚀 Starting Auto Evolution..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@if ! grep -q "AUTO_EVOLVE_ENABLED=true" .env; then \
		echo "❌ Auto-evolution is disabled. Set AUTO_EVOLVE_ENABLED=true in .env"; \
		exit 1; \
	fi
	@if [ -d "venv" ]; then \
		./venv/bin/python scripts/auto_evolve_better.py; \
	else \
		python3 scripts/auto_evolve_better.py; \
	fi

# Configure auto-evolution
configure-auto-evolve:
	@echo "Configuring auto-evolution..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
	fi
	@if grep -q "AUTO_EVOLVE_ENABLED=false" .env; then \
		sed -i '' 's/AUTO_EVOLVE_ENABLED=false/AUTO_EVOLVE_ENABLED=true/' .env; \
		echo "✓ Auto-evolution enabled"; \
	else \
		echo "✓ Auto-evolution already enabled"; \
	fi
	@echo "  Interval: $$(grep AUTO_EVOLVE_INTERVAL .env | cut -d= -f2)"
	@echo "  URL: $$(grep AUTO_EVOLVE_URL .env | cut -d= -f2)"