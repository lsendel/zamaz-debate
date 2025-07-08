#!/usr/bin/env python3
"""Web interface for Zamaz Debate System"""
import sys
from pathlib import Path
# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
from src.core.nucleus import DebateNucleus
from services.pr_review_service import PRReviewService
from services.adr_service import ADRService
from domain.models import PullRequest
import os
import json

app = FastAPI(title="Debate Nucleus API")
nucleus = DebateNucleus()
pr_review_service = PRReviewService()
adr_service = ADRService()

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class DecisionRequest(BaseModel):
    question: str
    context: str = ""


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
    return {
        "version": nucleus.VERSION,
        "decisions_made": nucleus.decision_count,
        "debates_run": nucleus.debate_count,
    }


@app.post("/evolve")
async def trigger_evolution():
    """Trigger self-improvement"""
    result = await nucleus.evolve_self()
    return result


@app.get("/adrs")
async def list_adrs():
    """Get list of all Architectural Decision Records"""
    return {
        "adrs": adr_service.get_all_adrs(),
        "total": len(adr_service.get_all_adrs())
    }


@app.get("/adrs/{number}")
async def get_adr(number: str):
    """Get a specific ADR by number"""
    adr = adr_service.get_adr(number)
    if not adr:
        raise HTTPException(status_code=404, detail="ADR not found")
    
    # Read the file content
    adr_file = adr_service.adr_dir / adr["filename"]
    if adr_file.exists():
        with open(adr_file, 'r') as f:
            adr["content"] = f.read()
    
    return adr


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
        decision=None  # Not needed for review
    )
    
    # Perform review
    review_result = await pr_review_service.review_pr(
        pr, request.implementation_code, request.reviewer
    )
    
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
            
            drafts.append({
                "id": pr_file.stem,
                "title": pr_data.get("title", "Unknown"),
                "assignee": pr_data.get("assignee", "Unknown"),
                "reviewer": pr_data.get("reviewer", "Unknown"),
                "created_at": pr_data.get("created_at", "Unknown")
            })
    
    return {"pr_drafts": drafts}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
