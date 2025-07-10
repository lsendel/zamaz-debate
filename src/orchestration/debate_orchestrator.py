"""
Hybrid Debate Orchestrator

This module implements the hybrid state machine approach for debate orchestration,
combining deterministic workflow logic with LLM-powered content analysis.
Based on the AI debate consensus from Issue #224.

Key Features:
- Deterministic state machine for core orchestration
- LLM analysis for content-based decisions and edge cases
- Circuit breakers and fallback mechanisms
- Integration with existing DDD architecture
- Comprehensive error handling and monitoring
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from src.contexts.debate.aggregates import DebateSession, DebateStatus, Decision, DecisionType
from src.contexts.debate.value_objects import Argument, Consensus, Topic
from src.orchestration.llm_orchestrator import (
    LLMOrchestrator,
    OrchestrationConfig,
    OrchestrationFactory,
    OrchestrationDecision,
    OrchestrationDecisionType,
    ConsensusResult,
    ConsensusLevel
)
from src.workflows.debate_workflow import (
    DebateWorkflow,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowState,
    WorkflowResult
)
from src.events.event_bus import EventBus, get_event_bus

logger = logging.getLogger(__name__)


class DebateOrchestrationState(Enum):
    """States in the debate orchestration state machine."""
    INITIALIZING = "initializing"
    ANALYZING_COMPLEXITY = "analyzing_complexity"
    SELECTING_WORKFLOW = "selecting_workflow"
    EXECUTING_WORKFLOW = "executing_workflow"
    MONITORING_PROGRESS = "monitoring_progress"
    CHECKING_CONSENSUS = "checking_consensus"
    HANDLING_ESCALATION = "handling_escalation"
    FINALIZING_DECISION = "finalizing_decision"
    COMPLETED = "completed"
    FAILED = "failed"


class OrchestrationStrategy(Enum):
    """Strategy for handling orchestration decisions."""
    DETERMINISTIC_ONLY = "deterministic_only"  # No LLM, pure state machine
    HYBRID = "hybrid"  # LLM assists deterministic logic
    LLM_DRIVEN = "llm_driven"  # LLM makes most decisions


@dataclass
class DebateOrchestrationConfig:
    """Configuration for debate orchestration."""
    strategy: OrchestrationStrategy = OrchestrationStrategy.HYBRID
    max_rounds: int = 5
    consensus_threshold: float = 0.8
    max_execution_time: timedelta = timedelta(minutes=30)
    enable_circuit_breakers: bool = True
    llm_timeout: float = 30.0
    max_llm_failures: int = 3
    fallback_to_deterministic: bool = True
    enable_monitoring: bool = True


@dataclass
class OrchestrationContext:
    """Context for orchestration decisions."""
    session_id: UUID = field(default_factory=uuid4)
    question: str = ""
    complexity: str = "moderate"
    current_state: DebateOrchestrationState = DebateOrchestrationState.INITIALIZING
    workflow_id: Optional[str] = None
    llm_failures: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)

    def set_variable(self, key: str, value: Any) -> None:
        """Set a context variable."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.variables.get(key, default)


@dataclass
class OrchestrationResult:
    """Result of debate orchestration."""
    session_id: UUID
    final_state: DebateOrchestrationState
    decision: Optional[Decision] = None
    consensus: Optional[Consensus] = None
    workflow_result: Optional[WorkflowResult] = None
    execution_time: Optional[timedelta] = None
    llm_decisions_made: int = 0
    deterministic_decisions_made: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """Circuit breaker for LLM operations."""
    
    def __init__(self, failure_threshold: int = 3, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if self.last_failure_time and \
               (datetime.now() - self.last_failure_time).total_seconds() > self.timeout:
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self) -> None:
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
        elif self.state == "half-open":
            self.state = "open"


class HybridDebateOrchestrator:
    """
    Hybrid debate orchestrator implementing the state machine approach.
    
    Combines deterministic workflow logic with LLM-powered content analysis.
    Features circuit breakers, fallback mechanisms, and comprehensive error handling.
    """
    
    def __init__(
        self,
        config: DebateOrchestrationConfig,
        workflow_engine: WorkflowEngine,
        ai_client_factory,
        event_bus: Optional[EventBus] = None
    ):
        self.config = config
        self.workflow_engine = workflow_engine
        self.ai_client_factory = ai_client_factory
        self.event_bus = event_bus or get_event_bus()
        
        # Initialize LLM orchestrator if needed
        self.llm_orchestrator: Optional[LLMOrchestrator] = None
        if config.strategy in [OrchestrationStrategy.HYBRID, OrchestrationStrategy.LLM_DRIVEN]:
            self._initialize_llm_orchestrator()
        
        # Circuit breaker for LLM operations
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.max_llm_failures,
            timeout=config.llm_timeout
        ) if config.enable_circuit_breakers else None
        
        # State transition map
        self.state_transitions = self._build_state_transitions()
    
    async def orchestrate_debate(
        self,
        question: str,
        context: str = "",
        complexity: str = "moderate"
    ) -> OrchestrationResult:
        """
        Main orchestration method that executes the hybrid state machine.
        
        Args:
            question: The question to debate
            context: Additional context for the debate
            complexity: Complexity level (simple, moderate, complex)
            
        Returns:
            OrchestrationResult with the final decision and metadata
        """
        orch_context = OrchestrationContext(
            question=question,
            complexity=complexity
        )
        
        logger.info(f"Starting debate orchestration for: {question[:50]}...")
        
        try:
            # Execute state machine
            while orch_context.current_state not in [
                DebateOrchestrationState.COMPLETED,
                DebateOrchestrationState.FAILED
            ]:
                # Check timeout
                if self._is_timeout_exceeded(orch_context):
                    await self._handle_timeout(orch_context)
                    break
                
                # Execute current state
                await self._execute_state(orch_context)
            
            return self._create_result(orch_context)
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            await self._handle_error(orch_context, e)
            return self._create_result(orch_context)
    
    async def _execute_state(self, context: OrchestrationContext) -> None:
        """Execute the current state and transition to the next."""
        current_state = context.current_state
        logger.debug(f"Executing state: {current_state}")
        
        try:
            # Execute state logic
            if current_state == DebateOrchestrationState.INITIALIZING:
                await self._initialize_debate(context)
            elif current_state == DebateOrchestrationState.ANALYZING_COMPLEXITY:
                await self._analyze_complexity(context)
            elif current_state == DebateOrchestrationState.SELECTING_WORKFLOW:
                await self._select_workflow(context)
            elif current_state == DebateOrchestrationState.EXECUTING_WORKFLOW:
                await self._execute_workflow(context)
            elif current_state == DebateOrchestrationState.MONITORING_PROGRESS:
                await self._monitor_progress(context)
            elif current_state == DebateOrchestrationState.CHECKING_CONSENSUS:
                await self._check_consensus(context)
            elif current_state == DebateOrchestrationState.HANDLING_ESCALATION:
                await self._handle_escalation(context)
            elif current_state == DebateOrchestrationState.FINALIZING_DECISION:
                await self._finalize_decision(context)
            
            # Transition to next state
            await self._transition_state(context)
            
        except Exception as e:
            logger.error(f"Error in state {current_state}: {e}")
            context.current_state = DebateOrchestrationState.FAILED
            context.metadata["error"] = str(e)
    
    async def _initialize_debate(self, context: OrchestrationContext) -> None:
        """Initialize the debate session."""
        logger.info(f"Initializing debate for: {context.question}")
        
        # Create debate session
        topic = Topic(context.question)
        debate_session = DebateSession(
            id=uuid4(),
            topic=topic,
            participants=[],  # Will be set by workflow
            max_rounds=self.config.max_rounds
        )
        
        context.set_variable("debate_session", debate_session)
        context.set_variable("initialization_time", datetime.now())
        
        logger.info(f"Debate session initialized: {debate_session.id}")
    
    async def _analyze_complexity(self, context: OrchestrationContext) -> None:
        """Analyze question complexity using hybrid approach."""
        logger.info("Analyzing question complexity")
        
        # Deterministic complexity analysis first
        deterministic_complexity = self._deterministic_complexity_analysis(context.question)
        context.set_variable("deterministic_complexity", deterministic_complexity)
        
        # LLM analysis if enabled and available
        llm_complexity = None
        if self.config.strategy != OrchestrationStrategy.DETERMINISTIC_ONLY:
            llm_complexity = await self._llm_complexity_analysis(context)
        
        # Combine results
        final_complexity = self._combine_complexity_analysis(
            deterministic_complexity, llm_complexity, context.complexity
        )
        
        context.complexity = final_complexity
        context.set_variable("final_complexity", final_complexity)
        context.set_variable("llm_complexity", llm_complexity)
        
        logger.info(f"Complexity analysis complete: {final_complexity}")
    
    async def _select_workflow(self, context: OrchestrationContext) -> None:
        """Select appropriate workflow based on complexity and LLM recommendations."""
        logger.info("Selecting workflow")
        
        available_workflows = self.workflow_engine.list_workflow_definitions()
        
        if not available_workflows:
            raise ValueError("No workflow definitions available")
        
        # Deterministic workflow selection
        deterministic_workflow = self._deterministic_workflow_selection(
            context.complexity, available_workflows
        )
        
        # LLM workflow recommendation if enabled
        llm_workflow = None
        if self.config.strategy != OrchestrationStrategy.DETERMINISTIC_ONLY and \
           self.llm_orchestrator and self._can_use_llm():
            try:
                recommendation = await self.llm_orchestrator.select_workflow(
                    context.question, context.complexity, available_workflows
                )
                llm_workflow = recommendation.workflow_id
                context.set_variable("llm_workflow_recommendation", recommendation)
            except Exception as e:
                logger.warning(f"LLM workflow selection failed: {e}")
                self._record_llm_failure()
        
        # Combine selections
        selected_workflow = self._combine_workflow_selection(
            deterministic_workflow, llm_workflow, context
        )
        
        context.workflow_id = selected_workflow
        context.set_variable("selected_workflow", selected_workflow)
        
        logger.info(f"Workflow selected: {selected_workflow}")
    
    async def _execute_workflow(self, context: OrchestrationContext) -> None:
        """Execute the selected workflow."""
        logger.info(f"Executing workflow: {context.workflow_id}")
        
        try:
            # Create and execute workflow
            workflow_result = await self.workflow_engine.execute_workflow(
                definition_id=context.workflow_id,
                question=context.question,
                complexity=context.complexity,
                ai_client_factory=self.ai_client_factory,
                orchestrator=self.llm_orchestrator
            )
            
            context.set_variable("workflow_result", workflow_result)
            context.set_variable("workflow_execution_time", datetime.now())
            
            # Update debate session with workflow results
            debate_session = context.get_variable("debate_session")
            if debate_session and workflow_result.decision:
                debate_session.make_decision(workflow_result.decision)
            
            logger.info(f"Workflow execution completed: {workflow_result.state}")
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            context.set_variable("workflow_error", str(e))
            raise
    
    async def _monitor_progress(self, context: OrchestrationContext) -> None:
        """Monitor workflow progress and make orchestration decisions."""
        logger.debug("Monitoring workflow progress")
        
        workflow_result = context.get_variable("workflow_result")
        debate_session = context.get_variable("debate_session")
        
        if not workflow_result or not debate_session:
            context.set_variable("monitoring_error", "Missing workflow result or debate session")
            return
        
        # Check if we need LLM assistance for progress analysis
        if self.config.strategy != OrchestrationStrategy.DETERMINISTIC_ONLY and \
           self._can_use_llm():
            try:
                orchestration_decision = await self.llm_orchestrator.make_orchestration_decision(
                    debate_session, context.metadata
                )
                context.set_variable("orchestration_decision", orchestration_decision)
                
                # Act on orchestration decision
                if orchestration_decision.decision_type == OrchestrationDecisionType.PAUSE:
                    context.set_variable("should_pause", True)
                elif orchestration_decision.decision_type == OrchestrationDecisionType.ESCALATE:
                    context.set_variable("should_escalate", True)
                elif orchestration_decision.decision_type == OrchestrationDecisionType.COMPLETE:
                    context.set_variable("early_completion", True)
                
            except Exception as e:
                logger.warning(f"Progress monitoring failed: {e}")
                self._record_llm_failure()
        
        context.set_variable("progress_monitored", True)
    
    async def _check_consensus(self, context: OrchestrationContext) -> None:
        """Check if consensus has been reached."""
        logger.info("Checking consensus")
        
        debate_session = context.get_variable("debate_session")
        if not debate_session:
            context.set_variable("consensus_error", "No debate session available")
            return
        
        # Collect all arguments
        all_arguments = []
        for round_obj in debate_session.rounds:
            all_arguments.extend(round_obj.arguments)
        
        if len(all_arguments) < 2:
            context.set_variable("consensus_reached", False)
            context.set_variable("consensus_reason", "Insufficient arguments")
            return
        
        # Try LLM consensus detection first
        consensus_result = None
        if self.config.strategy != OrchestrationStrategy.DETERMINISTIC_ONLY and \
           self._can_use_llm():
            try:
                consensus_result = await self.llm_orchestrator.detect_consensus(
                    debate_session, all_arguments
                )
                context.set_variable("llm_consensus_result", consensus_result)
            except Exception as e:
                logger.warning(f"LLM consensus detection failed: {e}")
                self._record_llm_failure()
        
        # Fallback to deterministic consensus detection
        if not consensus_result:
            consensus_result = self._deterministic_consensus_detection(all_arguments)
        
        # Check against threshold
        consensus_reached = consensus_result.confidence >= self.config.consensus_threshold
        
        context.set_variable("consensus_reached", consensus_reached)
        context.set_variable("consensus_result", consensus_result)
        
        # Update debate session if consensus reached
        if consensus_reached:
            consensus = Consensus(
                value=consensus_result.consensus_text,
                level=consensus_result.level.value,
                rationale=consensus_result.rationale,
                confidence=consensus_result.confidence,
                reached_at=datetime.now()
            )
            debate_session.reach_consensus(consensus)
        
        logger.info(f"Consensus check: {'reached' if consensus_reached else 'not reached'} "
                   f"(confidence: {consensus_result.confidence:.2f})")
    
    async def _handle_escalation(self, context: OrchestrationContext) -> None:
        """Handle escalation scenarios."""
        logger.info("Handling escalation")
        
        # For now, just log the escalation
        # In a full implementation, this could trigger human intervention
        context.set_variable("escalation_handled", True)
        context.set_variable("escalation_time", datetime.now())
    
    async def _finalize_decision(self, context: OrchestrationContext) -> None:
        """Finalize the debate decision."""
        logger.info("Finalizing decision")
        
        workflow_result = context.get_variable("workflow_result")
        debate_session = context.get_variable("debate_session")
        consensus_result = context.get_variable("consensus_result")
        
        if workflow_result and workflow_result.decision:
            # Decision already made by workflow
            final_decision = workflow_result.decision
        elif debate_session and debate_session.decision:
            # Decision made by debate session
            final_decision = debate_session.decision
        else:
            # Create a default decision
            final_decision = Decision(
                question=context.question,
                type=DecisionType.COMPLEX if context.complexity == "complex" else DecisionType.SIMPLE,
                rationale="Decision reached through hybrid orchestration",
                recommendation="Proceed with caution",
                confidence=consensus_result.confidence if consensus_result else 0.5
            )
        
        context.set_variable("final_decision", final_decision)
        context.set_variable("finalization_time", datetime.now())
        
        logger.info(f"Decision finalized: {final_decision.recommendation}")
    
    async def _transition_state(self, context: OrchestrationContext) -> None:
        """Transition to the next state based on current state and conditions."""
        current_state = context.current_state
        transitions = self.state_transitions.get(current_state, [])
        
        for condition, next_state in transitions:
            if condition(context):
                logger.debug(f"Transitioning from {current_state} to {next_state}")
                context.current_state = next_state
                return
        
        # Default transition to failed if no condition met
        logger.warning(f"No valid transition from {current_state}")
        context.current_state = DebateOrchestrationState.FAILED
    
    def _build_state_transitions(self) -> Dict[DebateOrchestrationState, List]:
        """Build the state transition map."""
        return {
            DebateOrchestrationState.INITIALIZING: [
                (lambda ctx: True, DebateOrchestrationState.ANALYZING_COMPLEXITY)
            ],
            DebateOrchestrationState.ANALYZING_COMPLEXITY: [
                (lambda ctx: True, DebateOrchestrationState.SELECTING_WORKFLOW)
            ],
            DebateOrchestrationState.SELECTING_WORKFLOW: [
                (lambda ctx: ctx.workflow_id is not None, DebateOrchestrationState.EXECUTING_WORKFLOW),
                (lambda ctx: True, DebateOrchestrationState.FAILED)
            ],
            DebateOrchestrationState.EXECUTING_WORKFLOW: [
                (lambda ctx: ctx.get_variable("workflow_error"), DebateOrchestrationState.FAILED),
                (lambda ctx: True, DebateOrchestrationState.MONITORING_PROGRESS)
            ],
            DebateOrchestrationState.MONITORING_PROGRESS: [
                (lambda ctx: ctx.get_variable("should_escalate"), DebateOrchestrationState.HANDLING_ESCALATION),
                (lambda ctx: ctx.get_variable("early_completion"), DebateOrchestrationState.FINALIZING_DECISION),
                (lambda ctx: True, DebateOrchestrationState.CHECKING_CONSENSUS)
            ],
            DebateOrchestrationState.CHECKING_CONSENSUS: [
                (lambda ctx: ctx.get_variable("consensus_reached"), DebateOrchestrationState.FINALIZING_DECISION),
                (lambda ctx: ctx.get_variable("consensus_error"), DebateOrchestrationState.FAILED),
                (lambda ctx: True, DebateOrchestrationState.FINALIZING_DECISION)
            ],
            DebateOrchestrationState.HANDLING_ESCALATION: [
                (lambda ctx: True, DebateOrchestrationState.FINALIZING_DECISION)
            ],
            DebateOrchestrationState.FINALIZING_DECISION: [
                (lambda ctx: True, DebateOrchestrationState.COMPLETED)
            ]
        }
    
    def _initialize_llm_orchestrator(self) -> None:
        """Initialize the LLM orchestrator."""
        try:
            orchestration_config = OrchestrationConfig()
            orchestration_config.primary_provider = "ollama"  # Use local Ollama by default
            orchestration_config.fallback_provider = "mock"
            
            self.llm_orchestrator = OrchestrationFactory.create_orchestrator(orchestration_config)
            logger.info("LLM orchestrator initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM orchestrator: {e}")
            self.llm_orchestrator = None
    
    def _can_use_llm(self) -> bool:
        """Check if LLM can be used (circuit breaker check)."""
        if not self.llm_orchestrator:
            return False
        
        if self.circuit_breaker:
            return self.circuit_breaker.can_execute()
        
        return True
    
    def _record_llm_failure(self) -> None:
        """Record an LLM operation failure."""
        if self.circuit_breaker:
            self.circuit_breaker.record_failure()
    
    def _record_llm_success(self) -> None:
        """Record an LLM operation success."""
        if self.circuit_breaker:
            self.circuit_breaker.record_success()
    
    def _deterministic_complexity_analysis(self, question: str) -> str:
        """Deterministic complexity analysis based on keywords."""
        q_lower = question.lower()
        
        complex_keywords = [
            "architecture", "design", "pattern", "system", "structure",
            "integrate", "improve", "evolve", "enhance", "feature"
        ]
        moderate_keywords = [
            "refactor", "optimize", "clean", "organize", "split", "merge"
        ]
        simple_keywords = [
            "rename", "format", "typo", "spacing", "comment", "import"
        ]
        
        if any(keyword in q_lower for keyword in complex_keywords):
            return "complex"
        elif any(keyword in q_lower for keyword in moderate_keywords):
            return "moderate"
        elif any(keyword in q_lower for keyword in simple_keywords):
            return "simple"
        
        return "moderate"  # Default
    
    async def _llm_complexity_analysis(self, context: OrchestrationContext) -> Optional[str]:
        """LLM-based complexity analysis."""
        if not self._can_use_llm():
            return None
        
        try:
            # Use LLM to analyze complexity
            # This would need a specific prompt for complexity analysis
            # For now, return None to use deterministic fallback
            return None
        except Exception as e:
            logger.warning(f"LLM complexity analysis failed: {e}")
            self._record_llm_failure()
            return None
    
    def _combine_complexity_analysis(
        self, 
        deterministic: str, 
        llm: Optional[str], 
        user_provided: str
    ) -> str:
        """Combine complexity analysis results."""
        # Prioritize user input, then LLM, then deterministic
        if user_provided and user_provided in ["simple", "moderate", "complex"]:
            return user_provided
        
        if llm and llm in ["simple", "moderate", "complex"]:
            return llm
        
        return deterministic
    
    def _deterministic_workflow_selection(
        self, 
        complexity: str, 
        workflows: List[WorkflowDefinition]
    ) -> str:
        """Deterministic workflow selection based on complexity."""
        if complexity == "simple":
            # Prefer simple workflows
            for workflow in workflows:
                if "simple" in workflow.id.lower():
                    return workflow.id
        elif complexity == "complex":
            # Prefer complex workflows
            for workflow in workflows:
                if "complex" in workflow.id.lower():
                    return workflow.id
        
        # Default to first available workflow
        return workflows[0].id if workflows else "default"
    
    def _combine_workflow_selection(
        self, 
        deterministic: str, 
        llm: Optional[str], 
        context: OrchestrationContext
    ) -> str:
        """Combine workflow selection results."""
        # If LLM provided a recommendation and strategy allows it, use LLM
        if self.config.strategy == OrchestrationStrategy.LLM_DRIVEN and llm:
            return llm
        
        # For hybrid strategy, prefer LLM but fall back to deterministic
        if self.config.strategy == OrchestrationStrategy.HYBRID:
            return llm if llm else deterministic
        
        # For deterministic only, always use deterministic
        return deterministic
    
    def _deterministic_consensus_detection(self, arguments: List[Argument]) -> ConsensusResult:
        """Deterministic consensus detection fallback."""
        if not arguments:
            return ConsensusResult(
                level=ConsensusLevel.NONE,
                confidence=0.0,
                consensus_text="No arguments to analyze",
                rationale="No arguments provided"
            )
        
        # Simple keyword-based analysis
        positive_keywords = ["yes", "should", "recommend", "beneficial", "agree", "support"]
        negative_keywords = ["no", "shouldn't", "avoid", "problematic", "disagree", "oppose"]
        
        positive_count = 0
        negative_count = 0
        
        for arg in arguments:
            content_lower = arg.content.lower()
            if any(keyword in content_lower for keyword in positive_keywords):
                positive_count += 1
            elif any(keyword in content_lower for keyword in negative_keywords):
                negative_count += 1
        
        total_indicators = positive_count + negative_count
        if total_indicators == 0:
            return ConsensusResult(
                level=ConsensusLevel.NONE,
                confidence=0.0,
                consensus_text="No clear position indicators",
                rationale="No clear positive or negative indicators found"
            )
        
        # Determine consensus
        if positive_count > negative_count:
            consensus_text = "Proceed with implementation"
            confidence = positive_count / total_indicators
        elif negative_count > positive_count:
            consensus_text = "Do not proceed"
            confidence = negative_count / total_indicators
        else:
            consensus_text = "No clear consensus"
            confidence = 0.5
        
        # Determine level
        if confidence >= 0.8:
            level = ConsensusLevel.STRONG
        elif confidence >= 0.6:
            level = ConsensusLevel.MODERATE
        elif confidence >= 0.4:
            level = ConsensusLevel.WEAK
        else:
            level = ConsensusLevel.NONE
        
        return ConsensusResult(
            level=level,
            confidence=confidence,
            consensus_text=consensus_text,
            rationale=f"Based on {total_indicators} indicators: {positive_count} positive, {negative_count} negative"
        )
    
    def _is_timeout_exceeded(self, context: OrchestrationContext) -> bool:
        """Check if orchestration has exceeded timeout."""
        elapsed = datetime.now() - context.start_time
        return elapsed > self.config.max_execution_time
    
    async def _handle_timeout(self, context: OrchestrationContext) -> None:
        """Handle orchestration timeout."""
        logger.error(f"Orchestration timed out after {self.config.max_execution_time}")
        context.current_state = DebateOrchestrationState.FAILED
        context.metadata["timeout"] = True
    
    async def _handle_error(self, context: OrchestrationContext, error: Exception) -> None:
        """Handle orchestration error."""
        logger.error(f"Orchestration error: {error}")
        context.current_state = DebateOrchestrationState.FAILED
        context.metadata["error"] = str(error)
    
    def _create_result(self, context: OrchestrationContext) -> OrchestrationResult:
        """Create the final orchestration result."""
        execution_time = datetime.now() - context.start_time
        
        return OrchestrationResult(
            session_id=context.session_id,
            final_state=context.current_state,
            decision=context.get_variable("final_decision"),
            consensus=context.get_variable("debate_session", {}).consensus if context.get_variable("debate_session") else None,
            workflow_result=context.get_variable("workflow_result"),
            execution_time=execution_time,
            llm_decisions_made=len([k for k in context.variables.keys() if "llm_" in k]),
            deterministic_decisions_made=len([k for k in context.variables.keys() if "deterministic_" in k]),
            error_message=context.metadata.get("error"),
            metadata=context.metadata
        )


# Factory function for easy creation
def create_hybrid_orchestrator(
    ai_client_factory,
    strategy: OrchestrationStrategy = OrchestrationStrategy.HYBRID,
    event_bus: Optional[EventBus] = None
) -> HybridDebateOrchestrator:
    """Create a hybrid debate orchestrator with default configuration."""
    config = DebateOrchestrationConfig(strategy=strategy)
    workflow_engine = WorkflowEngine(event_bus)
    
    return HybridDebateOrchestrator(
        config=config,
        workflow_engine=workflow_engine,
        ai_client_factory=ai_client_factory,
        event_bus=event_bus
    )