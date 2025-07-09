"""
One final test file to reach 80% coverage
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))


class TestFinal80:
    """Final tests to reach exactly 80%"""

    def test_ai_client_factory_claude_production(self):
        """Test Claude client in production mode with API key"""
        from services.ai_client_factory import AIClientFactory

        # Set up for production mode
        with patch.dict(
            "os.environ", {"USE_MOCK_AI": "false", "USE_CACHED_RESPONSES": "false", "ANTHROPIC_API_KEY": "test-key-123"}
        ):
            factory = AIClientFactory()

            # Mock the anthropic import and client
            with patch("anthropic.Anthropic") as mock_anthropic:
                mock_client = Mock()
                mock_anthropic.return_value = mock_client

                # This should return a real Claude client wrapper
                client = factory.get_claude_client()

                # Verify it tried to create Anthropic client
                mock_anthropic.assert_called_once()

    def test_pr_service_labels(self):
        """Test label generation in PR service"""
        from services.pr_service import PRService
        from domain.models import Decision, DecisionType, ImplementationAssignee
        from datetime import datetime

        service = PRService()

        # Test with human assignee
        decision = Decision(
            id="test_1",
            question="Test?",
            context="",
            decision_text="Yes",
            decision_type=DecisionType.COMPLEX,
            method="debate",
            rounds=3,
            timestamp=datetime.now(),
            implementation_assignee=ImplementationAssignee.HUMAN,
            implementation_complexity="high",
        )

        labels = service._get_labels_for_decision(decision)

        assert "needs-human-review" in labels
        assert "complexity-high" in labels
        assert "ai-debate" in labels

    def test_localhost_checker_error_screenshot(self):
        """Test error screenshot capture failure"""
        from src.utils import localhost_checker

        # Mock browser that fails during navigation and screenshot
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Nav error"))
        mock_page.screenshot = AsyncMock(side_effect=Exception("Screenshot error"))

        mock_browser = AsyncMock()
        mock_browser.newPage = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        with patch("src.utils.localhost_checker.launch", return_value=mock_browser):
            with patch("builtins.print") as mock_print:
                with patch("os.makedirs"):
                    # Run the check
                    import asyncio

                    asyncio.run(localhost_checker.check_localhost("http://localhost:8000"))

                    # Should print both navigation error and screenshot error
                    print_calls = [str(call) for call in mock_print.call_args_list]
                    assert any("Nav error" in call for call in print_calls)
                    assert any("Could not save error screenshot" in call for call in print_calls)
