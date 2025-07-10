"""
Participant Notification System

This module provides a comprehensive notification system for managing communications
between debate participants, moderators, and observers during debates.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Protocol
from uuid import UUID, uuid4

from src.events.event_bus import EventBus, get_event_bus, subscribe, EventPriority
from src.contexts.debate.events import DebateStarted, RoundStarted, ArgumentPresented, DebateCompleted
from src.orchestration.template_engine import ParticipantConfig, ParticipantRole

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    DEBATE_STARTED = "debate_started"
    ROUND_STARTED = "round_started"
    TURN_NOTIFICATION = "turn_notification"
    ARGUMENT_REQUEST = "argument_request"
    RESPONSE_REQUEST = "response_request"
    CLARIFICATION_REQUEST = "clarification_request"
    CONSENSUS_UPDATE = "consensus_update"
    DEBATE_COMPLETED = "debate_completed"
    ESCALATION_NOTICE = "escalation_notice"
    REMINDER = "reminder"
    ERROR_NOTIFICATION = "error_notification"


class NotificationPriority(Enum):
    """Priority levels for notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DeliveryChannel(Enum):
    """Channels for delivering notifications."""
    IN_MEMORY = "in_memory"  # For AI participants
    WEBHOOK = "webhook"  # HTTP callbacks
    EMAIL = "email"  # Email notifications
    WEBSOCKET = "websocket"  # Real-time updates
    LOG = "log"  # Log entries only


@dataclass
class NotificationContent:
    """Content of a notification."""
    title: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    action_required: bool = False
    deadline: Optional[datetime] = None
    templates: Dict[str, str] = field(default_factory=dict)  # Custom templates per channel
    
    def format_for_channel(self, channel: DeliveryChannel) -> str:
        """Format notification content for specific delivery channel."""
        if channel in self.templates:
            template = self.templates[channel]
            # Simple template substitution
            for key, value in self.context.items():
                template = template.replace(f"{{{key}}}", str(value))
            return template
        
        # Default formatting
        base_message = f"{self.title}\n\n{self.message}"
        
        if self.action_required:
            base_message += "\n\n⚠️ Action Required"
            if self.deadline:
                base_message += f" (Deadline: {self.deadline.strftime('%Y-%m-%d %H:%M UTC')})"
        
        if self.context:
            base_message += f"\n\nContext: {json.dumps(self.context, indent=2)}"
        
        return base_message


@dataclass
class Notification:
    """A notification to be delivered to participants."""
    id: UUID
    type: NotificationType
    priority: NotificationPriority
    recipient_id: str
    content: NotificationContent
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    channels: List[DeliveryChannel] = field(default_factory=lambda: [DeliveryChannel.IN_MEMORY])
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_overdue(self) -> bool:
        """Check if notification deadline has passed."""
        return (
            self.content.deadline is not None and
            datetime.now() > self.content.deadline and
            not self.acknowledged_at
        )
    
    @property
    def is_delivered(self) -> bool:
        """Check if notification has been delivered."""
        return self.delivered_at is not None
    
    @property
    def is_acknowledged(self) -> bool:
        """Check if notification has been acknowledged."""
        return self.acknowledged_at is not None


class NotificationDeliveryChannel(Protocol):
    """Protocol for notification delivery channels."""
    
    async def deliver(self, notification: Notification) -> bool:
        """Deliver a notification. Returns True if successful."""
        ...
    
    def supports_acknowledgment(self) -> bool:
        """Check if this channel supports acknowledgment."""
        ...


class InMemoryChannel:
    """In-memory delivery channel for AI participants."""
    
    def __init__(self):
        self.pending_notifications: Dict[str, List[Notification]] = {}
        self.delivery_callbacks: Dict[str, Callable] = {}
    
    async def deliver(self, notification: Notification) -> bool:
        """Deliver notification to in-memory queue."""
        try:
            recipient_id = notification.recipient_id
            
            if recipient_id not in self.pending_notifications:
                self.pending_notifications[recipient_id] = []
            
            self.pending_notifications[recipient_id].append(notification)
            
            # Call delivery callback if registered
            if recipient_id in self.delivery_callbacks:
                try:
                    await self.delivery_callbacks[recipient_id](notification)
                except Exception as e:
                    logger.error(f"Error in delivery callback for {recipient_id}: {e}")
            
            logger.debug(f"Delivered notification {notification.id} to {recipient_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error delivering in-memory notification: {e}")
            return False
    
    def supports_acknowledgment(self) -> bool:
        """In-memory channel supports acknowledgment."""
        return True
    
    def register_callback(self, participant_id: str, callback: Callable):
        """Register a callback for when notifications are delivered."""
        self.delivery_callbacks[participant_id] = callback
    
    def get_pending_notifications(self, participant_id: str) -> List[Notification]:
        """Get pending notifications for a participant."""
        return self.pending_notifications.get(participant_id, [])
    
    def acknowledge_notification(self, participant_id: str, notification_id: UUID) -> bool:
        """Mark a notification as acknowledged."""
        notifications = self.pending_notifications.get(participant_id, [])
        for notification in notifications:
            if notification.id == notification_id:
                notification.acknowledged_at = datetime.now()
                return True
        return False


class WebhookChannel:
    """Webhook delivery channel for external integrations."""
    
    def __init__(self):
        self.webhook_urls: Dict[str, str] = {}
        self.session = None
    
    async def deliver(self, notification: Notification) -> bool:
        """Deliver notification via webhook."""
        try:
            recipient_id = notification.recipient_id
            webhook_url = self.webhook_urls.get(recipient_id)
            
            if not webhook_url:
                logger.warning(f"No webhook URL configured for {recipient_id}")
                return False
            
            if not self.session:
                import aiohttp
                self.session = aiohttp.ClientSession()
            
            payload = {
                'notification_id': str(notification.id),
                'type': notification.type.value,
                'priority': notification.priority.value,
                'recipient_id': notification.recipient_id,
                'content': {
                    'title': notification.content.title,
                    'message': notification.content.format_for_channel(DeliveryChannel.WEBHOOK),
                    'action_required': notification.content.action_required,
                    'deadline': notification.content.deadline.isoformat() if notification.content.deadline else None,
                    'context': notification.content.context
                },
                'created_at': notification.created_at.isoformat(),
                'metadata': notification.metadata
            }
            
            async with self.session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.debug(f"Delivered webhook notification {notification.id} to {recipient_id}")
                    return True
                else:
                    logger.error(f"Webhook delivery failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error delivering webhook notification: {e}")
            return False
    
    def supports_acknowledgment(self) -> bool:
        """Webhook channel supports acknowledgment via API."""
        return True
    
    def register_webhook(self, participant_id: str, webhook_url: str):
        """Register webhook URL for a participant."""
        self.webhook_urls[participant_id] = webhook_url
        logger.info(f"Registered webhook for {participant_id}: {webhook_url}")


class LogChannel:
    """Log-based delivery channel for audit and debugging."""
    
    async def deliver(self, notification: Notification) -> bool:
        """Deliver notification to log."""
        try:
            log_level = {
                NotificationPriority.LOW: logging.DEBUG,
                NotificationPriority.NORMAL: logging.INFO,
                NotificationPriority.HIGH: logging.WARNING,
                NotificationPriority.URGENT: logging.ERROR
            }.get(notification.priority, logging.INFO)
            
            message = f"[{notification.type.value.upper()}] {notification.content.title} -> {notification.recipient_id}"
            if notification.content.action_required:
                message += " (ACTION REQUIRED)"
            
            logger.log(log_level, message, extra={
                'notification_id': str(notification.id),
                'recipient_id': notification.recipient_id,
                'content': notification.content.message,
                'context': notification.content.context
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging notification: {e}")
            return False
    
    def supports_acknowledgment(self) -> bool:
        """Log channel does not support acknowledgment."""
        return False


class NotificationScheduler:
    """Schedules and manages notification delivery."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        self.channels: Dict[DeliveryChannel, NotificationDeliveryChannel] = {
            DeliveryChannel.IN_MEMORY: InMemoryChannel(),
            DeliveryChannel.WEBHOOK: WebhookChannel(),
            DeliveryChannel.LOG: LogChannel()
        }
        
        self.pending_notifications: List[Notification] = []
        self.delivered_notifications: List[Notification] = []
        self.participant_preferences: Dict[str, Dict[str, Any]] = {}
        
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the notification scheduler."""
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Notification scheduler started")
    
    async def stop(self):
        """Stop the notification scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Notification scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                await self._process_pending_notifications()
                await asyncio.sleep(1)  # Check every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5)  # Back off on error
    
    async def _process_pending_notifications(self):
        """Process pending notifications."""
        now = datetime.now()
        to_deliver = []
        
        # Find notifications ready for delivery
        for notification in self.pending_notifications[:]:
            if notification.scheduled_for is None or notification.scheduled_for <= now:
                to_deliver.append(notification)
                self.pending_notifications.remove(notification)
        
        # Deliver notifications
        for notification in to_deliver:
            await self._deliver_notification(notification)
    
    async def _deliver_notification(self, notification: Notification):
        """Deliver a single notification."""
        delivered = False
        
        for channel_type in notification.channels:
            channel = self.channels.get(channel_type)
            if not channel:
                logger.warning(f"Channel {channel_type} not available")
                continue
            
            try:
                success = await channel.deliver(notification)
                if success:
                    delivered = True
                    logger.debug(f"Delivered notification {notification.id} via {channel_type.value}")
                else:
                    logger.warning(f"Failed to deliver notification {notification.id} via {channel_type.value}")
            except Exception as e:
                logger.error(f"Error delivering notification {notification.id} via {channel_type.value}: {e}")
        
        if delivered:
            notification.delivered_at = datetime.now()
            self.delivered_notifications.append(notification)
        else:
            # Retry logic
            notification.retry_count += 1
            if notification.retry_count < notification.max_retries:
                # Schedule retry with exponential backoff
                retry_delay = min(300, 2 ** notification.retry_count)  # Max 5 minutes
                notification.scheduled_for = datetime.now() + timedelta(seconds=retry_delay)
                self.pending_notifications.append(notification)
                logger.info(f"Scheduled retry {notification.retry_count} for notification {notification.id}")
            else:
                logger.error(f"Max retries exceeded for notification {notification.id}")
    
    def schedule_notification(self, notification: Notification):
        """Schedule a notification for delivery."""
        self.pending_notifications.append(notification)
        logger.debug(f"Scheduled notification {notification.id} for {notification.recipient_id}")
    
    def set_participant_preferences(self, participant_id: str, preferences: Dict[str, Any]):
        """Set notification preferences for a participant."""
        self.participant_preferences[participant_id] = preferences
        logger.info(f"Updated notification preferences for {participant_id}")
    
    def get_channel(self, channel_type: DeliveryChannel) -> Optional[NotificationDeliveryChannel]:
        """Get a delivery channel by type."""
        return self.channels.get(channel_type)
    
    def get_pending_notifications(self, recipient_id: Optional[str] = None) -> List[Notification]:
        """Get pending notifications, optionally filtered by recipient."""
        if recipient_id:
            return [n for n in self.pending_notifications if n.recipient_id == recipient_id]
        return self.pending_notifications[:]
    
    def get_delivered_notifications(self, recipient_id: Optional[str] = None, limit: int = 100) -> List[Notification]:
        """Get delivered notifications, optionally filtered by recipient."""
        notifications = self.delivered_notifications
        if recipient_id:
            notifications = [n for n in notifications if n.recipient_id == recipient_id]
        return notifications[-limit:]


class ParticipantNotificationManager:
    """Manages notifications for debate participants."""
    
    def __init__(self, scheduler: NotificationScheduler, event_bus: Optional[EventBus] = None):
        self.scheduler = scheduler
        self.event_bus = event_bus or get_event_bus()
        self.participants: Dict[str, ParticipantConfig] = {}
        self.active_debates: Set[UUID] = set()
        
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers for debate events."""
        
        @subscribe(DebateStarted, priority=EventPriority.NORMAL, name="notification:debate_started")
        async def on_debate_started(event: DebateStarted):
            await self._handle_debate_started(event)
        
        @subscribe(RoundStarted, priority=EventPriority.NORMAL, name="notification:round_started")
        async def on_round_started(event: RoundStarted):
            await self._handle_round_started(event)
        
        @subscribe(ArgumentPresented, priority=EventPriority.NORMAL, name="notification:argument_presented")
        async def on_argument_presented(event: ArgumentPresented):
            await self._handle_argument_presented(event)
        
        @subscribe(DebateCompleted, priority=EventPriority.NORMAL, name="notification:debate_completed")
        async def on_debate_completed(event: DebateCompleted):
            await self._handle_debate_completed(event)
    
    async def _handle_debate_started(self, event: DebateStarted):
        """Handle debate started event."""
        self.active_debates.add(event.debate_id)
        
        for participant_id in event.participants:
            await self.send_notification(
                participant_id,
                NotificationType.DEBATE_STARTED,
                NotificationContent(
                    title="Debate Started",
                    message=f"A new debate has started: {event.topic}",
                    context={
                        'debate_id': str(event.debate_id),
                        'topic': event.topic,
                        'participants': event.participants
                    }
                ),
                priority=NotificationPriority.HIGH
            )
    
    async def _handle_round_started(self, event: RoundStarted):
        """Handle round started event."""
        for participant_id in event.participants:
            await self.send_notification(
                participant_id,
                NotificationType.ROUND_STARTED,
                NotificationContent(
                    title=f"Round {event.round_number} Started",
                    message="A new round has begun. Please prepare your argument.",
                    context={
                        'debate_id': str(event.debate_id),
                        'round_number': event.round_number
                    },
                    action_required=True,
                    deadline=datetime.now() + timedelta(minutes=5)  # 5-minute deadline
                ),
                priority=NotificationPriority.HIGH
            )
    
    async def _handle_argument_presented(self, event: ArgumentPresented):
        """Handle argument presented event."""
        # Notify other participants about the new argument
        participant = self.participants.get(event.participant)
        if not participant:
            return
        
        # Find other participants to notify
        for participant_id, config in self.participants.items():
            if participant_id != event.participant:
                await self.send_notification(
                    participant_id,
                    NotificationType.RESPONSE_REQUEST,
                    NotificationContent(
                        title="New Argument Presented",
                        message=f"{participant.name} has presented an argument. Please review and respond.",
                        context={
                            'debate_id': str(event.debate_id),
                            'presenter': event.participant,
                            'argument_preview': event.content[:200] + "..." if len(event.content) > 200 else event.content
                        },
                        action_required=True,
                        deadline=datetime.now() + timedelta(minutes=10)
                    ),
                    priority=NotificationPriority.NORMAL
                )
    
    async def _handle_debate_completed(self, event: DebateCompleted):
        """Handle debate completed event."""
        self.active_debates.discard(event.debate_id)
        
        # Notify all participants who were in this debate
        for participant_id in self.participants:
            await self.send_notification(
                participant_id,
                NotificationType.DEBATE_COMPLETED,
                NotificationContent(
                    title="Debate Completed",
                    message=f"The debate has concluded with {event.total_rounds} rounds and {event.total_arguments} arguments.",
                    context={
                        'debate_id': str(event.debate_id),
                        'total_rounds': event.total_rounds,
                        'total_arguments': event.total_arguments,
                        'consensus': event.final_consensus
                    }
                ),
                priority=NotificationPriority.NORMAL
            )
    
    def register_participant(self, participant: ParticipantConfig):
        """Register a participant for notifications."""
        self.participants[participant.id] = participant
        logger.info(f"Registered participant {participant.id} for notifications")
    
    async def send_notification(
        self,
        participant_id: str,
        notification_type: NotificationType,
        content: NotificationContent,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[DeliveryChannel]] = None,
        scheduled_for: Optional[datetime] = None
    ) -> UUID:
        """Send a notification to a participant."""
        
        # Get participant preferences for channels
        if channels is None:
            participant = self.participants.get(participant_id)
            if participant and participant.role == ParticipantRole.OBSERVER:
                channels = [DeliveryChannel.LOG]  # Observers get log notifications only
            else:
                channels = [DeliveryChannel.IN_MEMORY, DeliveryChannel.LOG]
        
        notification = Notification(
            id=uuid4(),
            type=notification_type,
            priority=priority,
            recipient_id=participant_id,
            content=content,
            created_at=datetime.now(),
            scheduled_for=scheduled_for,
            channels=channels
        )
        
        self.scheduler.schedule_notification(notification)
        logger.debug(f"Sent {notification_type.value} notification to {participant_id}")
        
        return notification.id
    
    async def send_reminder(
        self,
        participant_id: str,
        original_notification_id: UUID,
        message: str = "This is a reminder about your pending action."
    ):
        """Send a reminder notification."""
        await self.send_notification(
            participant_id,
            NotificationType.REMINDER,
            NotificationContent(
                title="Reminder",
                message=message,
                context={'original_notification_id': str(original_notification_id)}
            ),
            priority=NotificationPriority.HIGH
        )
    
    async def notify_escalation(self, debate_id: UUID, reason: str):
        """Notify about debate escalation."""
        for participant_id in self.participants:
            await self.send_notification(
                participant_id,
                NotificationType.ESCALATION_NOTICE,
                NotificationContent(
                    title="Debate Escalated",
                    message=f"The debate has been escalated for human review. Reason: {reason}",
                    context={
                        'debate_id': str(debate_id),
                        'escalation_reason': reason
                    }
                ),
                priority=NotificationPriority.URGENT
            )
    
    def get_participant_notifications(self, participant_id: str) -> List[Notification]:
        """Get all notifications for a participant."""
        # Get from in-memory channel
        in_memory_channel = self.scheduler.get_channel(DeliveryChannel.IN_MEMORY)
        if isinstance(in_memory_channel, InMemoryChannel):
            return in_memory_channel.get_pending_notifications(participant_id)
        return []
    
    def acknowledge_notification(self, participant_id: str, notification_id: UUID) -> bool:
        """Acknowledge a notification."""
        in_memory_channel = self.scheduler.get_channel(DeliveryChannel.IN_MEMORY)
        if isinstance(in_memory_channel, InMemoryChannel):
            return in_memory_channel.acknowledge_notification(participant_id, notification_id)
        return False


# Factory function
def create_notification_system(event_bus: Optional[EventBus] = None) -> tuple[NotificationScheduler, ParticipantNotificationManager]:
    """Create a complete notification system."""
    scheduler = NotificationScheduler(event_bus)
    manager = ParticipantNotificationManager(scheduler, event_bus)
    return scheduler, manager