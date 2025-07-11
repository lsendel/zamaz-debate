# Zamaz Debate System Makefile
# Run various commands for the debate system

.PHONY: help install setup run stop test clean debate evolve check-env web logs status dev \
	run-professional run-enhanced test-professional-ui manual-debate-web \
	evolve-once test-decision pr-drafts workflow-list check-localhost \
	run-mock run-cached clear-cache usage \
	kafka-up kafka-down kafka-logs kafka-test test-e2e \
	auto-evolve configure-auto-evolve \
	dev-install format format-check isort isort-check lint lint-deep type-check \
	quality quality-fix test-coverage quality-report \
	pre-commit-install pre-commit-all pre-commit \
	complexity security-scan security setup-hooks

# Default target - show help
help:
	@echo "Zamaz Debate System - Available Commands:"
	@echo "==========================================="
	@echo ""
	@echo "Core Commands:"
	@echo "============="
	@echo "  make install         - Install Python dependencies"
	@echo "  make setup           - Initial setup (venv, deps, directories)"
	@echo "  make run             - Start the basic web interface"
	@echo "  make run-professional - Start the professional web interface (recommended)"
	@echo "  make run-enhanced    - Start the enhanced web interface"
	@echo "  make stop            - Stop the web interface"
	@echo "  make dev             - Run in development mode (foreground with logs)"
	@echo "  make logs            - Show web interface logs"
	@echo "  make status          - Check system status"
	@echo "  make web             - Open web interface in browser"
	@echo ""
	@echo "Testing & Validation:"
	@echo "===================="
	@echo "  make test            - Run tests"
	@echo "  make test-professional-ui - Test professional UI with Puppeteer"
	@echo "  make check-localhost - Validate localhost is running"
	@echo "  make test-decision   - Create a test decision"
	@echo "  make debate          - Run a test debate"
	@echo ""
	@echo "Evolution & Enhancement:"
	@echo "======================="
	@echo "  make evolve          - Trigger system evolution"
	@echo "  make auto-evolve     - Run continuous auto-evolution"
	@echo "  make configure-auto-evolve - Configure auto-evolution settings"
	@echo ""
	@echo "Special Modes:"
	@echo "============="
	@echo "  make run-mock        - Run in mock mode (no API calls)"
	@echo "  make run-cached      - Run with response caching"
	@echo "  make manual-debate-web - Access manual debate interface"
	@echo ""
	@echo "Data Management:"
	@echo "==============="
	@echo "  make usage           - Show API usage and cache statistics"
	@echo "  make clear-cache     - Clear AI response cache"
	@echo "  make pr-drafts       - View PR drafts"
	@echo "  make clean           - Clean up generated files"
	@echo "  make clean-all       - Deep clean (including all data)"
	@echo ""
	@echo "Code Quality:"
	@echo "============"
	@echo "  make quality         - Run all quality checks"
	@echo "  make quality-fix     - Auto-fix formatting and imports"
	@echo "  make format          - Format code with Black"
	@echo "  make lint            - Run Flake8 linter"
	@echo "  make type-check      - Run MyPy type checking"
	@echo "  make test-coverage   - Run tests with coverage"
	@echo "  make quality-report  - Generate full quality report"
	@echo ""
	@echo "Advanced Features:"
	@echo "================="
	@echo "  make workflow-list   - List available workflows"
	@echo "  make kafka-test      - Test Kafka integration"
	@echo "  make kafka-up        - Start Kafka with Docker"
	@echo "  make kafka-down      - Stop Kafka container"
	@echo ""
	@echo "Environment:"
	@echo "==========="
	@echo "  make check-env       - Verify environment setup"
	@echo "  make dev-install     - Install development dependencies"

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

# Run the basic web interface
run: check-env
	@echo "Starting Zamaz Debate System..."
	@pkill -f "src/web/app.py" || true
	@pkill -f "src.web.app_simple" || true
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

# Run the professional web interface (recommended)
run-professional:
	@echo "Starting professional web interface..."
	@make stop 2>/dev/null || true
	@cp src/web/static/index_professional.html src/web/static/index.html
	@echo "Professional UI activated. Starting server..."
	@nohup ./venv/bin/python -m src.web.app_simple > web_interface.log 2>&1 &
	@sleep 2
	@echo "✓ Professional web interface started at http://localhost:8000"
	@echo "View logs with: make logs"

# Run the enhanced web interface
run-enhanced:
	@echo "Starting enhanced web interface..."
	@make stop 2>/dev/null || true
	@cp src/web/static/index_simple.html src/web/static/index.html
	@echo "Enhanced UI activated. Starting server..."
	@nohup ./venv/bin/python -m src.web.app_simple > web_interface.log 2>&1 &
	@sleep 2
	@echo "✓ Enhanced web interface started at http://localhost:8000"
	@echo "View logs with: make logs"

# Test professional UI with Puppeteer
test-professional-ui:
	@echo "Testing professional UI..."
	@python3 test_professional_ui.py

# Run in development mode (foreground with logs)
dev: check-env
	@echo "Starting in development mode..."
	./venv/bin/python src/web/app.py

# Stop the web interface
stop:
	@echo "Stopping web interface..."
	@pkill -f "src/web/app.py" || true
	@pkill -f "src.web.app_simple" || true
	@echo "✓ Stopped"

# Run tests
test:
	@echo "Running tests..."
	./venv/bin/pytest -v

# View logs
logs:
	@echo "=== Web Interface Logs ==="
	@tail -f web_interface.log

# Check system status
status:
	@echo "=== System Status ==="
	@ps aux | grep -E "src/web/app.py|src.web.app_simple" | grep -v grep > /dev/null && \
		echo "✓ Web interface: Running" || echo "✗ Web interface: Stopped"
	@echo ""
	@echo "=== Statistics ==="
	@curl -s http://localhost:8000/stats 2>/dev/null | python3 -m json.tool || \
		echo "Unable to fetch stats (web interface not running)"
	@echo ""
	@echo "=== Recent Debates ==="
	@ls -lt data/debates/*.json 2>/dev/null | head -5 || echo "No debates found"

# Open web interface in browser
web:
	@echo "Opening web interface..."
	@open http://localhost:8000 || xdg-open http://localhost:8000 || echo "Please open http://localhost:8000"

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
		rm -rf data/debates/* data/evolutions/* data/decisions/* data/pr_drafts/* data/pr_history/*; \
		echo "✓ All data cleaned"; \
	else \
		echo "Cancelled"; \
	fi

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
	@ls -la data/pr_drafts/*.json 2>/dev/null || echo "No PR drafts found"
	@echo ""
	@if ls data/pr_drafts/*.json 2>/dev/null | head -1 > /dev/null; then \
		echo "Latest PR draft:"; \
		ls -t data/pr_drafts/*.json | head -1 | xargs cat | python3 -m json.tool | head -20; \
	fi

# Access manual debate interface
manual-debate-web:
	@echo "Opening manual debate interface..."
	@make run-professional
	@sleep 2
	@python3 -c "import webbrowser; webbrowser.open('http://localhost:8000#manual')"

# List available workflows
workflow-list:
	@echo "Fetching available workflows..."
	@curl -s http://localhost:8000/workflows | python3 -m json.tool || echo "Server not running. Start with: make run"

# Check localhost with puppeteer
check-localhost:
	@echo "Checking localhost with Puppeteer..."
	./venv/bin/python check_localhost.py

# Run in mock mode (no API calls)
run-mock:
	@echo "Starting in mock mode (no API calls)..."
	@make stop 2>/dev/null || true
	@USE_MOCK_AI=true nohup ./venv/bin/python -m src.web.app_simple > web_interface.log 2>&1 &
	@sleep 2
	@echo "✓ Started in mock mode - no API costs!"

# Run with response caching
run-cached:
	@echo "Starting with response caching enabled..."
	@make stop 2>/dev/null || true
	@USE_CACHED_RESPONSES=true nohup ./venv/bin/python -m src.web.app_simple > web_interface.log 2>&1 &
	@sleep 2
	@echo "✓ Started with caching - responses will be reused!"

# Clear AI cache
clear-cache:
	@echo "Clearing AI response cache..."
	@rm -rf data/ai_cache/*
	@echo "✓ Cache cleared"

# Show API usage estimate
usage:
	@echo "=== API Usage Summary ==="
	@echo "Cached responses: $$(find data/ai_cache -name "*.json" 2>/dev/null | wc -l)"
	@echo "Cache size: $$(du -sh data/ai_cache 2>/dev/null | cut -f1)"
	@echo "Manual debates: $$(ls data/debates/manual_* 2>/dev/null | wc -l)"
	@echo ""
	@echo "Current mode: $$(grep AI_MODE .env | cut -d= -f2)"
	@echo "Mock AI: $$(grep USE_MOCK_AI .env | cut -d= -f2)"
	@echo "Caching: $$(grep USE_CACHED_RESPONSES .env | cut -d= -f2)"
	@echo ""
	@echo "💰 Estimated API savings: $$$(( ($$(find data/ai_cache -name "*.json" 2>/dev/null | wc -l) + $$(ls data/debates/manual_* 2>/dev/null | wc -l)) * 3 )) cents"

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

# Kafka commands
kafka-test:
	@echo "Testing Kafka integration..."
	@if [ "$$KAFKA_ENABLED" = "true" ]; then \
		echo "Kafka is enabled. Sending test event..."; \
		curl -X POST http://localhost:8000/kafka/test | python3 -m json.tool; \
	else \
		echo "Kafka is not enabled. Set KAFKA_ENABLED=true to test."; \
	fi

test-kafka:
	@echo "Running Kafka integration tests..."
	./venv/bin/pytest tests/integration/test_kafka_integration.py -v

test-e2e:
	@echo "Running end-to-end Kafka-DDD integration demo..."
	./venv/bin/python scripts/test_kafka_e2e.py

kafka-up:
	@echo "Starting Kafka..."
	docker run -d --name kafka-zamaz \
		-p 9092:9092 \
		-e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
		-e KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092 \
		-e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
		confluentinc/cp-kafka:latest

kafka-down:
	@echo "Stopping Kafka..."
	docker stop kafka-zamaz || true
	docker rm kafka-zamaz || true

kafka-logs:
	docker logs -f kafka-zamaz

# Development tools
dev-install: install
	@echo "Installing development dependencies..."
	./venv/bin/pip install -r requirements-dev.txt
	@echo "✓ Development dependencies installed"

# Code quality commands
format:
	@echo "Formatting code..."
	./venv/bin/black src/ services/ domain/

format-check:
	@echo "Checking code formatting..."
	./venv/bin/black --check src/ services/ domain/

isort:
	@echo "Sorting imports..."
	./venv/bin/isort src/ services/ domain/

isort-check:
	@echo "Checking import sorting..."
	./venv/bin/isort --check-only src/ services/ domain/

lint:
	@echo "Linting code..."
	./venv/bin/flake8 src/ services/ domain/

lint-deep:
	@echo "Running deep lint with pylint..."
	./venv/bin/pylint --disable=R,C src/ services/ domain/ || true

type-check:
	@echo "Running type checking..."
	./venv/bin/mypy src/ services/ domain/ --ignore-missing-imports || true

quality: format-check isort-check lint type-check
	@echo "✓ All quality checks passed"

quality-fix: format isort
	@echo "✓ Code formatted and imports sorted"

test-coverage:
	@echo "Running tests with coverage..."
	./venv/bin/pytest --cov=src --cov=services --cov=domain --cov-report=term-missing --cov-report=xml

quality-report:
	@echo "Generating quality report..."
	@echo "=== Code Quality Report ===" > quality_report.txt
	@echo "" >> quality_report.txt
	@echo "## Complexity Analysis" >> quality_report.txt
	@./venv/bin/radon cc src/ services/ domain/ -a >> quality_report.txt || true
	@echo "" >> quality_report.txt
	@echo "## Type Coverage" >> quality_report.txt
	@./venv/bin/mypy src/ services/ domain/ --ignore-missing-imports 2>&1 | grep -E "Success:|error:" >> quality_report.txt || true
	@echo "" >> quality_report.txt
	@echo "## Security Issues" >> quality_report.txt
	@./venv/bin/bandit -r src/ services/ domain/ -f txt >> quality_report.txt || true
	@echo "✓ Quality report generated: quality_report.txt"

# Git hooks and pre-commit
pre-commit-install:
	@echo "Installing pre-commit hooks..."
	./venv/bin/pre-commit install
	@echo "✓ Pre-commit hooks installed"

pre-commit-all:
	@echo "Running pre-commit on all files..."
	./venv/bin/pre-commit run --all-files

pre-commit: security lint
	@echo "✓ Pre-commit checks passed"

setup-hooks:
	@echo "Setting up git hooks..."
	@git config core.hooksPath .githooks
	@echo "✓ Git hooks configured"

# Security and analysis
complexity:
	@echo "Analyzing code complexity..."
	@./venv/bin/radon cc src/ services/ domain/ -a -nc

security-scan:
	@echo "Running security scan..."
	@./venv/bin/bandit -r src/ services/ domain/ -ll

security:
	@echo "Running security audit..."
	@./scripts/security_check.sh