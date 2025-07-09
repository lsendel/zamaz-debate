"""
Quality Debates for Zamaz Debate System
These debates help the self-improving system maintain code quality
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.core.nucleus import DebateNucleus

QUALITY_QUESTIONS = [
    {
        "id": "code_quality_tools",
        "question": "Which code quality tools should our self-improving system use to validate its own evolutions?",
        "context": "We need to ensure each evolution maintains or improves code quality. Consider tools like SonarCloud, Black, Flake8, PyLint, MyPy, and pytest-cov.",
    },
    {
        "id": "quality_metrics",
        "question": "What metrics should trigger a rollback of a self-improvement?",
        "context": "Consider: complexity score, test coverage, performance, security issues, code smells, technical debt ratio",
    },
    {
        "id": "quality_gates",
        "question": "Should we enforce quality gates that prevent merging PRs with declining code quality?",
        "context": "Balance between rapid evolution and maintaining code quality. Consider automated vs manual gates.",
    },
    {
        "id": "evolution_testing",
        "question": "How should we test AI-generated code evolutions before deployment?",
        "context": "Consider unit tests, integration tests, performance tests, and manual review requirements",
    },
    {
        "id": "code_style_enforcement",
        "question": "Should we enforce strict code style rules for AI-generated code?",
        "context": "Consider Black formatting, import sorting, docstring requirements, and type hints",
    },
]


def save_quality_debate_summary(results):
    """Save a summary of quality debate results"""
    # Create quality debates directory if it doesn't exist
    quality_dir = Path("data/quality_debates")
    quality_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = quality_dir / f"quality_summary_{timestamp}.json"

    # Prepare summary data
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_debates": len(results),
        "debates_with_prs": sum(1 for r in results if r["result"].get("pr_created")),
        "debates": results,
    }

    # Save to file
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\n📊 Summary saved to: {summary_file}")

    # Print summary statistics
    print(f"\n📈 Quality Debate Summary:")
    print(f"   Total debates run: {summary['total_debates']}")
    print(f"   PRs created: {summary['debates_with_prs']}")

    # List any PRs created
    prs_created = [r for r in results if r["result"].get("pr_created")]
    if prs_created:
        print(f"\n📄 Pull Requests Created:")
        for pr in prs_created:
            print(
                f"   - {pr['question_id']}: PR {pr['result']['pr_id']} on branch {pr['result']['pr_branch']}"
            )


async def run_quality_debate(question_id: str = None):
    """Run a specific quality debate or all debates"""
    # Get quality debate specific branch setting
    quality_use_current_branch = (
        os.getenv("QUALITY_DEBATE_USE_CURRENT_BRANCH", "false").lower() == "true"
    )

    # Store original PR_USE_CURRENT_BRANCH value
    original_pr_use_current_branch = os.getenv("PR_USE_CURRENT_BRANCH", "true")

    # Temporarily set PR_USE_CURRENT_BRANCH for quality debates
    os.environ["PR_USE_CURRENT_BRANCH"] = str(quality_use_current_branch).lower()

    try:
        nucleus = DebateNucleus()
        results = []

        if question_id:
            # Run specific debate
            question_data = next(
                (q for q in QUALITY_QUESTIONS if q["id"] == question_id), None
            )
            if not question_data:
                print(f"Question ID '{question_id}' not found")
                return

            print(f"\n🤔 Running quality debate: {question_data['id']}")
            result = await nucleus.decide(
                question_data["question"], question_data["context"]
            )

            # Display results
            print(f"\n✅ Decision: {result['decision'][:200]}...")
            print(f"Method: {result['method']}")
            print(f"Rounds: {result['rounds']}")

            # Check if PR was created
            if result.get("pr_created"):
                print(f"\n📄 Pull Request Created!")
                print(f"   PR ID: {result.get('pr_id')}")
                print(f"   Branch: {result.get('pr_branch')}")
                print(f"   Assignee: {result.get('pr_assignee')}")

            # Store result with question data
            results.append(
                {
                    "question_id": question_data["id"],
                    "question": question_data["question"],
                    "context": question_data["context"],
                    "result": result,
                }
            )
        else:
            # Run all debates
            for question_data in QUALITY_QUESTIONS:
                print(f"\n🤔 Running quality debate: {question_data['id']}")
                result = await nucleus.decide(
                    question_data["question"], question_data["context"]
                )
                print(
                    f"\n✅ Decision made via {result['method']} ({result['rounds']} rounds)"
                )

                # Check if PR was created
                if result.get("pr_created"):
                    print(
                        f"   📄 PR created: {result.get('pr_id')} on branch {result.get('pr_branch')}"
                    )

                # Store result
                results.append(
                    {
                        "question_id": question_data["id"],
                        "question": question_data["question"],
                        "context": question_data["context"],
                        "result": result,
                    }
                )

                print("-" * 80)

        # Save results summary if any debates were run
        if results:
            save_quality_debate_summary(results)

        return results

    finally:
        # Restore original PR_USE_CURRENT_BRANCH value
        os.environ["PR_USE_CURRENT_BRANCH"] = original_pr_use_current_branch


def list_quality_questions():
    """List all available quality debate questions"""
    print("\n📋 Available Quality Debate Questions:\n")
    for q in QUALITY_QUESTIONS:
        print(f"ID: {q['id']}")
        print(f"Question: {q['question']}")
        print(f"Context: {q['context'][:100]}...")
        print("-" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run quality debates")
    parser.add_argument("--question", help="Specific question ID to debate")
    parser.add_argument("--list", action="store_true", help="List available questions")
    args = parser.parse_args()

    if args.list:
        list_quality_questions()
    else:
        asyncio.run(run_quality_debate(args.question))
