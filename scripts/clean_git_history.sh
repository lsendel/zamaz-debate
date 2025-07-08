#!/bin/bash
# Script to clean sensitive data from git history
# USE WITH CAUTION - This rewrites git history!

echo "⚠️  WARNING: This script will rewrite git history!"
echo "Make sure you have a backup before proceeding."
echo ""
read -p "Are you sure you want to continue? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

# Patterns to remove
patterns=(
    "sk-ant-api"
    "AIza[a-zA-Z0-9_-]{35}"
    "ANTHROPIC_API_KEY=.*"
    "GOOGLE_API_KEY=.*"
)

echo "🔍 Searching for sensitive patterns in history..."

# Use BFG Repo-Cleaner if available
if command -v bfg &> /dev/null; then
    echo "Using BFG Repo-Cleaner..."
    
    # Create a file with patterns
    echo "Creating patterns file..."
    cat > .bfg-patterns.txt << EOF
sk-ant-api*
AIza*
*_API_KEY=*
EOF
    
    # Run BFG
    bfg --replace-text .bfg-patterns.txt
    
    # Clean up
    rm .bfg-patterns.txt
    
else
    echo "BFG not found. Using git filter-branch (slower)..."
    
    # Create a script to filter content
    cat > .filter-script.sh << 'EOF'
#!/bin/bash
sed -e 's/sk-ant-api[a-zA-Z0-9_-]*/REDACTED_ANTHROPIC_KEY/g' \
    -e 's/AIza[a-zA-Z0-9_-]{35}/REDACTED_GOOGLE_KEY/g' \
    -e 's/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=REDACTED/g' \
    -e 's/GOOGLE_API_KEY=.*/GOOGLE_API_KEY=REDACTED/g'
EOF
    
    chmod +x .filter-script.sh
    
    # Run filter-branch
    git filter-branch --tree-filter '
        find . -type f -name "*.py" -o -name "*.json" -o -name "*.md" -o -name ".env*" | \
        while read file; do
            if [ -f "$file" ]; then
                ./.filter-script.sh < "$file" > "$file.tmp" && mv "$file.tmp" "$file"
            fi
        done
    ' --tag-name-filter cat -- --all
    
    # Clean up
    rm .filter-script.sh
fi

echo ""
echo "✅ Git history cleaned."
echo ""
echo "Next steps:"
echo "1. Review the changes: git log --all --full-history"
echo "2. Force push to remote: git push --force --all"
echo "3. Tell all collaborators to re-clone the repository"
echo ""
echo "⚠️  IMPORTANT: Anyone who has the old history can still access the removed data."
echo "   Consider rotating any exposed API keys immediately!"