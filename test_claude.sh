#!/bin/bash
# Quick test to validate Claude can pick up tasks

echo "🤖 Testing Claude Task Pickup System..."
echo "======================================"
echo ""

# Run validation
echo "1️⃣ Running validation..."
python3 scripts/validate_claude_pickup.py

echo ""
echo "2️⃣ Current task status..."
echo "=========================="

# Show urgent tasks
echo "📌 Urgent Tasks:"
find . -name "*URGENT*" -o -name "*178*" -o -name "*180*" | grep -E "\.(md|txt)$" | grep -v ".git" | head -10

echo ""
echo "3️⃣ Checking for Claude confirmation..."
echo "======================================"

if [ -f "CLAUDE_CONFIRMED.md" ]; then
    echo "✅ Claude has confirmed task visibility!"
    echo "Last confirmed: $(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" CLAUDE_CONFIRMED.md 2>/dev/null || stat -c "%y" CLAUDE_CONFIRMED.md 2>/dev/null)"
else
    echo "⏳ Waiting for Claude to confirm (CLAUDE_CONFIRMED.md not found)"
    echo ""
    echo "👉 Claude should create CLAUDE_CONFIRMED.md when tasks are seen"
fi

echo ""
echo "📊 Quick Summary:"
echo "================"
[ -f "CLAUDE_TASKS.md" ] && echo "✅ CLAUDE_TASKS.md exists" || echo "❌ CLAUDE_TASKS.md missing"
[ -f "IMPLEMENT_NOW.md" ] && echo "✅ IMPLEMENT_NOW.md exists" || echo "❌ IMPLEMENT_NOW.md missing"
[ -d ".claude-tasks" ] && echo "✅ .claude-tasks/ directory exists" || echo "❌ .claude-tasks/ missing"
[ -f "CLAUDE_CAN_YOU_SEE_THIS.md" ] && echo "✅ Visibility test file exists" || echo "❌ Visibility test file missing"

echo ""
echo "🚀 To create a new test issue:"
echo "gh issue create --title 'Test: Sample task' --body 'Claude, please implement this' --label 'ai-assigned'"