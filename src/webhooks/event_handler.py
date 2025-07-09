"""
Webhook Event Handler

This module handles integration between the domain event system and webhook notifications.
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from src.contexts.debate.events import (
    ArgumentPresented,
    ComplexityAssessed,
    ConsensusReached,
    DebateCancelled,
    DebateCompleted,
    DebateInitiated,
    DebateMetricsCalculated,
    DebateTimeoutOccurred,
    DecisionMade,
    RoundCompleted,
    RoundStarted,
)
from src.events.domain_event import DomainEvent
from src.events.event_bus import EventBus
from src.webhooks.models import WebhookEventType
from src.webhooks.service import WebhookService

logger = logging.getLogger(__name__)


class WebhookEventHandler:
    """
    Handles domain events and triggers webhook notifications
    """

    def __init__(self, webhook_service: WebhookService, event_bus: EventBus):
        self.webhook_service = webhook_service
        self.event_bus = event_bus
        self._subscribed = False

    async def start(self):
        """Start the webhook event handler"""
        if not self._subscribed:
            await self._subscribe_to_events()
            self._subscribed = True
            logger.info("Webhook event handler started")

    async def stop(self):
        """Stop the webhook event handler"""
        if self._subscribed:
            await self._unsubscribe_from_events()
            self._subscribed = False
            logger.info("Webhook event handler stopped")

    async def _subscribe_to_events(self):
        """Subscribe to relevant domain events"""
        # Map domain event types to their handlers
        event_handlers = {
            "DecisionMade": self._handle_decision_made,
            "DebateCompleted": self._handle_debate_completed,
            "ConsensusReached": self._handle_consensus_reached,
            "DebateInitiated": self._handle_debate_initiated,
            "RoundStarted": self._handle_round_started,
            "RoundCompleted": self._handle_round_completed,
            "ComplexityAssessed": self._handle_complexity_assessed,
            "DebateCancelled": self._handle_debate_cancelled,
            "DebateTimeoutOccurred": self._handle_debate_timeout,
            "DebateMetricsCalculated": self._handle_debate_metrics_calculated,
            "ArgumentPresented": self._handle_argument_presented,
        }

        # Subscribe to each event type
        for event_type, handler in event_handlers.items():
            await self.event_bus.subscribe(event_type, handler)
            logger.debug(f"Subscribed to {event_type} events")

    async def _unsubscribe_from_events(self):
        """Unsubscribe from domain events"""
        event_handlers = {
            "DecisionMade": self._handle_decision_made,
            "DebateCompleted": self._handle_debate_completed,
            "ConsensusReached": self._handle_consensus_reached,
            "DebateInitiated": self._handle_debate_initiated,
            "RoundStarted": self._handle_round_started,
            "RoundCompleted": self._handle_round_completed,
            "ComplexityAssessed": self._handle_complexity_assessed,
            "DebateCancelled": self._handle_debate_cancelled,
            "DebateTimeoutOccurred": self._handle_debate_timeout,
            "DebateMetricsCalculated": self._handle_debate_metrics_calculated,
            "ArgumentPresented": self._handle_argument_presented,
        }

        for event_type, handler in event_handlers.items():
            await self.event_bus.unsubscribe(event_type, handler)

    async def _handle_decision_made(self, event: DecisionMade):
        """Handle DecisionMade event"""
        try:
            webhook_data = {
                "decision_id": str(event.decision_id),
                "question": event.question,
                "recommendation": event.recommendation,
                "decision_type": event.decision_type,
                "confidence": event.confidence,
                "implementation_required": event.implementation_required,
                "debate_id": str(event.debate_id) if event.debate_id else None,
                "timestamp": event.occurred_at.isoformat(),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.DECISION_MADE,
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending decision_made webhook: {e}")

    async def _handle_debate_completed(self, event: DebateCompleted):
        """Handle DebateCompleted event"""
        try:
            webhook_data = {
                "debate_id": str(event.debate_id),
                "total_rounds": event.total_rounds,
                "total_arguments": event.total_arguments,
                "final_consensus": event.final_consensus,
                "decision_id": str(event.decision_id) if event.decision_id else None,
                "timestamp": event.occurred_at.isoformat(),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.DEBATE_COMPLETED,
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending debate_completed webhook: {e}")

    async def _handle_consensus_reached(self, event: ConsensusReached):
        """Handle ConsensusReached event"""
        try:
            webhook_data = {
                "debate_id": str(event.debate_id),
                "consensus": event.consensus,
                "consensus_level": event.consensus_level,
                "confidence": event.confidence,
                "timestamp": event.occurred_at.isoformat(),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.CONSENSUS_REACHED,
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending consensus_reached webhook: {e}")

    async def _handle_debate_initiated(self, event: DebateInitiated):
        """Handle DebateInitiated event"""
        try:
            webhook_data = {
                "debate_id": str(event.debate_id),
                "topic": event.topic,
                "participants": event.participants,
                "max_rounds": event.max_rounds,
                "timestamp": event.occurred_at.isoformat(),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.DEBATE_INITIATED,
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending debate_initiated webhook: {e}")

    async def _handle_round_started(self, event: RoundStarted):
        """Handle RoundStarted event"""
        try:
            webhook_data = {
                "debate_id": str(event.debate_id),
                "round_id": str(event.round_id),
                "round_number": event.round_number,
                "timestamp": event.occurred_at.isoformat(),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.ROUND_STARTED,
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending round_started webhook: {e}")

    async def _handle_round_completed(self, event: RoundCompleted):
        """Handle RoundCompleted event"""
        try:
            webhook_data = {
                "debate_id": str(event.debate_id),
                "round_id": str(event.round_id),
                "round_number": event.round_number,
                "arguments_count": event.arguments_count,
                "timestamp": event.occurred_at.isoformat(),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.ROUND_COMPLETED,
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending round_completed webhook: {e}")

    async def _handle_complexity_assessed(self, event: ComplexityAssessed):
        """Handle ComplexityAssessed event"""
        try:
            webhook_data = {
                "decision_id": str(event.decision_id),
                "complexity_score": event.complexity_score,
                "requires_debate": event.requires_debate,
                "criteria": event.criteria,
                "timestamp": event.occurred_at.isoformat(),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.COMPLEXITY_ASSESSED,
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending complexity_assessed webhook: {e}")

    async def _handle_debate_cancelled(self, event: DebateCancelled):
        """Handle DebateCancelled event"""
        try:
            webhook_data = {
                "debate_id": str(event.debate_id),
                "reason": event.reason,
                "cancelled_by": event.cancelled_by,
                "timestamp": event.occurred_at.isoformat(),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.DEBATE_CANCELLED,
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending debate_cancelled webhook: {e}")

    async def _handle_debate_timeout(self, event: DebateTimeoutOccurred):
        """Handle DebateTimeoutOccurred event"""
        try:
            webhook_data = {
                "debate_id": str(event.debate_id),
                "timeout_duration_minutes": event.timeout_duration_minutes,
                "current_round": event.current_round,
                "timestamp": event.occurred_at.isoformat(),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.DEBATE_TIMEOUT,
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending debate_timeout webhook: {e}")

    async def _handle_debate_metrics_calculated(self, event: DebateMetricsCalculated):
        """Handle DebateMetricsCalculated event"""
        try:
            webhook_data = {
                "debate_id": str(event.debate_id),
                "total_rounds": event.total_rounds,
                "total_arguments": event.total_arguments,
                "average_argument_length": event.average_argument_length,
                "debate_duration_minutes": event.debate_duration_minutes,
                "consensus_time_minutes": event.consensus_time_minutes,
                "efficiency_score": event.efficiency_score,
                "timestamp": event.occurred_at.isoformat(),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.DEBATE_METRICS_CALCULATED,
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending debate_metrics_calculated webhook: {e}")

    async def _handle_argument_presented(self, event: ArgumentPresented):
        """Handle ArgumentPresented event - this is used for detailed argument tracking"""
        try:
            # Only send webhook if there are subscribers for this detailed event
            # This might be useful for real-time debate monitoring
            webhook_data = {
                "debate_id": str(event.debate_id),
                "round_id": str(event.round_id),
                "participant": event.participant,
                "argument_type": event.argument_type,
                "confidence": event.confidence,
                # Note: We don't include full argument content for security/privacy
                "argument_length": len(event.argument_content),
                "timestamp": event.occurred_at.isoformat(),
            }

            # This is a high-frequency event, so we might want to make it optional
            # For now, let's create a custom event type for this
            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.DEBATE_METRICS_CALCULATED,  # Reusing existing type
                event_data=webhook_data,
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(f"Error sending argument_presented webhook: {e}")

    async def send_custom_webhook(
        self,
        event_type: WebhookEventType,
        event_data: Dict[str, Any],
        event_id: Optional[UUID] = None,
    ):
        """
        Send a custom webhook notification
        
        This can be used for system events that don't map directly to domain events
        """
        try:
            await self.webhook_service.send_webhook_notification(
                event_type=event_type,
                event_data=event_data,
                event_id=event_id,
            )
        except Exception as e:
            logger.error(f"Error sending custom webhook ({event_type.value}): {e}")

    async def send_error_webhook(
        self,
        error_type: str,
        error_message: str,
        component: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Send webhook notification for system errors"""
        try:
            webhook_data = {
                "error_type": error_type,
                "error_message": error_message,
                "component": component,
                "operation": operation,
                "context": context or {},
                "timestamp": str(datetime.now().isoformat()),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.ERROR_OCCURRED,
                event_data=webhook_data,
            )
        except Exception as e:
            logger.error(f"Error sending error webhook: {e}")

    async def send_evolution_webhook(
        self,
        evolution_type: str,
        feature: str,
        description: str,
        debate_id: Optional[str] = None,
    ):
        """Send webhook notification for system evolution events"""
        try:
            webhook_data = {
                "evolution_type": evolution_type,
                "feature": feature,
                "description": description,
                "debate_id": debate_id,
                "timestamp": str(datetime.now().isoformat()),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.EVOLUTION_TRIGGERED,
                event_data=webhook_data,
            )
        except Exception as e:
            logger.error(f"Error sending evolution webhook: {e}")

    async def send_pr_created_webhook(
        self,
        pr_id: str,
        pr_title: str,
        pr_branch: str,
        assignee: str,
        decision_id: Optional[str] = None,
    ):
        """Send webhook notification when a PR is created"""
        try:
            webhook_data = {
                "pr_id": pr_id,
                "pr_title": pr_title,
                "pr_branch": pr_branch,
                "assignee": assignee,
                "decision_id": decision_id,
                "timestamp": str(datetime.now().isoformat()),
            }

            await self.webhook_service.send_webhook_notification(
                event_type=WebhookEventType.PR_CREATED,
                event_data=webhook_data,
            )
        except Exception as e:
            logger.error(f"Error sending PR created webhook: {e}")


# Import datetime here to avoid circular imports
from datetime import datetime