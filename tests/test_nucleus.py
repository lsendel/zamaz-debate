import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Only import if nucleus exists
if os.path.exists("nucleus.py"):
    from nucleus import DebateNucleus


class TestDebateNucleus:
    @pytest.fixture
    def nucleus(self):
        if "DebateNucleus" in globals():
            return DebateNucleus()
        pytest.skip("nucleus.py not yet created")

    def test_complexity_assessment(self, nucleus):
        assert nucleus._assess_complexity("rename variable") == "simple"
        assert nucleus._assess_complexity("refactor module") == "moderate"
        assert nucleus._assess_complexity("design system architecture") == "complex"

    @pytest.mark.asyncio
    async def test_simple_decision(self, nucleus):
        result = await nucleus.decide("Should we rename x to count?")
        assert result["method"] == "direct"
        assert result["rounds"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
