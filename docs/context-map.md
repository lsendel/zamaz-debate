# Context Map Documentation

## Overview

This document describes the bounded contexts in the Zamaz Debate System and their relationships. The context map follows Domain-Driven Design patterns to show how different parts of the system interact.

## Bounded Contexts

### 1. Debate Context (Core Domain)
**Purpose:** Manages AI debates, decision-making, and consensus building  
**Key Aggregates:** DebateSession, Decision, Round  
**Key Concepts:** Topic, Argument, Consensus, Complexity Assessment

### 2. Implementation Context
**Purpose:** Handles task creation, PR management, and code implementation  
**Key Aggregates:** Task, PullRequest, Implementation  
**Key Concepts:** Assignment, Review, Deployment

### 3. Testing Context
**Purpose:** Manages test execution, coverage analysis, and quality assurance  
**Key Aggregates:** TestSuite, TestCase, MockConfiguration  
**Key Concepts:** Coverage, Assertions, Test Results

### 4. Performance Context
**Purpose:** Monitors system performance, benchmarks, and optimizations  
**Key Aggregates:** Metric, Benchmark, OptimizationStrategy  
**Key Concepts:** Thresholds, Resource Usage, Performance Profiles

### 5. Evolution Context
**Purpose:** Manages system self-improvement and architectural evolution  
**Key Aggregates:** Evolution, Improvement, EvolutionHistory  
**Key Concepts:** Self-Analysis, Duplication Detection, Validation

### 6. AI Integration Context
**Purpose:** Manages AI provider integrations and conversations  
**Key Aggregates:** AIProvider, Conversation, CachedResponse  
**Key Concepts:** Token Usage, Rate Limiting, Provider Switching

## Context Relationships

### Customer-Supplier Relationships

```
Debate Context [Customer] ← Implementation Context [Supplier]
- Debate Context creates decisions that require implementation
- Implementation Context provides implementation status back
- Conformist pattern: Implementation conforms to Debate's decisions
```

```
Implementation Context [Customer] ← Testing Context [Supplier]
- Implementation requests test execution
- Testing provides test results and coverage
- Open Host Service: Testing exposes standard testing API
```

```
All Contexts [Customer] ← AI Integration Context [Supplier]
- All contexts use AI services for their operations
- AI Integration provides unified AI access
- Shared Kernel: Common AI client interfaces
```

### Upstream-Downstream Relationships

```
Evolution Context [Upstream] → All Other Contexts [Downstream]
- Evolution can trigger changes in any context
- Downstream contexts must adapt to evolution decisions
- Published Language: Evolution uses defined improvement patterns
```

```
Performance Context [Upstream] → Evolution Context [Downstream]
- Performance metrics trigger evolution decisions
- Evolution responds to performance degradation
- Event-driven: Performance publishes threshold events
```

## Integration Patterns

### 1. Shared Kernel
**Between:** All contexts share domain events infrastructure  
**Implementation:** Common DomainEvent base class and EventBus

### 2. Open Host Service
**Context:** Testing Context  
**Service:** Test execution API  
**Consumers:** Implementation, Evolution contexts

### 3. Anticorruption Layer
**Context:** AI Integration  
**Purpose:** Protects domain from AI provider API changes  
**Implementation:** AIClientFactory abstracts provider details

### 4. Published Language
**Context:** Debate Context  
**Language:** Decision types, complexity levels  
**Consumers:** All contexts understand decision vocabulary

### 5. Conformist
**Context:** Implementation Context  
**Conforms to:** Debate Context decisions  
**Reason:** Implementation must follow architectural decisions

## Event Flow Diagram

```
┌─────────────────┐     DecisionMade      ┌────────────────────┐
│  Debate Context │ ─────────────────────→ │ Implementation      │
│                 │                        │ Context            │
└─────────────────┘                        └────────────────────┘
        │                                            │
        │ ComplexityAssessed                         │ TaskCreated
        ↓                                            ↓
┌─────────────────┐                        ┌────────────────────┐
│ Evolution       │                        │ Testing Context    │
│ Context         │                        │                    │
└─────────────────┘                        └────────────────────┘
        ↑                                            │
        │ EvolutionTriggered                         │ TestCompleted
        │                                            ↓
┌─────────────────┐     ThresholdExceeded  ┌────────────────────┐
│ Performance     │ ←───────────────────── │ All Contexts       │
│ Context         │                        │                    │
└─────────────────┘                        └────────────────────┘
```

## Context Boundaries

### Well-Defined Boundaries
1. **Debate ↔ Implementation:** Clear separation between decision and execution
2. **Testing ↔ Performance:** Distinct concerns (correctness vs efficiency)
3. **AI Integration ↔ Domain:** AI details hidden from business logic

### Shared Concepts
1. **Decision:** Shared between Debate and Implementation
2. **Metrics:** Used by Performance, Testing, and Evolution
3. **Events:** Common event infrastructure across all contexts

## Anti-Patterns to Avoid

1. **Chatty Interfaces:** Minimize cross-context calls
2. **Shared Database:** Each context owns its data
3. **Distributed Transactions:** Use eventual consistency
4. **Feature Envy:** Keep behavior with data

## Migration Strategy

When evolving the context map:

1. **Split Contexts:** When a context grows too large
2. **Merge Contexts:** When boundaries prove artificial
3. **Extract Shared Kernel:** When duplication becomes problematic
4. **Introduce ACL:** When external integration changes frequently

## Governance

### Context Ownership
- **Debate Context:** Core team (highest priority)
- **Implementation Context:** DevOps team
- **Testing Context:** QA team
- **Performance Context:** SRE team
- **Evolution Context:** Architecture team
- **AI Integration Context:** Platform team

### Change Management
1. Changes to shared kernel require all context owners' approval
2. Published language changes need migration period
3. Event schema changes must be backward compatible
4. New contexts require architecture review

## Future Considerations

### Potential New Contexts
1. **Security Context:** For security scanning and compliance
2. **Analytics Context:** For business intelligence and reporting
3. **Notification Context:** For alerts and communications

### Potential Mergers
1. **Testing + Performance:** If quality concerns converge
2. **Implementation + Evolution:** If continuous improvement becomes core

### External Integrations
1. **GitHub Context:** Extract GitHub-specific logic
2. **Cloud Provider Context:** Abstract infrastructure concerns
3. **Monitoring Context:** Separate from Performance for external tools

---

*This context map is a living document and should be updated as the system evolves.*