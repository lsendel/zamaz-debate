#!/usr/bin/env python3
"""Simplified web interface for Zamaz Debate System with basic enhancements"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from domain.models import PullRequest
from services.pr_review_service import PRReviewService
from src.core.error_handler import get_error_handler
from src.core.nucleus import DebateNucleus
from src.webhooks import WebhookService, WebhookEventHandler, webhook_router, init_webhook_api
from src.events.event_bus import EventBus
from src.core.api_rate_limiting import create_rate_limit_middleware, rate_limit_manager
from src.core.rate_limit_config import get_rate_limit_config

app = FastAPI(title="Debate Nucleus API - Enhanced")

# Initialize rate limiting
config_manager = get_rate_limit_config()
if config_manager.global_settings.enabled:
    from src.core.api_rate_limiting import APIRateLimitMiddleware
    app.add_middleware(
        APIRateLimitMiddleware,
        default_config=None,
        endpoint_configs=config_manager.get_all_configs(),
        store=None,
    )

# Initialize event bus
event_bus = EventBus()

# Initialize webhook system
webhook_service = WebhookService()
webhook_event_handler = WebhookEventHandler(webhook_service, event_bus)

# Initialize main services with event bus
nucleus = DebateNucleus(event_bus=event_bus)
pr_review_service = PRReviewService()

# Initialize webhook API
init_webhook_api(webhook_service)

# Import and include error handling endpoints
from src.web.error_endpoints import router as error_router

app.include_router(error_router)
app.include_router(webhook_router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await webhook_service.start()
    await webhook_event_handler.start()
    print("✅ Enhanced web interface started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    await webhook_event_handler.stop()
    await webhook_service.stop()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    error_handler = get_error_handler()

    # Extract useful context
    context = {
        "path": request.url.path,
        "method": request.method,
        "client": request.client.host if request.client else None,
    }

    # Log error
    await error_handler.handle_error(
        error=exc,
        component="api",
        operation=f"{request.method} {request.url.path}",
        context=context,
    )

    # Return error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": request.url.path,
        },
    )


# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class DecisionRequest(BaseModel):
    question: str
    context: str = ""

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        return v


class DecisionResponse(BaseModel):
    decision: str
    method: str
    rounds: int
    time: str
    implementation_assignee: Optional[str] = None
    implementation_complexity: Optional[str] = None


@app.get("/")
async def root():
    """Serve the main HTML interface"""
    index_file = Path(__file__).parent / "static" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Welcome to Debate Nucleus API"}


@app.post("/decide", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest):
    """Make a decision using the debate system"""
    result = await nucleus.decide(request.question, request.context)
    return DecisionResponse(**result)


@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    # Count actual files on disk for accurate stats
    debates_dir = Path("data/debates")
    decisions_dir = Path("data/decisions")

    debate_count = len(list(debates_dir.glob("*.json"))) if debates_dir.exists() else 0
    decision_count = len(list(decisions_dir.glob("*.json"))) if decisions_dir.exists() else 0

    stats = {
        "version": nucleus.VERSION,
        "decisions_made": decision_count,
        "debates_run": debate_count,
        "enhanced_features": True,
    }
    
    return stats


@app.post("/evolve")
async def trigger_evolution():
    """Trigger self-improvement"""
    result = await nucleus.evolve_self()
    return result


class PRReviewRequest(BaseModel):
    pr_id: str
    implementation_code: str
    reviewer: str


@app.post("/review-pr")
async def review_pr(request: PRReviewRequest):
    """Review a pull request"""
    # Load PR details from draft
    pr_drafts_dir = Path(__file__).parent.parent.parent / "data" / "pr_drafts"
    pr_file = pr_drafts_dir / f"{request.pr_id}.json"

    if not pr_file.exists():
        raise HTTPException(status_code=404, detail="PR draft not found")

    with open(pr_file, "r") as f:
        pr_data = json.load(f)

    # Create PR object
    pr = PullRequest(
        id=request.pr_id,
        title=pr_data["title"],
        body=pr_data["body"],
        branch_name=pr_data["branch"],
        base_branch=pr_data["base"],
        assignee=pr_data["assignee"],
        labels=pr_data.get("labels", []),
        decision=None,  # Not needed for review
    )

    # Perform review
    review_result = await pr_review_service.review_pr(pr, request.implementation_code, request.reviewer)

    return review_result


@app.get("/pending-reviews")
async def get_pending_reviews():
    """Get list of PRs pending review"""
    pending = await pr_review_service.check_pending_reviews()
    return {"pending_reviews": pending}


@app.get("/pr-drafts")
async def get_pr_drafts():
    """Get list of PR drafts"""
    pr_drafts_dir = Path(__file__).parent.parent.parent / "data" / "pr_drafts"
    drafts = []

    if pr_drafts_dir.exists():
        for pr_file in pr_drafts_dir.glob("*.json"):
            with open(pr_file, "r") as f:
                pr_data = json.load(f)

            drafts.append(
                {
                    "id": pr_file.stem,
                    "title": pr_data.get("title", "Unknown"),
                    "assignee": pr_data.get("assignee", "Unknown"),
                    "reviewer": pr_data.get("reviewer", "Unknown"),
                    "created_at": pr_data.get("created_at", "Unknown"),
                }
            )

    return {"pr_drafts": drafts}


@app.get("/rate-limits/stats")
async def get_rate_limit_stats():
    """Get rate limiting statistics"""
    stats = await rate_limit_manager.get_rate_limit_stats()
    return stats


@app.get("/rate-limits/config")
async def get_rate_limit_config():
    """Get current rate limiting configuration"""
    config_summary = config_manager.get_config_summary()
    return config_summary


@app.post("/rate-limits/reset/{client_id}")
async def reset_rate_limit(client_id: str, endpoint: Optional[str] = None):
    """Reset rate limits for a specific client"""
    success = await rate_limit_manager.reset_rate_limit(client_id, endpoint)
    return {
        "success": success,
        "message": f"Rate limit reset for {client_id}" + (f" on {endpoint}" if endpoint else "")
    }


@app.get("/rate-limits/health")
async def rate_limit_health():
    """Health check for rate limiting system"""
    validation = config_manager.validate_configuration()
    stats = await rate_limit_manager.get_rate_limit_stats()
    
    return {
        "status": "healthy" if validation["valid"] else "degraded",
        "enabled": config_manager.global_settings.enabled,
        "total_limiters": stats.get("total_limiters", 0),
        "validation": validation,
    }


# Enhanced endpoints that work with existing infrastructure

@app.get("/debates")
async def list_debates(limit: int = 50, offset: int = 0, search: Optional[str] = None):
    """List all debates from the data directory"""
    debates_dir = Path("data/debates")
    if not debates_dir.exists():
        return {"debates": [], "total": 0}
    
    debate_files = sorted(debates_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        filtered_files = []
        for file in debate_files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if search_lower in data.get("question", "").lower():
                        filtered_files.append(file)
            except:
                continue
        debate_files = filtered_files
    
    total = len(debate_files)
    
    debates = []
    for debate_file in debate_files[offset:offset + limit]:
        try:
            with open(debate_file, 'r') as f:
                debate_data = json.load(f)
                debates.append({
                    "id": debate_file.stem,
                    "question": debate_data.get("question", "Unknown"),
                    "complexity": debate_data.get("complexity", "unknown"),
                    "method": debate_data.get("method", "standard"),
                    "consensus": debate_data.get("consensus", False),
                    "rounds": len(debate_data.get("rounds", [])),
                    "created_at": datetime.fromtimestamp(debate_file.stat().st_mtime).isoformat()
                })
        except Exception:
            continue
    
    return {"debates": debates, "total": total, "limit": limit, "offset": offset}


@app.get("/debates/{debate_id}")
async def get_debate(debate_id: str):
    """Get details of a specific debate"""
    debate_file = Path("data/debates") / f"{debate_id}.json"
    
    if not debate_file.exists():
        raise HTTPException(status_code=404, detail="Debate not found")
    
    try:
        with open(debate_file, 'r') as f:
            debate_data = json.load(f)
        
        return {
            "id": debate_id,
            "question": debate_data.get("question"),
            "context": debate_data.get("context", ""),
            "complexity": debate_data.get("complexity"),
            "method": debate_data.get("method", "standard"),
            "rounds": debate_data.get("rounds", []),
            "consensus": debate_data.get("consensus", False),
            "final_decision": debate_data.get("final_decision", ""),
            "created_at": datetime.fromtimestamp(debate_file.stat().st_mtime).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading debate: {str(e)}")


@app.get("/debates/manual/template")
async def get_manual_debate_template():
    """Get template for conducting debates in Claude.ai"""
    template = """# Debate Template for Claude.ai

## Question Format
Please debate the following question with critical analysis:

**Question**: [Your question here]
**Context**: [Additional context or constraints]

## Instructions
1. First, present Claude's perspective with:
   - Clear position statement
   - 2-3 key supporting arguments
   - Potential risks or challenges
   - Implementation recommendation

2. Then, present Gemini's perspective with:
   - Critical analysis of the proposal
   - Alternative approaches
   - Feasibility assessment
   - Counter-recommendation

3. Finally, provide a consensus or summary of key disagreements

## Example Format
### Claude's Perspective
[Your response as Claude]

### Gemini's Perspective
[Your response as Gemini]

### Consensus/Summary
[Brief summary of agreement or key differences]
"""
    
    return {
        "template": template,
        "instructions": "Copy this template to Claude.ai, fill in your question, and paste the complete response back here"
    }


@app.get("/workflows")
async def list_workflows():
    """List available workflow types (simplified)"""
    return {
        "workflows": [
            {
                "id": "standard",
                "name": "Standard Debate",
                "description": "Default debate flow with Claude and Gemini",
                "participants": ["Claude", "Gemini"],
                "max_rounds": 5
            },
            {
                "id": "simple",
                "name": "Simple Decision",
                "description": "Quick decision without full debate",
                "participants": ["Claude"],
                "max_rounds": 1
            },
            {
                "id": "complex",
                "name": "Complex Analysis",
                "description": "Extended debate for complex decisions",
                "participants": ["Claude", "Gemini"],
                "max_rounds": 10
            }
        ]
    }


@app.get("/implementations/pending")
async def get_pending_implementations():
    """Get pending implementation tasks from GitHub and decisions"""
    implementations = []
    
    # Check GitHub for AI-assigned issues
    try:
        import subprocess
        result = subprocess.run(
            ["gh", "issue", "list", "--label", "ai-assigned", "--state", "open", "--json", "number,title,state,assignees,createdAt,url,labels"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            issues = json.loads(result.stdout)
            
            for issue in issues:
                implementations.append({
                    "id": f"issue_{issue['number']}",
                    "title": issue["title"],
                    "assignee": issue["assignees"][0]["login"] if issue["assignees"] else "unassigned",
                    "status": "in_progress" if any(label["name"] == "in-progress" for label in issue.get("labels", [])) else "open",
                    "created_at": issue["createdAt"],
                    "url": issue["url"],
                    "type": "github_issue",
                    "days_pending": (datetime.now() - datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))).days
                })
    except Exception as e:
        print(f"Error fetching GitHub issues: {e}")
    
    # Also check PR drafts
    pr_drafts_dir = Path("data/pr_drafts")
    if pr_drafts_dir.exists():
        for pr_file in pr_drafts_dir.glob("*.json"):
            try:
                with open(pr_file, 'r') as f:
                    pr_data = json.load(f)
                
                implementations.append({
                    "id": f"pr_draft_{pr_file.stem}",
                    "title": pr_data.get("title", "Unknown PR"),
                    "assignee": pr_data.get("assignee", "Unknown"),
                    "status": "draft",
                    "created_at": pr_data.get("created_at", datetime.now().isoformat()),
                    "type": "pr_draft",
                    "days_pending": (datetime.now() - datetime.fromisoformat(pr_data.get("created_at", datetime.now().isoformat()))).days
                })
            except:
                continue
    
    # Sort by days pending
    implementations.sort(key=lambda x: x.get("days_pending", 0), reverse=True)
    
    return {"pending_implementations": implementations}


@app.get("/implementations/{implementation_id}/status")
async def get_implementation_status(implementation_id: str):
    """Get detailed status of an implementation"""
    status = {
        "id": implementation_id,
        "commits": [],
        "pr_status": None,
        "issue_status": None
    }
    
    try:
        # If it's a GitHub issue
        if implementation_id.startswith("issue_"):
            issue_number = implementation_id.replace("issue_", "")
            
            # Get issue details
            import subprocess
            result = subprocess.run(
                ["gh", "issue", "view", issue_number, "--json", "number,title,state,assignees,createdAt,url,labels,body"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                issue = json.loads(result.stdout)
                status["issue_status"] = {
                    "number": issue["number"],
                    "title": issue["title"],
                    "state": issue["state"],
                    "url": issue["url"],
                    "assignee": issue["assignees"][0]["login"] if issue["assignees"] else None
                }
                
                # Check for linked PRs in the issue body or comments
                if "#" in issue.get("body", ""):
                    import re
                    pr_numbers = re.findall(r'#(\d+)', issue["body"])
                    for pr_num in pr_numbers:
                        # Get PR details
                        pr_result = subprocess.run(
                            ["gh", "pr", "view", pr_num, "--json", "number,state,merged,commits"],
                            capture_output=True,
                            text=True
                        )
                        if pr_result.returncode == 0:
                            pr_data = json.loads(pr_result.stdout)
                            status["pr_status"] = {
                                "number": pr_data["number"],
                                "state": pr_data["state"],
                                "merged": pr_data["merged"]
                            }
                            
                            # Get commits from PR
                            if pr_data.get("commits"):
                                for commit in pr_data["commits"][:5]:  # Last 5 commits
                                    status["commits"].append({
                                        "sha": commit["oid"][:7],
                                        "message": commit["messageHeadline"],
                                        "author": commit["authors"][0]["name"] if commit.get("authors") else "Unknown"
                                    })
                
    except Exception as e:
        print(f"Error getting implementation status: {e}")
    
    return status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)