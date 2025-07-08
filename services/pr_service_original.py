"""
Pull Request Service for Zamaz Debate System
Handles creation of GitHub PRs for decisions
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from domain.models import (
    Decision,
    Debate,
    PullRequest,
    DecisionType,
    DEFAULT_TEMPLATES,
    ImplementationAssignee,
)
from services.delegation_service import DelegationService


class PRService:
    """Service for creating and managing pull requests"""

    def __init__(self, repo_url: str = "https://github.com/lsendel/zamaz-debate"):
        self.repo_url = repo_url
        self.enabled = os.getenv("CREATE_PR_FOR_DECISIONS", "false").lower() == "true"
        self.auto_push = os.getenv("AUTO_PUSH_PR", "false").lower() == "true"
        self.assignee = os.getenv("PR_ASSIGNEE", "claude")
        self.base_branch = os.getenv("PR_BASE_BRANCH", "main")
        self.delegation_service = DelegationService()

    def should_create_pr(self, decision: Decision) -> bool:
        """Determine if a PR should be created for this decision"""
        if not self.enabled:
            return False

        # Create PRs for complex decisions and evolutions
        return decision.decision_type in [DecisionType.COMPLEX, DecisionType.EVOLUTION]

    async def create_pr_for_decision(
        self, decision: Decision, debate: Optional[Debate] = None
    ) -> Optional[PullRequest]:
        """Create a pull request for a decision"""
        if not self.enabled:
            return False

        # Generate PR content
        pr = self._generate_pr(decision, debate)

        # Create branch and files
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
            await self._push_and_create_pr(pr)
        else:
            # Just prepare the PR locally
            await self._save_pr_draft(pr)

        return pr

    def _generate_pr(self, decision: Decision, debate: Optional[Debate]) -> PullRequest:
        """Generate a pull request from a decision"""
        # Determine implementation assignment
        if decision.implementation_assignee:
            assignee_enum = decision.implementation_assignee
        else:
            assignee_enum, impl_complexity = (
                self.delegation_service.determine_implementation_assignment(
                    decision, debate
                )
            )
            decision.implementation_assignee = assignee_enum
            decision.implementation_complexity = impl_complexity

        # Get assignee username
        assignee = self._get_assignee_username(assignee_enum)

        template = DEFAULT_TEMPLATES.get(
            decision.decision_type, DEFAULT_TEMPLATES[DecisionType.SIMPLE]
        )

        pr_content = template.render(decision, debate)

        # Add implementation instructions to PR body
        if assignee_enum != ImplementationAssignee.NONE:
            impl_instructions = self.delegation_service.get_implementation_instructions(
                decision, assignee_enum
            )
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
            subprocess.run(
                ["git", "checkout", self.base_branch],
                check=True,
                capture_output=True
            )
            
            # Pull latest changes
            subprocess.run(
                ["git", "pull", "origin", self.base_branch],
                check=True,
                capture_output=True
            )
            
            # Create and checkout new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                check=True,
                capture_output=True
            )
            
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
            subprocess.run(
                ["git", "add", str(filename)],
                check=True,
                capture_output=True
            )
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
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True,
                capture_output=True
            )
            print(f"✓ Committed changes")
        except subprocess.CalledProcessError as e:
            print(f"Error committing: {e}")

    async def _push_and_create_pr(self, pr: PullRequest):
        """Push branch and create PR using gh CLI"""
        try:
            # Push the branch
            subprocess.run(
                ["git", "push", "-u", "origin", pr.branch_name],
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
            
            # Add Gemini as reviewer
            gemini_reviewer = os.getenv("GEMINI_GITHUB_USERNAME", "gemini-bot")
            if gemini_reviewer and gemini_reviewer != pr.assignee:
                try:
                    # Extract PR number from URL
                    pr_number = pr_url.split("/")[-1]
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
