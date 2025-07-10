# Integration Testing Guide

## Overview

This guide explains how to run and understand the integration tests for cross-context communication in the Zamaz Debate System's DDD architecture.

## Test Structure

### 1. Event Bus Tests (`test_event_bus.py`)
Tests the core event infrastructure:
- Basic publish/subscribe functionality
- Multiple handlers for same event
- Handler priority execution order
- Event history recording
- Error handling and resilience
- Synchronous and asynchronous handlers

### 2. Cross-Context Flow Tests (`test_cross_context_flows.py`)
Tests actual event flows between bounded contexts:

#### Debate → Implementation Flow
- Complex debates create implementation tasks
- Simple debates don't create tasks
- Task assignment based on debate winner

#### Evolution → All Contexts Flow
- Evolution triggers system-wide analysis
- Completed evolutions create implementation tasks
- Tasks assigned based on complexity

#### Testing → Performance Flow
- Performance test failures trigger analysis
- Coverage decrease triggers evolution
- Test suite completion updates benchmarks

#### Performance → Implementation Flow
- Critical metric breaches create urgent tasks
- Non-critical thresholds don't create tasks

#### End-to-End Scenarios
- Complete evolution cycle from trigger to task creation
- Full event chain verification

### 3. Saga Pattern Tests (`test_saga_patterns.py`)
Tests long-running processes with compensation:

#### Evolution Saga
- Happy path: Trigger → Analysis → Planning → Implementation → Validation
- Compensation on failure at any step
- State tracking through process

#### Deployment Saga
- PR Merge → Tests → Build → Staging → Production
- Rollback on failure
- Parallel saga execution
- State persistence and resumption

## Running the Tests

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Ensure you're in the project root
cd /path/to/zamaz-debate
```

### Run All Integration Tests
```bash
# Using the test runner script
python run_integration_tests.py

# Or using pytest directly
pytest tests/integration/ -v
```

### Run Specific Test Suite
```bash
# Event bus tests only
pytest tests/integration/test_event_bus.py -v

# Cross-context flows only
pytest tests/integration/test_cross_context_flows.py -v

# Saga patterns only
pytest tests/integration/test_saga_patterns.py -v
```

### Run Specific Test
```bash
# Run a single test function
pytest tests/integration/test_event_bus.py::TestEventBusBasics::test_publish_subscribe -v
```

## Understanding Test Output

### Successful Test Run
```
tests/integration/test_event_bus.py::TestEventBusBasics::test_publish_subscribe PASSED [10%]
tests/integration/test_event_bus.py::TestEventBusBasics::test_multiple_handlers PASSED [20%]
...
======================= 25 passed in 3.45s =======================
✅ All integration tests PASSED!
```

### Failed Test Run
```
tests/integration/test_cross_context_flows.py::TestDebateToImplementationFlow::test_complex_debate_creates_task FAILED [50%]
...
======================= 1 failed, 24 passed in 4.12s =======================
❌ Some integration tests FAILED!
```

## Test Data Management

### Temporary Test Data
Tests create temporary data in `tests/data/` subdirectories:
- `tests/data/debates/`
- `tests/data/tasks/`
- `tests/data/evolutions/`
- `tests/data/deployments/`

This data is automatically cleaned up after each test run.

### Event History
During tests, the event bus records all published events, which can be accessed via:
```python
bus = get_event_bus()
history = bus.get_event_history()
```

## Writing New Integration Tests

### 1. Event Flow Test Template
```python
@pytest.mark.asyncio
async def test_new_event_flow(setup_repositories, setup_event_bus):
    """Test description"""
    repos = setup_repositories
    bus = setup_event_bus
    
    # Arrange: Set up initial state
    entity = YourEntity(...)
    await repos["your_repo"].save(entity)
    
    # Act: Publish triggering event
    event = YourEvent(...)
    await bus.publish(event)
    
    # Allow async handlers to complete
    await asyncio.sleep(0.2)
    
    # Assert: Verify expected outcomes
    results = await repos["target_repo"].find_all(TargetEntity)
    assert len(results) == expected_count
    
    # Verify event chain
    history = bus.get_event_history()
    assert any(isinstance(e, ExpectedEvent) for e in history)
```

### 2. Saga Test Template
```python
class YourSaga:
    async def execute(self, input_data):
        try:
            # Step 1
            self.state = "step1"
            result1 = await self._step1(input_data)
            self.completed_steps.append("step1")
            
            # Step 2
            self.state = "step2"
            result2 = await self._step2(result1)
            self.completed_steps.append("step2")
            
            self.state = "completed"
            return {"status": "success"}
            
        except Exception as e:
            self.state = "failed"
            await self._compensate()
            raise
    
    async def _compensate(self):
        # Reverse completed steps
        for step in reversed(self.completed_steps):
            # Undo each step
            pass
```

## Debugging Failed Tests

### 1. Check Event Publishing
```python
# Add debug logging
@subscribe(YourEvent, context="test")
async def debug_handler(event: YourEvent):
    print(f"Received event: {event}")
```

### 2. Verify Repository State
```python
# Check what's actually saved
all_entities = await repo.find_all(Entity)
for entity in all_entities:
    print(f"Entity: {entity.id}, Status: {entity.status}")
```

### 3. Examine Event History
```python
# See full event flow
history = bus.get_event_history()
for event in history:
    print(f"{event.occurred_at}: {event.event_type}")
```

### 4. Check Handler Registration
```python
# Verify handlers are registered
handlers = bus.get_handlers_for_event(YourEvent)
print(f"Handlers for YourEvent: {len(handlers)}")
```

## Performance Considerations

### Event Processing
- Most event handlers complete within 10-50ms
- Complex flows with multiple events may take 100-500ms
- Use appropriate sleep times in tests (0.1-0.5s)

### Test Isolation
- Each test uses fresh repositories and event bus
- No shared state between tests
- Parallel test execution is safe

### Memory Usage
- Event history is cleared between tests
- Temporary files are cleaned up
- No memory leaks in normal operation

## Common Issues and Solutions

### Issue: Handler Not Executing
**Solution**: Ensure handler is registered before publishing event
```python
# Initialize handlers first
initialize_cross_context_handlers()

# Then publish events
await bus.publish(event)
```

### Issue: Timing Issues
**Solution**: Add appropriate wait times
```python
# After publishing event
await asyncio.sleep(0.2)  # Give handlers time to execute
```

### Issue: Repository Not Found
**Solution**: Ensure test data directories exist
```python
Path("tests/data/your_context").mkdir(parents=True, exist_ok=True)
```

### Issue: Event Not in History
**Solution**: Enable event recording
```python
bus = get_event_bus(record_events=True)
```

## Continuous Integration

Add to your CI pipeline:
```yaml
# .github/workflows/test.yml
- name: Run Integration Tests
  run: |
    python run_integration_tests.py
```

Or with coverage:
```bash
pytest tests/integration/ --cov=src/events --cov=src/contexts --cov-report=html
```

## Conclusion

The integration tests verify that:
1. ✅ Event bus correctly routes events between contexts
2. ✅ Cross-context workflows execute as designed
3. ✅ Saga patterns handle failures with proper compensation
4. ✅ The system maintains loose coupling between contexts
5. ✅ Performance is acceptable for typical workflows

Regular execution of these tests ensures the DDD architecture continues to function correctly as the system evolves.