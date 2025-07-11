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

### UI Options
```bash
make run               # Basic web interface
make run-professional  # Professional web interface (recommended)
make run-enhanced      # Enhanced web interface
make test-professional-ui # Test professional UI with Puppeteer
```

### Cost-Saving Modes
```bash
make run-mock          # Run without API calls (mock mode)
make run-cached        # Run with response caching enabled
make manual-debate-web # Access manual debate interface
```

### Advanced Features
```bash
make workflow-list     # List available workflows
make kafka-test        # Test Kafka integration
make orchestrator-demo # Run orchestration demo (when available)
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
- Endpoints: `/decide`, `/stats`, `/evolve`, `/pr-drafts`, `/webhooks/*`
- Enhanced endpoints: `/orchestrate`, `/workflows/*`, `/debates/*`, `/implementations/*`
- Serves static HTML interface at root

**Webhook System** (`src/webhooks/`):
- Real-time event notifications for external systems
- Secure webhook delivery with HMAC-SHA256 signatures
- Automatic retry logic with exponential backoff
- Comprehensive REST API for webhook management
- Integration with domain event system

**Orchestration Service** (`services/orchestration_service.py`):
- Intelligent workflow selection using low-cost LLMs
- Workflow engine with state machine pattern
- Support for simple and complex debate workflows
- Cost optimization through local LLMs (Ollama) or Grok

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
- Kafka event bridge for distributed messaging

### Design Patterns

1. **Domain-Driven Design (DDD)**: Organized into bounded contexts with clear boundaries
2. **Lazy Initialization**: AI clients initialized only when needed
3. **Complexity-Based Routing**: Simple decisions bypass debates, complex ones trigger full debate
4. **Cost Optimization**: Multiple strategies (caching, mocking, manual debates)
5. **Self-Evolution**: System can analyze itself and suggest improvements
6. **Event-Driven Architecture**: Domain events enable loose coupling between contexts
7. **Repository Pattern**: Abstracts persistence with JSON-based implementations
8. **Workflow Engine**: State machine pattern for orchestrating complex debates

## Key Features

- **Self-Improvement**: Analyzes its own code and suggests improvements
- **PR Integration**: Creates GitHub pull requests for complex decisions
- **Evolution Tracking**: Maintains history to prevent duplicate improvements
- **Cost Management**: Mock mode, response caching, and manual debate options
- **Intelligent Orchestration**: Uses low-cost LLMs to select optimal debate workflows
- **Delegation Rules**:
  - Complex tasks → Assigned to Claude (with Gemini as reviewer)
  - Regular tasks → Assigned to Gemini (with Codex as reviewer and committer)
- **Critical Debate Analysis**: Both AIs provide thorough analysis of pros/cons before recommendations
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

## Orchestration & Workflows

The system includes intelligent workflow orchestration for debates:

### Using Orchestrated Debates
```bash
make run-enhanced        # Start enhanced web interface
make orchestrator-demo   # Run orchestration demo
make workflow-list       # List available workflows
```

### Workflow Types
- **Simple Debate**: 2 rounds, basic consensus check
- **Complex Debate**: 5 rounds, detailed analysis, higher consensus threshold
- **Custom Workflows**: Define your own in `src/workflows/definitions/`

### Configuration
```bash
# Enable intelligent orchestration
export USE_ORCHESTRATION=true
export USE_OLLAMA_ORCHESTRATION=true  # For local LLM
export GROK_API_KEY=your_key          # For Grok orchestration
```

### API Endpoints
- `POST /orchestrate` - Start orchestrated debate with auto workflow selection
- `GET /workflows` - List available workflows
- `POST /workflows/{id}/execute` - Execute specific workflow
- `GET /workflows/active` - View active workflows
- `POST /workflows/{id}/pause|resume|abort` - Control active workflows

## Manual Debate Integration

Save costs by conducting debates in Claude.ai:

### Web Interface
```bash
make manual-debate-web   # Open manual debate UI
```

### Command Line
```bash
make manual-debate       # Use CLI tool
```

### Process
1. Get template from system
2. Conduct debate in Claude.ai
3. Paste results back into system
4. Debate is saved with full integration

### API Endpoints
- `GET /debates/manual/template` - Get Claude.ai template
- `POST /debates/manual` - Create manual debate
- `POST /debates/manual/import` - Import from Claude.ai

## Debate History & Search

### Viewing Past Debates
The enhanced interface includes comprehensive debate history:
- Search by question content
- Filter by complexity, method, consensus
- View full debate details including all rounds
- Track debate origins (PR/Issue)

### API Endpoints
- `GET /debates` - List debates with pagination
- `GET /debates/{id}` - Get specific debate
- `GET /debates/{id}/rounds` - View all rounds
- `POST /debates/search` - Advanced search
- `GET /debates/by-origin/{type}/{id}` - Find debates by PR/issue

## Implementation Tracking

Track what decisions have been implemented:

### Features
- View pending implementations
- Track days since decision
- Link to original debates
- Monitor implementation status

### API Endpoints
- `GET /implementations` - List all implementations
- `GET /implementations/{debate_id}` - Get implementation details
- `GET /implementations/pending` - View pending only

## Kafka Event Streaming

Real-time event integration:

### Configuration
```bash
export KAFKA_ENABLED=true
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Testing
```bash
make kafka-test          # Test Kafka connection
```

### Features
- Publish all domain events to Kafka
- Subscribe to external debate requests
- Hybrid event bus (local + distributed)
- Automatic event bridging

### API Endpoints
- `GET /kafka/status` - Check Kafka connection
- `POST /kafka/test` - Send test event

## Phase Management

Advanced debate phase orchestration:

### Workflow Phases
1. **Initial Arguments** - Opening positions
2. **Counter Arguments** - Rebuttals
3. **Clarification** - Address uncertainties
4. **Consensus Check** - Evaluate agreement
5. **Final Decision** - Conclude debate

### Custom Phases
- Define in workflow YAML files
- Set participant requirements
- Configure retry logic
- Add conditional transitions

## Enhanced Web Interface

### Running Enhanced UI
```bash
make run-enhanced        # Start with all features
```

### Features
- **Dashboard**: System overview and stats
- **New Debate**: Multiple debate modes
- **Orchestrated**: Workflow management
- **Manual**: Claude.ai integration
- **History**: Search and view past debates
- **Implementations**: Track follow-ups
- **System**: Monitor Kafka, orchestration, rate limits

### Navigation
- Tab-based interface
- Real-time updates
- Modal debate details
- Workflow progress tracking
- Implementation status badges

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
5. **Orchestrator not working**: Ensure `USE_ORCHESTRATION=true` and either Ollama is running or `GROK_API_KEY` is set
6. **Kafka events not publishing**: Check `KAFKA_ENABLED=true` and Kafka is running (`docker-compose up -d kafka`)