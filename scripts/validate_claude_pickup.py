#!/usr/bin/env python3
"""
Validate Claude Task Pickup System
Ensures all components are in place for Claude to see and implement tasks
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class ClaudeTaskValidator:
    def __init__(self):
        self.repo_root = Path.cwd()
        self.validation_results = []
        self.critical_files = [
            "CLAUDE_TASKS.md",
            "IMPLEMENT_THIS_NOW.md", 
            "IMPLEMENT_NOW.md",
            "README_FOR_CLAUDE.md",
            "README.md"
        ]
        self.task_directories = [
            ".claude-tasks",
            "ai-tasks",
            "TODO"
        ]
        
    def run_validation(self) -> Tuple[bool, List[Dict]]:
        """Run all validation checks"""
        print("🔍 Validating Claude Task Pickup System...\n")
        
        # Check critical files
        self._check_critical_files()
        
        # Check task directories
        self._check_task_directories()
        
        # Check README visibility
        self._check_readme_visibility()
        
        # Check GitHub issues
        self._check_github_issues()
        
        # Check workflow status
        self._check_workflow_status()
        
        # Generate report
        all_passed = all(r["status"] == "PASS" for r in self.validation_results)
        return all_passed, self.validation_results
    
    def _check_critical_files(self):
        """Check if critical visibility files exist and contain urgent markers"""
        print("📋 Checking critical files...")
        
        urgent_keywords = ["URGENT", "IMMEDIATE", "CLAUDE", "IMPLEMENT", "NOW"]
        
        for file in self.critical_files:
            file_path = self.repo_root / file
            if file_path.exists():
                content = file_path.read_text()
                has_urgent = any(keyword in content.upper() for keyword in urgent_keywords)
                
                if has_urgent:
                    self._add_result(
                        f"File: {file}",
                        "PASS",
                        f"✅ File exists with urgent markers"
                    )
                else:
                    self._add_result(
                        f"File: {file}",
                        "WARN",
                        f"⚠️  File exists but missing urgent markers"
                    )
            else:
                self._add_result(
                    f"File: {file}",
                    "FAIL" if file in ["CLAUDE_TASKS.md", "README.md"] else "WARN",
                    f"❌ File not found"
                )
    
    def _check_task_directories(self):
        """Check task directories for pending tasks"""
        print("\n📁 Checking task directories...")
        
        for dir_name in self.task_directories:
            dir_path = self.repo_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                task_files = list(dir_path.glob("*.md"))
                urgent_tasks = [f for f in task_files if "URGENT" in f.name.upper() or "178" in f.name or "180" in f.name]
                
                if urgent_tasks:
                    self._add_result(
                        f"Directory: {dir_name}",
                        "PASS",
                        f"✅ Contains {len(urgent_tasks)} urgent task(s)"
                    )
                elif task_files:
                    self._add_result(
                        f"Directory: {dir_name}",
                        "WARN",
                        f"⚠️  Contains {len(task_files)} task(s) but none marked urgent"
                    )
                else:
                    self._add_result(
                        f"Directory: {dir_name}",
                        "INFO",
                        f"ℹ️  Directory exists but empty"
                    )
            else:
                self._add_result(
                    f"Directory: {dir_name}",
                    "WARN",
                    f"⚠️  Directory not found"
                )
    
    def _check_readme_visibility(self):
        """Check if README has urgent notice at the top"""
        print("\n📄 Checking README visibility...")
        
        readme_path = self.repo_root / "README.md"
        if readme_path.exists():
            lines = readme_path.read_text().split('\n')
            # Check first 10 lines for urgent markers
            top_lines = '\n'.join(lines[:10])
            
            if "URGENT" in top_lines and "Claude" in top_lines:
                self._add_result(
                    "README Visibility",
                    "PASS",
                    "✅ README has urgent Claude notice at top"
                )
            else:
                self._add_result(
                    "README Visibility", 
                    "FAIL",
                    "❌ README missing urgent notice in first 10 lines"
                )
    
    def _check_github_issues(self):
        """Check GitHub issues with ai-assigned label"""
        print("\n🐙 Checking GitHub issues...")
        
        try:
            # Get issues with ai-assigned label
            result = subprocess.run(
                ["gh", "issue", "list", "--label", "ai-assigned", "--json", "number,title,state,isPinned"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                issues = json.loads(result.stdout)
                open_issues = [i for i in issues if i["state"] == "OPEN"]
                pinned_issues = [i for i in open_issues if i.get("isPinned", False)]
                
                if pinned_issues:
                    self._add_result(
                        "GitHub Issues",
                        "PASS",
                        f"✅ {len(pinned_issues)} pinned AI issue(s), {len(open_issues)} total open"
                    )
                elif open_issues:
                    self._add_result(
                        "GitHub Issues",
                        "WARN",
                        f"⚠️  {len(open_issues)} open AI issue(s) but none pinned"
                    )
                else:
                    self._add_result(
                        "GitHub Issues",
                        "INFO",
                        "ℹ️  No open AI-assigned issues"
                    )
            else:
                self._add_result(
                    "GitHub Issues",
                    "ERROR",
                    f"❌ Failed to check issues: {result.stderr}"
                )
                
        except Exception as e:
            self._add_result(
                "GitHub Issues",
                "ERROR", 
                f"❌ Error checking issues: {str(e)}"
            )
    
    def _check_workflow_status(self):
        """Check if AI workflows are active"""
        print("\n⚙️  Checking workflow status...")
        
        try:
            result = subprocess.run(
                ["gh", "workflow", "list", "--json", "name,state"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                workflows = json.loads(result.stdout)
                ai_workflows = [w for w in workflows if "AI" in w["name"] or "ai" in w["name"].lower()]
                active_ai = [w for w in ai_workflows if w["state"] == "active"]
                
                if active_ai:
                    self._add_result(
                        "AI Workflows",
                        "PASS",
                        f"✅ {len(active_ai)} active AI workflow(s)"
                    )
                else:
                    self._add_result(
                        "AI Workflows",
                        "FAIL",
                        "❌ No active AI workflows found"
                    )
            else:
                self._add_result(
                    "AI Workflows",
                    "ERROR",
                    f"❌ Failed to check workflows: {result.stderr}"
                )
                
        except Exception as e:
            self._add_result(
                "AI Workflows",
                "ERROR",
                f"❌ Error checking workflows: {str(e)}"
            )
    
    def _add_result(self, check: str, status: str, message: str):
        """Add a validation result"""
        self.validation_results.append({
            "check": check,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Print immediately
        status_emoji = {
            "PASS": "✅",
            "FAIL": "❌", 
            "WARN": "⚠️",
            "INFO": "ℹ️",
            "ERROR": "🚨"
        }
        print(f"{status_emoji.get(status, '•')} {check}: {message}")
    
    def generate_report(self, results: List[Dict]) -> str:
        """Generate a detailed validation report"""
        report = ["# Claude Task Pickup Validation Report", ""]
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append("")
        
        # Summary
        total = len(results)
        passed = len([r for r in results if r["status"] == "PASS"])
        failed = len([r for r in results if r["status"] == "FAIL"]) 
        warnings = len([r for r in results if r["status"] == "WARN"])
        
        report.append("## Summary")
        report.append(f"- Total Checks: {total}")
        report.append(f"- Passed: {passed} ✅")
        report.append(f"- Failed: {failed} ❌")
        report.append(f"- Warnings: {warnings} ⚠️")
        report.append("")
        
        # Detailed Results
        report.append("## Detailed Results")
        report.append("")
        
        for result in results:
            report.append(f"### {result['check']}")
            report.append(f"- Status: {result['status']}")
            report.append(f"- {result['message']}")
            report.append("")
        
        # Recommendations
        if failed > 0 or warnings > 0:
            report.append("## Recommendations")
            report.append("")
            
            if any(r["check"] == "README Visibility" and r["status"] == "FAIL" for r in results):
                report.append("1. Add urgent notice to top of README.md")
            
            if any("CLAUDE_TASKS.md" in r["check"] and r["status"] == "FAIL" for r in results):
                report.append("2. Create CLAUDE_TASKS.md with urgent task list")
            
            if any("GitHub Issues" in r["check"] and r["status"] == "WARN" for r in results):
                report.append("3. Pin urgent issues on GitHub")
            
            if any("AI Workflows" in r["check"] and r["status"] == "FAIL" for r in results):
                report.append("4. Enable AI workflow automation")
        
        return "\n".join(report)


def main():
    """Run validation and save report"""
    validator = ClaudeTaskValidator()
    
    # Run validation
    all_passed, results = validator.run_validation()
    
    # Generate report
    report = validator.generate_report(results)
    
    # Save report
    report_path = Path("claude_validation_report.md")
    report_path.write_text(report)
    
    print(f"\n📊 Validation {'PASSED' if all_passed else 'FAILED'}")
    print(f"📄 Full report saved to: {report_path}")
    
    # Create a visibility test file for Claude
    test_file = Path("CLAUDE_CAN_YOU_SEE_THIS.md")
    test_file.write_text(f"""# 👋 Claude Visibility Test

If you can see this file, the task pickup system is working!

## Current Status:
- Validation ran at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
- Result: {'✅ ALL SYSTEMS GO' if all_passed else '⚠️ SOME ISSUES FOUND'}

## Your Tasks:
1. Check CLAUDE_TASKS.md for urgent tasks
2. Look in .claude-tasks/ directory 
3. Review ai-tasks/issue-178.md for DDD implementation
4. Implement issue #180 (greeting function test)

## Quick Test:
If you see this, please create a file called `CLAUDE_CONFIRMED.md` with:
- Confirmation you can see the tasks
- Which task files you found
- Ready to begin implementation

This is a validation test file.
""")
    
    print(f"🧪 Created visibility test file: {test_file}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())