# Claude Integration Testing Guide

## 🧪 How to Validate Claude Picks Up Tasks

### 1. Automated Validation Script

Run the validation script to check all systems:

```bash
python3 scripts/validate_claude_pickup.py
```

This checks:
- ✅ Critical visibility files exist
- ✅ Urgent markers are present
- ✅ Task directories contain tasks
- ✅ README has urgent notice at top
- ✅ GitHub issues are properly labeled
- ✅ AI workflows are active

### 2. Real-Time Monitoring

Monitor the system status in real-time:

```bash
# Run the monitoring dashboard
bash scripts/claude_task_monitor.sh

# Or watch it update every 30 seconds
watch -n 30 bash scripts/claude_task_monitor.sh
```

### 3. Manual Testing Steps

#### Step 1: Create a Test Issue
```bash
gh issue create \
  --title "Test: [Your test description]" \
  --body "Claude, please [specific implementation request]" \
  --label "ai-assigned"
```

#### Step 2: Verify Workflow Triggered
```bash
# Check workflow runs
gh run list --workflow "AI Task Handler" --limit 5

# View specific run details
gh run view [RUN_ID]
```

#### Step 3: Check Task Files Created
```bash
# Pull latest changes
git pull

# Check for new task files
ls -la .claude-tasks/
cat .claude-tasks/URGENT_TASK_*.md

# Check main task list
cat CLAUDE_TASKS.md
```

#### Step 4: Visibility Test
Look for these files that Claude should see immediately:
1. `CLAUDE_CAN_YOU_SEE_THIS.md` - Created by validation script
2. `IMPLEMENT_THIS_NOW.md` - Latest urgent task
3. `CLAUDE_TASKS.md` - Central task list
4. `README.md` - Should have urgent notice at top

### 4. Claude Confirmation Test

When Claude accesses the repository, it should:

1. **See the test file**: `CLAUDE_CAN_YOU_SEE_THIS.md`
2. **Create confirmation**: `CLAUDE_CONFIRMED.md` with:
   - Timestamp of access
   - List of task files found
   - Ready status

### 5. Testing Different Trigger Methods

#### Method 1: Label Trigger
```bash
# Add ai-assigned label to existing issue
gh issue edit [ISSUE_NUMBER] --add-label "ai-assigned"
```

#### Method 2: Comment Trigger
```bash
# Mention @claude in a comment
gh issue comment [ISSUE_NUMBER] --body "@claude Please implement this"
```

#### Method 3: Manual Workflow Trigger
```bash
# Manually trigger for specific issue
gh workflow run "AI Task Handler" -f issue_number=[ISSUE_NUMBER]
```

### 6. Validation Checklist

- [ ] **File System**
  - [ ] CLAUDE_TASKS.md exists and has urgent content
  - [ ] .claude-tasks/ has URGENT_TASK files
  - [ ] README.md has urgent notice in first 10 lines

- [ ] **GitHub**
  - [ ] Issue has "ai-assigned" label
  - [ ] Issue is pinned (for critical tasks)
  - [ ] Workflow runs successfully

- [ ] **Claude Visibility**
  - [ ] CLAUDE_CAN_YOU_SEE_THIS.md is visible
  - [ ] Multiple entry points (README, IMPLEMENT_NOW, etc.)
  - [ ] Clear implementation instructions

### 7. Troubleshooting

#### Issue: Workflow Not Triggering
```bash
# Check workflow status
gh workflow list

# Check recent runs
gh run list --limit 10

# View workflow file
cat .github/workflows/ai-task-handler.yml
```

#### Issue: Task Files Not Created
```bash
# Check if commit was pushed
git log --oneline -5

# Check workflow logs
gh run view [RUN_ID] --log
```

#### Issue: Claude Not Seeing Tasks
1. Run validation: `python3 scripts/validate_claude_pickup.py`
2. Check monitoring: `bash scripts/claude_task_monitor.sh`
3. Ensure files have urgent keywords
4. Verify file permissions

### 8. Success Criteria

Claude successfully picks up tasks when:

1. ✅ Creates `CLAUDE_CONFIRMED.md` after seeing tasks
2. ✅ Creates implementation branch `ai-impl/issue-XXX`
3. ✅ Implements requested functionality
4. ✅ Creates pull request with proper references
5. ✅ Comments on original issue with PR link

### 9. Continuous Monitoring

Set up continuous monitoring:

```bash
# Create a cron job (on server)
crontab -e

# Add this line to run every hour
0 * * * * cd /path/to/zamaz-debate && python3 scripts/validate_claude_pickup.py >> logs/claude_validation.log 2>&1
```

### 10. Metrics to Track

- Time from issue creation to task file generation
- Time from task file to Claude confirmation  
- Time from confirmation to implementation
- Success rate of implementations
- Number of retry attempts needed

## 📊 Current System Status

Run this command to see current status:
```bash
python3 scripts/validate_claude_pickup.py && echo "---" && bash scripts/claude_task_monitor.sh
```