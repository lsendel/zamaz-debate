#!/bin/bash
# Complete PR creation script for template rendering decision

set -e

echo "Creating PR for template rendering decision..."

# Create a new branch
BRANCH_NAME="docs/complex/template-rendering-decision"
echo "Creating branch: $BRANCH_NAME"
git checkout -b $BRANCH_NAME

# Create a dummy commit to allow PR creation
echo "# Template Rendering Decision" > TEMPLATE_RENDERING_DECISION.md
echo "" >> TEMPLATE_RENDERING_DECISION.md
echo "This decision was made via AI debate and requires implementation." >> TEMPLATE_RENDERING_DECISION.md
echo "" >> TEMPLATE_RENDERING_DECISION.md
echo "See the PR description for detailed implementation approaches." >> TEMPLATE_RENDERING_DECISION.md

git add TEMPLATE_RENDERING_DECISION.md
git commit -m "Add template rendering decision documentation"

# Push the branch
echo "Pushing branch to origin..."
git push -u origin $BRANCH_NAME

# Create the PR using the saved draft
echo "Creating PR..."
gh pr create \
  --title "[Docs] Complex Implementation Guide" \
  --body-file /Users/lsendel/IdeaProjects/zamaz-debate/data/pr_drafts/main_body.md \
  --base main \
  --assignee lsendel \
  --label "documentation,automated,ai-generated,complex-decision,ai-debate"

echo "✅ PR created successfully!"
echo ""
echo "The PR will be automatically closed and an implementation issue will be created."