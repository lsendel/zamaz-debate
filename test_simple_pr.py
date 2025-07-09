#!/usr/bin/env python3
"""
Simple test to verify PR creation for complex decisions
"""

import requests
import time
import json
import subprocess

def test_pr_creation():
    """Test PR creation with a simple complex decision"""
    
    # Create a complex decision
    decision_data = {
        "question": "Should we implement comprehensive API rate limiting across all endpoints?",
        "context": "We're experiencing API abuse and need to protect our services. This is a COMPLEX technical decision that requires careful implementation of rate limiting strategies, monitoring, and user communication."
    }
    
    print("1. Submitting complex decision...")
    response = requests.post(
        "http://localhost:8000/decide",
        json=decision_data,
        timeout=180  # 3 minute timeout for complex decisions
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\n2. Decision completed successfully!")
        print(f"   Decision Type: {result.get('decision_type', 'unknown')}")
        print(f"   Method: {result.get('method', 'unknown')}")
        print(f"   PR Created: {result.get('pr_created', False)}")
        
        # Wait for async PR creation
        print("\n3. Waiting for PR creation (15 seconds)...")
        time.sleep(15)
        
        # Check for recent PRs
        print("\n4. Checking GitHub for recent PRs...")
        result = subprocess.run(
            ["gh", "pr", "list", "--limit", "3", "--json", "number,title,createdAt,labels,state"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            prs = json.loads(result.stdout)
            print(f"\nFound {len(prs)} recent PRs:")
            for pr in prs:
                print(f"\n  PR #{pr['number']}: {pr['title'][:60]}...")
                print(f"     State: {pr['state']}")
                labels = [l['name'] for l in pr.get('labels', [])]
                print(f"     Labels: {', '.join(labels)}")
                
        # Check for recent issues  
        print("\n5. Checking GitHub for recent issues...")
        result = subprocess.run(
            ["gh", "issue", "list", "--limit", "3", "--json", "number,title,labels,assignees"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            issues = json.loads(result.stdout)
            print(f"\nFound {len(issues)} recent issues:")
            for issue in issues:
                print(f"\n  Issue #{issue['number']}: {issue['title'][:60]}...")
                labels = [l['name'] for l in issue.get('labels', [])]
                print(f"     Labels: {', '.join(labels)}")
                assignees = [a['login'] for a in issue.get('assignees', [])]
                print(f"     Assignees: {', '.join(assignees) if assignees else 'None'}")
                
    else:
        print(f"\nError: Request failed with status {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_pr_creation()