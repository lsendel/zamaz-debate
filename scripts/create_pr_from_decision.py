#!/usr/bin/env python3
"""
Manual PR and Issue Creation Script
Creates PRs and Issues from existing decision/debate files
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from domain.models import Decision, Debate, DecisionType
from services.pr_service import PRService


async def create_pr_from_debate_file(debate_file_path: str):
    """Create PR and issue from an existing debate file"""
    
    print(f"Loading debate from: {debate_file_path}")
    
    # Load debate data
    with open(debate_file_path, 'r') as f:
        debate_data = json.load(f)
    
    # Create Decision object
    decision = Decision(
        id=debate_data.get('id', 'manual_' + datetime.now().strftime('%Y%m%d_%H%M%S')),
        question=debate_data.get('question', ''),
        context=debate_data.get('context', ''),
        decision_text=debate_data.get('final_decision', ''),
        decision_type=DecisionType.COMPLEX,  # Assume complex for manual creation
        method='debate',
        rounds=len(debate_data.get('rounds', [])),  # Count debate rounds
        timestamp=datetime.now()
    )
    
    # Create Debate object if we have rounds
    debate = None
    if 'rounds' in debate_data:
        debate = Debate(
            id=debate_data.get('id'),
            question=debate_data.get('question'),
            context=debate_data.get('context'),
            rounds=debate_data.get('rounds'),
            final_decision=debate_data.get('final_decision'),
            start_time=debate_data.get('start_time'),
            end_time=debate_data.get('end_time'),
            complexity=debate_data.get('complexity', 'complex')
        )
    
    # Create PR service
    pr_service = PRService()
    pr_service.enabled = True  # Force enable for manual creation
    
    print(f"Creating PR for decision: {decision.question[:80]}...")
    
    # Create the PR
    pr = await pr_service.create_pr_for_decision(decision, debate)
    
    if pr:
        print(f"✅ Successfully created PR!")
        print(f"   Branch: {pr.branch_name}")
        print(f"   Title: {pr.title}")
        print(f"   Assignee: {pr.assignee}")
    else:
        print("❌ Failed to create PR")


async def create_pr_from_decision_data(question: str, decision_text: str, context: str = ""):
    """Create PR from manual decision data"""
    
    # Create Decision object
    decision = Decision(
        id='manual_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
        question=question,
        context=context,
        decision_text=decision_text,
        decision_type=DecisionType.COMPLEX,
        method='manual',
        rounds=1,  # Manual decisions have 1 round
        timestamp=datetime.now()
    )
    
    # Create PR service
    pr_service = PRService()
    pr_service.enabled = True  # Force enable for manual creation
    
    print(f"Creating PR for decision: {question[:80]}...")
    
    # Create the PR
    pr = await pr_service.create_pr_for_decision(decision, None)
    
    if pr:
        print(f"✅ Successfully created PR!")
        print(f"   Branch: {pr.branch_name}")
        print(f"   Title: {pr.title}")
        print(f"   Assignee: {pr.assignee}")
    else:
        print("❌ Failed to create PR")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create PR from existing decision/debate')
    parser.add_argument('--debate-file', type=str, help='Path to debate JSON file')
    parser.add_argument('--question', type=str, help='Decision question (for manual creation)')
    parser.add_argument('--decision', type=str, help='Decision text (for manual creation)')
    parser.add_argument('--context', type=str, default='', help='Context (for manual creation)')
    parser.add_argument('--template-rendering', action='store_true', 
                       help='Create PR for the template rendering decision')
    
    args = parser.parse_args()
    
    if args.template_rendering:
        # Handle the specific template rendering case
        debate_file = "data/debates/debate_00f51d28_20250709_125408.json"
        asyncio.run(create_pr_from_debate_file(debate_file))
    elif args.debate_file:
        # Create from debate file
        asyncio.run(create_pr_from_debate_file(args.debate_file))
    elif args.question and args.decision:
        # Create from manual data
        asyncio.run(create_pr_from_decision_data(
            args.question, 
            args.decision, 
            args.context
        ))
    else:
        print("Error: Must specify either --debate-file or both --question and --decision")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()