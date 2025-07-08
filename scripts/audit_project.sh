#!/bin/bash

echo "🔍 Auditing zamaz-debate project..."
echo "================================="
echo ""

# Define required files
REQUIRED_FILES=(
    "README.md"
    "bootstrap.py"
    "requirements.txt"
    ".env.example"
    ".gitignore"
    "LICENSE"
    "IMPLEMENTATION_PLAN.md"
    "TECHNICAL_ROADMAP.md"
    "track_evolution.py"
)

# Define optional but recommended files
OPTIONAL_FILES=(
    "nucleus.py"
    ".env"
    "evolution_history.json"
    "tests/test_nucleus.py"
    "tests/__init__.py"
)

echo "📋 Required Files Status:"
echo "------------------------"
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - EXISTS"
    else
        echo "❌ $file - MISSING"
    fi
done

echo ""
echo "📋 Optional Files Status:"
echo "------------------------"
for file in "${OPTIONAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - EXISTS"
    else
        echo "⚪ $file - NOT CREATED YET (OK)"
    fi
done

echo ""
echo "📁 Directory Structure:"
echo "---------------------"
if [ -d "tests" ]; then
    echo "✅ tests/ - EXISTS"
else
    echo "❌ tests/ - MISSING"
fi

if [ -d "debates" ]; then
    echo "✅ debates/ - EXISTS"
else
    echo "⚪ debates/ - NOT CREATED YET (OK - created on first use)"
fi

if [ -d "evolutions" ]; then
    echo "✅ evolutions/ - EXISTS"
else
    echo "⚪ evolutions/ - NOT CREATED YET (OK - created on first use)"
fi

echo ""
echo "🔍 Checking file contents..."
echo "----------------------------"

# Check if bootstrap.py has content
if [ -f "bootstrap.py" ]; then
    lines=$(wc -l < bootstrap.py)
    if [ $lines -gt 10 ]; then
        echo "✅ bootstrap.py has content ($lines lines)"
    else
        echo "⚠️  bootstrap.py seems empty or minimal"
    fi
fi

# Check if requirements.txt has the required packages
if [ -f "requirements.txt" ]; then
    echo ""
    echo "📦 Requirements.txt contains:"
    cat requirements.txt
fi

echo ""
echo "📊 Project Statistics:"
echo "--------------------"
echo "Total Python files: $(find . -name "*.py" -type f | wc -l)"
echo "Total Markdown files: $(find . -name "*.md" -type f | wc -l)"
echo "Total files tracked by git: $(git ls-files | wc -l)"

echo ""
echo "🔄 Git Status:"
echo "-------------"
git status --short

echo ""
echo "📝 Next Steps:"
echo "-------------"
# Check what's missing and suggest next steps
if [ ! -f ".env" ]; then
    echo "1. Create .env file: cp .env.example .env"
    echo "2. Add your API keys to .env"
fi

if [ ! -f "nucleus.py" ]; then
    echo "3. Run bootstrap.py to create nucleus.py"
fi

if [ ! -d "venv" ]; then
    echo "4. Create virtual environment: python -m venv venv"
    echo "5. Activate it: source venv/bin/activate"
    echo "6. Install dependencies: pip install -r requirements.txt"
fi
