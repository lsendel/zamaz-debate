"""
Event-Driven Debate Orchestrator

This module implements a deterministic, event-driven orchestration system that replaces
the LLM-based orchestrator with predictable rules and event handling.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type
from uuid import UUID, uuid4

from src.contexts.debate.aggregates import DebateSession, Decision
from src.contexts.debate.events import (
    DebateStarted, DebateCompleted, RoundStarted, RoundCompleted,
    ArgumentPresented, ConsensusReached
)
from src.contexts.debate.value_objects import Argument, Consensus, Topic
from src.events.event_bus import EventBus, get_event_bus, subscribe, EventPriority
from src.orchestration.rules_engine import (
    RulesEngine, DebateRule, DebateContext, RuleEvaluationResult,
    RuleActionType, StandardRuleFactory
)
from src.workflows.debate_workflow import WorkflowDefinition, WorkflowConfig

logger = logging.getLogger(__name__)


class OrchestrationState(Enum):
    """States of orchestration."""
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OrchestrationSession:
    """Active orchestration session for a debate."""
    id: UUID
    debate_id: UUID
    state: OrchestrationState
    start_time: datetime
    context: DebateContext
    applied_template: Optional[str] = None
    last_action_time: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self):
        """Update last activity time."""
        self.last_action_time = datetime.now()
        self.context.last_activity = datetime.now()


class EventDrivenOrchestrator:
    """Deterministic orchestrator using rules engine and event-driven architecture."""
    
    def __init__(self, event_bus: Optional[EventBus] = None, ai_client_factory=None):
        self.event_bus = event_bus or get_event_bus()
        self.ai_client_factory = ai_client_factory
        self.rules_engine = RulesEngine()
        self.active_sessions: Dict[UUID, OrchestrationSession] = {}
        self.template_registry: Dict[str, WorkflowDefinition] = {}
        
        # Metrics
        self.metrics = {
            'total_debates_orchestrated': 0,
            'successful_completions': 0,
            'consensus_reached': 0,
            'escalations': 0,
            'average_debate_duration': 0.0,
            'rules_triggered_count': 0
        }
        
        # Initialize with standard rules
        self._load_standard_rules()
        
        # Subscribe to events
        self._setup_event_handlers()
    
    def _load_standard_rules(self):
        """Load standard orchestration rules."""
        standard_rules = StandardRuleFactory.create_all_standard_rules()
        for rule in standard_rules:
            self.rules_engine.add_rule(rule)
        
        logger.info(f"Loaded {len(standard_rules)} standard orchestration rules")
    
    def _setup_event_handlers(self):
        """Setup event handlers for orchestration."""
        
        @subscribe(DebateStarted, priority=EventPriority.HIGH, name="orchestrator:debate_started")
        async def on_debate_started(event: DebateStarted):
            await self._handle_debate_started(event)
        
        @subscribe(ArgumentPresented, priority=EventPriority.NORMAL, name="orchestrator:argument_presented")
        async def on_argument_presented(event: ArgumentPresented):
            await self._handle_argument_presented(event)
        
        @subscribe(RoundCompleted, priority=EventPriority.NORMAL, name="orchestrator:round_completed")
        async def on_round_completed(event: RoundCompleted):
            await self._handle_round_completed(event)
        
        @subscribe(ConsensusReached, priority=EventPriority.HIGH, name="orchestrator:consensus_reached")
        async def on_consensus_reached(event: ConsensusReached):
            await self._handle_consensus_reached(event)
    
    async def start_orchestration(
        self, 
        debate_session: DebateSession,
        question: str,
        complexity: str = "moderate"
    ) -> OrchestrationSession:
        """Start orchestrating a debate session."""
        logger.info(f"Starting orchestration for debate {debate_session.id}")
        
        # Create orchestration session
        context = DebateContext(
            debate_id=debate_session.id,
            round_count=len(debate_session.rounds),
            argument_count=sum(len(r.arguments) for r in debate_session.rounds),
            participant_count=len(debate_session.participants),
            start_time=datetime.now(),
            last_activity=datetime.now(),
            complexity=complexity,
            question_keywords=self._extract_keywords(question),
            consensus_indicators={"confidence": 0.0, "level": "none"}
        )
        
        session = OrchestrationSession(
            id=uuid4(),
            debate_id=debate_session.id,
            state=OrchestrationState.ACTIVE,
            start_time=datetime.now(),
            context=context
        )
        
        self.active_sessions[session.debate_id] = session
        self.metrics['total_debates_orchestrated'] += 1
        
        # Apply initial rules
        await self._evaluate_and_apply_rules(session)
        
        return session
    
    async def _handle_debate_started(self, event: DebateStarted):
        """Handle debate started event."""
        session = self.active_sessions.get(event.debate_id)
        if not session:
            logger.warning(f"No orchestration session found for debate {event.debate_id}")
            return
        
        session.update_activity()
        
        # Evaluate template selection rules
        results = self.rules_engine.evaluate_rules(session.context, "template_selection")
        await self._apply_rule_results(session, results)
    
    async def _handle_argument_presented(self, event: ArgumentPresented):
        """Handle argument presented event."""
        session = self.active_sessions.get(event.debate_id)
        if not session:
            return
        
        session.update_activity()
        session.context.argument_count += 1
        
        # Update consensus indicators
        await self._update_consensus_indicators(session, event)
        
        # Evaluate orchestration rules
        await self._evaluate_and_apply_rules(session)
    
    async def _handle_round_completed(self, event: RoundCompleted):
        """Handle round completed event."""
        session = self.active_sessions.get(event.debate_id)
        if not session:
            return
        
        session.update_activity()
        session.context.round_count += 1
        
        # Evaluate orchestration rules
        await self._evaluate_and_apply_rules(session)
    
    async def _handle_consensus_reached(self, event: ConsensusReached):
        """Handle consensus reached event."""
        session = self.active_sessions.get(event.debate_id)
        if not session:
            return
        
        session.update_activity()
        session.context.consensus_indicators = {
            "confidence": event.confidence,
            "level": event.consensus_level
        }
        
        self.metrics['consensus_reached'] += 1
        
        # Evaluate completion rules
        await self._evaluate_and_apply_rules(session)
    
    async def _evaluate_and_apply_rules(self, session: OrchestrationSession):
        """Evaluate rules and apply actions for a session."""
        try:
            # Evaluate all orchestration rules
            results = self.rules_engine.evaluate_rules(session.context)
            
            # Apply results
            await self._apply_rule_results(session, results)
            
            # Update metrics
            triggered_count = sum(1 for r in results if r.rule_triggered)
            self.metrics['rules_triggered_count'] += triggered_count
            
        except Exception as e:
            logger.error(f"Error evaluating rules for session {session.id}: {e}")
    
    async def _apply_rule_results(self, session: OrchestrationSession, results: List[RuleEvaluationResult]):
        """Apply rule evaluation results."""
        for result in results:
            if not result.rule_triggered or not result.actions:
                continue
            
            logger.info(f"Applying actions from rule: {result.rule.name}")
            
            for action in result.actions:
                try:
                    await self._execute_action(session, action)
                except Exception as e:
                    logger.error(f"Error executing action {action.type}: {e}")
    
    async def _execute_action(self, session: OrchestrationSession, action):
        """Execute a rule action."""
        if action.type == RuleActionType.CONTINUE_DEBATE:
            # Already continuing - no action needed
            pass
            
        elif action.type == RuleActionType.PAUSE_DEBATE:
            await self._pause_debate(session, action.parameters.get("reason", "rule_triggered"))
            
        elif action.type == RuleActionType.COMPLETE_DEBATE:
            await self._complete_debate(session, action.parameters.get("reason", "rule_triggered"))
            
        elif action.type == RuleActionType.START_NEW_ROUND:
            await self._start_new_round(session)
            
        elif action.type == RuleActionType.REQUEST_CLARIFICATION:
            await self._request_clarification(session, action.parameters)
            
        elif action.type == RuleActionType.ESCALATE_TO_HUMAN:
            await self._escalate_to_human(session, action.parameters.get("reason", "rule_triggered"))
            
        elif action.type == RuleActionType.APPLY_TEMPLATE:
            await self._apply_template(session, action.parameters.get("template"))
            
        elif action.type == RuleActionType.EMIT_EVENT:
            await self._emit_custom_event(session, action.parameters)
            
        elif action.type == RuleActionType.SET_VARIABLE:
            self._set_context_variable(session, action.parameters)
            
        else:
            logger.warning(f"Unknown action type: {action.type}")
    
    async def _pause_debate(self, session: OrchestrationSession, reason: str):
        """Pause a debate session."""
        session.state = OrchestrationState.PAUSED
        logger.info(f"Paused debate {session.debate_id}: {reason}")
        
        # Emit pause event if needed
        # await self.event_bus.publish(DebatePaused(...))
    
    async def _complete_debate(self, session: OrchestrationSession, reason: str):
        """Complete a debate session."""
        session.state = OrchestrationState.COMPLETED
        
        # Calculate duration
        duration = datetime.now() - session.start_time
        self._update_average_duration(duration)
        
        logger.info(f"Completed debate {session.debate_id}: {reason}")
        
        # Emit completion event
        await self.event_bus.publish(
            DebateCompleted(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="DebateCompleted",
                aggregate_id=session.debate_id,
                debate_id=session.debate_id,
                total_rounds=session.context.round_count,
                total_arguments=session.context.argument_count,
                final_consensus=session.context.consensus_indicators.get("level", "none")
            )
        )
        
        # Clean up session
        if session.debate_id in self.active_sessions:
            del self.active_sessions[session.debate_id]
        
        self.metrics['successful_completions'] += 1
    
    async def _start_new_round(self, session: OrchestrationSession):
        """Start a new round in the debate."""
        logger.info(f"Starting new round for debate {session.debate_id}")
        
        # Emit round started event
        await self.event_bus.publish(
            RoundStarted(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="RoundStarted",
                aggregate_id=session.debate_id,
                debate_id=session.debate_id,
                round_number=session.context.round_count + 1,
                participants=[]  # Will be filled by debate session
            )
        )
    
    async def _request_clarification(self, session: OrchestrationSession, parameters: Dict[str, Any]):
        """Request clarification in the debate."""
        logger.info(f"Requesting clarification for debate {session.debate_id}")
        # Implementation depends on how clarifications are handled
        pass
    
    async def _escalate_to_human(self, session: OrchestrationSession, reason: str):
        """Escalate debate to human review."""
        logger.info(f"Escalating debate {session.debate_id} to human: {reason}")
        
        session.state = OrchestrationState.PAUSED
        self.metrics['escalations'] += 1
        
        # Emit escalation event
        # await self.event_bus.publish(DebateEscalated(...))
    
    async def _apply_template(self, session: OrchestrationSession, template_name: str):
        """Apply a debate template."""
        if not template_name or template_name == session.applied_template:
            return
        
        logger.info(f"Applying template '{template_name}' to debate {session.debate_id}")
        session.applied_template = template_name
        
        # Load template and update session parameters
        if template_name in self.template_registry:
            template = self.template_registry[template_name]
            # Apply template configuration to context
            session.context.custom_variables.update({
                'template': template_name,
                'max_rounds': template.config.max_rounds,
                'consensus_threshold': template.config.consensus_threshold
            })
    
    async def _emit_custom_event(self, session: OrchestrationSession, parameters: Dict[str, Any]):
        """Emit a custom event."""
        event_type = parameters.get("event_type")
        if event_type:
            logger.info(f"Emitting custom event {event_type} for debate {session.debate_id}")
            # Implementation depends on event structure
    
    def _set_context_variable(self, session: OrchestrationSession, parameters: Dict[str, Any]):
        """Set a context variable."""
        variable_name = parameters.get("variable")
        variable_value = parameters.get("value")
        
        if variable_name:
            session.context.custom_variables[variable_name] = variable_value
            logger.debug(f"Set context variable {variable_name} = {variable_value}")
    
    async def _update_consensus_indicators(self, session: OrchestrationSession, event: ArgumentPresented):
        """Update consensus indicators based on new argument."""
        # Simple consensus detection based on argument sentiment
        content = event.content.lower()
        
        # Basic keyword analysis
        positive_keywords = ["yes", "should", "recommend", "beneficial", "agree", "support"]
        negative_keywords = ["no", "shouldn't", "avoid", "problematic", "disagree", "oppose"]
        
        positive_score = sum(1 for keyword in positive_keywords if keyword in content)
        negative_score = sum(1 for keyword in negative_keywords if keyword in content)
        
        total_score = positive_score + negative_score
        if total_score > 0:
            confidence = max(positive_score, negative_score) / total_score
            session.context.consensus_indicators["confidence"] = confidence
            
            if confidence >= 0.8:
                session.context.consensus_indicators["level"] = "strong"
            elif confidence >= 0.6:
                session.context.consensus_indicators["level"] = "moderate"
            elif confidence >= 0.4:
                session.context.consensus_indicators["level"] = "weak"
            else:
                session.context.consensus_indicators["level"] = "none"
    
    def _extract_keywords(self, question: str) -> Set[str]:
        """Extract keywords from question for rule evaluation."""
        # Simple keyword extraction
        words = question.lower().split()
        keywords = set()
        
        # Filter common words and extract meaningful terms
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        for word in words:
            cleaned = word.strip(".,!?:;")
            if len(cleaned) > 2 and cleaned not in common_words:
                keywords.add(cleaned)
        
        return keywords
    
    def _update_average_duration(self, duration: timedelta):
        """Update average debate duration metric."""
        current_avg = self.metrics['average_debate_duration']
        completions = self.metrics['successful_completions']
        
        if completions > 1:
            new_avg = ((current_avg * (completions - 1)) + duration.total_seconds()) / completions
            self.metrics['average_debate_duration'] = new_avg
        else:
            self.metrics['average_debate_duration'] = duration.total_seconds()
    
    def register_template(self, template: WorkflowDefinition):
        """Register a debate template."""
        self.template_registry[template.id] = template
        logger.info(f"Registered template: {template.name}")
    
    def add_custom_rule(self, rule: DebateRule):
        """Add a custom orchestration rule."""
        self.rules_engine.add_rule(rule)
        logger.info(f"Added custom rule: {rule.name}")
    
    def get_active_sessions(self) -> List[OrchestrationSession]:
        """Get all active orchestration sessions."""
        return list(self.active_sessions.values())
    
    def get_session(self, debate_id: UUID) -> Optional[OrchestrationSession]:
        """Get orchestration session for a debate."""
        return self.active_sessions.get(debate_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics."""
        metrics = self.metrics.copy()
        metrics.update(self.rules_engine.get_metrics())
        metrics['active_sessions'] = len(self.active_sessions)
        return metrics
    
    def get_rule_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get rule statistics."""
        return self.rules_engine.get_rule_stats()
    
    async def shutdown(self):
        """Shutdown the orchestrator."""
        logger.info("Shutting down event-driven orchestrator")
        
        # Complete any active sessions
        for session in list(self.active_sessions.values()):
            await self._complete_debate(session, "orchestrator_shutdown")
        
        # Clear event handlers if needed
        # self.event_bus.clear_handlers()


# Factory function for creating orchestrator
def create_event_driven_orchestrator(
    event_bus: Optional[EventBus] = None,
    ai_client_factory=None
) -> EventDrivenOrchestrator:
    """Create an event-driven orchestrator with standard configuration."""
    orchestrator = EventDrivenOrchestrator(event_bus, ai_client_factory)
    
    # Load any additional templates
    from src.workflows.definitions import simple_debate, complex_debate
    # Implementation depends on how templates are loaded
    
    return orchestrator