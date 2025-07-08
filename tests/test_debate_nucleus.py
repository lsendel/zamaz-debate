"""
Comprehensive tests for DebateNucleus
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.nucleus import DebateNucleus
from domain.models import DecisionType, ImplementationAssignee


class TestDebateNucleus:
    """Test suite for DebateNucleus"""
    
    @pytest.fixture
    def nucleus(self, temp_data_dir, mock_ai_factory):
        """Create a DebateNucleus instance with mocked dependencies"""
        with patch('src.core.nucleus.AIClientFactory', return_value=mock_ai_factory):
            nucleus = DebateNucleus()
            nucleus.data_dir = temp_data_dir
            nucleus.debates_dir = temp_data_dir / "debates"
            nucleus.debates_dir.mkdir(exist_ok=True)
            return nucleus
    
    def test_initialization(self, nucleus):
        """Test nucleus initialization"""
        assert nucleus.VERSION == "0.1.0"
        assert nucleus.decision_count == 0
        assert nucleus.debate_count == 0
        assert nucleus.debates_dir.exists()
    
    def test_assess_complexity_simple(self, nucleus):
        """Test complexity assessment for simple decisions"""
        simple_questions = [
            "Should we rename the function?",
            "Fix the typo in the comment",
            "Update import statements"
        ]
        
        for question in simple_questions:
            complexity = nucleus._assess_complexity(question)
            assert complexity == "simple"
    
    def test_assess_complexity_complex(self, nucleus):
        """Test complexity assessment for complex decisions"""
        complex_questions = [
            "How should we improve the architecture?",
            "What design pattern should we use?",
            "Should we integrate with external systems?",
            "Implement a new feature for the system",
            "Enhance the system architecture"
        ]
        
        for question in complex_questions:
            complexity = nucleus._assess_complexity(question)
            if complexity != "complex":
                print(f"Question: {question} -> Complexity: {complexity}")
                print(f"Complex keywords: {nucleus.complexity_keywords['complex']}")
            assert complexity == "complex"
    
    @pytest.mark.asyncio
    async def test_simple_decision(self, nucleus):
        """Test making a simple decision"""
        result = await nucleus.decide(
            "Should we rename this variable?",
            "Variable name is unclear"
        )
        
        assert result['method'] == 'direct'
        assert result['complexity'] == 'simple'
        assert 'decision' in result
        assert 'time' in result
    
    @pytest.mark.asyncio
    async def test_complex_decision_debate(self, nucleus, mock_claude_client, mock_gemini_client):
        """Test complex decision triggers debate"""
        result = await nucleus.decide(
            "Should we migrate to a microservices architecture?",
            "Our monolithic app is becoming hard to maintain"
        )
        
        assert result['method'] == 'debate'
        assert result['complexity'] == 'complex'
        assert result['rounds'] == 1
        assert 'debate_id' in result
        assert mock_claude_client.messages.create.called
        assert mock_gemini_client.generate_content_async.called
    
    @pytest.mark.asyncio
    async def test_evolve_self(self, nucleus):
        """Test self-evolution functionality"""
        result = await nucleus.evolve_self()
        
        assert 'decision' in result
        assert result['method'] == 'debate'
        # Evolution might be a duplicate, so check both cases
        if result.get('duplicate_detected', False):
            assert result.get('evolution_tracked', True) is False
        else:
            # If not duplicate, it should be tracked
            assert result.get('evolution_tracked', False) is True
    
    def test_save_and_load_debate(self, nucleus):
        """Test saving and loading debate data"""
        debate_data = {
            "id": "test_debate_123",
            "question": "Test question",
            "complexity": "complex",
            "start_time": datetime.now().isoformat(),
            "rounds": []
        }
        
        # Save debate
        nucleus._save_debate(debate_data)
        
        # Verify file exists
        debate_file = nucleus.debates_dir / "test_debate_123.json"
        assert debate_file.exists()
        
        # Load and verify
        with open(debate_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data['id'] == debate_data['id']
        assert loaded_data['question'] == debate_data['question']
    
    def test_extract_evolution_feature(self, nucleus):
        """Test extraction of evolution features from decision text"""
        test_cases = [
            ("Implement automated testing framework", "automated_testing"),
            ("Add monitoring and observability stack", "monitoring_system"),
            ("Improve error handling", "error_handling"),
            ("Optimize performance tracking", "performance_tracking"),
            ("Add caching layer", "caching_system")
        ]
        
        for decision_text, expected_feature in test_cases:
            feature = nucleus._extract_evolution_feature(decision_text)
            assert feature == expected_feature
    
    def test_extract_evolution_type(self, nucleus):
        """Test extraction of evolution type"""
        test_cases = [
            ("Add new feature for testing", "feature"),
            ("Enhance existing functionality", "enhancement"),
            ("Fix critical bug", "fix"),
            ("Refactor codebase", "refactor")
        ]
        
        for decision_text, expected_type in test_cases:
            evolution_type = nucleus._extract_evolution_type(decision_text)
            assert evolution_type == expected_type