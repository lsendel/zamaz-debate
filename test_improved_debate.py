#!/usr/bin/env python3
"""
Test script for the improved debate system with enhanced consensus detection
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.core.nucleus import DebateNucleus
import json


async def test_improved_debate():
    """Test the improved debate system"""
    print("Testing Improved Debate System")
    print("=" * 50)
    
    # Create nucleus instance
    nucleus = DebateNucleus()
    
    # Test 1: Complex debate to test consensus detection
    print("\nTest 1: Complex Architecture Decision")
    question = "Should we implement a microservices architecture to replace our monolithic system?"
    context = "Current system handles 10K requests/day, team size is 5 developers, experiencing scaling issues"
    
    result = await nucleus.decide(question, context)
    
    print(f"\nQuestion: {question}")
    print(f"Complexity: {result.get('complexity')}")
    print(f"Consensus: {result.get('consensus', 'Unknown')}")
    print(f"Consensus Level: {result.get('consensus_level', 0):.1%}")
    print(f"Consensus Type: {result.get('consensus_type', 'Unknown')}")
    
    # Load the debate file to see consensus details
    if 'debate_id' in result:
        debate_file = Path(f"data/debates/{result['debate_id']}.json")
        if debate_file.exists():
            with open(debate_file) as f:
                debate_data = json.load(f)
                consensus = debate_data.get('consensus', {})
                
                print("\nConsensus Analysis:")
                print(f"- Has Consensus: {consensus.get('has_consensus', False)}")
                print(f"- Level: {consensus.get('level', 0):.1%}")
                print(f"- Type: {consensus.get('type', 'Unknown')}")
                
                if consensus.get('areas_of_agreement'):
                    print("\nAreas of Agreement:")
                    for area in consensus['areas_of_agreement']:
                        print(f"  • {area}")
                
                if consensus.get('areas_of_disagreement'):
                    print("\nAreas of Disagreement:")
                    for area in consensus['areas_of_disagreement']:
                        print(f"  • {area}")
                
                print(f"\nCombined Recommendation:")
                print(f"  {consensus.get('combined_recommendation', 'Not available')}")
    
    # Test 2: Test where AIs might disagree
    print("\n" + "=" * 50)
    print("\nTest 2: Controversial Decision")
    question2 = "Should we immediately rewrite all our code in Rust for better performance?"
    context2 = "Current codebase is 100K lines of Python, team has no Rust experience"
    
    result2 = await nucleus.decide(question2, context2)
    
    print(f"\nQuestion: {question2}")
    print(f"Consensus: {result2.get('consensus', 'Unknown')}")
    print(f"Consensus Level: {result2.get('consensus_level', 0):.1%}")
    print(f"Consensus Type: {result2.get('consensus_type', 'Unknown')}")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_improved_debate())