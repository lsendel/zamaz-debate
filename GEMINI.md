# GEMINI.md

This file provides guidance to Gemini when working with code in this repository.

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

## PR and Issue Creation Workflow

The system follows this workflow for complex decisions:

1. **Complex Decision** → AI Debate between Claude and Gemini
2. **Documentation PR** → Created with detailed implementation approaches
3. **Auto-Close PR** → Documentation PRs are automatically closed
4. **Implementation Issue** → Created and assigned to @claude with `ai-assigned` label

### Important Configuration
- `CREATE_PR_FOR_DECISIONS=true` must be set in `.env`
- `PR_DOCUMENTATION_ONLY=true` creates documentation-only PRs
- PRs are only created for COMPLEX and EVOLUTION decision types
- Issues are automatically created after PR closure for implementation

### GitHub Labels Required
The following labels must exist in the repository:
- `ai-generated`, `automated`, `documentation` (for PRs)
- `ai-assigned`, `implementation` (for issues)
- `decision`, `evolution`, `complex-decision`, `ai-debate`
- `complexity-high`, `complexity-medium`, `complexity-low`

### Decision Types
- **SIMPLE**: No PR/issue created (typos, renames)
- **MODERATE**: No PR/issue created (refactoring, cleanup)
- **COMPLEX**: Creates PR and issue (architectural changes)
- **EVOLUTION**: Creates PR and issue (system improvements)

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

## Troubleshooting

### PR Creation Not Working
1. Check `CREATE_PR_FOR_DECISIONS=true` is set in `.env`
2. Restart the server after environment changes with `make stop && make run`
3. Verify all required GitHub labels exist (use `gh label list`)
4. Check logs with `make logs` for error messages

### Issue Creation Not Working
1. Ensure PR was successfully created and closed first
2. Check that the GitHub user in assignee field exists
3. Verify `ai-assigned` and `implementation` labels exist
4. The issue creation happens in `services/pr_service.py:_create_implementation_issue()`
