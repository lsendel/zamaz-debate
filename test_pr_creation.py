#!/usr/bin/env python3
"""
Test script to verify PR creation is working with new format
"""

import os
import json
from pathlib import Path

# Check environment settings
print("=== PR Creation Settings ===")
print(f"CREATE_PR_FOR_DECISIONS: {os.getenv('CREATE_PR_FOR_DECISIONS', 'false')}")
print(f"AUTO_PUSH_PR: {os.getenv('AUTO_PUSH_PR', 'false')}")
print(f"PR_ASSIGNEE: {os.getenv('PR_ASSIGNEE', 'claude')}")
print()

# Check for recent PR drafts
pr_drafts_dir = Path(__file__).parent / "data" / "pr_drafts"
if pr_drafts_dir.exists():
    drafts = list(pr_drafts_dir.glob("*.json"))
    drafts.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print(f"=== Recent PR Drafts ({len(drafts)} total) ===")
    for draft in drafts[:5]:
        print(f"- {draft.name}")
        
        # Check if markdown body exists
        body_file = pr_drafts_dir / f"{draft.stem}_body.md"
        if body_file.exists():
            print(f"  ✓ Has markdown body file")
        else:
            print(f"  ✗ No markdown body file (server needs restart)")
    print()

# Show git commands for latest evolution
latest_evolution = None
for draft in drafts:
    if "evolution" in draft.name:
        latest_evolution = draft
        break

if latest_evolution:
    with open(latest_evolution, 'r') as f:
        data = json.load(f)
    
    print("=== To Create Latest Evolution PR Manually ===")
    print(f"Branch: {data.get('branch', 'N/A')}")
    print(f"Title: {data.get('title', 'N/A')}")
    print()
    print("Commands to run:")
    print(f"1. git checkout -b {data.get('branch', 'N/A')}")
    print(f"2. # Add your implementation files")
    print(f"3. git add .")
    print(f"4. git commit -m 'Implement: {data.get('title', 'N/A')}'")
    print(f"5. git push -u origin {data.get('branch', 'N/A')}")
    
    # Check for body file
    body_file = pr_drafts_dir / f"{latest_evolution.stem}_body.md"
    if body_file.exists():
        print(f"6. gh pr create --title \"{data.get('title', 'N/A')}\" --body-file {body_file} --assignee {data.get('assignee', 'claude')}")
    else:
        print(f"6. gh pr create --title \"{data.get('title', 'N/A')}\" --body-file {latest_evolution} --assignee {data.get('assignee', 'claude')}")

print("\n=== Next Steps ===")
print("1. Restart the server to pick up the new PR format changes")
print("2. The next evolution/complex decision will automatically:")
print("   - Create a git branch")
print("   - Add decision files")
print("   - Commit changes")
print("   - Push to GitHub")
print("   - Create PR with enhanced markdown format")
print("   - Assign to the appropriate implementer")