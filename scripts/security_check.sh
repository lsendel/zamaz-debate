#!/bin/bash
# Security check script for Zamaz Debate System

echo "🔐 Running security audit..."
echo "============================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

errors=0
warnings=0

# Check if .env exists and has proper permissions
if [ -f .env ]; then
    perms=$(stat -f "%Lp" .env 2>/dev/null || stat -c "%a" .env 2>/dev/null)
    if [ "$perms" != "600" ] && [ "$perms" != "644" ]; then
        echo -e "${YELLOW}⚠️  Warning: .env has permissive permissions ($perms)${NC}"
        echo "   Consider running: chmod 600 .env"
        ((warnings++))
    fi
fi

# Check for exposed API keys in code
echo -e "\n📝 Checking source files for secrets..."
found_keys=0

for file in $(find . -name "*.py" -o -name "*.js" -o -name "*.json" | grep -v venv | grep -v node_modules); do
    if grep -l "sk-ant-api" "$file" 2>/dev/null | grep -v ".env.example"; then
        echo -e "${RED}❌ Found Anthropic API key in: $file${NC}"
        ((errors++))
        found_keys=1
    fi
    
    if grep -l "AIza[a-zA-Z0-9_-]{35}" "$file" 2>/dev/null | grep -v ".env.example"; then
        echo -e "${RED}❌ Found Google API key in: $file${NC}"
        ((errors++))
        found_keys=1
    fi
done

if [ $found_keys -eq 0 ]; then
    echo -e "${GREEN}✅ No API keys found in source files${NC}"
fi

# Check .gitignore
echo -e "\n📋 Checking .gitignore..."
required_entries=(".env" "*.pem" "*.key" "credentials.json" "secrets.json")
missing_entries=()

for entry in "${required_entries[@]}"; do
    if ! grep -q "^$entry" .gitignore 2>/dev/null; then
        missing_entries+=("$entry")
    fi
done

if [ ${#missing_entries[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ .gitignore properly configured${NC}"
else
    echo -e "${YELLOW}⚠️  Missing entries in .gitignore:${NC}"
    for entry in "${missing_entries[@]}"; do
        echo "   - $entry"
        ((warnings++))
    done
fi

# Check for sensitive files that shouldn't exist
echo -e "\n🔍 Checking for sensitive files..."
sensitive_files=(
    "config.json"
    "secrets.json"
    "credentials.json"
    "*.pem"
    "*.key"
    "*.cert"
)

found_sensitive=0
for pattern in "${sensitive_files[@]}"; do
    files=$(find . -name "$pattern" -not -path "./venv/*" -not -path "./.git/*" 2>/dev/null)
    if [ ! -z "$files" ]; then
        echo -e "${RED}❌ Found sensitive file: $files${NC}"
        ((errors++))
        found_sensitive=1
    fi
done

if [ $found_sensitive -eq 0 ]; then
    echo -e "${GREEN}✅ No sensitive files found${NC}"
fi

# Check git history for secrets (last 10 commits)
echo -e "\n📜 Checking recent git history..."
if command -v git &> /dev/null; then
    if git rev-parse --git-dir > /dev/null 2>&1; then
        found_in_history=0
        
        # Check last 10 commits
        commits=$(git log --oneline -n 10 --format="%H" 2>/dev/null)
        
        for commit in $commits; do
            if git show "$commit" | grep -E "(sk-ant-api|AIza[a-zA-Z0-9_-]{35})" 2>/dev/null | head -1; then
                echo -e "${RED}❌ Found potential secret in commit: $commit${NC}"
                ((errors++))
                found_in_history=1
                break
            fi
        done
        
        if [ $found_in_history -eq 0 ]; then
            echo -e "${GREEN}✅ No secrets found in recent history${NC}"
        fi
    fi
fi

# Summary
echo -e "\n============================="
echo "Security Audit Summary"
echo "============================="

if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
    echo -e "${GREEN}✅ All security checks passed!${NC}"
    exit 0
else
    echo -e "Errors: ${RED}$errors${NC}"
    echo -e "Warnings: ${YELLOW}$warnings${NC}"
    
    if [ $errors -gt 0 ]; then
        echo -e "\n${RED}❌ Security issues found. Please fix before committing.${NC}"
        exit 1
    else
        echo -e "\n${YELLOW}⚠️  Warnings found. Consider addressing them.${NC}"
        exit 0
    fi
fi