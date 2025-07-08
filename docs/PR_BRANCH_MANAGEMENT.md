# PR and Branch Management in Zamaz Debate

This document explains the improved PR and branch management system implemented to prevent duplicates and conflicts.

## Problem Statement

The system was experiencing several issues:
1. **Duplicate Debate IDs**: When the system restarted or multiple instances ran, debate IDs would reset (debate_1, debate_2, etc.), causing branch name conflicts
2. **Weak Evolution Fingerprinting**: Similar evolutions were not being detected as duplicates, leading to repetitive PRs
3. **Generic PR Titles**: All evolution PRs had the same title "[Evolution] Add comprehensive testing framework"
4. **Branch Conflicts**: No detection of existing branches before creation
5. **Excessive Evolution**: No throttling mechanism, leading to too many evolution attempts

## Solutions Implemented

### 1. Unique Debate IDs Using UUIDs

**Before:**
```python
debate_id = f"debate_{self.debate_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
```

**After:**
```python
debate_id = f"debate_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
```

This ensures debate IDs are always unique, even across system restarts.

### 2. Improved Evolution Fingerprinting

The fingerprinting algorithm now includes:
- First 200 characters of description and decision text
- The debate_id for extra uniqueness
- A 32-character hash (instead of 16) to reduce collision probability

```python
def _generate_fingerprint(self, evolution: Dict) -> str:
    key_parts = [
        evolution.get("type", "").lower().strip(),
        evolution.get("feature", "").lower().strip(),
        description[:200],  # Include content
        decision_text[:200],  # Include content
        evolution.get("debate_id")  # Include unique ID
    ]
    # Use 32-char hash for better uniqueness
    return hashlib.sha256(content.encode()).hexdigest()[:32]
```

### 3. Evolution Throttling

Added `should_evolve()` method with two throttling rules:
- **5-minute cooldown**: Prevents evolutions within 5 minutes of the last one
- **Hourly limit**: Maximum 5 evolutions per hour

```python
def should_evolve(self) -> bool:
    # Check 5-minute cooldown
    if time_since_last < 300:
        print(f"⏳ Evolution throttled: Only {time_since_last}s since last evolution")
        return False
    
    # Check hourly limit
    if recent_count >= 5:
        print(f"⏳ Evolution throttled: {recent_count} evolutions in last hour")
        return False
    
    return True
```

### 4. Descriptive PR Titles

PR titles now include:
- Decision ID suffix for uniqueness
- Specific feature detection (ADR, usability, testing, etc.)

**Examples:**
- `[Evolution-073229] Implement Architectural Decision Records (ADRs)`
- `[Evolution-074903] Improve usability and user experience`
- `[Evolution-075312] Add comprehensive testing framework`

### 5. Branch Conflict Detection

Before creating a branch, the system now:
1. Checks if branch exists locally
2. Checks if branch exists on remote
3. Generates alternative name with timestamp if conflicts found

```python
async def _create_branch(self, branch_name: str) -> bool:
    # Check local branches
    if branch_exists_locally:
        branch_name = f"{branch_name}_v{int(time.time())}"
    
    # Check remote branches
    if branch_exists_on_remote:
        branch_name = f"{branch_name}_v{int(time.time())}"
```

### 6. PR Deduplication

Before creating a PR, check for similar existing PRs:

```python
def _find_similar_prs(self, decision: Decision) -> List[str]:
    # List open PRs with evolution label
    # Check if any PR has similar decision ID in title
    if decision.id and any(part in pr["title"] for part in decision.id.split("_")[-2:]):
        similar_prs.append(f"#{pr['number']}: {pr['title']}")
```

## Auto-Evolution Updates

The auto-evolution script now respects throttling:
```python
# Initialize evolution tracker
evolution_tracker = EvolutionTracker()

# Check throttling before evolution
if trigger_evolution(base_url, evolution_tracker):
    evolution_count += 1
```

## Testing

Comprehensive tests verify:
- Debate ID uniqueness across instances
- Evolution fingerprint improvements
- Throttling mechanism functionality
- Hourly limit enforcement

Run tests with:
```bash
pytest tests/test_pr_branch_management.py -v
```

## Impact

These improvements significantly reduce:
- Duplicate PR creation
- Branch naming conflicts
- Excessive evolution attempts
- Confusion from generic PR titles

The system is now more stable and maintainable with clearer PR organization.