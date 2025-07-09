# Zamaz Debate Data System Guide

## Overview

The Zamaz Debate System uses a file-based storage approach where all data is stored as JSON files in organized directories. This guide explains how the system works and the relationship between different data types.

## Directory Structure

```
data/
├── debates/         # All debate records
├── decisions/       # Formal decision records
├── evolutions/      # System evolution history
├── pr_drafts/       # Pull request drafts
├── pr_history/      # PR tracking history
├── pr_reviews/      # PR review results
├── ai_cache/        # Cached AI responses
└── localhost_checks/# Localhost validation results
```

## Data Types and Relationships

### 1. Debates (`/data/debates/`)

Every interaction that requires AI processing creates a debate file:

- **File naming**: `debate_{id}_{timestamp}.json`
- **Created when**: Any question is processed by the system
- **Contains**: Question, context, AI responses, consensus status

**Example structure**:
```json
{
  "id": "debate_123_20250708_143022",
  "question": "Should we add caching?",
  "rounds": [
    {
      "agent": "claude",
      "response": "Analysis of caching benefits..."
    }
  ],
  "consensus": true,
  "timestamp": "2025-07-08T14:30:22"
}
```

### 2. Decisions (`/data/decisions/`)

Formal decisions are created from successful debates:

- **File naming**: `decision_{id}_{timestamp}.json`
- **Created when**: 
  - Complex debates reach consensus
  - Evolution debates identify improvements
  - PR-worthy changes are identified
- **Contains**: Decision details, implementation assignment, debate reference

**Example structure**:
```json
{
  "id": "decision_456_20250708_143022",
  "debate_id": "debate_123_20250708_143022",
  "decision": "Implement Redis caching for API responses",
  "decision_type": "feature",
  "implementation_assignee": "claude",
  "complexity": "complex"
}
```

### 3. Evolutions (`/data/evolutions/`)

Tracks system self-improvement history:

- **Main file**: `evolution_history.json` - Central registry
- **Individual files**: `evo_{id}_{timestamp}.json`
- **Purpose**: Prevent duplicate improvements, track system growth

## Why More Debates Than Decisions?

The system typically has more debates than decisions because:

1. **Not all debates create decisions**:
   - Simple questions get direct answers
   - Some debates don't reach consensus
   - Informational queries don't need decisions

2. **Decision criteria**:
   - Must be complex enough to warrant formal tracking
   - Must reach consensus between AIs
   - Must have actionable outcomes

3. **Debate types**:
   - **Simple**: Single AI response, no decision needed
   - **Complex**: Multi-round debate, may create decision
   - **Evolution**: System improvement debates, usually create decisions

## Data Flow Example

```
User Question
    ↓
Create Debate
    ↓
Is Complex? → No → Simple Response (Debate only)
    ↓ Yes
Full AI Debate
    ↓
Consensus? → No → Record Debate (No decision)
    ↓ Yes
Create Decision
    ↓
Is Evolution? → Yes → Update Evolution History
    ↓ No
Is PR-worthy? → Yes → Create PR Draft
```

## Statistics Explained

When you see statistics like:
- **Decisions Made: 69**
- **Debates Run: 145**

This means:
- 145 total questions have been processed
- 69 of those resulted in formal decisions
- 76 were simple queries or didn't reach consensus

## File Lifecycle

1. **Creation**: Files are created atomically when events occur
2. **Persistence**: All files are permanent (no automatic deletion)
3. **Reference**: Files reference each other via IDs
4. **Backup**: Can be backed up by copying the data directory

## Querying the Data

### Count debates:
```bash
ls data/debates/*.json | wc -l
```

### Count decisions:
```bash
ls data/decisions/*.json | wc -l
```

### View recent debates:
```bash
ls -lt data/debates/*.json | head -5
```

### Search for specific topics:
```bash
grep -l "caching" data/debates/*.json
```

## Best Practices

1. **Never manually edit** JSON files - use the system
2. **Regular backups** - Copy entire data directory
3. **Monitor growth** - Check directory sizes periodically
4. **Clean old cache** - `ai_cache/` can be cleared safely

## Troubleshooting

### Missing statistics:
- Check if data directories exist
- Ensure proper file permissions
- Verify JSON file integrity

### Inconsistent counts:
- Some files may be corrupted
- Check for incomplete writes
- Validate JSON structure

### Performance issues:
- Too many files in directories
- Consider archiving old data
- Implement pagination for file listing