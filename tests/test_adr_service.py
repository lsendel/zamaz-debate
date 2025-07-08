"""
Tests for ADR Service
"""
import pytest
import json
from pathlib import Path
from datetime import datetime
import tempfile

import sys
sys.path.append(str(Path(__file__).parent.parent))

from services.adr_service import ADRService, ADRStatus


class TestADRService:
    """Test suite for ADR Service"""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def adr_service(self, temp_data_dir):
        """Create an ADR service with temp directory"""
        return ADRService(adr_dir=temp_data_dir / "adr")
    
    def test_initialization(self, adr_service, temp_data_dir):
        """Test ADR service initialization"""
        assert adr_service.adr_dir == temp_data_dir / "adr"
        assert adr_service.adr_dir.exists()
        assert adr_service.adr_index_file.exists()
        assert adr_service.index["next_number"] == 2  # Starts at 2
    
    def test_create_adr(self, adr_service):
        """Test creating a new ADR"""
        filename = adr_service.create_adr(
            title="Use Testing Framework",
            context="We need to ensure code quality",
            decision="Implement pytest-based testing",
            consequences={
                "positive": ["Better code quality", "Regression prevention"],
                "negative": ["Initial setup time", "Maintenance overhead"],
                "neutral": ["Team needs training"]
            },
            implementation_details="Use pytest with fixtures and mocks"
        )
        
        assert filename == "002-use-testing-framework.md"
        
        # Check file was created
        adr_file = adr_service.adr_dir / filename
        assert adr_file.exists()
        
        # Check content
        with open(adr_file, 'r') as f:
            content = f.read()
        
        assert "ADR-002: Use Testing Framework" in content
        assert "Status\nProposed" in content
        assert "We need to ensure code quality" in content
        assert "Better code quality" in content
        assert "Initial setup time" in content
        assert "Use pytest with fixtures and mocks" in content
        
        # Check index was updated
        assert len(adr_service.index["adrs"]) == 1
        assert adr_service.index["adrs"][0]["number"] == "002"
        assert adr_service.index["next_number"] == 3
    
    def test_get_all_adrs(self, adr_service):
        """Test getting all ADRs"""
        # Create some ADRs
        adr_service.create_adr(
            title="ADR 1",
            context="Context 1",
            decision="Decision 1",
            consequences={"positive": ["Good"], "negative": ["Bad"], "neutral": ["OK"]}
        )
        adr_service.create_adr(
            title="ADR 2",
            context="Context 2",
            decision="Decision 2",
            consequences={"positive": ["Good"], "negative": ["Bad"], "neutral": ["OK"]}
        )
        
        adrs = adr_service.get_all_adrs()
        assert len(adrs) == 2
        assert adrs[0]["title"] == "ADR 1"
        assert adrs[1]["title"] == "ADR 2"
    
    def test_get_adr(self, adr_service):
        """Test getting a specific ADR"""
        adr_service.create_adr(
            title="Test ADR",
            context="Test context",
            decision="Test decision",
            consequences={"positive": ["Good"], "negative": ["Bad"], "neutral": ["OK"]}
        )
        
        adr = adr_service.get_adr("002")
        assert adr is not None
        assert adr["title"] == "Test ADR"
        assert adr["number"] == "002"
        
        # Non-existent ADR
        assert adr_service.get_adr("999") is None
    
    def test_update_adr_status(self, adr_service):
        """Test updating ADR status"""
        adr_service.create_adr(
            title="Test ADR",
            context="Test context",
            decision="Test decision",
            consequences={"positive": ["Good"], "negative": ["Bad"], "neutral": ["OK"]}
        )
        
        # Update status
        result = adr_service.update_adr_status("002", ADRStatus.ACCEPTED)
        assert result is True
        
        # Check it was updated
        adr = adr_service.get_adr("002")
        assert adr["status"] == ADRStatus.ACCEPTED.value
        
        # Try to update non-existent ADR
        result = adr_service.update_adr_status("999", ADRStatus.ACCEPTED)
        assert result is False
    
    def test_create_adr_from_decision(self, adr_service):
        """Test creating ADR from a decision"""
        decision_data = {
            "question": "Should we implement Architectural Decision Records?",
            "context": "The system lacks documentation",
            "decision_text": """Decision: Implement ADRs for better documentation.
            
            Pros:
            - Better documentation
            - Knowledge sharing
            
            Cons:
            - Extra overhead
            - Requires discipline""",
            "decision_type": "complex"
        }
        
        filename = adr_service.create_adr_from_decision(decision_data)
        assert filename is not None
        assert filename.endswith(".md")
        
        # Check the ADR was created properly
        adr_file = adr_service.adr_dir / filename
        assert adr_file.exists()
        
        with open(adr_file, 'r') as f:
            content = f.read()
        
        assert "Better documentation" in content
        assert "Extra overhead" in content
    
    def test_create_adr_from_non_architectural_decision(self, adr_service):
        """Test that non-architectural decisions don't create ADRs"""
        decision_data = {
            "question": "What color should the button be?",
            "context": "UI design",
            "decision_text": "Use blue color for better visibility",
            "decision_type": "simple"
        }
        
        filename = adr_service.create_adr_from_decision(decision_data)
        assert filename is None
    
    def test_slugify(self, adr_service):
        """Test text slugification"""
        assert adr_service._slugify("Hello World") == "hello-world"
        assert adr_service._slugify("Test_With_Underscores") == "test-with-underscores"
        assert adr_service._slugify("A very long title that should be truncated at fifty characters") == "a-very-long-title-that-should-be-truncated-at-fift"