#!/usr/bin/env python3
"""
Test creating debates via Kafka events
This simulates external systems triggering debates through event streaming
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.events import DomainEvent, subscribe
from src.infrastructure.kafka import (
    KafkaConfig,
    KafkaEventProducer,
    HybridEventBus,
    get_hybrid_event_bus,
)
from src.contexts.debate import DebateRequested, DebateStarted, DebateCompleted
from src.contexts.implementation import TaskCreated, PullRequestCreated

# For browser automation
from pyppeteer import launch


class DebateViaKafkaTest:
    """Test creating debates through Kafka events"""
    
    def __init__(self):
        self.kafka_config = KafkaConfig.from_env()
        self.producer = KafkaEventProducer(self.kafka_config)
        self.events_received = []
        self.debate_completed = None
        self.pr_created = None
        self.task_created = None
    
    async def setup_event_handlers(self, bus: HybridEventBus):
        """Set up handlers to track events"""
        
        @subscribe(DebateCompleted, context="test", priority=10)
        async def track_debate_completed(event: DebateCompleted):
            print(f"✅ Debate completed: {event.topic}")
            print(f"   Winner: {event.winner}")
            print(f"   Decision Type: {event.decision_type}")
            self.debate_completed = event
            self.events_received.append(event)
        
        @subscribe(PullRequestCreated, context="test", priority=10)
        async def track_pr_created(event: PullRequestCreated):
            print(f"✅ PR created: {event.title}")
            print(f"   PR Number: {event.pr_number}")
            self.pr_created = event
            self.events_received.append(event)
        
        @subscribe(TaskCreated, context="test", priority=10)
        async def track_task_created(event: TaskCreated):
            print(f"✅ Task created: {event.title}")
            print(f"   Priority: {event.priority}")
            self.task_created = event
            self.events_received.append(event)
    
    def create_debate_request_event(self, question: str, context: str) -> DebateRequested:
        """Create a DebateRequested event"""
        return DebateRequested(
            debate_id=uuid4(),
            question=question,
            context=context,
            requester="kafka-test",
            metadata={
                "source": "kafka",
                "test": True,
                "timestamp": datetime.now().isoformat()
            },
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DebateRequested",
            aggregate_id=uuid4(),
            version=1,
        )
    
    async def publish_debate_request_via_kafka(self, question: str, context: str):
        """Publish a debate request directly to Kafka"""
        print(f"\n📤 Publishing debate request to Kafka...")
        print(f"   Question: {question}")
        print(f"   Context: {context}")
        
        # Create the event
        event = self.create_debate_request_event(question, context)
        
        # Publish to Kafka
        self.producer.publish(event, context="debate")
        self.producer.flush()
        
        print(f"✅ Published DebateRequested event (ID: {event.event_id})")
        return event
    
    async def simulate_debate_completion(self, request_event: DebateRequested):
        """Simulate the debate system processing the request"""
        print("\n🤖 Simulating debate processing...")
        
        # In a real system, the DebateNucleus would handle this
        # For testing, we'll create a completion event
        
        # First, create a DebateStarted event
        started = DebateStarted(
            debate_id=request_event.debate_id,
            topic=request_event.question,
            context=request_event.context,
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DebateStarted",
            aggregate_id=request_event.debate_id,
            version=1,
        )
        
        self.producer.publish(started, context="debate")
        
        # Wait a bit to simulate debate processing
        await asyncio.sleep(2)
        
        # Create completion event
        completed = DebateCompleted(
            debate_id=request_event.debate_id,
            topic=request_event.question,
            winner="Claude",
            consensus=True,
            decision_type="COMPLEX",  # This should trigger PR creation
            decision_id=uuid4(),
            summary="After careful analysis, implementing Kafka monitoring is critical for production readiness.",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DebateCompleted",
            aggregate_id=request_event.debate_id,
            version=1,
        )
        
        self.producer.publish(completed, context="debate")
        self.producer.flush()
        
        print(f"✅ Published DebateCompleted event")
        return completed
    
    async def wait_for_events(self, timeout: int = 30):
        """Wait for events to be processed"""
        print(f"\n⏳ Waiting up to {timeout}s for event processing...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.debate_completed and (self.pr_created or self.task_created):
                print("✅ All expected events received!")
                return True
            await asyncio.sleep(1)
        
        print("⏱️  Timeout reached")
        return False
    
    def check_pr_files(self):
        """Check if PR files were created"""
        print("\n🔍 Checking PR files...")
        
        pr_drafts_dir = Path("data/pr_drafts")
        if not pr_drafts_dir.exists():
            print("❌ PR drafts directory not found")
            return False
        
        # Look for recent PR drafts
        pr_files = sorted(pr_drafts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if pr_files:
            print(f"✅ Found {len(pr_files)} PR draft(s)")
            # Check the most recent one
            with open(pr_files[0]) as f:
                pr_data = json.load(f)
                print(f"   📄 Title: {pr_data.get('title', 'N/A')}")
                print(f"   🌿 Branch: {pr_data.get('branch', 'N/A')}")
                print(f"   📝 Description: {pr_data.get('description', 'N/A')[:100]}...")
                return True
        else:
            print("❌ No PR drafts found")
            return False
    
    async def validate_with_puppeteer(self):
        """Use Puppeteer to check the web UI"""
        print("\n🌐 Validating web UI with Puppeteer...")
        
        browser = await launch(headless=True, args=['--no-sandbox'])
        page = await browser.newPage()
        
        try:
            # Navigate to stats endpoint
            await page.goto('http://localhost:8000/stats', {'waitUntil': 'networkidle0'})
            content = await page.content()
            
            # Parse stats
            try:
                stats = json.loads(await page.evaluate('() => document.body.textContent'))
                print(f"📊 System Stats:")
                print(f"   Total Decisions: {stats.get('total_decisions', 0)}")
                print(f"   Total Debates: {stats.get('total_debates', 0)}")
                print(f"   Complex Decisions: {stats.get('complex_decisions', 0)}")
                
                # Take screenshot
                screenshot_dir = Path("localhost_checks")
                screenshot_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                await page.screenshot({
                    'path': f'{screenshot_dir}/kafka_test_stats_{timestamp}.png'
                })
                
            except json.JSONDecodeError:
                print("❌ Failed to parse stats")
            
            # Check PR drafts endpoint
            await page.goto('http://localhost:8000/pr-drafts', {'waitUntil': 'networkidle0'})
            pr_content = await page.evaluate('() => document.body.textContent')
            
            try:
                pr_drafts = json.loads(pr_content)
                if pr_drafts:
                    print(f"\n📋 Found {len(pr_drafts)} PR draft(s) via API")
                    for draft in pr_drafts[:3]:  # Show first 3
                        print(f"   - {draft.get('title', 'N/A')}")
            except:
                print("❌ Failed to parse PR drafts")
                
        finally:
            await browser.close()
    
    def cleanup(self):
        """Clean up resources"""
        self.producer.close()


async def test_kafka_to_pr_flow():
    """Test the complete flow from Kafka event to PR creation"""
    print("🚀 Testing Kafka → Debate → PR → Issue Flow")
    print("=" * 60)
    
    # Check if Kafka is configured
    if not os.getenv('KAFKA_BOOTSTRAP_SERVERS'):
        print("⚠️  KAFKA_BOOTSTRAP_SERVERS not configured")
        print("   Using default: localhost:9092")
    
    tester = DebateViaKafkaTest()
    
    try:
        # Get hybrid event bus
        bus = get_hybrid_event_bus(tester.kafka_config)
        
        # Set up event handlers
        await tester.setup_event_handlers(bus)
        
        # Bridge all events
        bus.kafka_bridge.bridge_all_events()
        
        # Start consumers
        print("\n🎧 Starting Kafka consumers...")
        consumer_task = asyncio.create_task(bus.kafka_bridge.start_consumers())
        
        # Wait for consumers to be ready
        await asyncio.sleep(3)
        
        # Create debate via Kafka
        question = "Should we implement distributed tracing for our Kafka event flows?"
        context = "We need to track events across services and debug complex workflows. This is a COMPLEX architectural decision requiring OpenTelemetry integration."
        
        request_event = await tester.publish_debate_request_via_kafka(question, context)
        
        # Simulate debate processing
        await tester.simulate_debate_completion(request_event)
        
        # Wait for events to propagate
        success = await tester.wait_for_events()
        
        if success:
            print("\n✅ Event flow completed successfully!")
            
            # Check created files
            tester.check_pr_files()
            
            # Validate with Puppeteer
            await tester.validate_with_puppeteer()
            
            # Summary
            print("\n📋 Summary:")
            print(f"   Events received: {len(tester.events_received)}")
            if tester.debate_completed:
                print(f"   ✅ Debate completed: {tester.debate_completed.decision_type}")
            if tester.pr_created:
                print(f"   ✅ PR created: #{tester.pr_created.pr_number}")
            if tester.task_created:
                print(f"   ✅ Task created: {tester.task_created.priority} priority")
        else:
            print("\n❌ Some events were not received in time")
            print(f"   Debate completed: {'✅' if tester.debate_completed else '❌'}")
            print(f"   PR created: {'✅' if tester.pr_created else '❌'}")
            print(f"   Task created: {'✅' if tester.task_created else '❌'}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        tester.cleanup()
        if bus._kafka_enabled:
            bus.disable_kafka()
        
        # Cancel consumer task
        if 'consumer_task' in locals():
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass


async def test_kafka_commands():
    """Show useful Kafka commands for debugging"""
    print("\n📚 Useful Kafka Commands:")
    print("=" * 60)
    print("""
# List topics
docker exec kafka-zamaz kafka-topics --list --bootstrap-server localhost:9092

# Consume debate events
docker exec kafka-zamaz kafka-console-consumer \\
  --bootstrap-server localhost:9092 \\
  --topic debate.events \\
  --from-beginning \\
  --property print.headers=true

# Check consumer groups
docker exec kafka-zamaz kafka-consumer-groups \\
  --bootstrap-server localhost:9092 \\
  --list

# Check consumer lag
docker exec kafka-zamaz kafka-consumer-groups \\
  --bootstrap-server localhost:9092 \\
  --group zamaz-debate-group \\
  --describe

# Produce test event manually
echo '{"event_type":"DebateRequested","question":"Test from CLI"}' | \\
docker exec -i kafka-zamaz kafka-console-producer \\
  --bootstrap-server localhost:9092 \\
  --topic debate.events
""")


async def main():
    """Run the tests"""
    # First, check if server is running
    import subprocess
    result = subprocess.run("curl -s http://localhost:8000/stats", shell=True, capture_output=True)
    if result.returncode != 0:
        print("❌ Web server not running! Start with: make run")
        return
    
    # Check if Kafka is running
    result = subprocess.run("docker ps | grep kafka-zamaz", shell=True, capture_output=True)
    if result.returncode != 0:
        print("⚠️  Kafka container not running")
        print("   Start with: make kafka-up")
        print("   Or run without Kafka (local events only)")
    
    # Run the test
    await test_kafka_to_pr_flow()
    
    # Show commands
    await test_kafka_commands()


if __name__ == "__main__":
    asyncio.run(main())