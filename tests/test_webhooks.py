"""
Tests for the webhook notification system
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from src.webhooks.models import (
    WebhookEndpoint,
    WebhookEventType,
    WebhookPayload,
    WebhookDeliveryStatus,
    WebhookDeliveryAttempt,
    WebhookStats,
)
from src.webhooks.service import WebhookService
from src.webhooks.event_handler import WebhookEventHandler
from src.events.event_bus import EventBus
from src.contexts.debate.events import DecisionMade, DebateCompleted


class TestWebhookModels:
    """Test webhook domain models"""

    def test_webhook_endpoint_creation(self):
        """Test creating a webhook endpoint"""
        endpoint = WebhookEndpoint(
            url="https://example.com/webhook",
            event_types={WebhookEventType.DECISION_MADE},
            secret="test-secret",
            description="Test webhook",
        )
        
        assert endpoint.url == "https://example.com/webhook"
        assert WebhookEventType.DECISION_MADE in endpoint.event_types
        assert endpoint.secret == "test-secret"
        assert endpoint.is_active is True
        assert endpoint.subscribes_to(WebhookEventType.DECISION_MADE)
        assert not endpoint.subscribes_to(WebhookEventType.DEBATE_COMPLETED)

    def test_webhook_endpoint_serialization(self):
        """Test webhook endpoint serialization"""
        endpoint = WebhookEndpoint(
            url="https://example.com/webhook",
            event_types={WebhookEventType.DECISION_MADE, WebhookEventType.DEBATE_COMPLETED},
            secret="test-secret",
        )
        
        data = endpoint.to_dict()
        assert data["url"] == "https://example.com/webhook"
        assert set(data["event_types"]) == {"decision_made", "debate_completed"}
        assert data["secret"] == "test-secret"
        
        # Test deserialization
        endpoint2 = WebhookEndpoint.from_dict(data)
        assert endpoint2.url == endpoint.url
        assert endpoint2.event_types == endpoint.event_types
        assert endpoint2.secret == endpoint.secret

    def test_webhook_payload_creation(self):
        """Test creating a webhook payload"""
        payload = WebhookPayload(
            event_id=uuid4(),
            event_type=WebhookEventType.DECISION_MADE,
            timestamp=datetime.now(),
            data={"decision": "Test decision"},
        )
        
        assert payload.event_type == WebhookEventType.DECISION_MADE
        assert payload.data["decision"] == "Test decision"
        assert payload.source == "zamaz-debate-system"
        assert payload.version == "1.0"

    def test_webhook_stats_success_rate(self):
        """Test webhook stats calculation"""
        stats = WebhookStats(
            total_deliveries=10,
            successful_deliveries=8,
            failed_deliveries=2,
        )
        
        assert stats.success_rate() == 80.0
        
        # Test with zero deliveries
        empty_stats = WebhookStats()
        assert empty_stats.success_rate() == 0.0


class TestWebhookService:
    """Test webhook service functionality"""

    @pytest.fixture
    async def webhook_service(self, tmp_path):
        """Create a webhook service for testing"""
        service = WebhookService(data_dir=tmp_path)
        await service.start()
        yield service
        await service.stop()

    def test_add_endpoint(self, webhook_service):
        """Test adding a webhook endpoint"""
        endpoint = WebhookEndpoint(
            url="https://example.com/webhook",
            event_types={WebhookEventType.DECISION_MADE},
        )
        
        endpoint_id = webhook_service.add_endpoint(endpoint)
        assert endpoint_id == endpoint.id
        
        # Test retrieval
        retrieved = webhook_service.get_endpoint(endpoint_id)
        assert retrieved is not None
        assert retrieved.url == endpoint.url

    def test_update_endpoint(self, webhook_service):
        """Test updating a webhook endpoint"""
        endpoint = WebhookEndpoint(
            url="https://example.com/webhook",
            event_types={WebhookEventType.DECISION_MADE},
        )
        
        endpoint_id = webhook_service.add_endpoint(endpoint)
        
        # Update endpoint
        updates = {
            "url": "https://updated.com/webhook",
            "event_types": ["decision_made", "debate_completed"],
        }
        
        success = webhook_service.update_endpoint(endpoint_id, updates)
        assert success is True
        
        # Verify updates
        updated = webhook_service.get_endpoint(endpoint_id)
        assert updated.url == "https://updated.com/webhook"
        assert WebhookEventType.DEBATE_COMPLETED in updated.event_types

    def test_remove_endpoint(self, webhook_service):
        """Test removing a webhook endpoint"""
        endpoint = WebhookEndpoint(
            url="https://example.com/webhook",
            event_types={WebhookEventType.DECISION_MADE},
        )
        
        endpoint_id = webhook_service.add_endpoint(endpoint)
        
        # Remove endpoint
        success = webhook_service.remove_endpoint(endpoint_id)
        assert success is True
        
        # Verify removal
        retrieved = webhook_service.get_endpoint(endpoint_id)
        assert retrieved is None

    def test_get_endpoints_for_event(self, webhook_service):
        """Test getting endpoints for specific event types"""
        endpoint1 = WebhookEndpoint(
            url="https://example1.com/webhook",
            event_types={WebhookEventType.DECISION_MADE},
        )
        
        endpoint2 = WebhookEndpoint(
            url="https://example2.com/webhook",
            event_types={WebhookEventType.DEBATE_COMPLETED},
        )
        
        endpoint3 = WebhookEndpoint(
            url="https://example3.com/webhook",
            event_types={WebhookEventType.DECISION_MADE, WebhookEventType.DEBATE_COMPLETED},
        )
        
        webhook_service.add_endpoint(endpoint1)
        webhook_service.add_endpoint(endpoint2)
        webhook_service.add_endpoint(endpoint3)
        
        # Test filtering
        decision_endpoints = webhook_service.get_endpoints_for_event(WebhookEventType.DECISION_MADE)
        assert len(decision_endpoints) == 2
        assert any(ep.url == "https://example1.com/webhook" for ep in decision_endpoints)
        assert any(ep.url == "https://example3.com/webhook" for ep in decision_endpoints)
        
        debate_endpoints = webhook_service.get_endpoints_for_event(WebhookEventType.DEBATE_COMPLETED)
        assert len(debate_endpoints) == 2
        assert any(ep.url == "https://example2.com/webhook" for ep in debate_endpoints)
        assert any(ep.url == "https://example3.com/webhook" for ep in debate_endpoints)

    @pytest.mark.asyncio
    async def test_send_webhook_notification(self, webhook_service):
        """Test sending webhook notifications"""
        endpoint = WebhookEndpoint(
            url="https://httpbin.org/post",  # Using httpbin for testing
            event_types={WebhookEventType.DECISION_MADE},
        )
        
        webhook_service.add_endpoint(endpoint)
        
        # Mock HTTP client response
        with patch.object(webhook_service, '_http_client') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "ok"}'
            mock_client.post.return_value = mock_response
            
            # Send notification
            delivery_attempts = await webhook_service.send_webhook_notification(
                event_type=WebhookEventType.DECISION_MADE,
                event_data={"decision": "Test decision"},
            )
            
            assert len(delivery_attempts) == 1
            attempt = delivery_attempts[0]
            assert attempt.status == WebhookDeliveryStatus.DELIVERED
            assert attempt.response_status == 200

    def test_generate_signature(self, webhook_service):
        """Test webhook signature generation"""
        payload = '{"test": "data"}'
        secret = "test-secret"
        
        signature = webhook_service._generate_signature(payload, secret)
        assert signature.startswith("sha256=")
        
        # Test verification
        is_valid = webhook_service.verify_signature(payload, signature, secret)
        assert is_valid is True
        
        # Test with wrong secret
        is_valid_wrong = webhook_service.verify_signature(payload, signature, "wrong-secret")
        assert is_valid_wrong is False


class TestWebhookEventHandler:
    """Test webhook event handler"""

    @pytest.fixture
    async def event_handler_setup(self, tmp_path):
        """Set up event handler for testing"""
        webhook_service = WebhookService(data_dir=tmp_path)
        event_bus = EventBus()
        event_handler = WebhookEventHandler(webhook_service, event_bus)
        
        await webhook_service.start()
        await event_bus.start()
        await event_handler.start()
        
        yield webhook_service, event_bus, event_handler
        
        await event_handler.stop()
        await event_bus.stop()
        await webhook_service.stop()

    @pytest.mark.asyncio
    async def test_handle_decision_made_event(self, event_handler_setup):
        """Test handling DecisionMade events"""
        webhook_service, event_bus, event_handler = event_handler_setup
        
        # Add webhook endpoint
        endpoint = WebhookEndpoint(
            url="https://example.com/webhook",
            event_types={WebhookEventType.DECISION_MADE},
        )
        webhook_service.add_endpoint(endpoint)
        
        # Mock webhook delivery
        with patch.object(webhook_service, 'send_webhook_notification') as mock_send:
            mock_send.return_value = []
            
            # Create and publish event
            event = DecisionMade(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="DecisionMade",
                aggregate_id=uuid4(),
                decision_id=uuid4(),
                debate_id=uuid4(),
                decision_type="complex",
                question="Test question",
                recommendation="Test recommendation",
                confidence=0.8,
                implementation_required=True,
            )
            
            await event_bus.publish(event)
            
            # Allow some time for event processing
            await asyncio.sleep(0.1)
            
            # Verify webhook was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[1]['event_type'] == WebhookEventType.DECISION_MADE
            assert call_args[1]['event_data']['question'] == "Test question"

    @pytest.mark.asyncio
    async def test_handle_debate_completed_event(self, event_handler_setup):
        """Test handling DebateCompleted events"""
        webhook_service, event_bus, event_handler = event_handler_setup
        
        # Add webhook endpoint
        endpoint = WebhookEndpoint(
            url="https://example.com/webhook",
            event_types={WebhookEventType.DEBATE_COMPLETED},
        )
        webhook_service.add_endpoint(endpoint)
        
        # Mock webhook delivery
        with patch.object(webhook_service, 'send_webhook_notification') as mock_send:
            mock_send.return_value = []
            
            # Create and publish event
            event = DebateCompleted(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="DebateCompleted",
                aggregate_id=uuid4(),
                debate_id=uuid4(),
                total_rounds=3,
                total_arguments=6,
                final_consensus="Test consensus",
                decision_id=uuid4(),
            )
            
            await event_bus.publish(event)
            
            # Allow some time for event processing
            await asyncio.sleep(0.1)
            
            # Verify webhook was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[1]['event_type'] == WebhookEventType.DEBATE_COMPLETED
            assert call_args[1]['event_data']['total_rounds'] == 3

    @pytest.mark.asyncio
    async def test_send_custom_webhook(self, event_handler_setup):
        """Test sending custom webhook notifications"""
        webhook_service, event_bus, event_handler = event_handler_setup
        
        # Mock webhook delivery
        with patch.object(webhook_service, 'send_webhook_notification') as mock_send:
            mock_send.return_value = []
            
            # Send custom webhook
            await event_handler.send_custom_webhook(
                event_type=WebhookEventType.EVOLUTION_TRIGGERED,
                event_data={"evolution_type": "feature", "feature": "test_feature"},
            )
            
            # Verify webhook was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[1]['event_type'] == WebhookEventType.EVOLUTION_TRIGGERED
            assert call_args[1]['event_data']['evolution_type'] == "feature"


class TestWebhookIntegration:
    """Test full webhook integration"""

    @pytest.mark.asyncio
    async def test_full_webhook_flow(self, tmp_path):
        """Test complete webhook flow from event to delivery"""
        # Set up services
        webhook_service = WebhookService(data_dir=tmp_path)
        event_bus = EventBus()
        event_handler = WebhookEventHandler(webhook_service, event_bus)
        
        await webhook_service.start()
        await event_bus.start()
        await event_handler.start()
        
        try:
            # Add webhook endpoint
            endpoint = WebhookEndpoint(
                url="https://httpbin.org/post",
                event_types={WebhookEventType.DECISION_MADE},
                secret="test-secret",
            )
            webhook_service.add_endpoint(endpoint)
            
            # Mock successful HTTP response
            with patch.object(webhook_service, '_http_client') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = '{"status": "received"}'
                mock_client.post.return_value = mock_response
                
                # Send webhook notification
                delivery_attempts = await webhook_service.send_webhook_notification(
                    event_type=WebhookEventType.DECISION_MADE,
                    event_data={"decision": "Test decision", "confidence": 0.9},
                )
                
                # Verify delivery
                assert len(delivery_attempts) == 1
                attempt = delivery_attempts[0]
                assert attempt.status == WebhookDeliveryStatus.DELIVERED
                assert attempt.response_status == 200
                assert attempt.duration_ms is not None
                
                # Verify webhook payload was correct
                call_args = mock_client.post.call_args
                assert call_args[0][0] == "https://httpbin.org/post"
                
                # Check headers
                headers = call_args[1]['headers']
                assert headers['Content-Type'] == 'application/json'
                assert 'X-Zamaz-Signature' in headers
                
                # Check payload
                payload_json = call_args[1]['content']
                payload_data = json.loads(payload_json)
                assert payload_data['event_type'] == 'decision_made'
                assert payload_data['data']['decision'] == 'Test decision'
                assert payload_data['source'] == 'zamaz-debate-system'
                
        finally:
            await event_handler.stop()
            await event_bus.stop()
            await webhook_service.stop()

    @pytest.mark.asyncio
    async def test_webhook_retry_logic(self, tmp_path):
        """Test webhook retry logic for failed deliveries"""
        webhook_service = WebhookService(data_dir=tmp_path)
        await webhook_service.start()
        
        try:
            # Add webhook endpoint with retry settings
            endpoint = WebhookEndpoint(
                url="https://httpbin.org/status/500",
                event_types={WebhookEventType.DECISION_MADE},
                max_retries=2,
                retry_delay_seconds=1,
            )
            webhook_service.add_endpoint(endpoint)
            
            # Mock failed HTTP response
            with patch.object(webhook_service, '_http_client') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_client.post.return_value = mock_response
                
                # Send webhook notification (should fail)
                delivery_attempts = await webhook_service.send_webhook_notification(
                    event_type=WebhookEventType.DECISION_MADE,
                    event_data={"decision": "Test decision"},
                )
                
                # Verify initial failure
                assert len(delivery_attempts) == 1
                attempt = delivery_attempts[0]
                assert attempt.status == WebhookDeliveryStatus.FAILED
                assert attempt.response_status == 500
                assert attempt.attempt_number == 1
                
                # Mock successful retry
                mock_response.status_code = 200
                mock_response.text = "OK"
                
                # Manually trigger retry (in real scenario, this would be scheduled)
                retry_attempts = await webhook_service.retry_failed_deliveries()
                
                # Verify retry was successful
                assert len(retry_attempts) == 1
                retry_attempt = retry_attempts[0]
                assert retry_attempt.status == WebhookDeliveryStatus.DELIVERED
                assert retry_attempt.response_status == 200
                assert retry_attempt.attempt_number == 2
                
        finally:
            await webhook_service.stop()


if __name__ == "__main__":
    pytest.main([__file__])