"""
Tests for the hybrid debate orchestration system.

This module tests the new orchestration workflow implementation
including state machine transitions, LLM integration, and fallback mechanisms.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.orchestration.debate_orchestrator import (
    HybridDebateOrchestrator,
    DebateOrchestrationConfig,
    OrchestrationStrategy,
    DebateOrchestrationState,
    OrchestrationContext,
    CircuitBreaker,
    create_hybrid_orchestrator
)
from src.workflows.debate_workflow import WorkflowEngine, WorkflowDefinition, WorkflowConfig
from src.contexts.debate.aggregates import DebateSession, Decision, DecisionType
from src.contexts.debate.value_objects import Topic, Argument, Consensus


class TestCircuitBreaker:
    """Test the circuit breaker functionality."""
    
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in closed state."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60.0)
        assert cb.state == "closed"
        assert cb.can_execute() is True
        assert cb.failure_count == 0
    
    def test_circuit_breaker_failures(self):
        """Test circuit breaker opens after failures."""
        cb = CircuitBreaker(failure_threshold=2, timeout=60.0)
        
        # First failure
        cb.record_failure()
        assert cb.state == "closed"
        assert cb.can_execute() is True
        
        # Second failure - should open
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        cb = CircuitBreaker(failure_threshold=1, timeout=0.1)
        
        # Trigger opening
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False
        
        # Wait for timeout
        import time
        time.sleep(0.2)
        
        # Should be half-open and allow execution
        assert cb.can_execute() is True
        assert cb.state == "half-open"
        
        # Success should close it
        cb.record_success()
        assert cb.state == "closed"


class TestOrchestrationContext:
    """Test the orchestration context."""
    
    def test_context_creation(self):
        """Test context is created with correct defaults."""
        context = OrchestrationContext(
            question="Test question",
            complexity="complex"
        )
        
        assert context.question == "Test question"
        assert context.complexity == "complex"
        assert context.current_state == DebateOrchestrationState.INITIALIZING
        assert context.llm_failures == 0
        assert isinstance(context.start_time, datetime)
    
    def test_context_variables(self):
        """Test context variable management."""
        context = OrchestrationContext()
        
        # Set and get variables
        context.set_variable("test_key", "test_value")
        assert context.get_variable("test_key") == "test_value"
        assert context.get_variable("missing_key", "default") == "default"


class TestHybridDebateOrchestrator:
    """Test the hybrid debate orchestrator."""
    
    @pytest.fixture
    def mock_ai_factory(self):
        """Create a mock AI client factory."""
        factory = MagicMock()
        factory.get_claude_client.return_value = MagicMock()
        factory.get_gemini_client.return_value = MagicMock()
        return factory
    
    @pytest.fixture
    def mock_workflow_engine(self):
        """Create a mock workflow engine."""
        engine = MagicMock(spec=WorkflowEngine)
        engine.list_workflow_definitions.return_value = [
            WorkflowDefinition(
                id="simple_debate",
                name="Simple Debate",
                description="Test workflow",
                version="1.0",
                participants=["claude", "gemini"],
                steps=[],
                config=WorkflowConfig()
            )
        ]
        return engine
    
    @pytest.fixture
    def orchestrator(self, mock_ai_factory, mock_workflow_engine):
        """Create a test orchestrator."""
        config = DebateOrchestrationConfig(
            strategy=OrchestrationStrategy.DETERMINISTIC_ONLY,
            max_execution_time=timedelta(seconds=30)
        )
        return HybridDebateOrchestrator(
            config=config,
            workflow_engine=mock_workflow_engine,
            ai_client_factory=mock_ai_factory
        )
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert orchestrator.config.strategy == OrchestrationStrategy.DETERMINISTIC_ONLY
        assert orchestrator.llm_orchestrator is None  # Should be None for deterministic only
        assert orchestrator.circuit_breaker is not None
    
    def test_deterministic_complexity_analysis(self, orchestrator):
        """Test deterministic complexity analysis."""
        # Test complex keywords
        assert orchestrator._deterministic_complexity_analysis(
            "What architecture pattern should we use?"
        ) == "complex"
        
        # Test moderate keywords
        assert orchestrator._deterministic_complexity_analysis(
            "Should we refactor this code?"
        ) == "moderate"
        
        # Test simple keywords
        assert orchestrator._deterministic_complexity_analysis(
            "Should we rename this variable?"
        ) == "simple"
        
        # Test default
        assert orchestrator._deterministic_complexity_analysis(
            "Random question without keywords"
        ) == "moderate"
    
    def test_deterministic_workflow_selection(self, orchestrator, mock_workflow_engine):
        """Test deterministic workflow selection."""
        workflows = mock_workflow_engine.list_workflow_definitions()
        
        # Test simple complexity
        workflow_id = orchestrator._deterministic_workflow_selection("simple", workflows)
        assert workflow_id == "simple_debate"  # Should select the simple workflow
        
        # Test complex complexity with no complex workflow available
        workflow_id = orchestrator._deterministic_workflow_selection("complex", workflows)
        assert workflow_id == "simple_debate"  # Should fall back to first available
    
    @pytest.mark.asyncio
    async def test_orchestrate_debate_deterministic(self, orchestrator, mock_workflow_engine):
        """Test orchestrating a debate with deterministic strategy."""
        # Mock workflow execution
        mock_result = MagicMock()
        mock_result.state = "completed"
        mock_result.decision = Decision(
            question="Test question",
            type=DecisionType.SIMPLE,
            recommendation="Test recommendation",
            rationale="Test rationale"
        )
        mock_result.steps_completed = 2
        
        mock_workflow_engine.execute_workflow = AsyncMock(return_value=mock_result)
        
        # Run orchestration
        result = await orchestrator.orchestrate_debate(
            question="Should we rename this variable?",
            complexity="simple"
        )
        
        # Verify result
        assert result.final_state == DebateOrchestrationState.COMPLETED
        assert result.decision is not None
        assert result.decision.recommendation == "Test recommendation"
        assert result.deterministic_decisions_made > 0
        assert result.llm_decisions_made == 0  # No LLM in deterministic mode
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_ai_factory, mock_workflow_engine):
        """Test timeout handling."""
        config = DebateOrchestrationConfig(
            strategy=OrchestrationStrategy.DETERMINISTIC_ONLY,
            max_execution_time=timedelta(milliseconds=1)  # Very short timeout
        )
        orchestrator = HybridDebateOrchestrator(
            config=config,
            workflow_engine=mock_workflow_engine,
            ai_client_factory=mock_ai_factory
        )
        
        # Mock slow workflow execution
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(0.1)  # Longer than timeout
            return MagicMock()
        
        mock_workflow_engine.execute_workflow = slow_execute
        
        # Run orchestration - should timeout
        result = await orchestrator.orchestrate_debate(
            question="Test question",
            complexity="moderate"
        )
        
        # Should fail due to timeout
        assert result.final_state == DebateOrchestrationState.FAILED
        assert result.metadata.get("timeout") is True


class TestIntegration:
    """Integration tests for the orchestration system."""
    
    @pytest.mark.asyncio
    async def test_create_hybrid_orchestrator(self):
        """Test creating orchestrator with factory function."""
        mock_ai_factory = MagicMock()
        
        orchestrator = create_hybrid_orchestrator(
            ai_client_factory=mock_ai_factory,
            strategy=OrchestrationStrategy.HYBRID
        )
        
        assert isinstance(orchestrator, HybridDebateOrchestrator)
        assert orchestrator.config.strategy == OrchestrationStrategy.HYBRID
        assert orchestrator.ai_client_factory == mock_ai_factory
    
    @pytest.mark.asyncio
    async def test_state_transitions(self, mock_ai_factory):
        """Test state machine transitions."""
        # Create minimal orchestrator for testing
        config = DebateOrchestrationConfig(strategy=OrchestrationStrategy.DETERMINISTIC_ONLY)
        workflow_engine = MagicMock(spec=WorkflowEngine)
        workflow_engine.list_workflow_definitions.return_value = []
        
        orchestrator = HybridDebateOrchestrator(
            config=config,
            workflow_engine=workflow_engine,
            ai_client_factory=mock_ai_factory
        )
        
        # Test transition logic
        context = OrchestrationContext()
        
        # Test initialization transition
        context.current_state = DebateOrchestrationState.INITIALIZING
        await orchestrator._transition_state(context)
        assert context.current_state == DebateOrchestrationState.ANALYZING_COMPLEXITY
        
        # Test workflow selection failure
        context.current_state = DebateOrchestrationState.SELECTING_WORKFLOW
        context.workflow_id = None  # No workflow selected
        await orchestrator._transition_state(context)
        assert context.current_state == DebateOrchestrationState.FAILED


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])