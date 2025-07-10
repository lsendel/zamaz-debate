"""
Handler for DebateRequested events received via Kafka

This handler processes debate requests and triggers the debate system.
"""

import asyncio
import logging
from uuid import uuid4

from src.contexts.debate import DebateRequested, DebateStarted, DebateCompleted
from src.core.nucleus import DebateNucleus
from src.events import subscribe, get_event_bus

logger = logging.getLogger(__name__)


@subscribe(DebateRequested, context="debate-handler", priority=10)
async def handle_debate_request(event: DebateRequested):
    """
    Process a debate request received via Kafka.
    
    This handler:
    1. Creates a DebateNucleus instance
    2. Runs the debate
    3. Publishes DebateStarted and DebateCompleted events
    """
    logger.info(f"Processing debate request: {event.question}")
    
    try:
        # Get event bus for publishing
        event_bus = get_event_bus()
        
        # Publish DebateStarted event
        started_event = DebateStarted(
            debate_id=event.debate_id,
            topic=event.question,
            context=event.context,
            event_id=uuid4(),
            occurred_at=event.occurred_at,
            event_type="DebateStarted",
            aggregate_id=event.debate_id,
            version=1,
        )
        await event_bus.publish(started_event)
        
        # Create debate nucleus and run debate
        nucleus = DebateNucleus()
        result = await nucleus.decide(event.question, event.context)
        
        # Extract decision info
        decision_id = result.get('decision_id', uuid4())
        decision_type = result.get('decision_type', 'MODERATE')
        winner = result.get('winner', 'Unknown')
        consensus = result.get('consensus', False)
        summary = result.get('decision', 'No summary available')[:500]
        
        # Publish DebateCompleted event
        completed_event = DebateCompleted(
            debate_id=event.debate_id,
            topic=event.question,
            winner=winner,
            consensus=consensus,
            decision_type=decision_type,
            decision_id=decision_id,
            summary=summary,
            event_id=uuid4(),
            occurred_at=event.occurred_at,
            event_type="DebateCompleted",
            aggregate_id=event.debate_id,
            version=1,
        )
        await event_bus.publish(completed_event)
        
        logger.info(
            f"Debate completed: {event.question} - "
            f"Type: {decision_type}, Winner: {winner}"
        )
        
    except Exception as e:
        logger.error(f"Error processing debate request: {str(e)}", exc_info=True)
        # Could publish a DebateFailed event here


def register_debate_handlers():
    """Register all debate-related event handlers"""
    # The @subscribe decorator automatically registers the handler
    logger.info("Debate request handler registered")