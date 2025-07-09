#!/usr/bin/env python3
"""
Test that both PR and Issue are created for complex decisions
"""

import requests
import time
import json
import subprocess

def test_pr_and_issue_creation():
    """Test PR and Issue creation with a complex decision"""
    
    # Create a complex architectural decision
    decision_data = {
        "question": "Should we implement event-driven architecture using Apache Kafka for real-time data processing?",
        "context": "Our system needs to process millions of events per day with low latency. This is a COMPLEX architectural decision requiring careful evaluation of message brokers, scalability patterns, and operational complexity."
    }
    
    print("1. Submitting complex architectural decision...")
    print(f"   Question: {decision_data['question'][:60]}...")
    
    response = requests.post(
        "http://localhost:8000/decide",
        json=decision_data,
        timeout=180
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\n2. Decision completed successfully!")
        print(f"   Decision Type: {result.get('decision_type', 'unknown')}")
        print(f"   Method: {result.get('method', 'unknown')}")
        
        # Wait for async operations
        print("\n3. Waiting for PR and Issue creation (20 seconds)...")
        time.sleep(20)
        
        # Check for recent PRs
        print("\n4. Checking GitHub for recent PRs...")
        result = subprocess.run(
            ["gh", "pr", "list", "--limit", "5", "--json", "number,title,createdAt,labels"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            prs = json.loads(result.stdout)
            print(f"\nFound {len(prs)} recent PRs:")
            for pr in prs:
                if "event-driven" in pr['title'].lower() or "kafka" in pr['title'].lower():
                    print(f"\n✓ FOUND OUR PR!")
                print(f"  PR #{pr['number']}: {pr['title'][:60]}...")
                labels = [l['name'] for l in pr.get('labels', [])]
                if labels:
                    print(f"     Labels: {', '.join(labels[:3])}...")
                
        # Check for recent issues  
        print("\n5. Checking GitHub for recent issues...")
        result = subprocess.run(
            ["gh", "issue", "list", "--limit", "5", "--json", "number,title,labels,assignees,createdAt"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            issues = json.loads(result.stdout)
            print(f"\nFound {len(issues)} recent issues:")
            for issue in issues:
                if "event-driven" in issue['title'].lower() or "kafka" in issue['title'].lower():
                    print(f"\n✓ FOUND OUR ISSUE!")
                print(f"  Issue #{issue['number']}: {issue['title'][:60]}...")
                labels = [l['name'] for l in issue.get('labels', [])]
                if labels:
                    print(f"     Labels: {', '.join(labels[:3])}...")
                assignees = [a['login'] for a in issue.get('assignees', [])]
                if assignees:
                    print(f"     Assignees: {', '.join(assignees)}")
                if 'ai-assigned' in labels:
                    print("     ✓ This is an AI-assigned issue!")
                    
        print("\n✓ Test complete!")
                
    else:
        print(f"\nError: Request failed with status {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_pr_and_issue_creation()