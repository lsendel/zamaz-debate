# Claude-Implements-Gemini-Reviews Workflow

This demonstrates the new PR workflow:

1. **Implementation Phase**: PRs are assigned to Claude
   - Claude implements the changes based on the debate decision
   - All complex architectural decisions go to Claude

2. **Review Phase**: Gemini reviews before merge
   - Gemini is automatically added as a reviewer
   - Provides code review and quality checks
   - Must approve before merge

3. **Benefits**:
   - Claude handles complex implementation
   - Gemini provides independent review
   - Two-AI collaboration ensures quality

## Configuration

```env
CLAUDE_GITHUB_USERNAME=lsendel  # Implementer
GEMINI_GITHUB_USERNAME=lsendel  # Reviewer
```