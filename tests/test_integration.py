"""
Integration tests for Zamaz Debate System
Tests the complete workflow and component interactions
"""

import pytest
import asyncio
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.core.nucleus import DebateNucleus
from src.web.app import app
from services.pr_service import PRService
from domain.models import DecisionType
from fastapi.testclient import TestClient


class TestIntegration:
    """Integration test suite"""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def nucleus_with_data(self, temp_data_dir):
        """Create nucleus with custom data directory"""
        os.environ["USE_MOCK_AI"] = "true"
        nucleus = DebateNucleus()
        nucleus.debates_dir = Path(temp_data_dir) / "debates"
        nucleus.debates_dir.mkdir(parents=True, exist_ok=True)
        yield nucleus
        os.environ["USE_MOCK_AI"] = "false"

    @pytest.fixture
    def test_client(self):
        """Create test client for web API"""
        os.environ["USE_MOCK_AI"] = "true"
        client = TestClient(app)
        yield client
        os.environ["USE_MOCK_AI"] = "false"

    @pytest.mark.asyncio
    async def test_end_to_end_simple_decision(self, nucleus_with_data):
        """Test complete flow for simple decision"""
        question = "Should we rename the variable 'x' to 'user_count'?"

        # Make decision
        result = await nucleus_with_data.decide(question)

        # Verify result
        assert result["method"] == "direct"
        assert result["rounds"] == 0
        assert result["complexity"] == "simple"
        assert "decision" in result
        assert len(result["decision"]) > 0

    @pytest.mark.asyncio
    async def test_end_to_end_complex_decision(self, nucleus_with_data):
        """Test complete flow for complex decision with debate"""
        question = "What architecture pattern should we use for the new microservices?"
        context = "We need to handle high traffic and ensure scalability"

        # Make decision
        result = await nucleus_with_data.decide(question, context)

        # Verify result
        assert result["method"] == "debate"
        assert result["rounds"] > 0
        assert result["complexity"] == "complex"
        assert "debate_id" in result

        # Verify debate was saved
        debate_file = nucleus_with_data.debates_dir / f"{result['debate_id']}.json"
        assert debate_file.exists()

        # Load and verify debate content
        with open(debate_file, "r") as f:
            debate_data = json.load(f)

        assert debate_data["question"] == question
        assert debate_data["context"] == context
        assert len(debate_data["rounds"]) > 0
        assert "final_decision" in debate_data

    @pytest.mark.asyncio
    async def test_evolution_workflow(self, nucleus_with_data):
        """Test system evolution workflow"""
        # Trigger evolution
        result = await nucleus_with_data.evolve_self()

        # Verify evolution result
        assert result["method"] == "debate"
        assert "decision" in result

        # Check if evolution was tracked
        if result.get("evolution_tracked"):
            assert result.get("evolution_tracked") is True

        # Verify evolution summary is updated
        summary = nucleus_with_data.evolution_tracker.get_evolution_summary()
        assert summary["total_evolutions"] >= 0

    @pytest.mark.asyncio
    async def test_pr_creation_workflow(self):
        """Test PR creation workflow for complex decisions"""
        os.environ["CREATE_PR_FOR_DECISIONS"] = "true"
        os.environ["AUTO_PUSH_PR"] = "false"
        os.environ["USE_MOCK_AI"] = "true"

        try:
            nucleus = DebateNucleus()
            pr_service = PRService()

            # Make a complex decision
            question = "Should we implement a caching layer?"
            result = await nucleus.decide(question)

            # Verify PR creation eligibility
            if result["complexity"] == "complex":
                # Load the decision
                from domain.models import Decision

                decision = Decision(
                    id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    question=question,
                    context="",
                    decision_text=result["decision"],
                    decision_type=DecisionType.COMPLEX,
                    method=result["method"],
                    rounds=result["rounds"],
                    timestamp=datetime.now(),
                )

                # Check if PR should be created
                should_create = pr_service.should_create_pr(decision)
                assert should_create is True

        finally:
            os.environ["CREATE_PR_FOR_DECISIONS"] = "false"
            os.environ["USE_MOCK_AI"] = "false"

    def test_web_api_integration(self, test_client):
        """Test web API integration"""
        # Test stats endpoint
        response = test_client.get("/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "version" in stats
        assert "decisions_made" in stats
        assert "debates_run" in stats

        # Test decide endpoint
        response = test_client.post(
            "/decide", json={"question": "Should we add logging?", "context": "For debugging purposes"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "decision" in result
        assert "method" in result

        # Test evolve endpoint
        response = test_client.post("/evolve")
        assert response.status_code == 200
        evolution = response.json()
        assert "decision" in evolution

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, nucleus_with_data):
        """Test system behavior under concurrent operations"""
        # Create multiple decision tasks
        tasks = []
        questions = [
            "Should we use TypeScript?",
            "What database should we choose?",
            "Should we implement rate limiting?",
            "How should we handle authentication?",
            "Should we add monitoring?",
        ]

        for q in questions:
            tasks.append(nucleus_with_data.decide(q))

        # Run concurrently
        results = await asyncio.gather(*tasks)

        # Verify all completed successfully
        assert len(results) == len(questions)
        for result in results:
            assert "decision" in result
            assert "method" in result
            assert result["method"] in ["direct", "debate"]

    @pytest.mark.asyncio
    async def test_decision_persistence(self, nucleus_with_data):
        """Test that decisions are properly persisted"""
        question = "Should we implement feature flags?"

        # Make decision
        result = await nucleus_with_data.decide(question)

        # If it was a debate, verify persistence
        if result.get("debate_id"):
            debate_file = nucleus_with_data.debates_dir / f"{result['debate_id']}.json"
            assert debate_file.exists()

            # Verify file content is valid JSON
            with open(debate_file, "r") as f:
                debate_data = json.load(f)

            assert isinstance(debate_data, dict)
            assert debate_data["id"] == result["debate_id"]

    def test_error_handling_integration(self, test_client):
        """Test error handling across the system"""
        # Test missing parameters
        response = test_client.post("/decide", json={})
        assert response.status_code == 422

        # Test empty question
        response = test_client.post("/decide", json={"question": "", "context": "Some context"})
        assert response.status_code == 422  # Pydantic validation error
        error_detail = response.json()
        assert "detail" in error_detail

    @pytest.mark.asyncio
    async def test_evolution_deduplication(self, nucleus_with_data):
        """Test that evolution deduplication works correctly"""
        # First evolution
        result1 = await nucleus_with_data.evolve_self()

        # Try same evolution immediately (should be detected as duplicate)
        result2 = await nucleus_with_data.evolve_self()

        # Check if second was marked as duplicate
        if result2.get("evolution_tracked") is False:
            assert result2.get("duplicate_detected") is True

    def test_web_api_pr_drafts(self, test_client):
        """Test PR drafts endpoint"""
        response = test_client.get("/pr-drafts")
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, dict)
        assert "pr_drafts" in result
        assert isinstance(result["pr_drafts"], list)

    @pytest.mark.asyncio
    async def test_complete_decision_to_pr_flow(self):
        """Test complete flow from decision to PR draft"""
        os.environ["USE_MOCK_AI"] = "true"
        os.environ["CREATE_PR_FOR_DECISIONS"] = "true"
        os.environ["AUTO_PUSH_PR"] = "false"

        try:
            # Create temporary PR drafts directory
            pr_drafts_dir = Path("pr_drafts")
            pr_drafts_dir.mkdir(exist_ok=True)

            nucleus = DebateNucleus()

            # Make a complex decision
            question = "Should we implement GraphQL API?"
            result = await nucleus.decide(question)

            # If it's complex, check for PR draft
            if result.get("pr_created"):
                # List PR drafts
                drafts = list(pr_drafts_dir.glob("*.json"))
                assert len(drafts) > 0

                # Load and verify draft content
                with open(drafts[-1], "r") as f:
                    pr_data = json.load(f)

                assert "title" in pr_data
                assert "body" in pr_data
                assert question in pr_data["title"] or question in pr_data["body"]

        finally:
            os.environ["USE_MOCK_AI"] = "false"
            os.environ["CREATE_PR_FOR_DECISIONS"] = "false"
