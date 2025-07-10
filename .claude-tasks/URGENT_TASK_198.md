# 🚨 URGENT: Claude Implementation Required!

## Task Details
- **Issue #**: 198
- **Title**: Implement Event-Driven Architecture with Apache Kafka
- **URL**: https://github.com/lsendel/zamaz-debate/pull/198
- **Created**: 2025-07-09T23:51:15Z

## Implementation Instructions

Claude, when you see this file, please:

1. Read the issue details below
2. Create a new branch: `ai-impl/issue-${ISSUE_NUMBER}`
3. Implement the requested changes
4. Commit with message: "AI Implementation: Issue #${ISSUE_NUMBER}"
5. Create a pull request

## Issue Content

## Summary

Implemented comprehensive Apache Kafka integration for high-throughput, real-time event processing in the Zamaz Debate System.

## Key Features

- High-throughput processing for millions of events per day
- Event persistence with configurable retention policies
- Horizontal scaling through partitioned topics
- Dead letter queues for error handling
- Real-time analytics and monitoring
- Fault tolerance with automatic retries

## Components Added

- KafkaClient, KafkaProducer, KafkaConsumer
- KafkaEventBridge for seamless integration
- Event processors for different event types
- KafkaService for coordinating all components
- Comprehensive test suite and documentation

## Testing

- Added 20+ test cases for all components
- Integration tests for end-to-end event flow
- Performance and error handling tests

## Documentation

- Comprehensive Kafka integration guide
- API documentation for new endpoints
- Configuration and deployment instructions

Closes #197

Generated with [Claude Code](https://claude.ai/code)

Co-authored-by: Luis Diaz Sendel <lsendel@users.noreply.github.com>

## Quick Start Commands

```bash
# Create branch
git checkout -b ai-impl/issue-${ISSUE_NUMBER}

# After implementation
git add .
git commit -m "AI Implementation: Issue #${ISSUE_NUMBER}

Implemented by Claude

Closes #${ISSUE_NUMBER}"
git push origin ai-impl/issue-${ISSUE_NUMBER}

# Create PR
gh pr create --title "AI Implementation: Implement Event-Driven Architecture with Apache Kafka" \
  --body "Automated implementation for issue #${ISSUE_NUMBER}" \
  --label "ai-generated"
```

---
**This is an automated task for Claude AI**
