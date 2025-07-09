"""
PR Review Service for Zamaz Debate System
Handles PR reviews and automatic merging based on reviewer decisions
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from domain.models import ImplementationAssignee, PullRequest
from services.ai_client_factory import AIClientFactory


class PRReviewService:
    """Service for reviewing PRs and merging them if approved"""

    def __init__(self):
        self.ai_factory = AIClientFactory()
        self.reviews_dir = Path(__file__).parent.parent / "data" / "pr_reviews"
        self.reviews_dir.mkdir(parents=True, exist_ok=True)

    async def review_pr(
        self, pr: PullRequest, implementation_code: str, reviewer: str
    ) -> Dict[str, Any]:
        """
        Review a PR based on who the reviewer is

        Args:
            pr: The pull request to review
            implementation_code: The code changes to review
            reviewer: Who is reviewing (gemini-bot, codex, human)

        Returns:
            Review result with approval status and feedback
        """

        if reviewer == "gemini-bot":
            # Gemini reviews Claude's work
            return await self._gemini_review(pr, implementation_code)
        elif reviewer == "codex":
            # Codex reviews Gemini's work
            return await self._codex_review(pr, implementation_code)
        else:
            # Human review required
            return self._request_human_review(pr)

    async def _gemini_review(
        self, pr: PullRequest, implementation_code: str
    ) -> Dict[str, Any]:
        """Gemini reviews Claude's implementation"""

        # Get Gemini client
        gemini_client = self.ai_factory.get_gemini_client()

        prompt = f"""You are reviewing a pull request implementation by Claude.

PR Title: {pr.title}
PR Description: {pr.body[:500]}...

Implementation Code:
```
{implementation_code}
```

Please review this implementation critically:
1. Does it correctly implement the decision?
2. Are there any bugs or edge cases not handled?
3. Is the code quality acceptable (naming, structure, documentation)?
4. Are there security concerns?
5. Is it production-ready?

Provide your review with:
- APPROVED: If the code is ready to merge
- CHANGES_REQUESTED: If modifications are needed
- Specific feedback on what needs to be fixed (if any)
"""

        try:
            response = gemini_client.generate_content(prompt)
            review_text = response.text

            # Parse review decision
            approved = (
                "APPROVED" in review_text and "CHANGES_REQUESTED" not in review_text
            )

            review_result = {
                "reviewer": "gemini-bot",
                "status": "approved" if approved else "changes_requested",
                "feedback": review_text,
                "timestamp": datetime.now().isoformat(),
                "pr_id": pr.id,
                "can_merge": approved,
            }

            # Save review
            self._save_review(pr.id, review_result)

            return review_result

        except Exception as e:
            return {
                "reviewer": "gemini-bot",
                "status": "error",
                "feedback": f"Review failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "can_merge": False,
            }

    async def _codex_review(
        self, pr: PullRequest, implementation_code: str
    ) -> Dict[str, Any]:
        """Codex reviews Gemini's implementation and can merge"""

        # For now, Codex uses Claude as the review engine
        claude_client = self.ai_factory.get_claude_client()

        prompt = f"""You are Codex, reviewing a pull request implementation by Gemini.

PR Title: {pr.title}
PR Description: {pr.body[:500]}...

Implementation Code:
```
{implementation_code}
```

As Codex, you have the authority to merge this PR if it meets quality standards.

Please review this implementation:
1. Is the implementation correct and complete?
2. Code quality and best practices?
3. Error handling and edge cases?
4. Performance considerations?
5. Testing requirements met?

Provide your review with:
- APPROVED_AND_MERGE: If ready to merge immediately
- CHANGES_REQUESTED: If modifications needed
- Detailed feedback

Be thorough but practical. If the code is good enough for production, approve and merge.
"""

        try:
            response = claude_client.messages.create(
                model="claude-opus-4-20250514",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
            )
            review_text = response.content[0].text

            # Parse review decision
            merge_approved = "APPROVED_AND_MERGE" in review_text
            changes_needed = "CHANGES_REQUESTED" in review_text

            review_result = {
                "reviewer": "codex",
                "status": "approved_merge" if merge_approved else "changes_requested",
                "feedback": review_text,
                "timestamp": datetime.now().isoformat(),
                "pr_id": pr.id,
                "can_merge": merge_approved,
                "will_merge": merge_approved,  # Codex auto-merges if approved
            }

            # Save review
            self._save_review(pr.id, review_result)

            # If approved by Codex, merge the PR
            if merge_approved:
                merge_result = await self.merge_pr(pr, review_result)
                review_result["merge_result"] = merge_result

            return review_result

        except Exception as e:
            return {
                "reviewer": "codex",
                "status": "error",
                "feedback": f"Review failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "can_merge": False,
            }

    def _request_human_review(self, pr: PullRequest) -> Dict[str, Any]:
        """Request human review for special cases"""

        review_result = {
            "reviewer": "human",
            "status": "pending",
            "feedback": "Awaiting human review",
            "timestamp": datetime.now().isoformat(),
            "pr_id": pr.id,
            "can_merge": False,
            "instructions": f"Please review PR #{pr.id} manually",
        }

        self._save_review(pr.id, review_result)
        return review_result

    async def merge_pr(self, pr: PullRequest, review: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge a PR if it has been approved

        Args:
            pr: The pull request to merge
            review: The review that approved the merge

        Returns:
            Merge result
        """

        if not review.get("can_merge", False):
            return {
                "status": "failed",
                "error": "PR not approved for merge",
                "timestamp": datetime.now().isoformat(),
            }

        try:
            # In a real implementation, this would:
            # 1. Push the branch
            # 2. Create the PR on GitHub
            # 3. Merge it

            # For now, simulate the merge
            merge_commit = f"Merge PR #{pr.id}: {pr.title}"

            merge_result = {
                "status": "merged",
                "merge_commit": merge_commit,
                "merged_by": review["reviewer"],
                "timestamp": datetime.now().isoformat(),
                "pr_id": pr.id,
                "branch": pr.branch_name,
            }

            # Save merge record
            merge_file = (
                self.reviews_dir
                / f"merge_{pr.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(merge_file, "w") as f:
                json.dump(merge_result, f, indent=2)

            print(f"[SIMULATED] PR #{pr.id} merged by {review['reviewer']}")
            print(f"[SIMULATED] Merge commit: {merge_commit}")

            return merge_result

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _save_review(self, pr_id: str, review: Dict[str, Any]):
        """Save review to file"""

        review_file = (
            self.reviews_dir
            / f"review_{pr_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(review_file, "w") as f:
            json.dump(review, f, indent=2)

    async def check_pending_reviews(self) -> list[Dict[str, Any]]:
        """Check for PRs that need review"""

        # In a real implementation, this would query GitHub API
        # For now, check local PR drafts

        pr_drafts_dir = Path(__file__).parent.parent / "data" / "pr_drafts"
        pending_reviews = []

        if pr_drafts_dir.exists():
            for pr_file in pr_drafts_dir.glob("*.json"):
                with open(pr_file, "r") as f:
                    pr_data = json.load(f)

                # Check if already reviewed
                pr_id = pr_file.stem
                if not self._has_recent_review(pr_id):
                    pending_reviews.append(
                        {
                            "pr_id": pr_id,
                            "title": pr_data.get("title", "Unknown"),
                            "assignee": pr_data.get("assignee", "Unknown"),
                            "reviewer": pr_data.get("reviewer", "Unknown"),
                            "created_at": pr_data.get("created_at", "Unknown"),
                        }
                    )

        return pending_reviews

    def _has_recent_review(self, pr_id: str) -> bool:
        """Check if PR has a recent review"""

        # Look for review files for this PR
        review_pattern = f"review_{pr_id}_*.json"
        reviews = list(self.reviews_dir.glob(review_pattern))

        if not reviews:
            return False

        # Check if any review is less than 24 hours old
        latest_review = max(reviews, key=lambda p: p.stat().st_mtime)
        review_age = datetime.now().timestamp() - latest_review.stat().st_mtime

        return review_age < 86400  # 24 hours
