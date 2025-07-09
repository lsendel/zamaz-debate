# JSON Schema Documentation for Zamaz Debate System

## Overview

This document describes the JSON schema and structure for all data files in the Zamaz Debate System. Each file type has a specific structure that must be maintained for system integrity.

## File Types and Schemas

### 1. Debate Files (`/data/debates/debate_*.json`)

**Purpose**: Records of all AI debates, including questions, responses, and consensus.

```json
{
  "id": "debate_123_20250708_143022",
  "question": "String - The original question posed",
  "context": "String - Additional context provided",
  "rounds": [
    {
      "claude": "String - Claude's response",
      "gemini": "String - Gemini's response"
    }
  ],
  "consensus": "Boolean - Whether consensus was reached",
  "final_decision": "String - The consensus decision (if reached)",
  "complexity": "String - 'simple' or 'complex'",
  "start_time": "ISO 8601 timestamp",
  "end_time": "ISO 8601 timestamp",
  "method": "String - 'simple' or 'debate'"
}
```

### 2. Decision Files (`/data/decisions/decision_*.json`)

**Purpose**: Formal decisions derived from debates that require action.

```json
{
  "id": "decision_456_20250708_143022",
  "debate_id": "String - Reference to source debate",
  "question": "String - Original question",
  "context": "String - Decision context",
  "decision_text": "String - The actual decision",
  "decision_type": "String - 'complex', 'evolution', etc.",
  "implementation_assignee": "String - 'claude', 'gemini', or 'human'",
  "implementation_complexity": "String - 'simple' or 'complex'",
  "method": "String - How decision was made",
  "rounds": "Number - Debate rounds (if applicable)",
  "timestamp": "ISO 8601 timestamp"
}
```

### 3. Evolution History (`/data/evolutions/evolution_history.json`)

**Purpose**: Central registry of all system evolutions to prevent duplicates.

```json
{
  "evolutions": [
    {
      "id": "Number - Sequential ID",
      "type": "String - 'feature', 'enhancement', etc.",
      "feature": "String - Short feature description",
      "description": "String - Full description",
      "timestamp": "ISO 8601 timestamp",
      "fingerprint": "String - Hash for duplicate detection",
      "debate_id": "String - Source debate reference"
    }
  ],
  "last_updated": "ISO 8601 timestamp"
}
```

### 4. Individual Evolution Files (`/data/evolutions/evo_*.json`)

**Purpose**: Detailed record of each evolution including AI suggestions.

```json
{
  "type": "String - Evolution type",
  "feature": "String - Feature name",
  "description": "String - Full description",
  "debate_id": "String - Source debate",
  "claude_suggestion": "String - Claude's full analysis",
  "gemini_suggestion": "String - Gemini's full analysis",
  "timestamp": "ISO 8601 timestamp",
  "id": "Number - Evolution ID"
}
```

### 5. PR Draft Files (`/data/pr_drafts/pr_draft_*.json`)

**Purpose**: Pull request drafts before they're pushed to GitHub.

```json
{
  "pr": {
    "id": "String - GitHub PR number (null if draft)",
    "title": "String - PR title",
    "body": "String - PR description (markdown)",
    "branch_name": "String - Git branch name",
    "base_branch": "String - Target branch (usually 'main')",
    "assignee": "String - GitHub username",
    "labels": ["Array", "of", "labels"],
    "status": "String - 'draft', 'open', 'merged', 'closed'"
  },
  "decision": {
    "id": "String - Decision ID",
    "decision_text": "String - What to implement",
    "decision_type": "String - Type of decision"
  },
  "created_at": "ISO 8601 timestamp"
}
```

## Field Conventions

### Required vs Optional Fields

- **Required**: Fields that must always be present
- **Optional**: Fields that may be null or omitted
- **Nullable**: Fields that can explicitly be null

### Timestamp Format

All timestamps use ISO 8601 format: `YYYY-MM-DDTHH:MM:SS.ffffff`

### ID Formats

- **Debate ID**: `debate_{uuid}_{timestamp}`
- **Decision ID**: `decision_{uuid}_{timestamp}` or `evolution_debate_{uuid}_{timestamp}`
- **Evolution ID**: Sequential integer
- **PR ID**: GitHub PR number (string)

### Enum Values

**Decision Types**:
- `simple`: Simple decisions
- `complex`: Complex decisions requiring debate
- `evolution`: System self-improvement decisions

**Implementation Assignees**:
- `claude`: Assigned to Claude AI
- `gemini`: Assigned to Gemini AI  
- `human`: Requires human implementation

**PR Status**:
- `draft`: Local draft, not pushed
- `open`: Open PR on GitHub
- `merged`: PR has been merged
- `closed`: PR closed without merging

## Validation Rules

1. **IDs must be unique** within their file type
2. **Timestamps must be valid** ISO 8601 format
3. **References must exist** (e.g., debate_id must point to real debate)
4. **Enum values must be valid** from the defined sets
5. **Required fields cannot be null**

## Common Issues and Solutions

### Issue: Truncated AI Responses
**Cause**: Token limits in AI APIs
**Solution**: Increase `max_tokens` parameter in AI client calls

### Issue: Null PR IDs
**Cause**: PR created but ID not captured from GitHub response
**Solution**: Extract PR number from GitHub CLI output and set on PR object

### Issue: Missing Fields
**Cause**: Schema evolution over time
**Solution**: Add default values for missing fields during migration

### Issue: Invalid JSON
**Cause**: Concurrent writes or interrupted operations
**Solution**: Use atomic file operations with temporary files

## Migration Guide

When adding new fields:

1. Make them optional with defaults
2. Update this documentation
3. Create migration script if needed
4. Test backward compatibility

## Example Validation Script

```python
import json
import jsonschema
from pathlib import Path

# Define schemas here
debate_schema = {
    "type": "object",
    "required": ["id", "question", "rounds", "consensus"],
    "properties": {
        "id": {"type": "string"},
        "question": {"type": "string"},
        "rounds": {"type": "array"},
        "consensus": {"type": "boolean"}
    }
}

# Validate all debates
for debate_file in Path("data/debates").glob("*.json"):
    with open(debate_file) as f:
        data = json.load(f)
        jsonschema.validate(data, debate_schema)
```