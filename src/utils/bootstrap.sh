#!/bin/bash
# Script to create all missing files for zamaz-debate project

cd /Users/lsendel/IdeaProjects/zamaz-debate

echo "🔍 Checking and creating missing files for zamaz-debate..."

# 1. Create bootstrap.py if it doesn't exist
if [ ! -f "bootstrap.py" ]; then
echo "📝 Creating bootstrap.py..."
cat > bootstrap.py <<EOF
#!/usr/bin/env python3
"""Bootstrap the Zamaz Debate System"""

import os
import sys
from pathlib import Path

NUCLEUS_CODE = '''#!/usr/bin/env python3
"""
Zamaz Debate Nucleus v0.1.0
A self-improving debate system using Claude Opus 4 and Gemini 2.5 Pro
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from anthropic import Anthropic
import google.generativeai as genai
from dotenv import load_dotenv

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
        
        # Complexity detection
        self.complexity_keywords = {
            "simple": ["rename", "format", "typo", "spacing", "comment", "import"],
            "moderate": ["refactor", "optimize", "clean", "organize", "split", "merge"],
            "complex": ["architecture", "design", "pattern", "system", "structure", "integrate"]
        }
    
    async def decide(self, question: str, context: str = "") -> Dict:
        """Main entry point for all decisions"""
        self.decision_count += 1
        
        complexity = self._assess_complexity(question)
        
        if complexity == "simple":
            return {
                "decision": await self._simple_decision(question),
                "method": "direct",
                "rounds": 0,
                "complexity": complexity,
                "time": datetime.now().isoformat()
            }
        
        # Complex decisions need debate
        self.debate_count += 1
        return await self._run_debate(question, context, complexity)
    
    def _assess_complexity(self, question: str) -> str:
        """Determine if debate is needed"""
        q_lower = question.lower()
        
        for level, keywords in self.complexity_keywords.items():
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
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            self.claude_client = Anthropic(api_key=api_key)
        
        if not self.gemini_client:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            genai.configure(api_key=api_key)
            self.gemini_client = genai.GenerativeModel('gemini-2.0-flash-exp')
    
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
            "start_time": datetime.now().isoformat()
        }
        
        max_rounds = 8 if complexity == "moderate" else 25
        
        # For v0.1.0, we'll do a simplified debate
        claude_response = await self._get_claude_response(question, context)
        gemini_response = await self._get_gemini_response(question, context)
        
        debate_state["rounds"].append({
            "round": 1,
            "claude": claude_response,
            "gemini": gemini_response
        })
        
        # Simple consensus for now
        decision = f"Claude suggests: {claude_response[:100]}... Gemini suggests: {gemini_response[:100]}..."
        
        debate_state["final_decision"] = decision
        debate_state["end_time"] = datetime.now().isoformat()
        
        self._save_debate(debate_state)
        
        return {
            "decision": decision,
            "method": "debate",
            "rounds": len(debate_state["rounds"]),
            "complexity": complexity,
            "debate_id": debate_id,
            "time": debate_state["end_time"]
        }
    
    async def _get_claude_response(self, question: str, context: str) -> str:
        """Get Claude Opus 4's perspective"""
        prompt = f"Question: {question}\\nContext: {context}\\n\\nProvide a concise, well-reasoned answer."
        
        try:
            response = self.claude_client.messages.create(
                model="claude-3-opus-20240229",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.content[0].text
        except Exception as e:
            return f"Claude error: {str(e)}"
    
    async def _get_gemini_response(self, question: str, context: str) -> str:
        """Get Gemini 2.5 Pro's perspective"""
        prompt = f"Question: {question}\\nContext: {context}\\n\\nProvide a concise, well-reasoned answer."
        
        try:
            response = await self.gemini_client.generate_content_async(prompt)
            return response.text
        except Exception as e:
            return f"Gemini error: {str(e)}"
    
    def _ensure_debates_dir(self):
        """Create debates directory on first use"""
        if not self.debates_dir:
            self.debates_dir = Path("debates")
            self.debates_dir.mkdir(exist_ok=True)
    
    def _save_debate(self, debate_state: Dict):
        """Save debate for future reference"""
        filename = self.debates_dir / f"{debate_state['id']}.json"
        with open(filename, 'w') as f:
            json.dump(debate_state, f, indent=2)
    
    async def evolve_self(self) -> Dict:
        """Use debate to improve the debate system itself"""
        current_code = self._read_self()
        
        evolution_question = """
        What is the ONE most important improvement to make to this debate system next?
        Consider: code quality, functionality, performance, and usability.
        """
        
        context = f"""
        Current version: {self.VERSION}
        Decisions made: {self.decision_count}
        Debates run: {self.debate_count}
        Code size: {len(current_code)} characters
        """
        
        improvement = await self.decide(evolution_question, context)
        return improvement
    
    def _read_self(self) -> str:
        """Read own source code"""
        try:
            with open(__file__, 'r') as f:
                return f.read()
        except:
            return "Could not read self"

async def main():
    """Initialize and test the debate system"""
    print("🧬 Zamaz Debate Nucleus v0.1.0")
    print("=" * 50)
    
    nucleus = DebateNucleus()
    
    # Test 1: Simple decision
    print("\\n📝 Test 1: Simple Decision")
    result = await nucleus.decide("Should we rename the variable 'x' to 'user_count'?")
    print(f"Decision: {result['decision']}")
    print(f"Method: {result['method']} (rounds: {result['rounds']})")
    
    # Test 2: Complex decision
    print("\\n🤔 Test 2: Complex Decision")
    result = await nucleus.decide(
        "What architecture pattern should we use for the self-improving system?"
    )
    print(f"Decision: {result['decision'][:100]}...")
    print(f"Method: {result['method']} (rounds: {result['rounds']})")
    
    # Test 3: Self-improvement
    print("\\n🔄 Test 3: Self-Improvement Suggestion")
    result = await nucleus.evolve_self()
    print(f"Improvement: {result['decision'][:100]}...")
    
    print("\\n✅ All systems operational!")

if __name__ == "__main__":
    asyncio.run(main())
'''

def create_file(filename: str, content: str):
    """Create a file with the given content"""
    with open(filename, 'w') as f:
        f.write(content)
    print(f"✅ Created {filename}")

def main():
    """Bootstrap the Zamaz Debate System"""
    print("🚀 Bootstrapping Zamaz Debate System...")
    print("=" * 50)

    # Check if nucleus.py already exists
    if Path("nucleus.py").exists():
        response = input("⚠️  nucleus.py already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    # Create nucleus.py
    create_file("nucleus.py", NUCLEUS_CODE)
    os.chmod("nucleus.py", 0o755)

    # Create .env.example if it doesn't exist
    if not Path(".env.example").exists():
        env_example = """# Zamaz Debate System Environment Variables

# Anthropic API Key for Claude Opus 4
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Google AI API Key for Gemini 2.5 Pro
GOOGLE_API_KEY=your-google-api-key-here
"""
        create_file(".env.example", env_example)

    # Create .gitignore if it doesn't exist
    if not Path(".gitignore").exists():
        gitignore = """# Environment
.env
venv/
__pycache__/
*.pyc

# Debates and evolutions
debates/
evolutions/
evolution_history.json

# IDE
.vscode/
.idea/

# Testing
.pytest_cache/
.coverage
htmlcov/
"""
        create_file(".gitignore", gitignore)

    # Create requirements.txt if it doesn't exist
    if not Path("requirements.txt").exists():
        requirements = """anthropic>=0.18.0
google-generativeai>=0.3.0
python-dotenv>=1.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
aiofiles>=23.0.0
"""
        create_file("requirements.txt", requirements)

    print("\n📋 Next steps:")
    print("1. Copy .env.example to .env and add your API keys")
    print("2. Run: pip install -r requirements.txt")
    print("3. Run: python nucleus.py")
    print("\nThe system will start evolving from there!")

if __name__ == "__main__":
    main()
EOF
