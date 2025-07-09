#!/usr/bin/env python3
"""
Example: Using the Webhook Notification System

This example demonstrates how to use the webhook notification system
to receive notifications about system events.
"""

import asyncio
import json
from datetime import datetime
from uuid import uuid4

from src.webhooks import WebhookService, WebhookEventHandler, WebhookEndpoint, WebhookEventType
from src.events.event_bus import EventBus
from src.contexts.debate.events import DecisionMade, DebateCompleted


async def main():
    """Example usage of the webhook system"""
    print("🔔 Webhook System Example")
    print("=" * 50)
    
    # Initialize services
    webhook_service = WebhookService()
    event_bus = EventBus()
    webhook_handler = WebhookEventHandler(webhook_service, event_bus)
    
    # Start services
    await webhook_service.start()
    await event_bus.start()
    await webhook_handler.start()
    
    try:
        # 1. Add webhook endpoints
        print("\n1. Adding webhook endpoints...")
        
        # Add endpoint for decision events
        decision_endpoint = WebhookEndpoint(
            url="https://httpbin.org/post",
            event_types={WebhookEventType.DECISION_MADE},
            secret="my-secret-key",
            description="Webhook for decision notifications",
        )
        decision_endpoint_id = webhook_service.add_endpoint(decision_endpoint)
        print(f"   ✅ Added decision endpoint: {decision_endpoint_id}")
        
        # Add endpoint for debate events
        debate_endpoint = WebhookEndpoint(
            url="https://httpbin.org/post",
            event_types={WebhookEventType.DEBATE_COMPLETED, WebhookEventType.CONSENSUS_REACHED},
            secret="my-secret-key",
            description="Webhook for debate notifications",
        )
        debate_endpoint_id = webhook_service.add_endpoint(debate_endpoint)
        print(f"   ✅ Added debate endpoint: {debate_endpoint_id}")
        
        # 2. List all endpoints
        print("\n2. Listing webhook endpoints...")
        endpoints = webhook_service.list_endpoints()
        for endpoint in endpoints:
            print(f"   📍 {endpoint.url} - Events: {[et.value for et in endpoint.event_types]}")
        
        # 3. Send webhook notifications directly
        print("\n3. Sending webhook notifications...")
        
        # Send decision notification
        decision_attempts = await webhook_service.send_webhook_notification(
            event_type=WebhookEventType.DECISION_MADE,
            event_data={
                "decision_id": str(uuid4()),
                "question": "Should we implement feature X?",
                "recommendation": "Yes, implement feature X with proper testing",
                "confidence": 0.85,
                "implementation_required": True,
            }
        )
        print(f"   ✅ Sent decision notification to {len(decision_attempts)} endpoints")
        
        # Send debate completion notification
        debate_attempts = await webhook_service.send_webhook_notification(
            event_type=WebhookEventType.DEBATE_COMPLETED,
            event_data={
                "debate_id": str(uuid4()),
                "total_rounds": 3,
                "total_arguments": 6,
                "final_consensus": "Consensus reached on implementing feature X",
                "decision_id": str(uuid4()),
            }
        )
        print(f"   ✅ Sent debate completion notification to {len(debate_attempts)} endpoints")
        
        # 4. Publish domain events (will trigger webhooks automatically)
        print("\n4. Publishing domain events...")
        
        # Create and publish a DecisionMade event
        decision_event = DecisionMade(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DecisionMade",
            aggregate_id=uuid4(),
            decision_id=uuid4(),
            debate_id=uuid4(),
            decision_type="complex",
            question="Should we add logging to the system?",
            recommendation="Yes, implement structured logging",
            confidence=0.90,
            implementation_required=True,
        )
        await event_bus.publish(decision_event)
        print("   ✅ Published DecisionMade event")
        
        # Create and publish a DebateCompleted event
        debate_event = DebateCompleted(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DebateCompleted",
            aggregate_id=uuid4(),
            debate_id=uuid4(),
            total_rounds=2,
            total_arguments=4,
            final_consensus="Implement structured logging with proper log levels",
            decision_id=uuid4(),
        )
        await event_bus.publish(debate_event)
        print("   ✅ Published DebateCompleted event")
        
        # Give some time for events to be processed
        await asyncio.sleep(0.5)
        
        # 5. Check delivery statistics
        print("\n5. Webhook delivery statistics...")
        stats = webhook_service.get_delivery_stats()
        print(f"   📊 Total deliveries: {stats.total_deliveries}")
        print(f"   ✅ Successful: {stats.successful_deliveries}")
        print(f"   ❌ Failed: {stats.failed_deliveries}")
        print(f"   📈 Success rate: {stats.success_rate():.1f}%")
        print(f"   ⏱️  Average delivery time: {stats.average_delivery_time_ms:.1f}ms")
        
        # 6. Get delivery history
        print("\n6. Recent delivery attempts...")
        recent_deliveries = webhook_service.get_delivery_history(limit=5)
        for i, delivery in enumerate(recent_deliveries, 1):
            print(f"   {i}. {delivery.payload.event_type.value} - {delivery.status.value}")
            print(f"      URL: {webhook_service.get_endpoint(delivery.endpoint_id).url}")
            print(f"      Status: {delivery.response_status}")
            print(f"      Duration: {delivery.duration_ms}ms")
        
        # 7. Test webhook endpoint
        print("\n7. Testing webhook endpoint...")
        test_attempts = await webhook_service.send_webhook_notification(
            event_type=WebhookEventType.DECISION_MADE,
            event_data={
                "test": True,
                "message": "This is a test webhook notification",
                "timestamp": datetime.now().isoformat(),
            }
        )
        
        for attempt in test_attempts:
            endpoint = webhook_service.get_endpoint(attempt.endpoint_id)
            status = "✅ Success" if attempt.status.value == "delivered" else "❌ Failed"
            print(f"   {status} - {endpoint.url} ({attempt.duration_ms}ms)")
        
        # 8. Demonstrate custom webhook
        print("\n8. Sending custom webhook...")
        await webhook_handler.send_custom_webhook(
            event_type=WebhookEventType.EVOLUTION_TRIGGERED,
            event_data={
                "evolution_type": "feature",
                "feature": "webhook_notifications",
                "description": "Successfully implemented webhook notification system",
                "timestamp": datetime.now().isoformat(),
            }
        )
        print("   ✅ Sent custom evolution webhook")
        
        # 9. Error handling example
        print("\n9. Error handling example...")
        try:
            await webhook_handler.send_error_webhook(
                error_type="ValidationError",
                error_message="Invalid input provided",
                component="webhook_example",
                operation="demonstrate_error_handling",
                context={"user_input": "invalid_data"}
            )
            print("   ✅ Sent error webhook")
        except Exception as e:
            print(f"   ❌ Error webhook failed: {e}")
        
        print("\n✅ Webhook system example completed successfully!")
        print("\nThe webhook system is now ready to:")
        print("  • Accept webhook subscriptions via REST API")
        print("  • Deliver notifications with retry logic")
        print("  • Handle domain events automatically")
        print("  • Provide delivery statistics and history")
        print("  • Support custom webhooks for any event type")
        
    finally:
        # Clean up
        await webhook_handler.stop()
        await event_bus.stop()
        await webhook_service.stop()
        print("\n🧹 Services cleaned up")


if __name__ == "__main__":
    asyncio.run(main())