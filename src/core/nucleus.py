#!/usr/bin/env python3
"""
Zamaz Debate Nucleus v0.1.0 - Simplified version
A self-improving debate system using Claude Opus 4 and Gemini 2.5 Pro
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from src.core.evolution_tracker import EvolutionTracker
from services.ai_client_factory import AIClientFactory

# Load environment variables
load_dotenv()


class DebateNucleus:
    """Self-contained debate system that can evolve itself"""
    
    VERSION = "0.1.0"
    
    def __init__(self):
        self.claude_client = None
        self.gemini_client = None
        self.debates_dir = None
        self.decision_count = 0
        self.debate_count = 0
        
        # Evolution tracker
        self.evolution_tracker = EvolutionTracker()
        
        # AI client factory
        self.ai_factory = AIClientFactory()
        
        # Complexity detection
        self.complexity_keywords = {
            "simple": ["rename", "format", "typo", "spacing", "comment", "import"],
            "moderate": ["refactor", "optimize", "clean", "organize", "split", "merge"],
            "complex": [
                "architecture", "design", "pattern", "system", "structure",
                "integrate", "improve", "improvement", "evolve", "evolution",
                "enhance", "feature"
            ],
        }
    
    async def decide(self, question: str, context: str = "") -> Dict:
        """Main entry point for all decisions"""
        self.decision_count += 1
        
        complexity = self._assess_complexity(question)
        timestamp = datetime.now()
        
        if complexity == "simple":
            decision_text = await self._simple_decision(question)
            return {
                "decision": decision_text,
                "method": "direct",
                "rounds": 0,
                "complexity": complexity,
                "time": timestamp.isoformat(),
            }
        
        # Complex decisions need debate
        self.debate_count += 1
        result = await self._run_debate(question, context, complexity)
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
        
        debate_id = f"debate_{self.debate_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
        gemini_response = await self._get_gemini_response(question, context)
        
        debate_state["rounds"].append({
            "round": 1,
            "claude": claude_response,
            "gemini": gemini_response
        })
        
        # Full decision with both perspectives
        decision = f"Claude suggests: {claude_response}\n\nGemini suggests: {gemini_response}"
        
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
    
    async def _get_claude_response(self, question: str, context: str) -> str:
        """Get Claude Opus 4's perspective"""
        prompt = f"Question: {question}\nContext: {context}\n\nProvide a concise, well-reasoned answer."
        
        try:
            response = self.claude_client.messages.create(
                model="claude-opus-4-20250514",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.content[0].text
        except Exception as e:
            return f"Claude error: {str(e)}"
    
    async def _get_gemini_response(self, question: str, context: str) -> str:
        """Get Gemini 2.5 Pro's perspective"""
        prompt = f"Question: {question}\nContext: {context}\n\nProvide a concise, well-reasoned answer."
        
        try:
            response = await self.gemini_client.generate_content_async(prompt)
            return response.text
        except Exception as e:
            return f"Gemini error: {str(e)}"
    
    def _ensure_debates_dir(self):
        """Create debates directory on first use"""
        if not self.debates_dir:
            self.debates_dir = Path(__file__).parent.parent.parent / "data" / "debates"
            self.debates_dir.mkdir(parents=True, exist_ok=True)
    
    def _save_debate(self, debate_state: Dict):
        """Save debate for future reference"""
        filename = self.debates_dir / f"{debate_state['id']}.json"
        with open(filename, 'w') as f:
            json.dump(debate_state, f, indent=2)
    
    async def evolve_self(self) -> Dict:
        """Use debate to improve the debate system itself"""
        evolution_question = "What is the ONE most important improvement to make to this debate system next? Consider: code quality, functionality, performance, and usability. Ensure this is different from previous evolutions."
        
        evolution_summary = self.evolution_tracker.get_evolution_summary()
        recent_evolutions = self.evolution_tracker.get_recent_evolutions(5)
        
        context = f"""
        Current version: {self.VERSION}
        Decisions made: {self.decision_count}
        Debates run: {self.debate_count}
        
        Evolution History:
        Total evolutions: {evolution_summary['total_evolutions']}
        Evolution types: {json.dumps(evolution_summary['evolution_types'], indent=2)}
        
        Recent evolutions:
        {self._format_recent_evolutions(recent_evolutions)}
        """
        
        improvement = await self.decide(evolution_question, context)
        
        # Track evolution if it's a debate result
        if improvement.get('method') == 'debate':
            debate_id = improvement.get('debate_id')
            if debate_id:
                # Load the debate to extract suggestions
                debate_file = self.debates_dir / f"{debate_id}.json"
                if debate_file.exists():
                    with open(debate_file, 'r') as f:
                        debate_data = json.load(f)
                    
                    # Extract the actual improvement from the decision
                    decision_text = improvement.get('decision', '')
                    
                    # Parse out the specific feature being suggested
                    feature = self._extract_evolution_feature(decision_text)
                    evolution_type = self._extract_evolution_type(decision_text)
                    
                    # Create evolution from debate
                    evolution = {
                        "type": evolution_type,
                        "feature": feature,
                        "description": decision_text,
                        "debate_id": debate_id,
                        "claude_suggestion": debate_data["rounds"][0]["claude"],
                        "gemini_suggestion": debate_data["rounds"][0]["gemini"],
                    }
                    
                    if self.evolution_tracker.add_evolution(evolution):
                        improvement['evolution_tracked'] = True
                    else:
                        improvement['evolution_tracked'] = False
                        improvement['duplicate_detected'] = True
        
        return improvement
    
    def _format_recent_evolutions(self, evolutions: List[Dict]) -> str:
        """Format recent evolutions for context"""
        if not evolutions:
            return "No previous evolutions"
        
        formatted = []
        for evo in evolutions:
            formatted.append(
                f"- {evo.get('type', 'unknown')}: {evo.get('feature', 'unknown')} ({evo.get('timestamp', 'unknown')[:10]})"
            )
        
        return "\n".join(formatted)
    
    def _extract_evolution_feature(self, decision_text: str) -> str:
        """Extract specific feature from decision text"""
        text_lower = decision_text.lower()
        
        # Common feature patterns
        features = {
            "performance tracking": "performance_tracking",
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
        }
        
        for pattern, feature in features.items():
            if pattern in text_lower:
                return feature
        
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
    result = await nucleus.decide(
        "What architecture pattern should we use for the self-improving system?"
    )
    print(f"Decision: {result['decision'][:100]}...")
    print(f"Method: {result['method']} (rounds: {result['rounds']})")
    
    # Test 3: Self-improvement
    print("\n🔄 Test 3: Self-Improvement Suggestion")
    result = await nucleus.evolve_self()
    print(f"Improvement: {result['decision'][:100]}...")
    
    print("\n✅ All systems operational!")


if __name__ == "__main__":
    asyncio.run(main())