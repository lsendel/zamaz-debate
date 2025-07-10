#!/usr/bin/env python3
"""
Orchestration Demo Script

This script demonstrates the hybrid debate orchestration system
implementing the state machine approach from Issue #224.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.nucleus import DebateNucleus
from src.orchestration.debate_orchestrator import (
    create_hybrid_orchestrator,
    OrchestrationStrategy,
    DebateOrchestrationState
)


async def demo_simple_decision():
    """Demonstrate simple decision (no orchestration)."""
    print("=" * 60)
    print("🔧 DEMO 1: Simple Decision (Direct Logic)")
    print("=" * 60)
    
    nucleus = DebateNucleus()
    
    result = await nucleus.decide(
        question="Should we rename the variable 'x' to 'user_count'?",
        context="Code readability improvement"
    )
    
    print(f"Question: {result.get('decision', 'No decision')}")
    print(f"Method: {result['method']}")
    print(f"Complexity: {result['complexity']}")
    print(f"Rounds: {result['rounds']}")
    print()


async def demo_orchestrated_decision():
    """Demonstrate orchestrated decision."""
    print("=" * 60) 
    print("🔬 DEMO 2: Complex Decision (Hybrid Orchestration)")
    print("=" * 60)
    
    nucleus = DebateNucleus()
    
    if nucleus.hybrid_orchestrator:
        print("✅ Hybrid orchestrator is available")
        
        result = await nucleus.decide(
            question="What orchestration workflow pattern should we implement for managing AI debates?",
            context="Need to balance deterministic reliability with LLM intelligence for complex architectural decisions"
        )
        
        print(f"Decision Method: {result['method']}")
        print(f"Complexity: {result['complexity']}")
        print(f"Rounds: {result['rounds']}")
        print(f"Orchestration State: {result.get('orchestration_state', 'N/A')}")
        print(f"LLM Decisions: {result.get('llm_decisions', 0)}")
        print(f"Deterministic Decisions: {result.get('deterministic_decisions', 0)}")
        print(f"Execution Time: {result.get('execution_time', 'N/A')} seconds")
        print()
        print("Decision:")
        print("-" * 40)
        print(result.get('decision', 'No decision reached')[:500] + "...")
        
    else:
        print("❌ Hybrid orchestrator not available, using fallback")
        
        result = await nucleus.decide(
            question="What orchestration workflow pattern should we implement?",
            context="Architectural decision"
        )
        
        print(f"Decision Method: {result['method']}")
        print(f"Complexity: {result['complexity']}")
    
    print()


async def demo_orchestration_strategies():
    """Demonstrate different orchestration strategies."""
    print("=" * 60)
    print("⚙️  DEMO 3: Orchestration Strategies Comparison")
    print("=" * 60)
    
    from services.ai_client_factory import AIClientFactory
    
    ai_factory = AIClientFactory()
    
    strategies = [
        (OrchestrationStrategy.DETERMINISTIC_ONLY, "Pure State Machine"),
        (OrchestrationStrategy.HYBRID, "Hybrid (LLM + Deterministic)"),
        (OrchestrationStrategy.LLM_DRIVEN, "LLM-Driven with Fallbacks")
    ]
    
    question = "Should we implement caching for debate results?"
    context = "Performance optimization consideration"
    
    for strategy, description in strategies:
        print(f"\n🎯 Testing {description}")
        print("-" * 40)
        
        try:
            orchestrator = create_hybrid_orchestrator(
                ai_client_factory=ai_factory,
                strategy=strategy
            )
            
            result = await orchestrator.orchestrate_debate(
                question=question,
                context=context,
                complexity="moderate"
            )
            
            print(f"Final State: {result.final_state.value}")
            print(f"LLM Decisions: {result.llm_decisions_made}")
            print(f"Deterministic Decisions: {result.deterministic_decisions_made}")
            print(f"Success: {result.final_state == DebateOrchestrationState.COMPLETED}")
            
            if result.decision:
                print(f"Recommendation: {result.decision.recommendation}")
            
        except Exception as e:
            print(f"❌ Strategy failed: {e}")


async def demo_workflow_loading():
    """Demonstrate workflow definition loading."""
    print("=" * 60)
    print("📋 DEMO 4: Workflow Definition Loading")
    print("=" * 60)
    
    from src.workflows.yaml_loader import load_default_workflows
    
    workflows = load_default_workflows()
    
    print(f"Loaded {len(workflows)} workflow definitions:")
    print()
    
    for workflow in workflows:
        print(f"🔄 {workflow.name}")
        print(f"   ID: {workflow.id}")
        print(f"   Description: {workflow.description}")
        print(f"   Participants: {', '.join(workflow.participants)}")
        print(f"   Steps: {len(workflow.steps)}")
        print(f"   Max Rounds: {workflow.config.max_rounds}")
        print(f"   Consensus Threshold: {workflow.config.consensus_threshold}")
        
        print("   Step Details:")
        for i, step in enumerate(workflow.steps[:3], 1):  # Show first 3 steps
            print(f"     {i}. {step.name} ({step.type.value})")
        
        if len(workflow.steps) > 3:
            print(f"     ... and {len(workflow.steps) - 3} more steps")
        
        print()


async def demo_circuit_breaker():
    """Demonstrate circuit breaker functionality."""
    print("=" * 60)
    print("🔌 DEMO 5: Circuit Breaker Protection")
    print("=" * 60)
    
    from src.orchestration.debate_orchestrator import CircuitBreaker
    
    # Create circuit breaker with low thresholds for demo
    cb = CircuitBreaker(failure_threshold=2, timeout=1.0)
    
    print("Initial state:")
    print(f"  State: {cb.state}")
    print(f"  Can execute: {cb.can_execute()}")
    print(f"  Failure count: {cb.failure_count}")
    print()
    
    print("Simulating failures...")
    
    # First failure
    cb.record_failure()
    print("After 1st failure:")
    print(f"  State: {cb.state}")
    print(f"  Can execute: {cb.can_execute()}")
    print(f"  Failure count: {cb.failure_count}")
    print()
    
    # Second failure - should open circuit
    cb.record_failure()
    print("After 2nd failure:")
    print(f"  State: {cb.state}")
    print(f"  Can execute: {cb.can_execute()}")
    print(f"  Failure count: {cb.failure_count}")
    print()
    
    print("Waiting for recovery timeout...")
    await asyncio.sleep(1.1)  # Wait for timeout
    
    print("After timeout:")
    print(f"  State: {cb.state}")
    print(f"  Can execute: {cb.can_execute()}")
    print()
    
    # Simulate success
    cb.record_success()
    print("After successful operation:")
    print(f"  State: {cb.state}")
    print(f"  Can execute: {cb.can_execute()}")
    print(f"  Failure count: {cb.failure_count}")
    print()


async def main():
    """Run all orchestration demos."""
    print("🧬 Zamaz Debate System - Orchestration Demo")
    print("Demonstrating Issue #224 Implementation")
    print("=" * 60)
    print()
    
    demos = [
        demo_simple_decision,
        demo_orchestrated_decision,
        demo_workflow_loading,
        demo_circuit_breaker,
        demo_orchestration_strategies,
    ]
    
    for demo in demos:
        try:
            await demo()
        except KeyboardInterrupt:
            print("\n👋 Demo interrupted by user")
            break
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            print()
        
        # Wait between demos
        print("Press Enter to continue to next demo...")
        input()
    
    print("🎉 All demos completed!")
    print()
    print("Summary of Orchestration Features:")
    print("  ✅ Hybrid state machine implementation")
    print("  ✅ Circuit breaker protection")
    print("  ✅ YAML workflow definitions")
    print("  ✅ Multiple orchestration strategies")
    print("  ✅ Comprehensive error handling")
    print("  ✅ Integration with existing nucleus")
    print()
    print("The orchestration system successfully implements the")
    print("'Hybrid State Machine Approach' from Issue #224!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        sys.exit(1)