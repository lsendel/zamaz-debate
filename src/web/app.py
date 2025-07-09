#!/usr/bin/env python3
"""Web interface for Zamaz Debate System"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import asyncio
import json
import os
from typing import Any, Dict, Optional

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

app = FastAPI(title="Debate Nucleus API")

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

# Initialize webhook system
webhook_service = WebhookService()
event_bus = EventBus()
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
    await event_bus.start()
    await webhook_event_handler.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    await webhook_event_handler.stop()
    await event_bus.stop()
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
