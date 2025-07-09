# Zamaz Debate System Information

## Summary
Zamaz Debate is a self-improving AI debate system that uses Claude Opus 4 and Gemini 2.5 Pro to make architectural decisions through structured debates. Starting from a minimal nucleus, it evolves through AI-guided decisions, implementing a "dogfooding" approach where it uses AI debates to improve its own architecture.

## Structure
- **src/**: Core application code including debate nucleus, web interface, and utilities
- **domain/**: Domain models following DDD principles
- **services/**: Service layer for AI clients, PR management, and delegation
- **data/**: Storage for debates, decisions, and AI cache
- **tests/**: Comprehensive test suite
- **scripts/**: Utility scripts for evolution, auditing, and deployment
- **github-app/**: GitHub integration for webhook processing
- **docs/**: Documentation and implementation guides

## Language & Runtime
**Language**: Python
**Version**: 3.10+
**Build System**: Standard Python package
**Package Manager**: pip

## Dependencies
**Main Dependencies**:
- anthropic>=0.18.0 (Claude API client)
- google-generativeai>=0.3.0 (Gemini API client)
- python-dotenv>=1.0.0 (Environment variable management)
- openai (Optional fallback for API rate limiting)

**Development Dependencies**:
- pytest>=7.4.0 (Testing framework)
- pytest-asyncio>=0.21.0 (Async testing support)

## Build & Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up API keys
cp .env.example .env
# Edit .env with actual API keys

# Run the system
python src/quality_debates.py
```

## Core Components

### Debate Nucleus
The central component (`src/core/nucleus.py`) orchestrates debates between AI models:
- Assesses question complexity to determine if debate is needed
- Manages AI client interactions through the factory pattern
- Tracks debate history and evolution
- Implements error handling and resilience patterns

### AI Client Factory
The `services/ai_client_factory.py` provides:
- Support for multiple AI providers (Anthropic, Google, OpenAI)
- Caching mechanism for API responses
- Mock clients for testing
- Fallback mechanisms when rate limited

### Domain Models
The system follows Domain-Driven Design with models in `domain/models.py`:
- `Decision`: Value object for system decisions
- `Debate`: Entity representing AI agent debates
- `PullRequest`: Entity for GitHub PR integration
- `PRTemplate`: Value object for PR templates

### PR Service
The `services/pr_service.py` handles:
- Creation of GitHub PRs for complex decisions
- Implementation planning and delegation
- PR status tracking and management

## Testing
**Framework**: pytest with pytest-asyncio
**Test Location**: tests/ directory
**Naming Convention**: test_*.py
**Configuration**: tests/conftest.py with mock fixtures
**Run Command**:
```bash
pytest
```

## Environment Configuration
The system uses environment variables for configuration:
- `ANTHROPIC_API_KEY`: API key for Claude
- `GOOGLE_API_KEY`: API key for Gemini
- `OPENAI_API_KEY`: Optional fallback API key
- `CREATE_PR_FOR_DECISIONS`: Enable PR creation (true/false)
- `USE_MOCK_AI`: Use mock AI clients for testing (true/false)
- `USE_CACHED_RESPONSES`: Use cached AI responses (true/false)