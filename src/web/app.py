#!/usr/bin/env python3
"""Web interface for Zamaz Debate System"""
import sys
from pathlib import Path
# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
import asyncio
from src.core.nucleus import DebateNucleus
from services.pr_review_service import PRReviewService
from domain.models import PullRequest
from src.core.error_handler import get_error_handler
import os
import json

app = FastAPI(title="Debate Nucleus API")
nucleus = DebateNucleus()
pr_review_service = PRReviewService()

# Import and include error handling endpoints
from src.web.error_endpoints import router as error_router
app.include_router(error_router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    error_handler = get_error_handler()
    
    # Extract useful context
    context = {
        "path": request.url.path,
        "method": request.method,
        "client": request.client.host if request.client else None
    }
    
    # Log error
    await error_handler.handle_error(
        error=exc,
        component="api",
        operation=f"{request.method} {request.url.path}",
        context=context
    )
    
    # Return error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": request.url.path
        }
    )

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class DecisionRequest(BaseModel):
    question: str
    context: str = ""
    
    @field_validator('question')
    @classmethod
    def question_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Question cannot be empty')
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
    
    return {
        "version": nucleus.VERSION,
        "decisions_made": decision_count,
        "debates_run": debate_count,
    }


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
