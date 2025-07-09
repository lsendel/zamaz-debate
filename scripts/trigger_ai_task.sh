#!/bin/bash
# Script to manually trigger AI task creation for an issue

set -e

ISSUE_NUMBER=${1:-178}

echo "🤖 Triggering AI task creation for issue #$ISSUE_NUMBER"

# Get issue details
ISSUE_DATA=$(gh issue view $ISSUE_NUMBER --json number,title,body,labels,assignees)

# Check if issue has ai-assigned label
HAS_AI_LABEL=$(echo "$ISSUE_DATA" | jq -r '.labels[] | select(.name == "ai-assigned") | .name' || echo "")

if [ -z "$HAS_AI_LABEL" ]; then
    echo "⚠️  Issue #$ISSUE_NUMBER doesn't have 'ai-assigned' label. Adding it..."
    gh issue edit $ISSUE_NUMBER --add-label "ai-assigned"
fi

# Create AI task files manually (for local development)
mkdir -p ai-tasks

# Extract issue details
TITLE=$(echo "$ISSUE_DATA" | jq -r '.title')
BODY=$(echo "$ISSUE_DATA" | jq -r '.body')

# Create task file
cat > ai-tasks/issue-${ISSUE_NUMBER}.md << EOF
# AI Implementation Task

**Issue Number:** #${ISSUE_NUMBER}
**Title:** ${TITLE}
**URL:** https://github.com/lsendel/zamaz-debate/issues/${ISSUE_NUMBER}
**Created:** $(date -u +"%Y-%m-%dT%H:%M:%SZ")
**Labels:** ai-assigned, implementation, ddd, architecture

## Task Description

${BODY}

---
*This file was created for AI implementation*
EOF

# Create CLAUDE_TASKS.md
cat > CLAUDE_TASKS.md << EOF
# 🤖 Claude Implementation Tasks

This file contains AI-assigned tasks from GitHub issues. When you see this file, please check the \`ai-tasks/\` directory for specific implementation tasks.

## Current AI-Assigned Issues

### Issue #${ISSUE_NUMBER}: ${TITLE}
- **Status:** Open
- **Priority:** High (DDD Implementation)
- **File:** \`ai-tasks/issue-${ISSUE_NUMBER}.md\`

## Instructions for Claude

1. Read the task file in \`ai-tasks/issue-${ISSUE_NUMBER}.md\`
2. Follow the Domain-Driven Design approach specified
3. Create the file structure as outlined
4. Implement according to the acceptance criteria
5. Add comments indicating which issue you're implementing

## Quick Start Commands

\`\`\`bash
# View the task
cat ai-tasks/issue-${ISSUE_NUMBER}.md

# Start implementation
mkdir -p src/contexts src/events src/domain docs

# Create event storming doc
touch docs/event-storming.md
\`\`\`

## Implementation Markers

When implementing, please include these markers in your commits:
- \`AI-Implementation: Issue #${ISSUE_NUMBER}\`
- Add clear commit messages indicating what you're implementing

Remember to follow DDD best practices and create comprehensive tests!
EOF

echo "✅ AI task files created:"
echo "   - ai-tasks/issue-${ISSUE_NUMBER}.md"
echo "   - CLAUDE_TASKS.md"
echo ""
echo "📋 Next steps:"
echo "1. Review the generated files"
echo "2. Commit and push to trigger GitHub Action"
echo "3. Claude will see CLAUDE_TASKS.md in the next session"
echo ""
echo "To commit and push:"
echo "git add ai-tasks/issue-${ISSUE_NUMBER}.md CLAUDE_TASKS.md"
echo "git commit -m \"Add AI task for issue #${ISSUE_NUMBER}\""
echo "git push"