# Domain-Driven Design Architecture Guide

## Overview

The Zamaz Debate System has been refactored to follow Domain-Driven Design (DDD) principles, organizing the codebase into bounded contexts that represent distinct business domains.

## Bounded Contexts

### 1. Debate Context (`src/contexts/debate/`)
**Purpose**: Manages AI debates and their outcomes

**Key Components**:
- **Aggregates**: 
  - `Debate`: Orchestrates debates between AI participants
  - `DebateResult`: Captures debate outcomes and consensus
- **Value Objects**: 
  - `Participant`: AI participant details
  - `DebateRound`: Round of arguments
  - `Argument`: Individual argument with evidence
- **Events**: DebateStarted, ArgumentPresented, RoundCompleted, DebateCompleted
- **Use Cases**: Starting debates, presenting arguments, determining winners

### 2. Testing Context (`src/contexts/testing/`)
**Purpose**: Manages test execution and mock configurations

**Key Components**:
- **Aggregates**: 
  - `TestSuite`: Collection of related tests
  - `TestCase`: Individual test with assertions
  - `MockConfiguration`: Mock service configurations
- **Value Objects**: 
  - `Coverage`: Test coverage metrics
  - `TestAssertion`: Expected vs actual comparisons
  - `TestResult`: Test execution outcome
- **Domain Services**: 
  - `TestExecutionService`: Orchestrates test runs
  - `CoverageAnalysisService`: Analyzes code coverage
- **Use Cases**: Running tests, configuring mocks, analyzing coverage

### 3. Performance Context (`src/contexts/performance/`)
**Purpose**: Monitors and optimizes system performance

**Key Components**:
- **Aggregates**: 
  - `Metric`: Performance measurements
  - `Benchmark`: Performance benchmarks
  - `OptimizationStrategy`: Performance improvement strategies
- **Value Objects**: 
  - `MetricValue`: Point-in-time measurements
  - `PerformanceThreshold`: Alert thresholds
  - `Optimization`: Specific optimization technique
- **Domain Services**: 
  - `PerformanceMonitoringService`: Real-time monitoring
  - `BenchmarkExecutionService`: Runs benchmarks
- **Use Cases**: Collecting metrics, running benchmarks, applying optimizations

### 4. Implementation Context (`src/contexts/implementation/`)
**Purpose**: Manages development workflow from tasks to deployment

**Key Components**:
- **Aggregates**: 
  - `Task`: Development tasks
  - `PullRequest`: Code changes for review
  - `CodeReview`: Review feedback
  - `Deployment`: Production deployments
- **Value Objects**: 
  - `Assignment`: Task assignments
  - `ImplementationPlan`: Development approach
  - `CodeChange`: File modifications
- **Domain Services**: 
  - `TaskAssignmentService`: Assigns tasks to developers
  - `PullRequestService`: Manages PR lifecycle
  - `DeploymentService`: Orchestrates deployments
- **Use Cases**: Creating tasks, submitting PRs, deploying code

### 5. Evolution Context (`src/contexts/evolution/`)
**Purpose**: Enables system self-improvement

**Key Components**:
- **Aggregates**: 
  - `Evolution`: System evolution cycle
  - `Improvement`: Specific improvement
  - `EvolutionHistory`: Historical evolutions
- **Value Objects**: 
  - `ImprovementSuggestion`: Proposed improvement
  - `EvolutionPlan`: Implementation plan
  - `ValidationResult`: Evolution validation
- **Domain Services**: 
  - `EvolutionAnalysisService`: Identifies improvements
  - `EvolutionPlanningService`: Creates evolution plans
  - `EvolutionValidationService`: Validates changes
- **Use Cases**: Analyzing system, suggesting improvements, validating evolutions

## Infrastructure Layer (`src/infrastructure/`)

### Repository Implementations
- **Base Repository**: Common JSON file operations
- **Concrete Repositories**: JSON-based persistence for each context
- **Storage**: Data stored in `data/` directory organized by entity type

## Cross-Context Communication

### Domain Events
Events enable loose coupling between contexts:

```python
# Evolution context publishes event
evolution.complete()  # Publishes EvolutionCompleted event

# Implementation context subscribes
@handle(EvolutionCompleted)
def create_implementation_tasks(event):
    # Create tasks for approved improvements
    pass
```

### Event Flow Examples

1. **Debate → Implementation**:
   - DebateCompleted → Create implementation task
   - Complex decision → Generate PR

2. **Testing → Performance**:
   - TestFailed → Trigger performance analysis
   - CoverageDecreased → Suggest optimization

3. **Evolution → All Contexts**:
   - EvolutionTriggered → Analyze all contexts
   - ImprovementApproved → Update relevant context

## Design Principles

### 1. Aggregate Design
- Aggregates enforce business invariants
- Only aggregate roots have public IDs
- Entities within aggregates are accessed through the root

### 2. Value Objects
- Immutable once created
- Represent domain concepts without identity
- Used for measurements, configurations, and descriptions

### 3. Domain Services
- Orchestrate complex workflows
- Handle operations spanning multiple aggregates
- Contain domain logic that doesn't fit in entities

### 4. Repository Pattern
- Abstract persistence concerns
- Enable testing with in-memory implementations
- Support different storage backends

## Best Practices

### Adding New Features
1. Identify the owning context
2. Model as aggregate, entity, or value object
3. Define necessary domain events
4. Implement repository if persistence needed
5. Add domain service for complex logic
6. Write comprehensive unit tests

### Testing Strategy
- Unit test domain logic without infrastructure
- Integration test repository implementations
- Use domain events for test assertions
- Mock external dependencies

### Event Guidelines
- Events should be immutable
- Include all relevant data
- Use past tense naming (OrderPlaced, not PlaceOrder)
- Version events for backward compatibility

## Migration from Legacy Code

### Current Integration Points
- `DebateNucleus` remains as the main orchestrator
- Web API delegates to appropriate contexts
- Legacy JSON files migrated to new structure
- Backward compatibility maintained

### Future Improvements
1. Replace DebateNucleus with context orchestration
2. Implement CQRS for read/write separation
3. Add event sourcing for audit trail
4. Introduce saga pattern for long-running processes

## Common Patterns

### Creating Aggregates
```python
# Create aggregate
task = Task(
    decision_id=decision.id,
    title="Implement feature X",
    description="...",
)

# Perform domain action
task.assign(Assignment(assignee="claude", assignee_type="ai"))

# Save via repository
await task_repo.save(task)
```

### Handling Domain Events
```python
# In aggregate
def complete(self):
    self.status = Status.COMPLETED
    self._publish_event(TaskCompleted(task_id=self.id))

# In event handler
async def handle_task_completed(event: TaskCompleted):
    # Update metrics, trigger deployments, etc.
    pass
```

### Using Domain Services
```python
# Complex operation across aggregates
evolution_service = EvolutionOrchestrationService(
    analysis_service,
    planning_service,
    validation_service,
)

evolution = await evolution_service.trigger_evolution(
    trigger=EvolutionTrigger.PERFORMANCE,
    current_metrics=metrics,
)
```

## Conclusion

The DDD architecture provides:
- Clear separation of concerns
- Maintainable and testable code
- Flexibility to evolve each context independently
- Foundation for future architectural improvements

This structure supports the system's goal of self-improvement while maintaining code quality and business logic integrity.