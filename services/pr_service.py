"""
Pull Request Service for Zamaz Debate System
Handles creation of GitHub PRs for decisions
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from domain.models import (
    DEFAULT_TEMPLATES,
    Debate,
    Decision,
    DecisionType,
    ImplementationAssignee,
    PullRequest,
)
from services.delegation_service import DelegationService
from services.implementation_planner import ImplementationPlanner


class PRService:
    """Service for creating and managing pull requests"""

    def __init__(self, repo_url: str = "https://github.com/lsendel/zamaz-debate"):
        self.repo_url = repo_url
        self.enabled = os.getenv("CREATE_PR_FOR_DECISIONS", "false").lower() == "true"
        self.auto_push = os.getenv("AUTO_PUSH_PR", "false").lower() == "true"
        self.assignee = os.getenv("PR_ASSIGNEE", "claude")
        self.base_branch = os.getenv("PR_BASE_BRANCH", "main")
        self.use_current_branch = os.getenv("PR_USE_CURRENT_BRANCH", "true").lower() == "true"
        self.delegation_service = DelegationService()
        self.implementation_planner = ImplementationPlanner()
        self.documentation_only = os.getenv("PR_DOCUMENTATION_ONLY", "true").lower() == "true"

        # Log initialization
        print(
            f"PRService initialized: use_current_branch={self.use_current_branch}, documentation_only={self.documentation_only}"
        )

    def should_create_pr(self, decision: Decision) -> bool:
        """Determine if a PR should be created for this decision"""
        if not self.enabled:
            return False

        # Create PRs for all decisions that reached consensus
        # Check if decision has consensus (assuming decisions from debates have consensus)
        return True  # Create PR for all decisions when PR creation is enabled

    async def create_pr_for_decision(
        self, decision: Decision, debate: Optional[Debate] = None
    ) -> Optional[PullRequest]:
        """Create a pull request for a decision"""
        if not self.enabled:
            return False

        # Generate PR content
        pr = self._generate_pr(decision, debate)

        if self.use_current_branch:
            # Get current branch name instead of creating a new one
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                current_branch = result.stdout.strip()
                pr.branch_name = current_branch
                print(f"✓ Using current branch: {current_branch}")
            except subprocess.CalledProcessError as e:
                print(f"Error getting current branch: {e}")
                return None
        else:
            # Create new branch (original behavior)
            branch_created = await self._create_branch(pr.branch_name)
            if not branch_created:
                return None

        # Skip git operations if auto_push is disabled
        if self.auto_push:
            # Add decision file
            await self._add_decision_file(decision, pr.branch_name)

            # Commit changes
            await self._commit_changes(pr, decision)

        if self.auto_push:
            # Push branch and create PR
            await self._push_and_create_pr(pr, decision, debate)
        else:
            # Just prepare the PR locally
            await self._save_pr_draft(pr)

        return pr

    def _generate_documentation_pr(self, decision: Decision, debate: Optional[Debate]) -> PullRequest:
        """Generate an enhanced documentation-only PR with multiple implementation approaches"""
        # Get implementation plans
        impl_plans = self.implementation_planner.generate_implementation_plans(decision, debate)

        # Build enhanced PR body
        pr_body = f"""# 📚 Implementation Documentation

## 📋 Summary

This is a **documentation-only PR** that provides multiple implementation approaches for the following decision.

**Decision Type:** `{decision.decision_type.value}` | **Method:** `{decision.method}` | **Complexity:** `{getattr(decision, 'complexity', 'complex')}`

---

## 🤔 The Question

**{decision.question}**

### Context
```
{decision.context}
```

---

## 💡 Decision

{decision.decision_text}

---

## 🎯 Implementation Approaches

This PR provides **{len(impl_plans['approaches'])} different implementation approaches** for human developers or Anthropic teams to choose from:

"""

        # Add each implementation approach
        for i, approach in enumerate(impl_plans["approaches"], 1):
            pr_body += f"""
### Approach {i}: {approach['name']}

**Description:** {approach['description']}

**Estimated Effort:** {approach['estimated_effort']}  
**Risk Level:** {approach['risk_level']}  
**Best For:** {approach['suitable_for']}

<details>
<summary>👍 Pros & 👎 Cons (click to expand)</summary>

**Pros:**
"""
            for pro in approach["pros"]:
                pr_body += f"- ✅ {pro}\n"

            pr_body += "\n**Cons:**\n"
            for con in approach["cons"]:
                pr_body += f"- ⚠️ {con}\n"

            pr_body += "\n</details>\n\n"

            # Add implementation steps
            pr_body += "<details>\n<summary>📝 Implementation Steps (click to expand)</summary>\n\n"

            for step in approach["steps"]:
                pr_body += f"**{step['phase']}** ({step['duration']})\n"
                for task in step["tasks"]:
                    pr_body += f"- {task}\n"
                pr_body += "\n"

            pr_body += "</details>\n"

            # Add specific details for DDD approach
            if "bounded_contexts" in approach:
                pr_body += "\n<details>\n<summary>🔷 Domain-Driven Design Details (click to expand)</summary>\n\n"
                pr_body += "**Bounded Contexts:**\n"
                for ctx in approach["bounded_contexts"]:
                    pr_body += f"- **{ctx['name']}**: {ctx['responsibility']}\n"
                    pr_body += f"  - Entities: {', '.join(ctx['entities'])}\n"

                if approach.get("aggregate_roots"):
                    pr_body += f"\n**Aggregate Roots:** {', '.join(approach['aggregate_roots'])}\n"

                if approach.get("domain_events"):
                    pr_body += f"\n**Domain Events:** {', '.join(approach['domain_events'])}\n"

                pr_body += "\n</details>\n"

            # Add event-driven details
            if "events" in approach:
                pr_body += "\n<details>\n<summary>📡 Event-Driven Architecture Details (click to expand)</summary>\n\n"
                pr_body += "**Key Events:**\n"
                for event in approach["events"][:5]:  # Show first 5 events
                    pr_body += f"- **{event['name']}**\n"
                    pr_body += f"  - Producers: {', '.join(event['producers'])}\n"
                    pr_body += f"  - Consumers: {', '.join(event['consumers'])}\n"
                pr_body += "\n</details>\n"

        # Add implementation checklist
        pr_body += "\n---\n\n## ✅ Implementation Checklist\n\n"

        for category in impl_plans["checklist"]:
            pr_body += f"\n**{category['category']}**\n"
            for item in category["items"]:
                pr_body += f"- [ ] {item}\n"

        # Add testing strategy
        pr_body += "\n---\n\n## 🧪 Testing Strategy\n\n"
        testing = impl_plans["testing_strategy"]

        for test_type, details in testing.items():
            pr_body += f"\n**{test_type.replace('_', ' ').title()}**\n"
            pr_body += f"- Focus: {details['focus']}\n"
            if "coverage_target" in details:
                pr_body += f"- Coverage Target: {details['coverage_target']}\n"
            if "tools" in details:
                pr_body += f"- Tools: {', '.join(details['tools'])}\n"

        # Add Anthropic best practices
        pr_body += "\n---\n\n## 🏆 Anthropic Best Practices\n\n"

        for practice in impl_plans["anthropic_best_practices"]:
            pr_body += f"**{practice['practice']}**\n"
            pr_body += f"- {practice['description']}\n"
            pr_body += f"- 💡 *Application:* {practice['application']}\n\n"

        # Add footer
        pr_body += f"""
---

## 🤝 How to Use This Documentation

1. **Choose an Approach**: Review the three implementation approaches above and select the one that best fits your needs
2. **Follow the Checklist**: Use the implementation checklist to ensure all aspects are covered
3. **Apply Best Practices**: Incorporate Anthropic's best practices throughout your implementation
4. **Test Thoroughly**: Follow the testing strategy to ensure quality

## 🚫 Important Note

This is a **documentation-only PR** that will be automatically closed after creation. The actual implementation should be done by:
- Human developers on the team
- Anthropic's implementation team
- Community contributors

The PR serves as a detailed specification and guide for whoever implements this feature.

---

*🤖 This documentation PR was automatically generated by the Zamaz Debate System*
*📝 Based on AI consensus from debate {debate.id if debate else 'N/A'}*
"""

        # Generate descriptive title
        title = self._generate_descriptive_title(
            decision,
            f"[Docs] {decision.decision_type.value.capitalize()} Implementation Guide",
        )

        # Branch name will be set later if using current branch
        if self.use_current_branch:
            branch_name = "current-branch-placeholder"
        else:
            branch_name = f"docs/{decision.decision_type.value}/{decision.id}"

        # Create the PR object
        return PullRequest(
            id=None,
            title=title,
            body=pr_body,
            branch_name=branch_name,
            base_branch=self.base_branch,
            assignee=os.getenv("HUMAN_GITHUB_USERNAME", "lsendel"),  # Assign to human
            labels=["documentation", "automated", "ai-generated"],
            decision=decision,
        )

    def _generate_pr(self, decision: Decision, debate: Optional[Debate]) -> PullRequest:
        """Generate a pull request from a decision"""
        # If documentation-only mode is enabled, generate enhanced documentation PR
        if self.documentation_only:
            return self._generate_documentation_pr(decision, debate)

        # Otherwise, use the original PR generation logic
        # Determine implementation assignment
        if decision.implementation_assignee:
            assignee_enum = decision.implementation_assignee
        else:
            (
                assignee_enum,
                impl_complexity,
            ) = self.delegation_service.determine_implementation_assignment(decision, debate)
            decision.implementation_assignee = assignee_enum
            decision.implementation_complexity = impl_complexity

        # Get assignee username
        assignee = self._get_assignee_username(assignee_enum)

        template = DEFAULT_TEMPLATES.get(decision.decision_type, DEFAULT_TEMPLATES[DecisionType.SIMPLE])

        pr_content = template.render(decision, debate)

        # Improve PR title based on decision content
        pr_content["title"] = self._generate_descriptive_title(decision, pr_content["title"])

        # Add implementation instructions to PR body
        if assignee_enum != ImplementationAssignee.NONE:
            impl_instructions = self.delegation_service.get_implementation_instructions(decision, assignee_enum)
            pr_content["body"] += f"\n\n---\n{impl_instructions}"

        # Determine reviewer based on implementer
        reviewer = self.delegation_service.determine_reviewer(assignee_enum)

        # Add workflow instructions
        pr_content["body"] += f"\n\n---\n## 👥 Workflow\n"
        if assignee_enum == ImplementationAssignee.CLAUDE:
            pr_content["body"] += f"1. **Implementation**: Assigned to @{assignee} (Claude)\n"
            pr_content["body"] += f"2. **Code Review**: @{reviewer} (Gemini) will review before merge\n"
            pr_content["body"] += f"3. **Merge**: After Gemini approves the implementation\n\n"
            pr_content["body"] += f"---\n\n@{assignee} Please implement this feature as specified above."
        elif assignee_enum == ImplementationAssignee.GEMINI:
            pr_content["body"] += f"1. **Implementation**: Assigned to @{assignee} (Gemini)\n"
            pr_content["body"] += f"2. **Code Review**: @{reviewer} (Codex) will review and commit\n"
            pr_content["body"] += f"3. **Merge**: Codex will handle the final merge\n\n"
            pr_content["body"] += f"---\n\n@{assignee} Please implement this feature as specified above."
        else:
            pr_content["body"] += f"1. **Implementation**: Assigned to @{assignee}\n"
            pr_content["body"] += f"2. **Review**: Manual review required\n\n"
            pr_content["body"] += f"---\n\n@{assignee} Please review and implement this request."

        # Branch name will be set later if using current branch
        if self.use_current_branch:
            branch_name = "current-branch-placeholder"
        else:
            branch_name = f"decision/{decision.decision_type.value}/{decision.id}"

        return PullRequest(
            id=None,
            title=pr_content["title"],
            body=pr_content["body"],
            branch_name=branch_name,
            base_branch=self.base_branch,
            assignee=assignee,
            labels=self._get_labels_for_decision(decision),
            decision=decision,
        )

    def _get_assignee_username(self, assignee: ImplementationAssignee) -> str:
        """Convert assignee enum to GitHub username"""
        if assignee == ImplementationAssignee.CLAUDE:
            return os.getenv("CLAUDE_GITHUB_USERNAME", "claude")
        elif assignee == ImplementationAssignee.GEMINI:
            return os.getenv("GEMINI_GITHUB_USERNAME", "gemini-bot")
        elif assignee == ImplementationAssignee.HUMAN:
            return os.getenv("HUMAN_GITHUB_USERNAME", "human")
        else:
            return "unassigned"

    def _generate_descriptive_title(self, decision: Decision, default_title: str) -> str:
        """Generate a more descriptive PR title based on decision content"""
        max_title_length = 100

        if decision.decision_type == DecisionType.EVOLUTION:
            # Extract key improvement from decision text
            decision_text = decision.decision_text.lower()

            # Common improvement patterns to look for
            if "testing" in decision_text or "test" in decision_text:
                feature = "Add comprehensive testing framework"
            elif "monitoring" in decision_text or "observability" in decision_text:
                feature = "Implement monitoring and observability"
            elif "error handling" in decision_text or "error" in decision_text:
                feature = "Improve error handling and recovery"
            elif "performance" in decision_text:
                feature = "Optimize system performance"
            elif "documentation" in decision_text or "docs" in decision_text:
                feature = "Enhance documentation"
            elif "security" in decision_text:
                feature = "Strengthen security measures"
            elif "refactor" in decision_text or "technical debt" in decision_text:
                feature = "Refactor and reduce technical debt"
            elif "api" in decision_text:
                feature = "Enhance API functionality"
            elif "ui" in decision_text or "interface" in decision_text:
                feature = "Improve user interface"
            elif "database" in decision_text or "persistence" in decision_text:
                feature = "Implement data persistence layer"
            elif "cache" in decision_text or "caching" in decision_text:
                feature = "Add caching system"
            elif "plugin" in decision_text:
                feature = "Implement plugin architecture"
            elif "logging" in decision_text:
                feature = "Add comprehensive logging system"
            else:
                # Try to extract first meaningful sentence
                lines = decision.decision_text.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 10 and not line.startswith("#"):
                        feature = line[:80] + "..." if len(line) > 80 else line
                        break
                else:
                    feature = "System improvement"

            return f"[Evolution] {feature}"[:max_title_length]

        elif decision.decision_type == DecisionType.COMPLEX:
            # For complex decisions, extract the core question
            question = decision.question
            # Remove common prefixes
            question = question.replace("What is the ONE most important improvement to make to", "Improve")
            question = question.replace("Should we", "")
            question = question.replace("How should we", "")
            question = question.strip()

            # Truncate if too long
            if len(question) > 70:
                question = question[:67] + "..."

            return f"[Complex] {question}"

        # For other types, use the default but ensure it's not too long
        if len(default_title) > max_title_length:
            return default_title[: max_title_length - 3] + "..."

        return default_title

    def _get_labels_for_decision(self, decision: Decision) -> List[str]:
        """Get appropriate labels for a decision"""
        labels = ["automated", "decision"]

        if decision.decision_type == DecisionType.EVOLUTION:
            labels.append("evolution")
        elif decision.decision_type == DecisionType.COMPLEX:
            labels.append("complex-decision")

        if decision.method == "debate":
            labels.append("ai-debate")

        # Add implementation labels
        if decision.implementation_assignee == ImplementationAssignee.GEMINI:
            labels.append("gemini-implementation")
        elif decision.implementation_assignee == ImplementationAssignee.HUMAN:
            labels.append("needs-human-review")

        if decision.implementation_complexity:
            labels.append(f"complexity-{decision.implementation_complexity}")

        return labels

    async def _create_branch(self, branch_name: str) -> bool:
        """Create a new git branch"""
        try:
            # First, ensure we're on the base branch
            subprocess.run(["git", "checkout", self.base_branch], check=True, capture_output=True)

            # Pull latest changes
            subprocess.run(
                ["git", "pull", "origin", self.base_branch],
                check=True,
                capture_output=True,
            )

            # Create and checkout new branch
            subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True)

            print(f"✓ Created branch: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating branch: {e}")
            return False

    async def _add_decision_file(self, decision: Decision, branch_name: str):
        """Add decision details to a file"""
        decisions_dir = Path(__file__).parent.parent / "data" / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)

        filename = decisions_dir / f"{decision.id}.json"

        with open(filename, "w") as f:
            json.dump(decision.to_dict(), f, indent=2)

        # Stage the file
        try:
            subprocess.run(["git", "add", str(filename)], check=True, capture_output=True)
            print(f"✓ Staged file: {filename}")
        except subprocess.CalledProcessError as e:
            print(f"Error staging file: {e}")

    async def _commit_changes(self, pr: PullRequest, decision: Decision):
        """Commit changes for the PR"""
        commit_message = f"""Add decision: {decision.question[:60]}

Decision type: {decision.decision_type.value}
Method: {decision.method}
Timestamp: {decision.timestamp.isoformat()}

This commit was automatically generated by the Zamaz Debate System.
"""

        try:
            subprocess.run(["git", "commit", "-m", commit_message], check=True, capture_output=True)
            print(f"✓ Committed changes")
        except subprocess.CalledProcessError as e:
            print(f"Error committing: {e}")

    async def _push_and_create_pr(self, pr: PullRequest, decision: Decision, debate: Optional[Debate] = None):
        """Push branch and create PR using gh CLI"""
        try:
            # Push the current branch (without -u since it might already be tracked)
            subprocess.run(
                ["git", "push", "origin", pr.branch_name],
                check=True,
                capture_output=True,
            )

            # Create PR using gh CLI
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    pr.title,
                    "--body",
                    pr.body,
                    "--base",
                    pr.base_branch,
                    "--assignee",
                    pr.assignee,
                    "--label",
                    ",".join(pr.labels),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            # Extract PR URL from output
            pr_url = result.stdout.strip()
            print(f"Created PR: {pr_url}")

            # Extract PR number from URL and set it on the PR object
            pr_number = pr_url.split("/")[-1]
            pr.id = pr_number

            # If this is a documentation-only PR, auto-close it
            if self.documentation_only:
                try:
                    print(f"Auto-closing documentation PR #{pr_number}")
                    subprocess.run(
                        [
                            "gh",
                            "pr",
                            "close",
                            pr_number,
                            "--comment",
                            "This documentation-only PR has been automatically closed. The implementation guide is now available for human developers or Anthropic teams to use.",
                        ],
                        check=True,
                        capture_output=True,
                    )
                    print(f"✓ Documentation PR #{pr_number} closed")

                except subprocess.CalledProcessError as e:
                    print(f"Warning: Could not auto-close PR: {e}")
            
            # Create implementation issue for all complex decisions
            if decision.decision_type in [DecisionType.COMPLEX, DecisionType.EVOLUTION]:
                await self._create_implementation_issue(pr, decision, debate)

            # Add Gemini as reviewer (only for non-documentation PRs)
            if not self.documentation_only:
                gemini_reviewer = os.getenv("GEMINI_GITHUB_USERNAME", "gemini-bot")
                if gemini_reviewer and gemini_reviewer != pr.assignee:
                    try:
                        subprocess.run(
                            [
                                "gh",
                                "pr",
                                "edit",
                                pr_number,
                                "--add-reviewer",
                                gemini_reviewer,
                            ],
                            check=True,
                            capture_output=True,
                        )
                        print(f"Added {gemini_reviewer} as reviewer")
                    except subprocess.CalledProcessError:
                        print(f"Note: Could not add {gemini_reviewer} as reviewer (user may not exist)")

        except subprocess.CalledProcessError as e:
            print(f"Failed to create PR: {e}")
            if e.stderr:
                print(f"Error: {e.stderr}")

    async def _create_implementation_issue(self, pr: PullRequest, decision: Decision, debate: Optional[Debate] = None):
        """Create GitHub issue for implementation after documentation PR is closed"""
        try:
            # Determine assignee based on complexity
            assignee = "claude"  # Always assign to Claude as requested

            # Create issue title
            issue_title = f"Implement: {decision.question[:100]}"
            if len(decision.question) > 100:
                issue_title += "..."

            # Create issue body with implementation details
            issue_body = f"""## Implementation Task

This issue was automatically created from the documentation PR #{pr.id}.

### Original Question
{decision.question}

### Context
{decision.context or "No additional context provided"}

### Decision Type
- **Type**: {decision.decision_type.value}
- **Method**: {decision.method}
- **Complexity**: {getattr(decision, 'complexity', 'complex')}

### Implementation Guide
Please refer to the closed documentation PR #{pr.id} for detailed implementation approaches and guidelines.

### Assignee
This task is assigned to @{assignee} for implementation.

### Labels
- `ai-assigned`: This issue is assigned to AI for implementation
- `{decision.decision_type.value}`: Decision type
- `implementation`: This is an implementation task

### Related Resources
- Documentation PR: #{pr.id}
- Decision ID: {decision.id}
{f"- Debate ID: {debate.id}" if debate else ""}

---
*This issue was automatically generated by the Zamaz Debate System*
"""

            # Create the issue using gh CLI
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "--title",
                    issue_title,
                    "--body",
                    issue_body,
                    "--assignee",
                    assignee,
                    "--label",
                    "ai-assigned,implementation",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            # Extract issue URL from output
            issue_url = result.stdout.strip()
            issue_number = issue_url.split("/")[-1]

            print(f"✓ Created implementation issue #{issue_number}")
            print(f"  URL: {issue_url}")
            print(f"  Assigned to: @{assignee}")

        except subprocess.CalledProcessError as e:
            print(f"Error creating implementation issue: {e}")
            if e.stderr:
                print(f"Error details: {e.stderr}")

    async def _save_pr_draft(self, pr: PullRequest):
        """Save PR draft locally for manual creation"""
        pr_drafts_dir = Path(__file__).parent.parent / "data" / "pr_drafts"
        pr_drafts_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON metadata
        draft_file = pr_drafts_dir / f"{pr.branch_name.replace('/', '_')}.json"
        with open(draft_file, "w") as f:
            json.dump(
                {
                    "branch": pr.branch_name,
                    "title": pr.title,
                    "body": pr.body,
                    "base": pr.base_branch,
                    "assignee": pr.assignee,
                    "reviewer": os.getenv("GEMINI_GITHUB_USERNAME", "gemini-bot"),
                    "labels": pr.labels,
                    "created_at": datetime.now().isoformat(),
                    "workflow": "Claude implements, Gemini reviews before merge",
                },
                f,
                indent=2,
            )

        # Save markdown body separately
        body_file = pr_drafts_dir / f"{pr.branch_name.replace('/', '_')}_body.md"
        with open(body_file, "w") as f:
            f.write(pr.body)

        print(f"PR draft saved to: {draft_file}")
        print(f"To create PR manually, run:")
        print(f"git push -u origin {pr.branch_name}")
        print(f'gh pr create --title "{pr.title}" --body-file {body_file} --assignee {pr.assignee}')


class PRRepository:
    """Repository for storing and retrieving PR information"""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent / "data" / "pr_history"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_pr(self, pr: PullRequest):
        """Save PR information"""
        filename = self.storage_dir / f"{pr.branch_name.replace('/', '_')}.json"

        with open(filename, "w") as f:
            json.dump(
                {
                    "id": pr.id,
                    "title": pr.title,
                    "body": pr.body,
                    "branch_name": pr.branch_name,
                    "base_branch": pr.base_branch,
                    "assignee": pr.assignee,
                    "labels": pr.labels,
                    "status": pr.status.value,
                    "created_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def get_prs_for_decision_type(self, decision_type: DecisionType) -> List[Dict]:
        """Get all PRs for a specific decision type"""
        prs = []

        for file in self.storage_dir.glob("*.json"):
            with open(file, "r") as f:
                pr_data = json.load(f)
                if decision_type.value in pr_data.get("branch_name", ""):
                    prs.append(pr_data)

        return prs
