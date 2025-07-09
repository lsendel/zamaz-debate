"""
Comprehensive tests for PR Review Service
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from services.pr_review_service import PRReviewService
from domain.models import PullRequest, DecisionType, ImplementationAssignee, PRStatus, Decision
from services.ai_client_factory import AIClientFactory


class TestPRReviewService:
    """Test suite for PR Review Service"""

    @pytest.fixture
    def pr_review_service(self):
        """Create PR review service"""
        return PRReviewService()

    @pytest.fixture
    def sample_pr(self):
        """Create sample PR"""
        return PullRequest(
            id="pr_123",
            title="[Complex] Implement feature X",
            body="Implementation details...",
            branch_name="decision/complex/123",
            base_branch="main",
            assignee="claude",
            labels=["ai-debate", "complex-decision"],
            status=PRStatus.OPEN,
            decision=Decision(
                id="decision_123",
                question="Should we implement feature X?",
                context="Context",
                decision_text="Yes, implement it",
                decision_type=DecisionType.COMPLEX,
                method="debate",
                rounds=3,
                timestamp=datetime.now(),
                implementation_assignee=ImplementationAssignee.CLAUDE,
            ),
        )

    @pytest.mark.asyncio
    async def test_review_pr_gemini_reviewer(self, pr_review_service, sample_pr):
        """Test reviewing PR with Gemini as reviewer"""
        implementation_code = "def feature_x():\n    return 'implemented'"

        # Mock the AI factory's get_gemini_client method
        with patch.object(pr_review_service.ai_factory, "get_gemini_client") as mock_get_gemini:
            # Configure mock response
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "APPROVED: The implementation looks good and follows best practices."
            mock_client.generate_content.return_value = mock_response
            mock_get_gemini.return_value = mock_client

            review = await pr_review_service.review_pr(sample_pr, implementation_code, reviewer="gemini-bot")

        assert review is not None
        assert review["reviewer"] == "gemini-bot"
        assert review["status"] == "approved"
        assert review["can_merge"] is True
        assert "implementation looks good" in review["feedback"]

    @pytest.mark.asyncio
    async def test_review_pr_codex_reviewer(self, pr_review_service, sample_pr):
        """Test reviewing PR with Codex as reviewer"""
        implementation_code = "def feature_x():\n    return 'implemented'"

        # Mock the AI factory's get_claude_client method and merge_pr
        with patch.object(pr_review_service.ai_factory, "get_claude_client") as mock_get_claude:
            with patch.object(pr_review_service, "merge_pr", return_value={"status": "merged"}):
                # Configure mock response
                mock_client = Mock()
                mock_response = Mock()
                mock_response.content = [Mock(text="APPROVED_AND_MERGE: The code is production-ready.")]
                mock_client.messages.create.return_value = mock_response
                mock_get_claude.return_value = mock_client

                review = await pr_review_service.review_pr(sample_pr, implementation_code, reviewer="codex")

        assert review is not None
        assert review["reviewer"] == "codex"
        assert review["status"] == "approved_merge"
        assert review["can_merge"] is True
        assert review["will_merge"] is True
        assert "merge_result" in review

    @pytest.mark.asyncio
    async def test_review_pr_human_reviewer(self, pr_review_service, sample_pr):
        """Test reviewing PR with human reviewer"""
        implementation_code = "def feature_x():\n    return 'implemented'"

        review = await pr_review_service.review_pr(sample_pr, implementation_code, reviewer="human")

        assert review["reviewer"] == "human"
        assert review["status"] == "pending"
        assert review["can_merge"] is False
        assert "instructions" in review

    @pytest.mark.asyncio
    async def test_review_pr_gemini_changes_requested(self, pr_review_service, sample_pr):
        """Test Gemini requesting changes"""
        implementation_code = "def feature_x():\n    # TODO: implement\n    pass"

        with patch.object(pr_review_service.ai_factory, "get_gemini_client") as mock_get_gemini:
            # Configure mock response
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "CHANGES_REQUESTED: The implementation is incomplete. TODO comments found."
            mock_client.generate_content.return_value = mock_response
            mock_get_gemini.return_value = mock_client

            review = await pr_review_service.review_pr(sample_pr, implementation_code, reviewer="gemini-bot")

        assert review["status"] == "changes_requested"
        assert review["can_merge"] is False

    @pytest.mark.asyncio
    async def test_review_pr_error_handling(self, pr_review_service, sample_pr):
        """Test error handling in review"""
        implementation_code = "def feature_x():\n    return 'implemented'"

        with patch.object(pr_review_service.ai_factory, "get_gemini_client") as mock_get_gemini:
            # Make Gemini client raise an error
            mock_client = Mock()
            mock_client.generate_content.side_effect = Exception("API Error")
            mock_get_gemini.return_value = mock_client

            review = await pr_review_service.review_pr(sample_pr, implementation_code, reviewer="gemini-bot")

        assert review["status"] == "error"
        assert review["can_merge"] is False
        assert "API Error" in review["feedback"]

    @pytest.mark.asyncio
    async def test_merge_pr_approved(self, pr_review_service, sample_pr):
        """Test merging an approved PR"""
        review = {"reviewer": "codex", "status": "approved_merge", "can_merge": True, "feedback": "Approved"}

        merge_result = await pr_review_service.merge_pr(sample_pr, review)

        assert merge_result["status"] == "merged"
        assert merge_result["merged_by"] == "codex"
        assert f"PR #{sample_pr.id}" in merge_result["merge_commit"]

    @pytest.mark.asyncio
    async def test_merge_pr_not_approved(self, pr_review_service, sample_pr):
        """Test merge fails when not approved"""
        review = {
            "reviewer": "gemini-bot",
            "status": "changes_requested",
            "can_merge": False,
            "feedback": "Changes needed",
        }

        merge_result = await pr_review_service.merge_pr(sample_pr, review)

        assert merge_result["status"] == "failed"
        assert "not approved" in merge_result["error"]

    def test_save_review(self, pr_review_service):
        """Test saving review to file"""
        review = {
            "reviewer": "gemini-bot",
            "status": "approved",
            "feedback": "LGTM",
            "timestamp": datetime.now().isoformat(),
        }

        pr_review_service._save_review("test_pr_123", review)

        # Check if file was created
        review_files = list(pr_review_service.reviews_dir.glob("review_test_pr_123_*.json"))
        assert len(review_files) > 0

        # Clean up
        for f in review_files:
            f.unlink()

    @pytest.mark.asyncio
    async def test_check_pending_reviews(self, pr_review_service):
        """Test checking for pending reviews"""
        # Create a mock PR draft
        pr_drafts_dir = Path(__file__).parent.parent / "data" / "pr_drafts"
        pr_drafts_dir.mkdir(parents=True, exist_ok=True)

        test_pr_data = {
            "title": "Test PR",
            "assignee": "claude",
            "reviewer": "gemini-bot",
            "created_at": datetime.now().isoformat(),
        }

        test_pr_file = pr_drafts_dir / "test_pending_pr.json"
        with open(test_pr_file, "w") as f:
            json.dump(test_pr_data, f)

        try:
            pending = await pr_review_service.check_pending_reviews()

            # Should find our test PR
            test_pr_found = any(p["pr_id"] == "test_pending_pr" for p in pending)
            assert test_pr_found

        finally:
            # Clean up
            if test_pr_file.exists():
                test_pr_file.unlink()

    def test_has_recent_review(self, pr_review_service):
        """Test checking for recent reviews"""
        # Test PR without reviews
        assert pr_review_service._has_recent_review("no_reviews_pr") is False

        # Create a recent review
        review = {"reviewer": "gemini-bot", "status": "approved", "timestamp": datetime.now().isoformat()}
        pr_review_service._save_review("recent_review_pr", review)

        # Should find the recent review
        assert pr_review_service._has_recent_review("recent_review_pr") is True

        # Clean up
        review_files = list(pr_review_service.reviews_dir.glob("review_recent_review_pr_*.json"))
        for f in review_files:
            f.unlink()

    @pytest.mark.asyncio
    async def test_codex_auto_merge_flow(self, pr_review_service, sample_pr):
        """Test the complete flow of Codex reviewing and merging"""
        implementation_code = "def feature_x():\n    return 'fully implemented'"

        with patch.object(pr_review_service.ai_factory, "get_claude_client") as mock_get_claude:
            # Configure mock response for approval
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [
                Mock(
                    text="""
            APPROVED_AND_MERGE: 
            The implementation is excellent. All requirements are met.
            - Code quality: High
            - Error handling: Complete
            - Testing: Adequate
            Ready for production.
            """
                )
            ]
            mock_client.messages.create.return_value = mock_response
            mock_get_claude.return_value = mock_client

            review = await pr_review_service.review_pr(sample_pr, implementation_code, reviewer="codex")

        # Verify the complete flow
        assert review["reviewer"] == "codex"
        assert review["status"] == "approved_merge"
        assert review["will_merge"] is True
        assert "merge_result" in review
        assert review["merge_result"]["status"] == "merged"
