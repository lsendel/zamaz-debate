#!/usr/bin/env python3
"""
Script to close PRs that have already been implemented
"""

import subprocess
import json
import sys


def get_open_prs():
    """Get list of open PRs"""
    result = subprocess.run(
        ["gh", "pr", "list", "--limit", "100", "--json", "number,title,headRefName"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def close_pr(pr_number, reason):
    """Close a PR with a comment"""
    print(f"Closing PR #{pr_number}: {reason}")
    try:
        subprocess.run(
            ["gh", "pr", "close", str(pr_number), "--comment", f"Closing this PR because: {reason}"],
            check=True,
            capture_output=True,
        )
        print(f"  ✓ Closed PR #{pr_number}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to close PR #{pr_number}: {e}")
        return False


def main():
    print("🔍 Analyzing open PRs to identify implemented features...\n")

    # Get all open PRs
    prs = get_open_prs()
    print(f"Found {len(prs)} open PRs\n")

    # Features that have been implemented (based on merged PRs)
    implemented_features = {
        "testing framework": "Testing framework was implemented in PR #69",
        "error handling": "Error handling was implemented in PR #120",
        "documentation": "Documentation improvements were implemented in PR #86",
        "monitoring": "Monitoring was implemented in PR #120",
    }

    # Track PRs to close
    prs_to_close = []

    # Analyze each PR
    for pr in prs:
        pr_num = pr["number"]
        pr_title = pr["title"].lower()

        # Check if this PR is for an already implemented feature
        for feature, reason in implemented_features.items():
            if feature in pr_title:
                prs_to_close.append((pr_num, pr["title"], reason))
                break

        # Also close duplicate "improve this debate system" PRs (keep only the latest)
        if "improve this debate system next" in pr_title:
            # These are evolution PRs that keep getting created
            if pr_num < 175:  # Keep only the latest one
                prs_to_close.append((pr_num, pr["title"], "Duplicate evolution PR - keeping only the latest"))

    # Summary
    print(f"\n📊 Summary:")
    print(f"  - Total open PRs: {len(prs)}")
    print(f"  - PRs to close: {len(prs_to_close)}")
    print(f"  - PRs to keep open: {len(prs) - len(prs_to_close)}")

    if not prs_to_close:
        print("\n✅ No PRs need to be closed!")
        return

    # Show PRs that will be closed
    print(f"\n📋 PRs to close:")
    for pr_num, pr_title, reason in prs_to_close:
        print(f"  - PR #{pr_num}: {pr_title[:60]}...")

    # Check for --yes flag
    auto_confirm = "--yes" in sys.argv or "-y" in sys.argv

    if not auto_confirm:
        # Ask for confirmation
        print(f"\n⚠️  This will close {len(prs_to_close)} PRs!")
        try:
            response = input("Continue? [y/N] ")
            if response.lower() != "y":
                print("Cancelled.")
                return
        except EOFError:
            print("\n⚠️  Running in non-interactive mode. Use --yes to auto-confirm.")
            return
    else:
        print(f"\n✅ Auto-confirming closure of {len(prs_to_close)} PRs...")

    # Close the PRs
    print(f"\n🚀 Closing {len(prs_to_close)} PRs...")
    closed_count = 0

    for pr_num, pr_title, reason in prs_to_close:
        if close_pr(pr_num, reason):
            closed_count += 1

    print(f"\n✅ Successfully closed {closed_count} out of {len(prs_to_close)} PRs")


if __name__ == "__main__":
    main()
