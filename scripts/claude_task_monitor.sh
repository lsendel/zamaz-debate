#!/bin/bash
# Claude Task Monitoring Dashboard
# Shows real-time status of Claude's task pickup system

echo "🤖 Claude Task Monitor Dashboard"
echo "================================"
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo ""

# Function to check file presence and age
check_file() {
    local file=$1
    local label=$2
    
    if [ -f "$file" ]; then
        # Get file age in minutes
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            mod_time=$(stat -f %m "$file")
        else
            # Linux
            mod_time=$(stat -c %Y "$file")
        fi
        current_time=$(date +%s)
        age_minutes=$(( (current_time - mod_time) / 60 ))
        
        echo "✅ $label: Found (updated $age_minutes min ago)"
        
        # Show first few lines with urgent keywords
        if grep -q -i "urgent\|immediate\|now" "$file" 2>/dev/null; then
            echo "   🚨 Contains URGENT markers"
        fi
    else
        echo "❌ $label: Not found"
    fi
}

# Check critical files
echo "📋 Critical Files:"
echo "-----------------"
check_file "CLAUDE_TASKS.md" "CLAUDE_TASKS.md"
check_file "IMPLEMENT_THIS_NOW.md" "IMPLEMENT_THIS_NOW.md"
check_file "IMPLEMENT_NOW.md" "IMPLEMENT_NOW.md"
check_file "README_FOR_CLAUDE.md" "README_FOR_CLAUDE.md"
echo ""

# Check task directories
echo "📁 Task Directories:"
echo "-------------------"
for dir in ".claude-tasks" "ai-tasks" "TODO"; do
    if [ -d "$dir" ]; then
        count=$(find "$dir" -name "*.md" 2>/dev/null | wc -l | xargs)
        urgent_count=$(find "$dir" -name "*URGENT*" -o -name "*178*" -o -name "*180*" 2>/dev/null | wc -l | xargs)
        echo "✅ $dir/: $count files ($urgent_count urgent)"
        
        # List urgent files
        if [ $urgent_count -gt 0 ]; then
            find "$dir" -name "*URGENT*" -o -name "*178*" -o -name "*180*" 2>/dev/null | while read -r file; do
                echo "   - $(basename "$file")"
            done
        fi
    else
        echo "❌ $dir/: Not found"
    fi
done
echo ""

# Check GitHub issues
echo "🐙 GitHub Issues (ai-assigned):"
echo "-------------------------------"
if command -v gh &> /dev/null; then
    gh issue list --label "ai-assigned" --limit 5 --json number,title,isPinned,state | \
    jq -r '.[] | "   #\(.number): \(.title) [\(.state)]\(if .isPinned then " 📌" else "" end)"' 2>/dev/null || \
    echo "   Error fetching issues"
else
    echo "   GitHub CLI not available"
fi
echo ""

# Check recent workflow runs
echo "⚙️  Recent AI Workflow Runs:"
echo "---------------------------"
if command -v gh &> /dev/null; then
    gh run list --workflow "AI Task Handler" --limit 3 --json status,conclusion,createdAt,event | \
    jq -r '.[] | "   \(.createdAt | split("T")[0]): \(.status) - \(.conclusion // "running") (\(.event))"' 2>/dev/null || \
    echo "   No recent runs found"
else
    echo "   GitHub CLI not available"
fi
echo ""

# Check for Claude confirmation
echo "🔍 Claude Confirmation:"
echo "----------------------"
if [ -f "CLAUDE_CONFIRMED.md" ]; then
    mod_time=$(stat -f %m "CLAUDE_CONFIRMED.md" 2>/dev/null || stat -c %Y "CLAUDE_CONFIRMED.md" 2>/dev/null)
    current_time=$(date +%s)
    age_hours=$(( (current_time - mod_time) / 3600 ))
    echo "✅ Claude has confirmed visibility ($age_hours hours ago)"
else
    echo "⏳ Waiting for Claude confirmation (CLAUDE_CONFIRMED.md)"
fi
echo ""

# Summary
echo "📊 Summary:"
echo "-----------"
critical_count=$(ls CLAUDE_TASKS.md IMPLEMENT_THIS_NOW.md README_FOR_CLAUDE.md 2>/dev/null | wc -l | xargs)
task_count=$(find .claude-tasks ai-tasks -name "*.md" 2>/dev/null | wc -l | xargs)

echo "- Critical files present: $critical_count/3"
echo "- Total task files: $task_count"
echo "- System status: $([ $critical_count -ge 2 ] && echo "✅ READY" || echo "⚠️  NEEDS ATTENTION")"
echo ""

echo "💡 To test Claude pickup:"
echo "1. Run: python scripts/validate_claude_pickup.py"
echo "2. Check for CLAUDE_CAN_YOU_SEE_THIS.md"
echo "3. Wait for CLAUDE_CONFIRMED.md"