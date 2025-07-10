"""
Domain Event Handlers

This module contains event handlers that orchestrate cross-context communication.
These handlers listen for events from one context and trigger actions in another.
"""

import logging
from typing import Dict, Any
from uuid import UUID

from src.contexts.debate.events import ComplexityAssessed, DecisionMade
from src.contexts.implementation.events import ImplementationRequested
from src.contexts.performance.events import PerformanceThresholdExceeded
from src.contexts.evolution.events import EvolutionTriggered
from src.contexts.testing.events import TestSuiteCompleted, TestFailed

logger = logging.getLogger(__name__)


class CrossContextEventHandler:
    """
    Handles events that span multiple bounded contexts
    
    This handler coordinates the flow of events between contexts to implement
    the system's business workflows.
    """
    
    def __init__(self):
        self.handlers = {
            "DecisionMade": self.handle_decision_made,
            "ComplexityAssessed": self.handle_complexity_assessed,
            "PerformanceThresholdExceeded": self.handle_performance_threshold,
            "TestSuiteCompleted": self.handle_test_suite_completed,
            "TestFailed": self.handle_test_failed,
        }
    
    async def handle_event(self, event: Dict[str, Any]) -> None:
        """
        Route events to appropriate handlers
        
        Args:
            event: The domain event to handle
        """
        event_type = event.get("event_type")
        handler = self.handlers.get(event_type)
        
        if handler:
            try:
                await handler(event)
                logger.info(f"Successfully handled {event_type} event")
            except Exception as e:
                logger.error(f"Error handling {event_type} event: {e}")
                raise
        else:
            logger.debug(f"No handler registered for event type: {event_type}")
    
    async def handle_decision_made(self, event: Dict[str, Any]) -> None:
        """
        Handle DecisionMade events from the Debate context
        
        When a decision is made, check if implementation is required and
        trigger the Implementation context if needed.
        """
        decision_type = event.get("decision_type")
        implementation_required = event.get("implementation_required", False)
        
        if implementation_required and decision_type in ["complex", "architectural"]:
            # Trigger implementation workflow
            logger.info(f"Decision {event['decision_id']} requires implementation")
            
            # In a real implementation, this would publish an ImplementationRequested event
            # For now, we just log the action
            implementation_event = {
                "event_type": "ImplementationRequested",
                "decision_id": event["decision_id"],
                "decision_type": decision_type,
                "question": event.get("question"),
                "recommendation": event.get("recommendation"),
            }
            
            logger.info(f"Triggering implementation for decision: {implementation_event}")
    
    async def handle_complexity_assessed(self, event: Dict[str, Any]) -> None:
        """
        Handle ComplexityAssessed events from the Debate context
        
        Route decisions based on their complexity assessment.
        """
        requires_debate = event.get("requires_debate", False)
        complexity_score = event.get("complexity_score", 0)
        
        if requires_debate:
            logger.info(f"Decision {event['decision_id']} requires debate (complexity: {complexity_score})")
            # Trigger debate workflow
        else:
            logger.info(f"Decision {event['decision_id']} can be made directly (complexity: {complexity_score})")
            # Trigger simple decision workflow
    
    async def handle_performance_threshold(self, event: Dict[str, Any]) -> None:
        """
        Handle PerformanceThresholdExceeded events from the Performance context
        
        When critical performance thresholds are exceeded, trigger evolution
        or optimization workflows.
        """
        severity = event.get("severity")
        metric_name = event.get("metric_name")
        
        if severity == "critical":
            logger.warning(f"Critical performance threshold exceeded for {metric_name}")
            
            # Trigger evolution workflow for critical performance issues
            evolution_event = {
                "event_type": "EvolutionTriggered",
                "trigger_type": "performance",
                "metric_name": metric_name,
                "threshold_value": event.get("threshold_value"),
                "actual_value": event.get("actual_value"),
            }
            
            logger.info(f"Triggering system evolution due to performance: {evolution_event}")
    
    async def handle_test_suite_completed(self, event: Dict[str, Any]) -> None:
        """
        Handle TestSuiteCompleted events from the Testing context
        
        Analyze test results and trigger appropriate actions.
        """
        total_tests = event.get("total_tests", 0)
        failed_tests = event.get("failed_tests", 0)
        
        if failed_tests > 0:
            failure_rate = (failed_tests / total_tests) * 100 if total_tests > 0 else 0
            logger.warning(f"Test suite {event['test_suite_id']} completed with {failure_rate:.1f}% failure rate")
            
            if failure_rate > 10:  # More than 10% failure rate
                # Trigger quality improvement workflow
                logger.info("High test failure rate detected, triggering quality improvement workflow")
    
    async def handle_test_failed(self, event: Dict[str, Any]) -> None:
        """
        Handle TestFailed events from the Testing context
        
        Track and respond to individual test failures.
        """
        test_name = event.get("test_name")
        error_message = event.get("error_message")
        
        logger.error(f"Test '{test_name}' failed: {error_message}")
        
        # In a real implementation, this might trigger:
        # - Notification to development team
        # - Automatic rollback if in deployment
        # - Creation of bug report


class SagaOrchestrator:
    """
    Orchestrates complex workflows (sagas) that span multiple bounded contexts
    
    Each saga represents a business process that involves multiple steps
    across different contexts.
    """
    
    def __init__(self):
        self.active_sagas: Dict[UUID, Dict[str, Any]] = {}
    
    async def start_decision_implementation_saga(self, decision_id: UUID) -> None:
        """
        Start the Decision → Implementation → Testing saga
        
        This saga orchestrates the complete flow from decision to implementation.
        """
        saga_id = UUID()
        saga_state = {
            "id": saga_id,
            "type": "decision_implementation",
            "decision_id": decision_id,
            "current_step": "decision_made",
            "steps_completed": ["decision_made"],
            "created_at": datetime.now(),
        }
        
        self.active_sagas[saga_id] = saga_state
        logger.info(f"Started decision implementation saga: {saga_id}")
        
        # Trigger next step
        await self._trigger_implementation(saga_id, decision_id)
    
    async def _trigger_implementation(self, saga_id: UUID, decision_id: UUID) -> None:
        """Trigger the implementation phase of the saga"""
        # Update saga state
        if saga_id in self.active_sagas:
            self.active_sagas[saga_id]["current_step"] = "implementation_started"
            self.active_sagas[saga_id]["steps_completed"].append("implementation_started")
        
        # In a real implementation, this would publish events and coordinate
        # the implementation workflow
        logger.info(f"Saga {saga_id}: Triggering implementation for decision {decision_id}")
    
    async def handle_saga_event(self, event: Dict[str, Any]) -> None:
        """
        Handle events that are part of active sagas
        
        This method updates saga state and triggers next steps based on
        the event type and current saga state.
        """
        # Find relevant sagas for this event
        event_type = event.get("event_type")
        
        for saga_id, saga_state in self.active_sagas.items():
            if self._is_event_relevant_to_saga(event, saga_state):
                await self._update_saga_state(saga_id, event)
                await self._trigger_next_saga_step(saga_id)
    
    def _is_event_relevant_to_saga(self, event: Dict[str, Any], saga_state: Dict[str, Any]) -> bool:
        """Check if an event is relevant to a specific saga"""
        # Implementation would check event data against saga state
        # to determine relevance
        return True
    
    async def _update_saga_state(self, saga_id: UUID, event: Dict[str, Any]) -> None:
        """Update saga state based on received event"""
        if saga_id not in self.active_sagas:
            return
        
        saga_state = self.active_sagas[saga_id]
        event_type = event.get("event_type")
        
        # Update based on event type
        if event_type == "ImplementationCompleted":
            saga_state["current_step"] = "implementation_completed"
            saga_state["steps_completed"].append("implementation_completed")
        elif event_type == "TestSuiteCompleted":
            saga_state["current_step"] = "testing_completed"
            saga_state["steps_completed"].append("testing_completed")
    
    async def _trigger_next_saga_step(self, saga_id: UUID) -> None:
        """Trigger the next step in a saga based on current state"""
        if saga_id not in self.active_sagas:
            return
        
        saga_state = self.active_sagas[saga_id]
        current_step = saga_state["current_step"]
        
        # Determine and trigger next step
        if current_step == "implementation_completed":
            logger.info(f"Saga {saga_id}: Implementation completed, triggering testing")
            # Trigger testing workflow
        elif current_step == "testing_completed":
            logger.info(f"Saga {saga_id}: Testing completed, saga finished")
            # Complete the saga
            del self.active_sagas[saga_id]


# Import datetime for saga timestamps
from datetime import datetime