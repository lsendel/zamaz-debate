# 🚨 URGENT: Claude Implementation Required!

## Task Details
- **Issue #**: 180
- **Title**: Test: Implement a greeting function for Claude
- **URL**: https://github.com/lsendel/zamaz-debate/issues/180
- **Created**: 2025-07-09T04:37:08Z

## Implementation Instructions

Claude, when you see this file, please:

1. Read the issue details below
2. Create a new branch: `ai-impl/issue-${ISSUE_NUMBER}`
3. Implement the requested changes
4. Commit with message: "AI Implementation: Issue #${ISSUE_NUMBER}"
5. Create a pull request

## Issue Content

Claude, please implement a simple Python function called `greet(name)` that returns a personalized greeting message. 

The function should:
1. Take a name parameter
2. Return 'Hello, {name}\! Welcome to Zamaz.'
3. Include type hints
4. Add a docstring

Please create this in a new file: src/utils/greeting.py

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
gh pr create --title "AI Implementation: Test: Implement a greeting function for Claude" \
  --body "Automated implementation for issue #${ISSUE_NUMBER}" \
  --label "ai-generated"
```

---
**This is an automated task for Claude AI**
