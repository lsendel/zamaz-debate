#!/usr/bin/env python3
"""
Zamaz Debate Nucleus v0.1.0 - Simplified version
A self-improving debate system using Claude Opus 4 and Gemini 2.5 Pro
"""

import asyncio
import json
import os

# Add parent directory to path for imports
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from domain.models import Debate, Decision, DecisionType, ImplementationAssignee
from services.ai_client_factory import AIClientFactory
from services.pr_service import PRService
from src.core.evolution_tracker import EvolutionTracker
from src.core.evolution_implementation_bridge import EvolutionImplementationBridge

# Error handling imports - these will be initialized later to avoid circular imports
try:
    from src.core.error_handler import get_error_handler, with_error_handling
    from src.core.resilience import (
        RetryPolicy,
        retry_async,
        timeout_async,
        with_resilience,
    )
except ImportError:
    # Fallback decorators if imports fail
    def with_error_handling(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def retry_async(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def timeout_async(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    class RetryPolicy:
        def __init__(self, *args, **kwargs):
            pass

    def get_error_handler():
        return None


# Load environment variables
load_dotenv()


class DebateNucleus:
    """Self-contained debate system that can evolve itself"""

    VERSION = "0.1.0"

    def __init__(self, event_bus=None):
        self.claude_client = None
        self.gemini_client = None
        self.debates_dir = None
        self.decision_count = 0
        self.debate_count = 0
        self.event_bus = event_bus

        # Evolution tracker
        self.evolution_tracker = EvolutionTracker()
        
        # Evolution implementation bridge
        self.evolution_bridge = EvolutionImplementationBridge()

        # AI client factory
        self.ai_factory = AIClientFactory()

        # PR service for creating pull requests
        self.pr_service = PRService()

        # Complexity detection
        self.complexity_keywords = {
            "simple": ["rename", "format", "typo", "spacing", "comment", "import"],
            "moderate": ["refactor", "optimize", "clean", "organize", "split", "merge"],
            "complex": [
                "architecture",
                "design",
                "pattern",
                "system",
                "structure",
                "integrate",
                "improve",
                "improvement",
                "evolve",
                "evolution",
                "enhance",
                "feature",
            ],
        }

    async def decide(self, question: str, context: str = "") -> Dict:
        """Main entry point for all decisions"""
        self.decision_count += 1

        complexity = self._assess_complexity(question)
        timestamp = datetime.now()

        if complexity == "simple":
            decision_text = await self._simple_decision(question)
            result = {
                "decision": decision_text,
                "method": "direct",
                "rounds": 0,
                "complexity": complexity,
                "time": timestamp.isoformat(),
            }
            
            # Emit decision event
            await self._emit_decision_event(
                decision_id=f"simple_{self.decision_count}",
                question=question,
                decision_text=decision_text,
                complexity=complexity,
                timestamp=timestamp
            )
            
            return result

        # Complex decisions need debate
        self.debate_count += 1
        result = await self._run_debate(question, context, complexity)

        # Create PR for complex and moderate decisions if enabled
        if complexity in ["complex", "moderate"] and self.pr_service.enabled:
            decision_type = DecisionType.COMPLEX

            # Create Decision object
            decision = Decision(
                id=result.get("debate_id", f"decision_{self.decision_count}"),
                question=question,
                context=context,
                decision_text=result["decision"],
                decision_type=decision_type,
                method=result["method"],
                rounds=result["rounds"],
                timestamp=datetime.fromisoformat(result["time"]),
            )

            # Load debate data if available
            debate_obj = None
            if "debate_id" in result:
                debate_file = self.debates_dir / f"{result['debate_id']}.json"
                if debate_file.exists():
                    with open(debate_file, "r") as f:
                        debate_data = json.load(f)

                    debate_obj = Debate(
                        id=result["debate_id"],
                        question=question,
                        context=context,
                        rounds=debate_data["rounds"],
                        final_decision=debate_data["final_decision"],
                        complexity=debate_data.get("complexity", complexity),
                        start_time=datetime.fromisoformat(debate_data["start_time"]),
                        end_time=datetime.fromisoformat(debate_data["end_time"]),
                    )

            # Create PR if decision qualifies
            if self.pr_service.should_create_pr(decision):
                pr = await self.pr_service.create_pr_for_decision(decision, debate_obj)
                if pr:
                    result["pr_created"] = True
                    result["pr_id"] = pr.id
                    result["pr_branch"] = pr.branch_name
                    result["pr_assignee"] = pr.assignee

        # Emit decision event for complex decisions
        await self._emit_decision_event(
            decision_id=result.get("debate_id", f"decision_{self.decision_count}"),
            question=question,
            decision_text=result["decision"],
            complexity=complexity,
            timestamp=datetime.fromisoformat(result["time"]),
            debate_id=result.get("debate_id")
        )
        
        return result

    def _assess_complexity(self, question: str) -> str:
        """Determine if debate is needed"""
        q_lower = question.lower()

        # Check from most complex to simplest to ensure proper categorization
        for level in ["complex", "moderate", "simple"]:
            keywords = self.complexity_keywords[level]
            if any(k in q_lower for k in keywords):
                return level

        return "moderate"

    async def _simple_decision(self, question: str) -> str:
        """Quick decision without debate"""
        q_lower = question.lower()

        if "rename" in q_lower:
            return "Yes, use descriptive names following Python conventions"
        if "format" in q_lower:
            return "Follow PEP 8 style guide"
        if "comment" in q_lower:
            return "Add docstrings for public methods, inline comments for complex logic"

        return "Proceed with standard best practices"

    def _ensure_clients(self):
        """Lazy initialization of AI clients"""
        if not self.claude_client:
            self.claude_client = self.ai_factory.get_claude_client()

        if not self.gemini_client:
            self.gemini_client = self.ai_factory.get_gemini_client()

    async def _run_debate(self, question: str, context: str, complexity: str) -> Dict:
        """Run a debate between Claude Opus 4 and Gemini 2.5 Pro"""
        self._ensure_clients()
        self._ensure_debates_dir()

        # Use UUID for unique debate IDs to prevent conflicts
        debate_id = f"debate_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        debate_state = {
            "id": debate_id,
            "question": question,
            "context": context,
            "complexity": complexity,
            "rounds": [],
            "start_time": datetime.now().isoformat(),
        }

        # For v0.1.0, we'll do a simplified debate
        claude_response = await self._get_claude_response(question, context)
        gemini_response = await self._get_gemini_response(question, context, complexity)

        debate_state["rounds"].append({"round": 1, "claude": claude_response, "gemini": gemini_response})

        # Analyze if they reached consensus
        claude_yes = any(word in claude_response.lower() for word in ["yes", "should", "recommend", "beneficial"])
        claude_no = any(word in claude_response.lower() for word in ["no", "should not", "avoid", "unnecessary"])
        gemini_yes = any(word in gemini_response.lower() for word in ["yes", "should", "recommend", "beneficial"])
        gemini_no = any(word in gemini_response.lower() for word in ["no", "should not", "avoid", "unnecessary"])

        consensus = (claude_yes and gemini_yes) or (claude_no and gemini_no)

        # Format decision with consensus indicator
        decision = f"Claude's Analysis:\n{claude_response}\n\nGemini's Analysis:\n{gemini_response}\n\nConsensus: {'Yes' if consensus else 'No'}"

        debate_state["final_decision"] = decision
        debate_state["end_time"] = datetime.now().isoformat()

        self._save_debate(debate_state)

        return {
            "decision": decision,
            "method": "debate",
            "rounds": len(debate_state["rounds"]),
            "complexity": complexity,
            "debate_id": debate_id,
            "time": debate_state["end_time"],
        }

    @with_error_handling(component="nucleus", operation="claude_response", reraise=False)
    @retry_async(RetryPolicy(max_attempts=3, initial_delay=2.0))
    @timeout_async(30.0)
    async def _get_claude_response(self, question: str, context: str) -> str:
        """Get Claude Opus 4's perspective"""
        prompt = f"""You are participating in a technical debate about system architecture decisions.

Question: {question}
Context: {context}

Provide a thorough analysis:
1. First, identify potential PROBLEMS or RISKS with this proposal
2. Consider alternative approaches that might be better
3. Analyze the trade-offs (pros AND cons)
4. Only then provide your recommendation with clear reasoning

Be analytical and critical. Don't just agree - really think about what could go wrong."""

        try:
            response = self.claude_client.messages.create(
                model="claude-opus-4-20250514",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            return response.content[0].text
        except Exception as e:
            # Log error for monitoring
            await get_error_handler().handle_error(
                error=e,
                component="nucleus",
                operation="claude_response",
                context={"question": question, "context_length": len(context)},
            )
            return f"Claude error: {str(e)}"

    @with_error_handling(component="nucleus", operation="gemini_response", reraise=False)
    @retry_async(RetryPolicy(max_attempts=3, initial_delay=2.0))
    @timeout_async(30.0)
    async def _get_gemini_response(self, question: str, context: str, complexity: str = "simple") -> str:
        """Get Gemini 2.5 Pro's perspective"""
        prompt = f"""You are participating in a technical debate about system architecture decisions.

Question: {question}
Context: {context}

Provide a critical analysis:
1. What are the DOWNSIDES or CHALLENGES of this approach?
2. What prerequisites or conditions must be met?
3. What simpler alternatives should be considered first?
4. Give your verdict with specific reasoning

Be skeptical and thorough. Challenge assumptions. Consider if this is really necessary."""

        try:
            response = await self.gemini_client.generate_content_async(prompt, complexity)
            return response.text
        except Exception as e:
            # Log error for monitoring
            await get_error_handler().handle_error(
                error=e,
                component="nucleus",
                operation="gemini_response",
                context={"question": question, "complexity": complexity},
            )
            return f"Gemini error: {str(e)}"

    def _ensure_debates_dir(self):
        """Create debates directory on first use"""
        if not self.debates_dir:
            self.debates_dir = Path(__file__).parent.parent.parent / "data" / "debates"
            self.debates_dir.mkdir(parents=True, exist_ok=True)

    def _save_debate(self, debate_state: Dict):
        """Save debate for future reference"""
        filename = self.debates_dir / f"{debate_state['id']}.json"
        with open(filename, "w") as f:
            json.dump(debate_state, f, indent=2)

    async def evolve_self(self) -> Dict:
        """Use debate to improve the debate system itself"""
        evolution_question = "What is the ONE most important improvement to make to this debate system next? Consider: code quality, functionality, performance, and usability. Ensure this is different from previous evolutions."

        evolution_summary = self.evolution_tracker.get_evolution_summary()
        recent_evolutions = self.evolution_tracker.get_recent_evolutions(5)

        # Count actual files on disk for accurate stats
        debates_dir = Path("data/debates")
        decisions_dir = Path("data/decisions")

        debate_count = len(list(debates_dir.glob("*.json"))) if debates_dir.exists() else 0
        decision_count = len(list(decisions_dir.glob("*.json"))) if decisions_dir.exists() else 0

        context = f"""
        Current version: {self.VERSION}
        Decisions made: {decision_count}
        Debates run: {debate_count}
        
        Evolution History:
        Total evolutions: {evolution_summary['total_evolutions']}
        Evolution types: {json.dumps(evolution_summary['evolution_types'], indent=2)}
        
        Recent evolutions:
        {self._format_recent_evolutions(recent_evolutions)}
        """

        improvement = await self.decide(evolution_question, context)

        # Process evolution through implementation bridge if it's a debate result
        if improvement.get("method") == "debate":
            try:
                # Process the evolution decision through the implementation bridge
                implementation_result = await self.evolution_bridge.process_evolution_decision(improvement)
                
                # Add implementation results to the improvement response
                improvement["implementation_result"] = implementation_result
                improvement["evolution_implemented"] = implementation_result.get("status") in ["implemented", "queued"]
                
                # Handle different implementation statuses
                if implementation_result.get("status") == "implemented":
                    improvement["evolution_tracked"] = True
                    improvement["implementation_status"] = "completed"
                    improvement["implementation_message"] = implementation_result.get("message", "")
                elif implementation_result.get("status") == "queued":
                    improvement["evolution_tracked"] = True  
                    improvement["implementation_status"] = "queued"
                    improvement["queue_position"] = implementation_result.get("queue_position", 0)
                elif implementation_result.get("status") == "duplicate":
                    improvement["evolution_tracked"] = False
                    improvement["duplicate_detected"] = True
                    improvement["implementation_status"] = "duplicate"
                else:
                    improvement["evolution_tracked"] = False
                    improvement["implementation_status"] = "failed"
                    improvement["implementation_error"] = implementation_result.get("message", "Unknown error")

                # Still create PR if enabled (for documentation/tracking purposes)
                debate_id = improvement.get("debate_id")
                if debate_id and self.pr_service.enabled:
                    # Load the debate to create PR
                    debate_file = self.debates_dir / f"{debate_id}.json"
                    if debate_file.exists():
                        with open(debate_file, "r") as f:
                            debate_data = json.load(f)

                        decision_text = improvement.get("decision", "")

                        # Create Decision object for PR creation
                        decision = Decision(
                            id=f"evolution_{debate_id}",
                            question=evolution_question,
                            context=context,
                            decision_text=decision_text,
                            decision_type=DecisionType.EVOLUTION,
                            method="debate",
                            rounds=len(debate_data["rounds"]),
                            timestamp=datetime.now(),
                            implementation_assignee=ImplementationAssignee.CLAUDE,
                        )

                        # Create Debate object
                        debate_obj = Debate(
                            id=debate_id,
                            question=evolution_question,
                            context=context,
                            rounds=debate_data["rounds"],
                            final_decision=decision_text,
                            complexity=debate_data.get("complexity", "complex"),
                            start_time=datetime.fromisoformat(debate_data["start_time"]),
                            end_time=datetime.fromisoformat(debate_data["end_time"]),
                        )

                        # Create PR if enabled
                        if self.pr_service.should_create_pr(decision):
                            pr = await self.pr_service.create_pr_for_decision(decision, debate_obj)
                            if pr:
                                improvement["pr_created"] = True
                                improvement["pr_id"] = pr.id
                                improvement["pr_branch"] = pr.branch_name
                                improvement["pr_assignee"] = pr.assignee
                
            except Exception as e:
                # Fallback to old tracking method if implementation bridge fails
                improvement["evolution_tracked"] = False
                improvement["implementation_status"] = "bridge_error"
                improvement["implementation_error"] = f"Implementation bridge failed: {str(e)}"
                
                # Log the error for debugging
                print(f"Evolution implementation bridge error: {str(e)}")

        return improvement

    def _format_recent_evolutions(self, evolutions: List[Dict]) -> str:
        """Format recent evolutions for context"""
        if not evolutions:
            return "No previous evolutions"

        formatted = []
        for i, evo in enumerate(evolutions, 1):
            evo_type = evo.get("type", "unknown").capitalize()
            feature = evo.get("feature", "unknown")
            timestamp = evo.get("timestamp", "unknown")
            date = timestamp[:10] if len(timestamp) >= 10 else timestamp

            formatted.append(f"{i}. {evo_type}: {feature} (Date: {date})")

        return "\n".join(formatted)

    def _extract_evolution_feature(self, decision_text: str) -> str:
        """Extract specific feature from decision text"""
        text_lower = decision_text.lower()

        # More comprehensive feature patterns
        features = {
            "performance profiling": "performance_profiling",
            "performance tracking": "performance_tracking",
            "performance optimization": "performance_optimization",
            "automated testing": "automated_testing",
            "test suite": "automated_testing",
            "plugin": "plugin_architecture",
            "caching": "caching_system",
            "logging": "logging_system",
            "metrics": "metrics_tracking",
            "api": "api_enhancement",
            "documentation": "documentation",
            "security": "security_enhancement",
            "ui": "user_interface",
            "web interface": "web_interface",
            "error handling": "error_handling",
            "validation": "input_validation",
            "monitoring": "monitoring_system",
            "observability": "observability_stack",
            "refactor": "code_refactoring",
            "code quality": "code_quality",
            "configuration": "configuration_management",
            "config management": "configuration_management",
            "rate limit": "rate_limiting",
            "debugging": "debugging_tools",
        }

        # Check for feature patterns
        for pattern, feature in features.items():
            if pattern in text_lower:
                return feature

        # Try to extract from common improvement phrases
        if "observability" in text_lower and "monitoring" in text_lower:
            return "observability_stack"
        elif "performance" in text_lower and "profiling" in text_lower:
            return "performance_profiling"

        return "general_improvement"

    def _extract_evolution_type(self, decision_text: str) -> str:
        """Extract evolution type from decision text"""
        text_lower = decision_text.lower()

        if any(word in text_lower for word in ["add", "implement", "create", "introduce"]):
            return "feature"
        elif any(word in text_lower for word in ["improve", "enhance", "optimize", "better"]):
            return "enhancement"
        elif any(word in text_lower for word in ["fix", "resolve", "correct", "bug"]):
            return "fix"
        elif any(word in text_lower for word in ["refactor", "reorganize", "restructure"]):
            return "refactor"
        elif any(word in text_lower for word in ["document", "docs", "readme"]):
            return "documentation"

        return "enhancement"

    async def _emit_decision_event(self, decision_id: str, question: str, decision_text: str, 
                                 complexity: str, timestamp: datetime, debate_id: str = None):
        """Emit a decision made event"""
        if not self.event_bus:
            return
            
        try:
            from src.contexts.debate.events import DecisionMade
            from uuid import uuid4
            
            event = DecisionMade(
                event_id=uuid4(),
                occurred_at=timestamp,
                event_type="DecisionMade",
                aggregate_id=uuid4(),
                decision_id=uuid4(),
                debate_id=uuid4() if debate_id else None,
                decision_type=complexity,
                question=question,
                recommendation=decision_text,
                confidence=0.8,  # Default confidence
                implementation_required=complexity in ["complex", "moderate"]
            )
            
            await self.event_bus.publish(event)
        except Exception as e:
            print(f"Error emitting decision event: {e}")
    
    async def _emit_debate_completed_event(self, debate_id: str, rounds: int, 
                                         final_decision: str, timestamp: datetime):
        """Emit a debate completed event"""
        if not self.event_bus:
            return
            
        try:
            from src.contexts.debate.events import DebateCompleted
            from uuid import uuid4
            
            event = DebateCompleted(
                event_id=uuid4(),
                occurred_at=timestamp,
                event_type="DebateCompleted",
                aggregate_id=uuid4(),
                debate_id=uuid4(),
                total_rounds=rounds,
                total_arguments=rounds * 2,  # Approximation
                final_consensus=final_decision
            )
            
            await self.event_bus.publish(event)
        except Exception as e:
            print(f"Error emitting debate completed event: {e}")


async def main():
    """Initialize and test the debate system"""
    print("🧬 Zamaz Debate Nucleus v0.1.0")
    print("=" * 50)

    nucleus = DebateNucleus()

    # Test 1: Simple decision
    print("\n📝 Test 1: Simple Decision")
    result = await nucleus.decide("Should we rename the variable 'x' to 'user_count'?")
    print(f"Decision: {result['decision']}")
    print(f"Method: {result['method']} (rounds: {result['rounds']})")

    # Test 2: Complex decision
    print("\n🤔 Test 2: Complex Decision")
    result = await nucleus.decide("What architecture pattern should we use for the self-improving system?")
    print(f"Decision: {result['decision'][:100]}...")
    print(f"Method: {result['method']} (rounds: {result['rounds']})")

    # Test 3: Self-improvement
    print("\n🔄 Test 3: Self-Improvement Suggestion")
    result = await nucleus.evolve_self()
    print(f"Improvement: {result['decision'][:100]}...")

    print("\n✅ All systems operational!")


if __name__ == "__main__":
    asyncio.run(main())
