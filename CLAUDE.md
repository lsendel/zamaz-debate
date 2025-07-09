# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Zamaz Debate System is a self-improving AI debate framework that facilitates architectural decision-making through structured debates between Claude Opus 4 and Gemini 2.5 Pro. It implements a "dogfooding" approach, using AI debates to improve its own architecture.

## Build and Development Commands

### Setup and Installation
```bash
make setup         # Initial setup (creates venv, installs deps, creates directories)
make install       # Install Python dependencies only
make check-env     # Verify environment setup and API keys
```

### Running the System
```bash
make run           # Start web interface at http://localhost:8000
make dev           # Run in development mode (foreground with logs)
make run-mock      # Run without API calls (mock mode)
make run-cached    # Run with response caching enabled
make stop          # Stop the web interface
```

### Testing and Debugging
```bash
make test          # Run pytest test suite
make debate        # Run a test debate
make evolve        # Trigger system evolution
make logs          # View web interface logs
make status        # Check system status and statistics
```

### Localhost Validation
```bash
make check-localhost  # Uses Puppeteer to validate localhost
python check_localhost.py http://localhost:8000  # Direct validation
```

## Architecture

### Core Components

**DebateNucleus** (`src/core/nucleus.py`):
- Main orchestrator that manages AI debates
- Implements complexity assessment to route decisions (simple vs complex)
- Handles debate persistence and evolution tracking

**Domain Models** (`domain/models.py`):
- `Decision`: Represents decisions made by the system
- `Debate`: Represents debates between AI agents
- `PullRequest`: GitHub PR representation
- Enums for decision types, PR status, and implementation assignees

**AI Client Factory** (`services/ai_client_factory.py`):
- Provides abstraction over AI providers (Claude, Gemini)
- Supports mock mode for testing without API calls
- Implements response caching to minimize costs
- Configurable usage modes: production, development, testing, demo

**Web Interface** (`src/web/app.py`):
- FastAPI-based REST API
- Endpoints: `/decide`, `/stats`, `/evolve`, `/pr-drafts`
- Serves static HTML interface at root

### Design Patterns

1. **Lazy Initialization**: AI clients initialized only when needed
2. **Complexity-Based Routing**: Simple decisions bypass debates, complex ones trigger full debate
3. **Cost Optimization**: Multiple strategies (caching, mocking, manual debates)
4. **Self-Evolution**: System can analyze itself and suggest improvements

## Key Features

- **Self-Improvement**: Analyzes its own code and suggests improvements
- **PR Integration**: Creates GitHub pull requests for complex decisions
- **Evolution Tracking**: Maintains history to prevent duplicate improvements
- **Cost Management**: Mock mode, response caching, and manual debate options
- **Delegation Rules**:
  - Complex tasks → Assigned to Claude (with Gemini as reviewer)
  - Regular tasks → Assigned to Gemini (with Codex as reviewer and committer)
- **Critical Debate Analysis**: Both AIs provide thorough analysis of pros/cons before recommendations

## Testing Strategy

The project uses pytest with asyncio support. Key test areas:
- Unit tests for core components
- Integration tests for AI client interactions
- Mock tests to validate behavior without API calls
- Localhost validation using Puppeteer for web interface testing

## Important Notes

- API keys (Anthropic and Google) must be configured in `.env`
- The system starts from a minimal nucleus and evolves through AI guidance
- All debates and evolutions are stored as JSON files for transparency
- Use cost-saving modes (mock, cached) during development to minimize API usage

## AI Implementation Tasks

When you see a GitHub issue with the `ai-assigned` label, it's intended for AI implementation. Look for issues at: https://github.com/lsendel/zamaz-debate/issues?q=is%3Aissue+is%3Aopen+label%3Aai-assigned

Current AI-assigned issues:
- Issue #178: Domain-Driven Design implementation for debate system architecture