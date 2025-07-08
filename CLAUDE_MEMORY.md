# Claude Memory Documentation

This document outlines what Claude needs to remember when working with the Zamaz Debate System.

## Key Commands and Workflows

### 1. Running the System
- **Start web interface**: `make run`
- **Stop web interface**: `make stop`
- **Run in development mode**: `make dev`
- **Check system status**: `make status`
- **View logs**: `make logs`

### 2. Testing
- **Run all tests**: `make test` or `./venv/bin/pytest tests/ -v`
- **Run specific test file**: `./venv/bin/pytest tests/test_file.py -v`
- **Run with short traceback**: `./venv/bin/pytest tests/ -v --tb=short`

### 3. Evolution and PRs
- **Trigger single evolution**: `make evolve`
- **Run auto-evolution**: `make auto-evolve` (runs continuously every 20 minutes)
- **Check PR drafts**: `make pr-drafts`

### 4. Git Operations
- **List open PRs**: `gh pr list`
- **Check out PR**: `gh pr checkout <PR_NUMBER>`
- **Merge PR**: `gh pr merge <PR_NUMBER> --merge`
- **View PR**: `gh pr view <PR_NUMBER>`

## Important Implementation Details

### 1. PR Assignment Rules
- **Evolution PRs**: Always assigned to @claude for implementation
- **Complex Decisions**: Assigned based on DelegationService rules
  - Complex technical tasks → Claude (with Gemini as reviewer)
  - Regular tasks → Gemini (with Codex as reviewer)

### 2. Testing Framework Structure
```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_debate_nucleus.py   # Core DebateNucleus tests
├── test_evolution_tracker.py # Evolution tracking tests
├── test_pr_service.py       # PR service tests
└── test_web_api.py         # Web API endpoint tests
```

### 3. Common Test Patterns
- **Clean test environment**: Always start with clean data in tests
  ```python
  tracker._save_history({"evolutions": [], "fingerprints": []})
  ```
- **Mock AI clients**: Use mock_claude_client and mock_gemini_client fixtures
- **Async tests**: Use `@pytest.mark.asyncio` decorator

### 4. Environment Variables
- `CREATE_PR_FOR_DECISIONS`: Enable/disable PR creation
- `AUTO_PUSH_PR`: Enable/disable automatic PR pushing
- `PR_ASSIGNEE`: Default PR assignee
- `AUTO_EVOLVE_ENABLED`: Enable/disable auto-evolution
- `AUTO_EVOLVE_INTERVAL`: Evolution interval (e.g., "20m", "1h")

### 5. File Locations
- **Debates**: `data/debates/`
- **Decisions**: `data/decisions/`
- **Evolution history**: `data/evolutions/evolution_history.json`
- **PR drafts**: `data/pr_drafts/`
- **Web logs**: `web_interface.log`

## Common Debugging Steps

1. **PR creation not working**:
   - Check if `CREATE_PR_FOR_DECISIONS=true` in environment
   - Restart web server: `make stop && make run`
   - Check web logs: `make logs`

2. **Tests failing**:
   - Ensure test data is isolated (not using production data)
   - Check for correct mock setup
   - Verify async functions are properly awaited

3. **Evolution duplicates**:
   - Check evolution_history.json for fingerprint collisions
   - Verify feature extraction is working correctly
   - Ensure evolution tracker is saving properly

## PR Implementation Workflow

When implementing evolution PRs:

1. **Check out the PR branch**:
   ```bash
   gh pr checkout <PR_NUMBER>
   ```

2. **Understand the requirements**:
   - Read the decision in the PR description
   - Check both Claude's and Gemini's analysis
   - Look for implementation notes

3. **Implement the feature**:
   - Follow existing code patterns
   - Add comprehensive tests
   - Update documentation as needed

4. **Test thoroughly**:
   ```bash
   make test
   ```

5. **Commit and push**:
   ```bash
   git add -A
   git commit -m "Implement <feature description>"
   git push
   ```

## Key Code Patterns

### 1. Complexity Assessment
```python
# Simple: rename, format, typo, spacing, comment, import
# Moderate: refactor, optimize, clean, organize, split, merge  
# Complex: architecture, design, pattern, system, structure, integrate, improve
```

### 2. Evolution Feature Extraction
```python
# Maps decision text patterns to feature names
"testing" → "automated_testing"
"monitoring" → "monitoring_system"
"caching" → "caching_system"
```

### 3. PR Title Generation
```python
# Evolution: "[Evolution] <specific feature>"
# Complex: "[Complex] <core question>"
```

## Notes for Claude

- Always use TodoWrite to track implementation progress
- Run tests before committing changes
- Check for existing patterns before implementing new features
- Ensure PR descriptions include @claude assignment for evolution PRs
- Use `make auto-evolve` for continuous improvement mode
- Remember to clean up test data to avoid interference between tests