#!/usr/bin/env python3
"""
Test PR and Issue creation for complex decisions using Puppeteer
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pyppeteer import launch
import json
import subprocess


async def test_pr_creation():
    """Test that complex decisions create PRs and issues"""
    
    url = "http://localhost:8000"
    print(f"Testing PR/Issue creation at {url}...")
    
    # Launch browser
    browser = await launch(headless=False, args=['--no-sandbox'])  # headless=False to see what's happening
    page = await browser.newPage()
    
    try:
        # Navigate to page
        print("1. Navigating to debate system...")
        await page.goto(url, {"waitUntil": "networkidle0"})
        
        # Fill in a complex architectural decision
        question = "Should we implement a new microservices architecture to replace our monolithic system?"
        context = "Our current monolithic system is becoming difficult to scale. We have 50+ developers and need better team autonomy. Performance is suffering under high load. This is a COMPLEX architectural decision requiring detailed analysis."
        
        print("2. Filling in complex decision form...")
        
        # Wait for and fill question input
        await page.waitForSelector("#question")
        await page.type("#question", question)
        
        # Fill context
        await page.waitForSelector("#context")
        await page.type("#context", context)
        
        # Take screenshot before submission
        await page.screenshot({"path": "test_before_submit.png"})
        print("   Screenshot saved: test_before_submit.png")
        
        # Click submit button
        print("3. Submitting decision...")
        await page.click("#submit-btn")
        
        # Wait for response (complex decisions take time)
        print("4. Waiting for AI debate to complete...")
        await page.waitForSelector("#result", {"timeout": 120000})  # 2 minute timeout
        
        # Get the result
        result_element = await page.querySelector("#result")
        result_text = await page.evaluate("(element) => element.innerText", result_element)
        
        # Take screenshot after submission
        await page.screenshot({"path": "test_after_submit.png", "fullPage": True})
        print("   Screenshot saved: test_after_submit.png")
        
        print("\n5. Decision Result:")
        print("-" * 50)
        print(result_text[:500] + "..." if len(result_text) > 500 else result_text)
        print("-" * 50)
        
        # Check if result mentions PR creation
        if "pr" in result_text.lower() or "pull request" in result_text.lower():
            print("\n✓ Result mentions PR creation")
        else:
            print("\n⚠ Result does not mention PR creation")
        
        # Wait a bit for async PR creation
        print("\n6. Waiting for PR/Issue creation (10 seconds)...")
        await asyncio.sleep(10)
        
        # Check GitHub for recent PRs
        print("\n7. Checking GitHub for recent PRs...")
        try:
            result = subprocess.run(
                ["gh", "pr", "list", "--limit", "5", "--json", "number,title,createdAt,labels"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                prs = json.loads(result.stdout)
                print(f"\nRecent PRs ({len(prs)}):")
                for pr in prs:
                    created = pr.get('createdAt', 'unknown')
                    labels = [l['name'] for l in pr.get('labels', [])]
                    print(f"  PR #{pr['number']}: {pr['title']}")
                    print(f"     Created: {created}")
                    print(f"     Labels: {', '.join(labels)}")
                    if 'ai-generated' in labels:
                        print("     ✓ This is an AI-generated PR!")
            else:
                print("Failed to fetch PRs")
        except Exception as e:
            print(f"Error checking PRs: {e}")
        
        # Check GitHub for recent issues
        print("\n8. Checking GitHub for recent issues...")
        try:
            result = subprocess.run(
                ["gh", "issue", "list", "--limit", "5", "--json", "number,title,createdAt,labels,assignees"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                issues = json.loads(result.stdout)
                print(f"\nRecent Issues ({len(issues)}):")
                for issue in issues:
                    created = issue.get('createdAt', 'unknown')
                    labels = [l['name'] for l in issue.get('labels', [])]
                    assignees = [a['login'] for a in issue.get('assignees', [])]
                    print(f"  Issue #{issue['number']}: {issue['title']}")
                    print(f"     Created: {created}")
                    print(f"     Labels: {', '.join(labels)}")
                    print(f"     Assignees: {', '.join(assignees)}")
                    if 'ai-assigned' in labels:
                        print("     ✓ This is an AI-assigned issue!")
            else:
                print("Failed to fetch issues")
        except Exception as e:
            print(f"Error checking issues: {e}")
        
        print("\n✓ Test complete!")
        
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        await page.screenshot({"path": "test_error.png"})
        print("Error screenshot saved: test_error.png")
    
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_pr_creation())