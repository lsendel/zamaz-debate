#!/usr/bin/env python3
"""
Replay Decision Script
Re-runs a decision through the web API to trigger PR creation
"""

import json
import requests
import sys
from pathlib import Path


def replay_debate_as_decision(debate_file_path: str, api_url: str = "http://localhost:8000"):
    """Replay a debate through the decision API to trigger PR creation"""
    
    print(f"Loading debate from: {debate_file_path}")
    
    # Load debate data
    with open(debate_file_path, 'r') as f:
        debate_data = json.load(f)
    
    question = debate_data.get('question', '')
    context = debate_data.get('context', '')
    
    print(f"Question: {question[:100]}...")
    print(f"Context: {context[:100]}...")
    
    # Make the decision request
    response = requests.post(
        f"{api_url}/decide",
        json={
            "question": question,
            "context": context
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Decision created successfully!")
        print(f"   Method: {result.get('method')}")
        print(f"   Decision Type: {result.get('decision_type')}")
        print(f"   Decision: {result.get('decision', '')[:200]}...")
        
        # Check if PR was created
        if result.get('pr_created'):
            print(f"✅ PR was created!")
        else:
            print(f"⚠️  No PR was created. Check CREATE_PR_FOR_DECISIONS environment variable.")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


def replay_template_rendering_decision():
    """Replay the specific template rendering decision"""
    
    question = "Replace the shell-here-docs for task-file generation with a small Python or Jinja2 templating helper (or a composite GitHub Action). This reduces quoting bugs and improves maintainability."
    context = "The current implementation uses shell here-docs which are prone to quoting issues and can become difficult to maintain as complexity grows."
    
    print("Replaying template rendering decision...")
    
    response = requests.post(
        "http://localhost:8000/decide",
        json={
            "question": question,
            "context": context
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Decision created successfully!")
        print(json.dumps(result, indent=2))
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Replay decision through web API')
    parser.add_argument('--debate-file', type=str, help='Path to debate JSON file')
    parser.add_argument('--template-rendering', action='store_true', 
                       help='Replay the template rendering decision')
    parser.add_argument('--api-url', type=str, default='http://localhost:8000',
                       help='API URL (default: http://localhost:8000)')
    
    args = parser.parse_args()
    
    if args.template_rendering:
        replay_template_rendering_decision()
    elif args.debate_file:
        replay_debate_as_decision(args.debate_file, args.api_url)
    else:
        print("Error: Must specify either --debate-file or --template-rendering")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()