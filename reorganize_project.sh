#!/bin/bash
# Script to reorganize the project structure

echo "🔧 Reorganizing Zamaz Debate System project structure..."

# Create all necessary directories
echo "📁 Creating directory structure..."
mkdir -p src/{core,web,utils}
mkdir -p data/{debates,evolutions,decisions,pr_drafts,pr_history,ai_cache,localhost_checks}
mkdir -p docs/examples
mkdir -p config
mkdir -p scripts

# Move core files
echo "📦 Moving core files..."
mv nucleus.py src/core/ 2>/dev/null || echo "  ⚠️  nucleus.py already moved or missing"
mv evolution_tracker.py src/core/ 2>/dev/null || echo "  ⚠️  evolution_tracker.py already moved or missing"

# Move web files
echo "🌐 Moving web files..."
mv web_interface.py src/web/app.py 2>/dev/null || echo "  ⚠️  web_interface.py already moved or missing"
mv static src/web/ 2>/dev/null || echo "  ⚠️  static/ already moved or missing"

# Move utils
echo "🛠️  Moving utility files..."
mv bootstrap.py src/utils/ 2>/dev/null || echo "  ⚠️  bootstrap.py already moved or missing"
mv check_localhost.py src/utils/localhost_checker.py 2>/dev/null || echo "  ⚠️  check_localhost.py already moved or missing"
mv self_improve.py src/utils/ 2>/dev/null || echo "  ⚠️  self_improve.py already moved or missing"
mv track_evolution.py src/utils/ 2>/dev/null || echo "  ⚠️  track_evolution.py already moved or missing"

# Move data directories
echo "💾 Moving data directories..."
mv debates/* data/debates/ 2>/dev/null || echo "  ⚠️  No debates to move"
mv evolutions/* data/evolutions/ 2>/dev/null || echo "  ⚠️  No evolutions to move"
mv decisions/* data/decisions/ 2>/dev/null || echo "  ⚠️  No decisions to move"
mv pr_drafts/* data/pr_drafts/ 2>/dev/null || echo "  ⚠️  No pr_drafts to move"
mv pr_history/* data/pr_history/ 2>/dev/null || echo "  ⚠️  No pr_history to move"
mv ai_cache/* data/ai_cache/ 2>/dev/null || echo "  ⚠️  No ai_cache to move"
mv localhost_checks/* data/localhost_checks/ 2>/dev/null || echo "  ⚠️  No localhost_checks to move"

# Move documentation
echo "📚 Moving documentation..."
mv CLAUDE.md docs/ 2>/dev/null || echo "  ⚠️  CLAUDE.md already moved or missing"
mv CLAUDE_AI_INTEGRATION.md docs/ 2>/dev/null || echo "  ⚠️  CLAUDE_AI_INTEGRATION.md already moved or missing"
mv COST_SAVING_GUIDE.md docs/ 2>/dev/null || echo "  ⚠️  COST_SAVING_GUIDE.md already moved or missing"
mv SECURITY.md docs/ 2>/dev/null || echo "  ⚠️  SECURITY.md already moved or missing"
mv QUICKSTART.md docs/ 2>/dev/null || echo "  ⚠️  QUICKSTART.md already moved or missing"
mv IMPLEMENTATION_PLAN.md docs/ 2>/dev/null || echo "  ⚠️  IMPLEMENTATION_PLAN.md already moved or missing"
mv TECHNICAL_ROADMAP.md docs/ 2>/dev/null || echo "  ⚠️  TECHNICAL_ROADMAP.md already moved or missing"
mv examples/* docs/examples/ 2>/dev/null || echo "  ⚠️  No examples to move"

# Move scripts
echo "🚀 Moving scripts..."
mv bootstrap_project.py scripts/ 2>/dev/null || echo "  ⚠️  bootstrap_project.py already moved or missing"
mv scripts/manual_debate.py scripts/manual_debate_temp.py 2>/dev/null
mv manual_debate.py scripts/ 2>/dev/null || echo "  ⚠️  manual_debate.py already moved or missing"
mv scripts/manual_debate_temp.py scripts/manual_debate.py 2>/dev/null
mv audit_project.sh scripts/ 2>/dev/null || echo "  ⚠️  audit_project.sh already moved or missing"

# Move config files
echo "⚙️  Moving configuration files..."
mv .env config/ 2>/dev/null || echo "  ⚠️  .env already moved or missing"
mv .env.example config/ 2>/dev/null || echo "  ⚠️  .env.example already moved or missing"

# Create symlinks for compatibility
echo "🔗 Creating compatibility symlinks..."
ln -sf config/.env .env 2>/dev/null || echo "  ⚠️  .env symlink already exists"
ln -sf config/.env.example .env.example 2>/dev/null || echo "  ⚠️  .env.example symlink already exists"

# Create __init__.py files
echo "🐍 Creating __init__.py files..."
touch src/__init__.py
touch src/core/__init__.py
touch src/web/__init__.py
touch src/utils/__init__.py

# Clean up empty directories
echo "🧹 Cleaning up empty directories..."
rmdir debates evolutions decisions pr_drafts pr_history ai_cache localhost_checks examples 2>/dev/null || true

echo "✅ Project reorganization complete!"
echo ""
echo "📋 New structure:"
echo "  src/          - All source code"
echo "    core/       - Core business logic"
echo "    web/        - Web interface"
echo "    utils/      - Utilities"
echo "    domain/     - Domain models"
echo "    services/   - Services"
echo "  data/         - All data files"
echo "  docs/         - All documentation"
echo "  config/       - Configuration files"
echo "  scripts/      - Executable scripts"
echo "  tests/        - Test files"
echo ""
echo "⚠️  Note: You'll need to update imports in Python files!"
