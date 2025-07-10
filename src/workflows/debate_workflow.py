"""
Debate Workflow Engine

This module implements a state machine-based workflow engine for orchestrating debates
in the Zamaz Debate System. It provides configurable debate patterns, dynamic participant
management, and integration with the existing DDD architecture.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID, uuid4

from src.contexts.debate.aggregates import DebateSession, Decision
from src.contexts.debate.events import DebateStarted, DebateCompleted, RoundStarted, RoundCompleted
from src.contexts.debate.value_objects import Argument, Consensus, Topic
from src.events.event_bus import EventBus, get_event_bus

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """States of a debate workflow."""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class StepType(Enum):
    """Types of workflow steps."""
    INITIAL_ARGUMENTS = "initial_arguments"
    COUNTER_ARGUMENTS = "counter_arguments"
    CLARIFICATION = "clarification"
    CONSENSUS_CHECK = "consensus_check"
    FINAL_DECISION = "final_decision"
    CUSTOM = "custom"


@dataclass
class WorkflowConfig:
    """Configuration for debate workflows."""
    max_rounds: int = 5
    min_rounds: int = 2
    consensus_threshold: float = 0.8
    max_execution_time: timedelta = timedelta(minutes=30)
    auto_consensus_check: bool = True
    allow_dynamic_participants: bool = False
    require_all_participants: bool = True


@dataclass
class WorkflowStep:
    """A single step in a debate workflow."""
    id: str
    type: StepType
    name: str
    description: str
    required_participants: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[timedelta] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class WorkflowDefinition:
    """Complete definition of a debate workflow."""
    id: str
    name: str
    description: str
    version: str
    participants: List[str]
    steps: List[WorkflowStep]
    config: WorkflowConfig
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowContext:
    """Context information for workflow execution."""
    workflow_id: UUID
    debate_id: UUID
    question: str
    complexity: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.variables.get(key, default)
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a context variable."""
        self.variables[key] = value


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    workflow_id: UUID
    state: WorkflowState
    decision: Optional[Decision] = None
    consensus: Optional[Consensus] = None
    execution_time: Optional[timedelta] = None
    steps_completed: int = 0
    total_steps: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowStepExecutor(ABC):
    """Abstract base class for workflow step executors."""
    
    @abstractmethod
    async def execute(
        self, 
        step: WorkflowStep, 
        context: WorkflowContext,
        debate_session: DebateSession
    ) -> Dict[str, Any]:
        """Execute a workflow step."""
        pass
    
    @abstractmethod
    def can_execute(self, step: WorkflowStep) -> bool:
        """Check if this executor can handle the given step."""
        pass


class InitialArgumentsExecutor(WorkflowStepExecutor):
    """Executor for initial arguments step."""
    
    def __init__(self, ai_client_factory):
        self.ai_client_factory = ai_client_factory
    
    async def execute(
        self, 
        step: WorkflowStep, 
        context: WorkflowContext,
        debate_session: DebateSession
    ) -> Dict[str, Any]:
        """Execute initial arguments step."""
        logger.info(f"Executing initial arguments step for debate {debate_session.id}")
        
        # Start a new round
        round_obj = debate_session.start_round()
        
        # Get arguments from each participant
        arguments = []
        for participant in step.required_participants:
            try:
                argument = await self._get_participant_argument(
                    participant, context, debate_session
                )
                arguments.append(argument)
                debate_session.add_argument(argument)
            except Exception as e:
                logger.error(f"Error getting argument from {participant}: {e}")
                raise
        
        return {
            "round_id": round_obj.id,
            "arguments": [arg.id for arg in arguments],
            "participant_count": len(arguments)
        }
    
    def can_execute(self, step: WorkflowStep) -> bool:
        """Check if this executor can handle the step."""
        return step.type == StepType.INITIAL_ARGUMENTS
    
    async def _get_participant_argument(
        self, 
        participant: str, 
        context: WorkflowContext,
        debate_session: DebateSession
    ) -> Argument:
        """Get argument from a specific participant."""
        # Get appropriate AI client
        if "claude" in participant.lower():
            client = self.ai_client_factory.get_claude_client()
            response = await self._get_claude_argument(client, context, debate_session)
        elif "gemini" in participant.lower():
            client = self.ai_client_factory.get_gemini_client()
            response = await self._get_gemini_argument(client, context, debate_session)
        else:
            raise ValueError(f"Unknown participant: {participant}")
        
        return Argument(
            id=uuid4(),
            participant=participant,
            content=response,
            created_at=datetime.now()
        )
    
    async def _get_claude_argument(self, client, context: WorkflowContext, debate_session: DebateSession) -> str:
        """Get argument from Claude."""
        prompt = f"""You are participating in a structured debate about: {context.question}

Provide your initial argument with the following structure:
1. State your position clearly
2. Provide 2-3 key supporting points
3. Acknowledge potential counterarguments
4. Conclude with your recommendation

Keep your argument focused and analytical."""
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        return response.content[0].text
    
    async def _get_gemini_argument(self, client, context: WorkflowContext, debate_session: DebateSession) -> str:
        """Get argument from Gemini."""
        prompt = f"""You are participating in a structured debate about: {context.question}

Provide your initial argument with critical analysis:
1. Identify potential risks and challenges
2. Consider alternative approaches
3. Evaluate feasibility and implementation complexity
4. Provide your reasoned recommendation

Be thorough and skeptical in your analysis."""
        
        response = await client.generate_content_async(prompt, context.complexity)
        return response.text


class ConsensusCheckExecutor(WorkflowStepExecutor):
    """Executor for consensus check step."""
    
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
    
    async def execute(
        self, 
        step: WorkflowStep, 
        context: WorkflowContext,
        debate_session: DebateSession
    ) -> Dict[str, Any]:
        """Execute consensus check step."""
        logger.info(f"Checking consensus for debate {debate_session.id}")
        
        # Analyze all arguments from all rounds
        all_arguments = []
        for round_obj in debate_session.rounds:
            all_arguments.extend(round_obj.arguments)
        
        if len(all_arguments) < 2:
            return {
                "consensus_reached": False,
                "confidence": 0.0,
                "reason": "Insufficient arguments for consensus analysis"
            }
        
        # Use orchestrator for intelligent consensus detection if available
        if self.orchestrator:
            consensus_result = await self.orchestrator.detect_consensus(
                debate_session, all_arguments
            )
        else:
            # Fall back to simple consensus detection
            consensus_result = self._simple_consensus_check(all_arguments)
        
        # Check against threshold
        consensus_reached = consensus_result.get("confidence", 0.0) >= step.conditions.get("threshold", 0.8)
        
        if consensus_reached:
            consensus = Consensus(
                value=consensus_result.get("consensus", "Agreement reached"),
                level=consensus_result.get("level", "moderate"),
                rationale=consensus_result.get("rationale", "Based on argument analysis"),
                confidence=consensus_result.get("confidence", 0.8),
                reached_at=datetime.now()
            )
            debate_session.reach_consensus(consensus)
        
        return {
            "consensus_reached": consensus_reached,
            "confidence": consensus_result.get("confidence", 0.0),
            "consensus": consensus_result.get("consensus", ""),
            "rationale": consensus_result.get("rationale", "")
        }
    
    def can_execute(self, step: WorkflowStep) -> bool:
        """Check if this executor can handle the step."""
        return step.type == StepType.CONSENSUS_CHECK
    
    def _simple_consensus_check(self, arguments: List[Argument]) -> Dict[str, Any]:
        """Simple consensus check implementation."""
        # Basic implementation - analyze argument similarity
        positive_indicators = ["yes", "should", "recommend", "beneficial", "agree"]
        negative_indicators = ["no", "should not", "avoid", "unnecessary", "disagree"]
        
        positive_count = 0
        negative_count = 0
        
        for arg in arguments:
            content_lower = arg.content.lower()
            if any(indicator in content_lower for indicator in positive_indicators):
                positive_count += 1
            elif any(indicator in content_lower for indicator in negative_indicators):
                negative_count += 1
        
        total_count = positive_count + negative_count
        if total_count == 0:
            return {"confidence": 0.0, "consensus": "No clear consensus"}
        
        confidence = max(positive_count, negative_count) / total_count
        consensus = "Proceed" if positive_count > negative_count else "Do not proceed"
        
        return {
            "confidence": confidence,
            "consensus": consensus,
            "rationale": f"Based on {total_count} arguments with {confidence:.1%} agreement"
        }


class DebateWorkflow:
    """Main debate workflow orchestrator."""
    
    def __init__(
        self, 
        definition: WorkflowDefinition, 
        event_bus: Optional[EventBus] = None,
        ai_client_factory=None,
        orchestrator=None
    ):
        self.definition = definition
        self.event_bus = event_bus or get_event_bus()
        self.ai_client_factory = ai_client_factory
        self.orchestrator = orchestrator
        
        # Workflow state
        self.id = uuid4()
        self.state = WorkflowState.INITIALIZED
        self.current_step = 0
        self.context: Optional[WorkflowContext] = None
        self.debate_session: Optional[DebateSession] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Step executors
        self.executors = {
            StepType.INITIAL_ARGUMENTS: InitialArgumentsExecutor(ai_client_factory),
            StepType.CONSENSUS_CHECK: ConsensusCheckExecutor(orchestrator),
            # Add more executors as needed
        }
    
    async def execute(self, question: str, complexity: str = "moderate") -> WorkflowResult:
        """Execute the complete workflow."""
        logger.info(f"Starting workflow execution: {self.definition.name}")
        
        try:
            # Initialize workflow
            await self._initialize_workflow(question, complexity)
            
            # Execute workflow steps
            while self.current_step < len(self.definition.steps) and self.state == WorkflowState.RUNNING:
                step = self.definition.steps[self.current_step]
                
                # Check execution timeout
                if self._is_timeout_exceeded():
                    await self._handle_timeout()
                    break
                
                # Execute step
                await self._execute_step(step)
                
                # Check for early completion (consensus reached)
                if self.definition.config.auto_consensus_check and self._should_check_consensus():
                    consensus_reached = await self._check_consensus()
                    if consensus_reached:
                        await self._complete_workflow()
                        break
                
                self.current_step += 1
            
            # Complete workflow if all steps executed
            if self.current_step >= len(self.definition.steps) and self.state == WorkflowState.RUNNING:
                await self._complete_workflow()
            
            return self._create_result()
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            await self._handle_error(e)
            return self._create_result()
    
    async def pause(self) -> None:
        """Pause workflow execution."""
        if self.state == WorkflowState.RUNNING:
            self.state = WorkflowState.PAUSED
            logger.info(f"Workflow {self.id} paused")
    
    async def resume(self) -> None:
        """Resume paused workflow."""
        if self.state == WorkflowState.PAUSED:
            self.state = WorkflowState.RUNNING
            logger.info(f"Workflow {self.id} resumed")
    
    async def abort(self) -> None:
        """Abort workflow execution."""
        if self.state in [WorkflowState.RUNNING, WorkflowState.PAUSED]:
            self.state = WorkflowState.ABORTED
            self.end_time = datetime.now()
            logger.info(f"Workflow {self.id} aborted")
    
    async def _initialize_workflow(self, question: str, complexity: str) -> None:
        """Initialize the workflow for execution."""
        self.start_time = datetime.now()
        self.state = WorkflowState.RUNNING
        
        # Create debate session
        topic = Topic(question)
        self.debate_session = DebateSession(
            id=uuid4(),
            topic=topic,
            participants=self.definition.participants.copy(),
            max_rounds=self.definition.config.max_rounds
        )
        
        # Create workflow context
        self.context = WorkflowContext(
            workflow_id=self.id,
            debate_id=self.debate_session.id,
            question=question,
            complexity=complexity
        )
        
        # Emit workflow started event
        await self.event_bus.publish(
            DebateStarted(
                debate_id=self.debate_session.id,
                topic=question,
                participants=self.definition.participants,
                occurred_at=datetime.now()
            )
        )
        
        logger.info(f"Workflow {self.id} initialized with {len(self.definition.steps)} steps")
    
    async def _execute_step(self, step: WorkflowStep) -> None:
        """Execute a single workflow step."""
        logger.info(f"Executing step {self.current_step + 1}/{len(self.definition.steps)}: {step.name}")
        
        # Find appropriate executor
        executor = self._get_executor_for_step(step)
        if not executor:
            raise ValueError(f"No executor found for step type: {step.type}")
        
        # Execute step with retry logic
        for attempt in range(step.max_retries + 1):
            try:
                result = await executor.execute(step, self.context, self.debate_session)
                
                # Store result in context
                self.context.set_variable(f"step_{step.id}_result", result)
                
                logger.info(f"Step {step.name} completed successfully")
                break
                
            except Exception as e:
                if attempt < step.max_retries:
                    logger.warning(f"Step {step.name} failed (attempt {attempt + 1}), retrying: {e}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Step {step.name} failed after {step.max_retries + 1} attempts: {e}")
                    raise
    
    def _get_executor_for_step(self, step: WorkflowStep) -> Optional[WorkflowStepExecutor]:
        """Get the appropriate executor for a workflow step."""
        return self.executors.get(step.type)
    
    async def _check_consensus(self) -> bool:
        """Check if consensus has been reached."""
        # Create a temporary consensus check step
        consensus_step = WorkflowStep(
            id="temp_consensus",
            type=StepType.CONSENSUS_CHECK,
            name="Consensus Check",
            description="Check if consensus has been reached",
            conditions={"threshold": self.definition.config.consensus_threshold}
        )
        
        executor = self.executors[StepType.CONSENSUS_CHECK]
        result = await executor.execute(consensus_step, self.context, self.debate_session)
        
        return result.get("consensus_reached", False)
    
    def _should_check_consensus(self) -> bool:
        """Determine if consensus should be checked."""
        # Check after each round is complete
        return (
            self.debate_session and
            len(self.debate_session.rounds) >= self.definition.config.min_rounds
        )
    
    def _is_timeout_exceeded(self) -> bool:
        """Check if workflow execution has exceeded timeout."""
        if not self.start_time:
            return False
        
        elapsed = datetime.now() - self.start_time
        return elapsed > self.definition.config.max_execution_time
    
    async def _handle_timeout(self) -> None:
        """Handle workflow timeout."""
        self.state = WorkflowState.FAILED
        self.end_time = datetime.now()
        logger.error(f"Workflow {self.id} timed out")
    
    async def _handle_error(self, error: Exception) -> None:
        """Handle workflow execution error."""
        self.state = WorkflowState.FAILED
        self.end_time = datetime.now()
        logger.error(f"Workflow {self.id} failed: {error}")
    
    async def _complete_workflow(self) -> None:
        """Complete workflow execution."""
        self.state = WorkflowState.COMPLETED
        self.end_time = datetime.now()
        
        # Emit workflow completed event
        if self.debate_session:
            await self.event_bus.publish(
                DebateCompleted(
                    debate_id=self.debate_session.id,
                    total_rounds=len(self.debate_session.rounds),
                    total_arguments=sum(len(r.arguments) for r in self.debate_session.rounds),
                    final_consensus=self.debate_session.consensus.value if self.debate_session.consensus else None,
                    occurred_at=datetime.now()
                )
            )
        
        logger.info(f"Workflow {self.id} completed successfully")
    
    def _create_result(self) -> WorkflowResult:
        """Create workflow result."""
        execution_time = None
        if self.start_time and self.end_time:
            execution_time = self.end_time - self.start_time
        
        return WorkflowResult(
            workflow_id=self.id,
            state=self.state,
            decision=self.debate_session.decision if self.debate_session else None,
            consensus=self.debate_session.consensus if self.debate_session else None,
            execution_time=execution_time,
            steps_completed=self.current_step,
            total_steps=len(self.definition.steps),
            metadata={
                "definition_id": self.definition.id,
                "definition_name": self.definition.name,
                "participants": self.definition.participants,
                "rounds_executed": len(self.debate_session.rounds) if self.debate_session else 0
            }
        )


class WorkflowEngine:
    """Engine for managing and executing debate workflows."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        self.active_workflows: Dict[UUID, DebateWorkflow] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
    
    def register_workflow_definition(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self.workflow_definitions[definition.id] = definition
        logger.info(f"Registered workflow definition: {definition.name}")
    
    def get_workflow_definition(self, definition_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by ID."""
        return self.workflow_definitions.get(definition_id)
    
    def list_workflow_definitions(self) -> List[WorkflowDefinition]:
        """List all registered workflow definitions."""
        return list(self.workflow_definitions.values())
    
    async def create_workflow(
        self, 
        definition_id: str, 
        ai_client_factory=None,
        orchestrator=None
    ) -> DebateWorkflow:
        """Create a new workflow instance."""
        definition = self.get_workflow_definition(definition_id)
        if not definition:
            raise ValueError(f"Workflow definition not found: {definition_id}")
        
        workflow = DebateWorkflow(
            definition=definition,
            event_bus=self.event_bus,
            ai_client_factory=ai_client_factory,
            orchestrator=orchestrator
        )
        
        self.active_workflows[workflow.id] = workflow
        logger.info(f"Created workflow instance: {workflow.id}")
        
        return workflow
    
    async def execute_workflow(
        self, 
        definition_id: str, 
        question: str, 
        complexity: str = "moderate",
        ai_client_factory=None,
        orchestrator=None
    ) -> WorkflowResult:
        """Create and execute a workflow."""
        workflow = await self.create_workflow(
            definition_id, 
            ai_client_factory=ai_client_factory,
            orchestrator=orchestrator
        )
        
        try:
            result = await workflow.execute(question, complexity)
            return result
        finally:
            # Clean up completed workflow
            if workflow.id in self.active_workflows:
                del self.active_workflows[workflow.id]
    
    def get_active_workflow(self, workflow_id: UUID) -> Optional[DebateWorkflow]:
        """Get an active workflow by ID."""
        return self.active_workflows.get(workflow_id)
    
    def list_active_workflows(self) -> List[DebateWorkflow]:
        """List all active workflows."""
        return list(self.active_workflows.values())
    
    async def pause_workflow(self, workflow_id: UUID) -> bool:
        """Pause a workflow."""
        workflow = self.get_active_workflow(workflow_id)
        if workflow:
            await workflow.pause()
            return True
        return False
    
    async def resume_workflow(self, workflow_id: UUID) -> bool:
        """Resume a paused workflow."""
        workflow = self.get_active_workflow(workflow_id)
        if workflow:
            await workflow.resume()
            return True
        return False
    
    async def abort_workflow(self, workflow_id: UUID) -> bool:
        """Abort a workflow."""
        workflow = self.get_active_workflow(workflow_id)
        if workflow:
            await workflow.abort()
            # Clean up aborted workflow
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
            return True
        return False