#!/usr/bin/env python3
"""
Test the complete flow: Debate → PR → Issue creation
Uses curl for API calls and Puppeteer for UI validation
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from pyppeteer import launch


def run_command(cmd, capture_output=True):
    """Run a shell command and return the output"""
    print(f"🔧 Running: {cmd}")
    if capture_output:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
        return result.stdout.strip(), result.returncode
    else:
        return subprocess.run(cmd, shell=True).returncode


def check_server_running():
    """Check if the web server is running"""
    output, code = run_command("curl -s http://localhost:8000/stats")
    return code == 0


async def capture_screenshots(page, prefix):
    """Capture screenshots of the current page"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_dir = Path("localhost_checks")
    screenshot_dir.mkdir(exist_ok=True)
    
    # Full page screenshot
    await page.screenshot({
        'path': f'{screenshot_dir}/{prefix}_{timestamp}_full.png',
        'fullPage': True
    })
    
    # Viewport screenshot
    await page.screenshot({
        'path': f'{screenshot_dir}/{prefix}_{timestamp}_viewport.png'
    })
    
    print(f"📸 Screenshots saved: {prefix}_{timestamp}")


async def test_with_puppeteer():
    """Use Puppeteer to validate the UI and capture screenshots"""
    print("\n🌐 Starting Puppeteer validation...")
    
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()
    
    try:
        # Set viewport
        await page.setViewport({'width': 1280, 'height': 800})
        
        # Navigate to the main page
        print("📍 Navigating to http://localhost:8000")
        await page.goto('http://localhost:8000', {'waitUntil': 'networkidle0'})
        await capture_screenshots(page, "main_page")
        
        # Check page title
        title = await page.title()
        print(f"📄 Page title: {title}")
        
        # Check for main elements
        elements = {
            'Question input': 'textarea[name="question"]',
            'Context input': 'textarea[name="context"]',
            'Submit button': 'button[type="submit"]',
            'Stats section': '#stats'
        }
        
        for name, selector in elements.items():
            try:
                await page.waitForSelector(selector, {'timeout': 5000})
                print(f"✅ Found: {name}")
            except:
                print(f"❌ Missing: {name}")
        
        # Fill in the form
        print("\n📝 Filling debate form...")
        await page.type('textarea[name="question"]', 
                       'Should we implement a comprehensive monitoring system for our Kafka integration?')
        await page.type('textarea[name="context"]', 
                       'We need to track event flow, consumer lag, and system health. This is a COMPLEX architectural decision.')
        
        await capture_screenshots(page, "form_filled")
        
        # Submit the form
        print("🚀 Submitting debate...")
        await page.click('button[type="submit"]')
        
        # Wait for response
        await page.waitForSelector('.result, .error', {'timeout': 120000})  # 2 minutes timeout
        await capture_screenshots(page, "debate_result")
        
        # Extract result
        result_element = await page.querySelector('.result')
        if result_element:
            result_text = await page.evaluate('(element) => element.textContent', result_element)
            print(f"✅ Debate completed successfully")
            print(f"📊 Result preview: {result_text[:200]}...")
        else:
            error_element = await page.querySelector('.error')
            if error_element:
                error_text = await page.evaluate('(element) => element.textContent', error_element)
                print(f"❌ Error: {error_text}")
        
        # Check stats
        await page.goto('http://localhost:8000', {'waitUntil': 'networkidle0'})
        stats_element = await page.querySelector('#stats')
        if stats_element:
            stats_text = await page.evaluate('(element) => element.textContent', stats_element)
            print(f"\n📊 Current stats: {stats_text}")
        
    finally:
        await browser.close()


def test_with_curl():
    """Test the API directly with curl"""
    print("\n🔌 Testing API with curl...")
    
    # Create a complex decision that should trigger PR and issue creation
    debate_data = {
        "question": "Should we implement a comprehensive monitoring system for our Kafka integration?",
        "context": "We need to track event flow, consumer lag, and system health. Consider Prometheus, Grafana, and custom dashboards. This is a COMPLEX architectural decision that requires careful planning."
    }
    
    # Create the debate
    print("\n📮 Creating debate via API...")
    cmd = f'''curl -X POST http://localhost:8000/decide \
        -H "Content-Type: application/json" \
        -d '{json.dumps(debate_data)}' '''
    
    output, code = run_command(cmd)
    
    if code == 0:
        try:
            result = json.loads(output)
            print("✅ Debate created successfully!")
            print(f"🆔 Decision ID: {result.get('decision_id', 'N/A')}")
            print(f"🏆 Winner: {result.get('winner', 'N/A')}")
            print(f"📊 Decision Type: {result.get('decision_type', 'N/A')}")
            print(f"🔄 Method: {result.get('method', 'N/A')}")
            
            # Check if PR was created
            if result.get('pr_url'):
                print(f"✅ PR Created: {result['pr_url']}")
            elif result.get('pr_number'):
                print(f"✅ PR Number: {result['pr_number']}")
            else:
                print("⚠️  No PR information in response")
            
            return result
        except json.JSONDecodeError:
            print(f"❌ Failed to parse response: {output}")
    else:
        print(f"❌ Failed to create debate")
    
    return None


def check_pr_creation(decision_id):
    """Check if a PR was created for the decision"""
    print(f"\n🔍 Checking PR creation for decision {decision_id}...")
    
    # Check PR drafts directory
    pr_drafts_dir = Path("data/pr_drafts")
    if pr_drafts_dir.exists():
        pr_files = list(pr_drafts_dir.glob(f"*{decision_id}*.json"))
        if pr_files:
            print(f"✅ Found {len(pr_files)} PR draft(s)")
            for pr_file in pr_files:
                with open(pr_file) as f:
                    pr_data = json.load(f)
                    print(f"  📄 Title: {pr_data.get('title', 'N/A')}")
                    print(f"  📝 Branch: {pr_data.get('branch', 'N/A')}")
                    if pr_data.get('pr_url'):
                        print(f"  🔗 URL: {pr_data['pr_url']}")
        else:
            print("❌ No PR drafts found")
    
    # Check PR history
    pr_history_dir = Path("data/pr_history")
    if pr_history_dir.exists():
        history_files = list(pr_history_dir.glob("*.json"))
        for history_file in history_files:
            with open(history_file) as f:
                history = json.load(f)
                if history.get('decision_id') == decision_id:
                    print(f"✅ Found PR in history: {history.get('pr_url', 'N/A')}")
                    return True
    
    return False


def check_issue_creation():
    """Check recent issues using GitHub CLI"""
    print("\n🔍 Checking GitHub issues...")
    
    # Check if gh is installed
    gh_check, _ = run_command("which gh")
    if not gh_check:
        print("⚠️  GitHub CLI (gh) not installed")
        return
    
    # List recent issues with ai-assigned label
    cmd = "gh issue list --label ai-assigned --limit 5 --json number,title,createdAt,labels"
    output, code = run_command(cmd)
    
    if code == 0:
        try:
            issues = json.loads(output)
            if issues:
                print(f"✅ Found {len(issues)} AI-assigned issue(s):")
                for issue in issues:
                    print(f"  📌 #{issue['number']}: {issue['title']}")
                    print(f"     Created: {issue['createdAt']}")
            else:
                print("❌ No AI-assigned issues found")
        except json.JSONDecodeError:
            print("❌ Failed to parse issue list")
    else:
        print("❌ Failed to list issues")


def check_environment():
    """Check environment configuration"""
    print("\n🔧 Checking environment configuration...")
    
    # Load .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    with open(env_path) as f:
        env_content = f.read()
    
    checks = {
        "CREATE_PR_FOR_DECISIONS": "true" in env_content and "CREATE_PR_FOR_DECISIONS=true" in env_content,
        "PR_USE_CURRENT_BRANCH": "PR_USE_CURRENT_BRANCH=false" in env_content,
        "GITHUB_TOKEN": "GITHUB_TOKEN=" in env_content and "your-github-token" not in env_content,
    }
    
    all_good = True
    for key, status in checks.items():
        if status:
            print(f"✅ {key} is configured")
        else:
            print(f"❌ {key} needs configuration")
            all_good = False
    
    return all_good


async def main():
    """Run the complete test flow"""
    print("🚀 Testing Debate → PR → Issue Creation Flow")
    print("=" * 60)
    
    # Check environment
    if not check_environment():
        print("\n⚠️  Please configure your environment first!")
        return
    
    # Check if server is running
    if not check_server_running():
        print("❌ Server not running! Start with: make run")
        return
    
    # Test with curl
    result = test_with_curl()
    
    if result and result.get('decision_id'):
        decision_id = result['decision_id']
        
        # Wait a bit for async operations
        print("\n⏳ Waiting for async operations...")
        time.sleep(5)
        
        # Check PR creation
        check_pr_creation(decision_id)
        
        # Check issue creation
        check_issue_creation()
    
    # Test with Puppeteer
    await test_with_puppeteer()
    
    # Final summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print("- Use 'make logs' to check server logs")
    print("- Use 'gh pr list' to see all PRs")
    print("- Use 'gh issue list --label ai-assigned' to see AI issues")
    print("- Check localhost_checks/ for screenshots")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())