# Claude Implementation Guide for Zamaz Debate Evolution PRs

This guide provides best practices and a structured approach for implementing evolution features assigned to @claude.

## Implementation Process

### 1. Pre-Implementation Analysis

Before writing any code, Claude should:

1. **Read the PR description thoroughly** to understand:
   - The specific improvement being requested
   - The debate consensus that led to this decision
   - Any complexity indicators or special requirements

2. **Analyze the current codebase**:
   ```bash
   # Check related files
   grep -r "relevant_keyword" src/
   
   # Understand existing patterns
   find . -name "*.py" -path "*/similar_feature/*"
   
   # Check for existing tests
   find tests/ -name "*test*.py" | xargs grep "related_functionality"
   ```

3. **Create an implementation plan** with:
   - List of files to modify/create
   - Test cases to write
   - Documentation to update

### 2. Implementation Best Practices

#### Code Organization
```python
# Follow existing patterns in the codebase
# Example structure for new features:

# src/features/new_feature/
# ├── __init__.py
# ├── service.py      # Core business logic
# ├── models.py       # Data models if needed
# └── utils.py        # Helper functions

# tests/features/
# └── test_new_feature.py
```

#### Code Style Guidelines

1. **Follow PEP 8** and existing code conventions
2. **Use type hints** for all function parameters and returns:
   ```python
   def process_evolution(self, evolution: Dict[str, Any]) -> Optional[Evolution]:
       """Process an evolution request with proper validation."""
       pass
   ```

3. **Add comprehensive docstrings**:
   ```python
   def implement_feature(self, config: Dict[str, Any]) -> bool:
       """
       Implement the specified feature based on configuration.
       
       Args:
           config: Configuration dictionary containing:
               - feature_name: Name of the feature to implement
               - parameters: Feature-specific parameters
               
       Returns:
           bool: True if implementation successful, False otherwise
           
       Raises:
           ImplementationError: If feature cannot be implemented
       """
   ```

#### Error Handling
```python
# Always handle errors gracefully
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Failed to perform operation: {e}")
    # Provide fallback or recovery mechanism
    return default_value
```

### 3. Testing Requirements

Every implementation MUST include:

1. **Unit Tests** (minimum 80% coverage):
   ```python
   # tests/test_feature.py
   import pytest
   from src.features.new_feature import FeatureService
   
   class TestFeatureService:
       def test_basic_functionality(self):
           """Test the core feature works as expected"""
           service = FeatureService()
           result = service.process("input")
           assert result == "expected_output"
       
       def test_edge_cases(self):
           """Test edge cases and error conditions"""
           pass
       
       def test_integration(self):
           """Test integration with existing components"""
           pass
   ```

2. **Integration Tests** for features that interact with other components

3. **Performance Tests** for performance-critical features:
   ```python
   def test_performance(self):
       """Ensure feature meets performance requirements"""
       import time
       start = time.time()
       # Run operation 1000 times
       for _ in range(1000):
           service.process("input")
       duration = time.time() - start
       assert duration < 1.0  # Should complete in under 1 second
   ```

### 4. Documentation Requirements

1. **Update relevant documentation**:
   - API documentation if adding new endpoints
   - README.md if adding new features
   - CLAUDE.md if adding new commands or workflows

2. **Add inline documentation**:
   - Document complex algorithms
   - Explain non-obvious design decisions
   - Add TODO comments for future improvements

3. **Create ADR if architectural decision**:
   ```bash
   make adr-create title="Feature Implementation" \
     context="Why we need this" \
     decision="How we implement it"
   ```

### 5. Implementation Checklist

Before marking implementation complete:

- [ ] All tests pass: `make test`
- [ ] Code follows style guidelines: `make lint`
- [ ] Documentation updated
- [ ] No hardcoded values (use config/env vars)
- [ ] Error handling implemented
- [ ] Logging added for debugging
- [ ] Performance acceptable
- [ ] Security considerations addressed
- [ ] Backward compatibility maintained

### 6. Common Patterns to Follow

#### Service Pattern
```python
class NewFeatureService:
    """Service for handling new feature logic"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
    
    def _default_config(self) -> Dict:
        """Provide sensible defaults"""
        return {
            "timeout": 30,
            "retry_count": 3,
        }
```

#### Factory Pattern
```python
class FeatureFactory:
    """Factory for creating feature instances"""
    
    @staticmethod
    def create(feature_type: str) -> BaseFeature:
        if feature_type == "type_a":
            return TypeAFeature()
        elif feature_type == "type_b":
            return TypeBFeature()
        raise ValueError(f"Unknown feature type: {feature_type}")
```

#### Repository Pattern
```python
class FeatureRepository:
    """Repository for feature data persistence"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)
    
    def save(self, feature: Feature) -> None:
        """Persist feature to storage"""
        pass
    
    def load(self, feature_id: str) -> Optional[Feature]:
        """Load feature from storage"""
        pass
```

### 7. PR Update Template

When implementing, update the PR with progress:

```markdown
## Implementation Progress

### ✅ Completed
- [x] Initial analysis and planning
- [x] Core feature implementation
- [x] Unit tests (85% coverage)

### 🚧 In Progress
- [ ] Integration tests
- [ ] Documentation updates

### 📋 Next Steps
- Performance optimization
- Add monitoring metrics

### 🐛 Issues Found
- Issue #1: [Description and solution]

### 💭 Implementation Notes
- Chose approach X because...
- Consider future enhancement Y
```

### 8. Security Considerations

1. **Never commit secrets**: Use environment variables
2. **Validate all inputs**: Especially from external sources
3. **Sanitize outputs**: Prevent injection attacks
4. **Follow principle of least privilege**
5. **Add rate limiting** where appropriate

### 9. Performance Guidelines

1. **Profile before optimizing**:
   ```python
   import cProfile
   cProfile.run('function_to_profile()')
   ```

2. **Use appropriate data structures**:
   - Sets for membership testing
   - Deque for queues
   - DefaultDict for counting

3. **Implement caching** where beneficial:
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def expensive_operation(param: str) -> Result:
       """Cache results of expensive operations"""
       pass
   ```

### 10. Commit Message Format

Follow conventional commits:
```
feat: Add monitoring dashboard

- Implement real-time metrics display
- Add performance graphs
- Include error rate tracking

Closes #88
```

### 11. Post-Implementation

1. **Request review** from Gemini (as specified in PR)
2. **Address review feedback** promptly
3. **Update documentation** based on final implementation
4. **Create follow-up issues** for future improvements

## Example Implementation Flow

1. **Start with tests** (TDD approach):
   ```python
   def test_feature_should_work():
       assert feature.process("input") == "expected"
   ```

2. **Implement minimal solution** to pass tests

3. **Refactor** for clarity and performance

4. **Add edge case handling**

5. **Document** thoroughly

6. **Submit** for review

Remember: Quality over speed. A well-implemented feature with tests and documentation is better than a quick hack that causes problems later.