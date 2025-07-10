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

### Orchestration System
```bash
python examples/orchestration_demo.py  # Demonstrate hybrid orchestration
python -m pytest tests/test_orchestration.py  # Test orchestration system
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
- Integrates with hybrid orchestration system for complex decisions
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
- Endpoints: `/decide`, `/stats`, `/evolve`, `/pr-drafts`, `/webhooks/*`
- Serves static HTML interface at root

**Webhook System** (`src/webhooks/`):
- Real-time event notifications for external systems
- Secure webhook delivery with HMAC-SHA256 signatures
- Automatic retry logic with exponential backoff
- Comprehensive REST API for webhook management
- Integration with domain event system

**Hybrid Orchestration System** (`src/orchestration/`):
- State machine-based debate orchestration with LLM assistance
- Circuit breaker protection for LLM operations
- YAML-based workflow definitions for flexible debate patterns
- Three orchestration strategies: Deterministic, Hybrid, LLM-driven
- Comprehensive error handling and fallback mechanisms
- Integration with existing DDD architecture and event system

### Domain-Driven Design Structure

The system is organized into bounded contexts following DDD principles:

**Debate Context** (`src/contexts/debate/`):
- Manages debates between AI participants
- Aggregates: Debate, DebateResult
- Value Objects: Participant, DebateRound, Argument
- Events: DebateStarted, ArgumentPresented, DebateCompleted

**Testing Context** (`src/contexts/testing/`):
- Handles test execution and mock configurations
- Aggregates: TestSuite, TestCase, MockConfiguration
- Value Objects: Coverage, TestAssertion, TestResult
- Domain Services: TestExecutionService, CoverageAnalysisService

**Performance Context** (`src/contexts/performance/`):
- Monitors and optimizes system performance
- Aggregates: Metric, Benchmark, OptimizationStrategy
- Value Objects: MetricValue, PerformanceThreshold, Optimization
- Domain Services: PerformanceMonitoringService, BenchmarkExecutionService

**Implementation Context** (`src/contexts/implementation/`):
- Manages task implementation, PRs, and deployments
- Aggregates: Task, PullRequest, CodeReview, Deployment
- Value Objects: Assignment, ImplementationPlan, CodeChange
- Domain Services: TaskAssignmentService, PullRequestService, DeploymentService

**Evolution Context** (`src/contexts/evolution/`):
- Handles system self-improvement and evolution
- Aggregates: Evolution, Improvement, EvolutionHistory
- Value Objects: ImprovementSuggestion, EvolutionPlan, ValidationResult
- Domain Services: EvolutionAnalysisService, EvolutionPlanningService

**Infrastructure** (`src/infrastructure/`):
- Repository implementations using JSON file storage
- Base repository class for common operations
- Concrete repositories for each bounded context

### Design Patterns

1. **Domain-Driven Design (DDD)**: Organized into bounded contexts with clear boundaries
2. **Lazy Initialization**: AI clients initialized only when needed
3. **Complexity-Based Routing**: Simple decisions bypass debates, complex ones trigger full debate
4. **Hybrid State Machine**: Combines deterministic logic with LLM-powered insights
5. **Circuit Breaker Pattern**: Prevents cascade failures from LLM services
6. **LLM as Assistant Pattern**: LLM provides insights, deterministic logic makes decisions
7. **Cost Optimization**: Multiple strategies (caching, mocking, manual debates)
8. **Self-Evolution**: System can analyze itself and suggest improvements
9. **Event-Driven Architecture**: Domain events enable loose coupling between contexts
10. **Repository Pattern**: Abstracts persistence with JSON-based implementations

## Key Features

- **Hybrid Orchestration**: State machine with LLM assistance for intelligent debate management
- **Self-Improvement**: Analyzes its own code and suggests improvements
- **PR Integration**: Creates GitHub pull requests for complex decisions
- **Evolution Tracking**: Maintains history to prevent duplicate improvements
- **Cost Management**: Mock mode, response caching, circuit breakers, and smart LLM usage
- **Delegation Rules**:
  - Complex tasks → Assigned to Claude (with Gemini as reviewer)
  - Regular tasks → Assigned to Gemini (with Codex as reviewer and committer)
- **Critical Debate Analysis**: Both AIs provide thorough analysis of pros/cons before recommendations
- **Resilient Operations**: Circuit breakers, fallback mechanisms, and graceful degradation
- **Flexible Workflows**: YAML-based workflow definitions for different debate patterns
- **Webhook Notifications**: Real-time event notifications for external integrations
  - Secure delivery with HMAC-SHA256 signatures
  - Automatic retry logic for failed deliveries
  - Comprehensive REST API for webhook management
  - Support for all major system events (decisions, debates, evolution, etc.)

## PR and Issue Creation Workflow

The system follows this workflow for complex decisions:

1. **Complex Decision** → AI Debate between Claude and Gemini
2. **Pull Request** → Created with detailed implementation approaches
3. **Implementation Issue** → Created automatically for COMPLEX and EVOLUTION decisions

### Important Configuration
- `CREATE_PR_FOR_DECISIONS=true` must be set in `.env`
- `PR_USE_CURRENT_BRANCH=false` to create new branches for PRs (required when base branch = current branch)
- `PR_DOCUMENTATION_ONLY=true` creates documentation-only PRs that auto-close
- `PR_DOCUMENTATION_ONLY=false` creates regular PRs that stay open
- PRs are only created for COMPLEX and EVOLUTION decision types
- Issues are automatically created for all COMPLEX and EVOLUTION decisions (regardless of PR_DOCUMENTATION_ONLY setting)

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

Current AI-assigned issues:
- Issue #197: Implement event-driven architecture using Apache Kafka
- Issue #193: Implement webhook notifications for system events  
- Issue #181: Evolve the debate system into a dev team
- Issue #178: Domain-Driven Design (DDD) implementation (COMPLETED)

## Working with DDD Architecture

### Understanding Bounded Contexts

Each bounded context is self-contained and follows these principles:
- **Aggregates**: Main entities that enforce business rules (e.g., Debate, TestSuite)
- **Value Objects**: Immutable objects representing domain concepts (e.g., Coverage, MetricValue)
- **Domain Events**: Enable communication between contexts without tight coupling
- **Repositories**: Abstract persistence, with JSON implementations in infrastructure layer
- **Domain Services**: Handle complex operations spanning multiple aggregates

### Adding New Features

When adding features to a bounded context:
1. Identify which context owns the feature
2. Create/modify aggregates and value objects as needed
3. Define domain events for cross-context communication
4. Implement repository interfaces if persistence is needed
5. Add domain services for complex workflows
6. Write unit tests for domain logic

### Cross-Context Communication

Contexts communicate through domain events:
- Events are published when significant domain actions occur
- Other contexts can subscribe to relevant events
- This maintains loose coupling between contexts
- Event handlers orchestrate cross-context workflows

## Troubleshooting

### PR Creation Not Working
1. Check `CREATE_PR_FOR_DECISIONS=true` is set in `.env`
2. Check `PR_USE_CURRENT_BRANCH=false` if your current branch equals base branch (e.g., both are 'main')
3. Restart the server after environment changes with `make stop && make run`
4. Verify all required GitHub labels exist (use `gh label list`)
5. Check logs with `make logs` for error messages
6. Common error: "Failed to create PR" when trying to create PR from main to main - set `PR_USE_CURRENT_BRANCH=false`

### Issue Creation Not Working
1. Issues are now created automatically for all COMPLEX and EVOLUTION decisions
2. Check that the GitHub user in assignee field exists (default: claude)
3. Verify `ai-assigned` and `implementation` labels exist
4. The issue creation happens in `services/pr_service.py:_create_implementation_issue()`
5. Check web_interface.log for any errors during issue creation

### Testing PR/Issue Creation
Use the test scripts to validate the workflow:
```bash
python3 test_pr_creation.py    # Full Puppeteer test with screenshots
python3 test_simple_pr.py      # Simple API test for PR creation
python3 test_pr_and_issue.py   # Test both PR and issue creation
```

### Common Issues and Fixes
1. **Dataclass field ordering error**: Remove default values from parent dataclass fields when child classes have non-default fields
2. **PR creation fails with same branch error**: Set `PR_USE_CURRENT_BRANCH=false` in `.env`
3. **Missing module errors**: The system uses Domain-Driven Design with contexts - ensure all context modules have proper `__init__.py` files
4. **Server not picking up env changes**: Always restart with `make stop && make run` after `.env` modifications