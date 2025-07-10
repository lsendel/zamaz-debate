"""
Tests for Phase 2: Template System and Notification System

Comprehensive tests for the template engine, template composition, and participant notification system.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch

from src.orchestration.template_engine import (
    TemplateComposer, TemplateRegistry, DebateTemplate, TemplateMetadata,
    ParticipantConfig, ParticipantRole, TemplateType, get_template_registry
)
from src.orchestration.notification_system import (
    NotificationScheduler, ParticipantNotificationManager, InMemoryChannel,
    WebhookChannel, LogChannel, Notification, NotificationContent,
    NotificationType, NotificationPriority, DeliveryChannel, create_notification_system
)
from src.contexts.debate.events import DebateStarted, RoundStarted, ArgumentPresented, DebateCompleted
from src.events.event_bus import EventBus
from src.workflows.debate_workflow import WorkflowConfig


class TestTemplateComposer:
    """Test suite for the template composer."""
    
    @pytest.fixture
    def composer(self):
        """Create a fresh template composer for testing."""
        return TemplateComposer()
    
    def test_composer_initialization(self, composer):
        """Test that composer initializes with standard components."""
        assert len(composer.step_library) > 0
        assert len(composer.participant_library) > 0
        
        # Check for expected standard steps
        expected_steps = ["opening_arguments", "counter_arguments", "consensus_check"]
        for step_id in expected_steps:
            assert step_id in composer.step_library
        
        # Check for expected standard participants
        expected_participants = ["claude_proposer", "gemini_opponent", "claude_reviewer"]
        for participant_id in expected_participants:
            assert participant_id in composer.participant_library
    
    def test_compose_simple_template(self, composer):
        """Test composing a simple debate template."""
        template = composer.compose_simple_template("test_simple")
        
        assert template.id == "test_simple"
        assert template.type == TemplateType.SIMPLE
        assert template.metadata.name == "Simple Debate"
        assert template.workflow_config.max_rounds == 2
        assert len(template.participants) >= 2
        assert len(template.steps) >= 3
        assert "start_new_round" in template.rules
    
    def test_compose_standard_template(self, composer):
        """Test composing a standard debate template."""
        template = composer.compose_standard_template("test_standard")
        
        assert template.id == "test_standard"
        assert template.type == TemplateType.STANDARD
        assert template.metadata.complexity_level == 3
        assert template.workflow_config.max_rounds == 3
        assert len(template.steps) > 3  # More steps than simple
    
    def test_compose_complex_template(self, composer):
        """Test composing a complex debate template."""
        template = composer.compose_complex_template("test_complex")
        
        assert template.id == "test_complex"
        assert template.type == TemplateType.COMPLEX
        assert template.metadata.complexity_level == 5
        assert template.workflow_config.max_rounds == 5
        assert len(template.participants) >= 3  # Includes reviewer
        assert "escalate_complex" in template.rules
    
    def test_compose_custom_template(self, composer):
        """Test composing a custom template."""
        metadata = TemplateMetadata(
            name="Custom Test Template",
            description="A custom template for testing",
            version="1.0",
            complexity_level=2
        )
        
        template = composer.compose_custom_template(
            "test_custom",
            metadata,
            ["claude_proposer", "gemini_opponent"],
            ["opening_arguments", "consensus_check"],
            {"max_rounds": 4}
        )
        
        assert template.id == "test_custom"
        assert template.type == TemplateType.CUSTOM
        assert template.metadata.name == "Custom Test Template"
        assert template.workflow_config.max_rounds == 4
        assert len(template.steps) == 2
    
    def test_add_custom_components(self, composer):
        """Test adding custom steps and participants."""
        from src.workflows.debate_workflow import WorkflowStep, StepType
        
        # Add custom step
        custom_step = WorkflowStep(
            id="custom_step",
            type=StepType.CUSTOM,
            name="Custom Step",
            description="A custom test step"
        )
        composer.add_step_to_library(custom_step)
        assert "custom_step" in composer.step_library
        
        # Add custom participant
        custom_participant = ParticipantConfig(
            id="custom_participant",
            name="Custom Participant",
            role=ParticipantRole.MODERATOR,
            ai_model="test-model"
        )
        composer.add_participant_to_library(custom_participant)
        assert "custom_participant" in composer.participant_library
    
    def test_participant_config_prompt_variables(self):
        """Test participant configuration prompt variables."""
        participant = ParticipantConfig(
            id="test_participant",
            name="Test Participant",
            role=ParticipantRole.PROPOSER,
            ai_model="test-model",
            expertise_areas={"testing", "development"},
            personality_traits={"analytical": 0.8}
        )
        
        variables = participant.get_prompt_variables()
        
        assert variables['role'] == "proposer"
        assert "testing" in variables['expertise_areas']
        assert variables['personality_traits']['analytical'] == 0.8


class TestTemplateRegistry:
    """Test suite for the template registry."""
    
    @pytest.fixture
    def registry(self, tmp_path):
        """Create a test template registry."""
        return TemplateRegistry(storage_path=tmp_path)
    
    @pytest.fixture
    def sample_template(self):
        """Create a sample template for testing."""
        metadata = TemplateMetadata(
            name="Test Template",
            description="A template for testing",
            version="1.0",
            tags={"test", "sample"}
        )
        
        participants = [
            ParticipantConfig(
                id="test_participant",
                name="Test Participant",
                role=ParticipantRole.PROPOSER,
                ai_model="test-model"
            )
        ]
        
        return DebateTemplate(
            id="test_template",
            type=TemplateType.CUSTOM,
            metadata=metadata,
            participants=participants,
            workflow_config=WorkflowConfig(),
            steps=[],
            rules=["test_rule"]
        )
    
    def test_registry_initialization(self, registry):
        """Test that registry initializes with default templates."""
        assert len(registry.templates) >= 3  # At least simple, standard, complex
        
        template_ids = list(registry.templates.keys())
        assert "simple_debate" in template_ids
        assert "standard_debate" in template_ids
        assert "complex_debate" in template_ids
    
    def test_register_template(self, registry, sample_template):
        """Test registering a template."""
        initial_count = len(registry.templates)
        registry.register_template(sample_template, save_to_disk=False)
        
        assert len(registry.templates) == initial_count + 1
        assert registry.get_template("test_template") == sample_template
    
    def test_list_templates(self, registry, sample_template):
        """Test listing templates with optional type filter."""
        registry.register_template(sample_template, save_to_disk=False)
        
        # Test listing all templates
        all_templates = registry.list_templates()
        assert len(all_templates) > 0
        
        # Test filtering by type
        simple_templates = registry.list_templates(TemplateType.SIMPLE)
        custom_templates = registry.list_templates(TemplateType.CUSTOM)
        
        assert len(simple_templates) >= 1
        assert len(custom_templates) >= 1
        assert sample_template in custom_templates
    
    def test_find_templates_by_criteria(self, registry):
        """Test finding templates by criteria."""
        # Find simple complexity templates
        simple_templates = registry.find_templates_by_criteria(complexity="simple")
        assert len(simple_templates) > 0
        
        # Find templates with max duration
        quick_templates = registry.find_templates_by_criteria(max_duration=10)
        assert all(t.metadata.estimated_duration_minutes <= 10 for t in quick_templates)
        
        # Find templates with max cost
        cheap_templates = registry.find_templates_by_criteria(max_cost=0.1)
        assert all(t.metadata.estimated_cost_usd <= 0.1 for t in cheap_templates)
        
        # Find templates by tags
        tagged_templates = registry.find_templates_by_criteria(tags={"simple"})
        assert len(tagged_templates) > 0
    
    def test_save_and_load_template(self, registry, sample_template, tmp_path):
        """Test saving and loading templates."""
        # Save template
        registry.register_template(sample_template, save_to_disk=True)
        
        # Check file was created
        template_file = tmp_path / f"{sample_template.id}.json"
        assert template_file.exists()
        
        # Load template from file
        loaded_template = registry.load_template_from_file(template_file)
        assert loaded_template is not None
        assert loaded_template.id == sample_template.id
        assert loaded_template.metadata.name == sample_template.metadata.name
    
    def test_template_stats(self, registry, sample_template):
        """Test getting template statistics."""
        registry.register_template(sample_template, save_to_disk=False)
        
        stats = registry.get_template_stats()
        
        assert 'total_templates' in stats
        assert 'by_type' in stats
        assert 'by_complexity' in stats
        assert 'avg_duration' in stats
        assert 'avg_cost' in stats
        
        assert stats['total_templates'] > 0
        assert isinstance(stats['avg_duration'], float)
        assert isinstance(stats['avg_cost'], float)
    
    def test_template_conversion_to_workflow(self, sample_template):
        """Test converting template to workflow definition."""
        workflow_def = sample_template.to_workflow_definition()
        
        assert workflow_def.id == sample_template.id
        assert workflow_def.name == sample_template.metadata.name
        assert workflow_def.description == sample_template.metadata.description
        assert workflow_def.participants == [p.id for p in sample_template.participants]


class TestNotificationChannels:
    """Test suite for notification delivery channels."""
    
    @pytest.fixture
    def sample_notification(self):
        """Create a sample notification for testing."""
        content = NotificationContent(
            title="Test Notification",
            message="This is a test notification",
            context={"test": "data"},
            action_required=True,
            deadline=datetime.now() + timedelta(hours=1)
        )
        
        return Notification(
            id=uuid4(),
            type=NotificationType.TURN_NOTIFICATION,
            priority=NotificationPriority.NORMAL,
            recipient_id="test_participant",
            content=content,
            created_at=datetime.now(),
            channels=[DeliveryChannel.IN_MEMORY]
        )
    
    def test_in_memory_channel(self, sample_notification):
        """Test in-memory delivery channel."""
        channel = InMemoryChannel()
        
        # Test delivery
        delivered = asyncio.run(channel.deliver(sample_notification))
        assert delivered is True
        
        # Test retrieval
        notifications = channel.get_pending_notifications("test_participant")
        assert len(notifications) == 1
        assert notifications[0].id == sample_notification.id
        
        # Test acknowledgment
        acknowledged = channel.acknowledge_notification("test_participant", sample_notification.id)
        assert acknowledged is True
        assert notifications[0].is_acknowledged
    
    @pytest.mark.asyncio
    async def test_in_memory_channel_callback(self, sample_notification):
        """Test in-memory channel with delivery callback."""
        channel = InMemoryChannel()
        callback_called = False
        
        async def test_callback(notification):
            nonlocal callback_called
            callback_called = True
            assert notification.id == sample_notification.id
        
        channel.register_callback("test_participant", test_callback)
        
        delivered = await channel.deliver(sample_notification)
        assert delivered is True
        assert callback_called is True
    
    @pytest.mark.asyncio
    async def test_webhook_channel(self, sample_notification):
        """Test webhook delivery channel."""
        channel = WebhookChannel()
        
        # Register webhook URL
        channel.register_webhook("test_participant", "https://example.com/webhook")
        
        # Mock aiohttp session
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            channel.session = mock_session
            
            delivered = await channel.deliver(sample_notification)
            assert delivered is True
            
            # Verify webhook was called
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            assert "https://example.com/webhook" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_log_channel(self, sample_notification):
        """Test log delivery channel."""
        channel = LogChannel()
        
        with patch('src.orchestration.notification_system.logger') as mock_logger:
            delivered = await channel.deliver(sample_notification)
            assert delivered is True
            
            # Verify log was called
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert "TEST_NOTIFICATION" in str(call_args).upper()
    
    def test_notification_properties(self, sample_notification):
        """Test notification property methods."""
        # Test is_delivered
        assert sample_notification.is_delivered is False
        sample_notification.delivered_at = datetime.now()
        assert sample_notification.is_delivered is True
        
        # Test is_acknowledged
        assert sample_notification.is_acknowledged is False
        sample_notification.acknowledged_at = datetime.now()
        assert sample_notification.is_acknowledged is True
        
        # Test is_overdue (deadline in future)
        assert sample_notification.is_overdue is False
        
        # Test is_overdue (deadline in past)
        sample_notification.content.deadline = datetime.now() - timedelta(hours=1)
        sample_notification.acknowledged_at = None  # Reset acknowledgment
        assert sample_notification.is_overdue is True


class TestNotificationScheduler:
    """Test suite for the notification scheduler."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a test notification scheduler."""
        return NotificationScheduler()
    
    @pytest.fixture
    def sample_notification(self):
        """Create a sample notification for testing."""
        content = NotificationContent(
            title="Test Notification",
            message="This is a test notification"
        )
        
        return Notification(
            id=uuid4(),
            type=NotificationType.TURN_NOTIFICATION,
            priority=NotificationPriority.NORMAL,
            recipient_id="test_participant",
            content=content,
            created_at=datetime.now(),
            channels=[DeliveryChannel.IN_MEMORY]
        )
    
    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert DeliveryChannel.IN_MEMORY in scheduler.channels
        assert DeliveryChannel.WEBHOOK in scheduler.channels
        assert DeliveryChannel.LOG in scheduler.channels
        assert not scheduler._running
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test starting and stopping the scheduler."""
        # Start scheduler
        await scheduler.start()
        assert scheduler._running is True
        assert scheduler._scheduler_task is not None
        
        # Stop scheduler
        await scheduler.stop()
        assert scheduler._running is False
    
    def test_schedule_notification(self, scheduler, sample_notification):
        """Test scheduling a notification."""
        initial_count = len(scheduler.pending_notifications)
        scheduler.schedule_notification(sample_notification)
        
        assert len(scheduler.pending_notifications) == initial_count + 1
        assert sample_notification in scheduler.pending_notifications
    
    @pytest.mark.asyncio
    async def test_notification_delivery(self, scheduler, sample_notification):
        """Test notification delivery process."""
        scheduler.schedule_notification(sample_notification)
        
        # Process pending notifications
        await scheduler._process_pending_notifications()
        
        # Check notification was delivered
        assert sample_notification not in scheduler.pending_notifications
        assert sample_notification in scheduler.delivered_notifications
        assert sample_notification.is_delivered
    
    @pytest.mark.asyncio
    async def test_notification_retry_logic(self, scheduler):
        """Test notification retry logic."""
        # Create notification with failing channel
        content = NotificationContent(title="Test", message="Test")
        notification = Notification(
            id=uuid4(),
            type=NotificationType.TURN_NOTIFICATION,
            priority=NotificationPriority.NORMAL,
            recipient_id="nonexistent_participant",
            content=content,
            created_at=datetime.now(),
            channels=[DeliveryChannel.WEBHOOK],  # Will fail without URL
            max_retries=2
        )
        
        scheduler.schedule_notification(notification)
        
        # Process notifications (should fail and retry)
        await scheduler._process_pending_notifications()
        
        # Check retry was scheduled
        assert notification.retry_count > 0
        assert notification in scheduler.pending_notifications or notification in scheduler.delivered_notifications
    
    def test_participant_preferences(self, scheduler):
        """Test setting participant preferences."""
        preferences = {
            'channels': ['in_memory', 'log'],
            'priority_threshold': 'normal'
        }
        
        scheduler.set_participant_preferences("test_participant", preferences)
        
        assert "test_participant" in scheduler.participant_preferences
        assert scheduler.participant_preferences["test_participant"] == preferences


class TestParticipantNotificationManager:
    """Test suite for the participant notification manager."""
    
    @pytest.fixture
    def event_bus(self):
        """Create a test event bus."""
        return EventBus()
    
    @pytest.fixture
    def notification_system(self, event_bus):
        """Create a complete notification system."""
        return create_notification_system(event_bus)
    
    @pytest.fixture
    def manager(self, notification_system):
        """Get the notification manager."""
        scheduler, manager = notification_system
        return manager
    
    @pytest.fixture
    def sample_participant(self):
        """Create a sample participant."""
        return ParticipantConfig(
            id="test_participant",
            name="Test Participant",
            role=ParticipantRole.PROPOSER,
            ai_model="test-model"
        )
    
    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.scheduler is not None
        assert manager.event_bus is not None
        assert len(manager.participants) == 0
        assert len(manager.active_debates) == 0
    
    def test_register_participant(self, manager, sample_participant):
        """Test registering a participant."""
        manager.register_participant(sample_participant)
        
        assert sample_participant.id in manager.participants
        assert manager.participants[sample_participant.id] == sample_participant
    
    @pytest.mark.asyncio
    async def test_send_notification(self, manager, sample_participant):
        """Test sending a notification."""
        manager.register_participant(sample_participant)
        
        notification_id = await manager.send_notification(
            sample_participant.id,
            NotificationType.TURN_NOTIFICATION,
            NotificationContent(
                title="Test Notification",
                message="Test message"
            )
        )
        
        assert notification_id is not None
        
        # Check notification was scheduled
        pending = manager.scheduler.get_pending_notifications(sample_participant.id)
        assert len(pending) >= 1
    
    @pytest.mark.asyncio
    async def test_debate_started_handling(self, manager, event_bus, sample_participant):
        """Test handling debate started events."""
        manager.register_participant(sample_participant)
        
        # Start scheduler to process notifications
        await manager.scheduler.start()
        
        try:
            # Emit debate started event
            event = DebateStarted(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="DebateStarted",
                aggregate_id=uuid4(),
                debate_id=uuid4(),
                topic="Test Topic",
                participants=[sample_participant.id]
            )
            
            await event_bus.publish(event)
            await asyncio.sleep(0.2)  # Allow event processing
            
            # Check notification was sent
            notifications = manager.get_participant_notifications(sample_participant.id)
            debate_start_notifications = [
                n for n in notifications 
                if n.type == NotificationType.DEBATE_STARTED
            ]
            assert len(debate_start_notifications) >= 1
            
        finally:
            await manager.scheduler.stop()
    
    @pytest.mark.asyncio
    async def test_round_started_handling(self, manager, event_bus, sample_participant):
        """Test handling round started events."""
        manager.register_participant(sample_participant)
        
        await manager.scheduler.start()
        
        try:
            event = RoundStarted(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="RoundStarted",
                aggregate_id=uuid4(),
                debate_id=uuid4(),
                round_number=1,
                participants=[sample_participant.id]
            )
            
            await event_bus.publish(event)
            await asyncio.sleep(0.2)
            
            notifications = manager.get_participant_notifications(sample_participant.id)
            round_start_notifications = [
                n for n in notifications 
                if n.type == NotificationType.ROUND_STARTED
            ]
            assert len(round_start_notifications) >= 1
            
            # Check action required and deadline
            notification = round_start_notifications[0]
            assert notification.content.action_required is True
            assert notification.content.deadline is not None
            
        finally:
            await manager.scheduler.stop()
    
    @pytest.mark.asyncio
    async def test_escalation_notification(self, manager, sample_participant):
        """Test escalation notification."""
        manager.register_participant(sample_participant)
        
        debate_id = uuid4()
        await manager.notify_escalation(debate_id, "Complex debate requires human review")
        
        # Check notification was sent
        pending = manager.scheduler.get_pending_notifications(sample_participant.id)
        escalation_notifications = [
            n for n in pending 
            if n.type == NotificationType.ESCALATION_NOTICE
        ]
        assert len(escalation_notifications) >= 1
        
        notification = escalation_notifications[0]
        assert notification.priority == NotificationPriority.URGENT
        assert "escalation_reason" in notification.content.context
    
    @pytest.mark.asyncio
    async def test_reminder_notification(self, manager, sample_participant):
        """Test reminder notification."""
        manager.register_participant(sample_participant)
        
        original_notification_id = uuid4()
        await manager.send_reminder(
            sample_participant.id,
            original_notification_id,
            "Custom reminder message"
        )
        
        pending = manager.scheduler.get_pending_notifications(sample_participant.id)
        reminder_notifications = [
            n for n in pending 
            if n.type == NotificationType.REMINDER
        ]
        assert len(reminder_notifications) >= 1
        
        notification = reminder_notifications[0]
        assert "Custom reminder message" in notification.content.message
        assert notification.priority == NotificationPriority.HIGH
    
    def test_acknowledge_notification(self, manager, sample_participant):
        """Test acknowledging notifications."""
        manager.register_participant(sample_participant)
        
        # Get in-memory channel and add a test notification
        in_memory_channel = manager.scheduler.get_channel(DeliveryChannel.IN_MEMORY)
        
        content = NotificationContent(title="Test", message="Test")
        notification = Notification(
            id=uuid4(),
            type=NotificationType.TURN_NOTIFICATION,
            priority=NotificationPriority.NORMAL,
            recipient_id=sample_participant.id,
            content=content,
            created_at=datetime.now()
        )
        
        # Deliver notification to in-memory channel
        asyncio.run(in_memory_channel.deliver(notification))
        
        # Acknowledge notification
        acknowledged = manager.acknowledge_notification(sample_participant.id, notification.id)
        assert acknowledged is True


class TestIntegration:
    """Integration tests for template and notification systems."""
    
    @pytest.fixture
    def complete_system(self, tmp_path):
        """Create a complete orchestration system with templates and notifications."""
        event_bus = EventBus()
        template_registry = TemplateRegistry(storage_path=tmp_path)
        scheduler, notification_manager = create_notification_system(event_bus)
        
        return {
            'event_bus': event_bus,
            'template_registry': template_registry,
            'scheduler': scheduler,
            'notification_manager': notification_manager
        }
    
    def test_template_notification_integration(self, complete_system):
        """Test integration between templates and notifications."""
        template_registry = complete_system['template_registry']
        notification_manager = complete_system['notification_manager']
        
        # Get a complex template
        complex_template = template_registry.get_template("complex_debate")
        assert complex_template is not None
        
        # Register participants from template
        for participant in complex_template.participants:
            notification_manager.register_participant(participant)
        
        # Verify participants are registered
        assert len(notification_manager.participants) >= 3
        
        # Check that different participant roles can receive notifications
        proposer = complex_template.get_participant_by_role(ParticipantRole.PROPOSER)
        opponent = complex_template.get_participant_by_role(ParticipantRole.OPPONENT)
        reviewer = complex_template.get_participant_by_role(ParticipantRole.REVIEWER)
        
        assert proposer is not None
        assert opponent is not None
        assert reviewer is not None
        
        assert proposer.id in notification_manager.participants
        assert opponent.id in notification_manager.participants
        assert reviewer.id in notification_manager.participants
    
    @pytest.mark.asyncio
    async def test_end_to_end_template_notification_flow(self, complete_system):
        """Test end-to-end flow from template to notifications."""
        event_bus = complete_system['event_bus']
        template_registry = complete_system['template_registry']
        scheduler = complete_system['scheduler']
        notification_manager = complete_system['notification_manager']
        
        # Start scheduler
        await scheduler.start()
        
        try:
            # Get standard template
            template = template_registry.get_template("standard_debate")
            
            # Register participants
            for participant in template.participants:
                notification_manager.register_participant(participant)
            
            # Simulate debate flow
            debate_id = uuid4()
            
            # Start debate
            debate_started = DebateStarted(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="DebateStarted",
                aggregate_id=debate_id,
                debate_id=debate_id,
                topic="Test Integration Topic",
                participants=[p.id for p in template.participants]
            )
            
            await event_bus.publish(debate_started)
            await asyncio.sleep(0.2)
            
            # Start round
            round_started = RoundStarted(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="RoundStarted",
                aggregate_id=debate_id,
                debate_id=debate_id,
                round_number=1,
                participants=[p.id for p in template.participants]
            )
            
            await event_bus.publish(round_started)
            await asyncio.sleep(0.2)
            
            # Check that notifications were sent to all participants
            for participant in template.participants:
                notifications = notification_manager.get_participant_notifications(participant.id)
                
                # Should have both debate started and round started notifications
                debate_notifications = [n for n in notifications if n.type == NotificationType.DEBATE_STARTED]
                round_notifications = [n for n in notifications if n.type == NotificationType.ROUND_STARTED]
                
                assert len(debate_notifications) >= 1
                assert len(round_notifications) >= 1
            
        finally:
            await scheduler.stop()
    
    def test_template_workflow_compatibility(self, complete_system):
        """Test that templates are compatible with workflow system."""
        template_registry = complete_system['template_registry']
        
        # Test all default templates
        for template_id in ["simple_debate", "standard_debate", "complex_debate"]:
            template = template_registry.get_template(template_id)
            assert template is not None
            
            # Convert to workflow definition
            workflow_def = template.to_workflow_definition()
            
            # Verify workflow definition is valid
            assert workflow_def.id == template.id
            assert workflow_def.name == template.metadata.name
            assert len(workflow_def.participants) > 0
            assert len(workflow_def.steps) > 0
            assert workflow_def.config is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])