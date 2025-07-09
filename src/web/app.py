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
from src.events.kafka.service import initialize_kafka_service, shutdown_kafka_service, get_kafka_service

app = FastAPI(title="Debate Nucleus API")

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
    
    # Initialize Kafka service if enabled
    kafka_enabled = os.getenv("KAFKA_ENABLED", "true").lower() == "true"
    if kafka_enabled:
        try:
            await initialize_kafka_service(event_bus)
        except Exception as e:
            print(f"Warning: Failed to initialize Kafka service: {e}")
            print("Continuing without Kafka integration")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    await webhook_event_handler.stop()
    await event_bus.stop()
    await webhook_service.stop()
    
    # Shutdown Kafka service if running
    try:
        await shutdown_kafka_service()
    except Exception as e:
        print(f"Warning: Error shutting down Kafka service: {e}")


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
    }
    
    # Add Kafka stats if available
    kafka_service = await get_kafka_service()
    if kafka_service:
        stats["kafka"] = kafka_service.get_stats()

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


# Kafka-specific endpoints
@app.get("/kafka/health")
async def kafka_health_check():
    """Get Kafka service health status"""
    kafka_service = await get_kafka_service()
    if not kafka_service:
        return {"status": "not_running", "message": "Kafka service not initialized"}
    
    health = await kafka_service.health_check()
    return {"status": "running", "health": health}


@app.get("/kafka/topics")
async def list_kafka_topics():
    """List all Kafka topics"""
    kafka_service = await get_kafka_service()
    if not kafka_service:
        raise HTTPException(status_code=503, detail="Kafka service not available")
    
    topics = await kafka_service.list_topics()
    return {"topics": topics}


@app.get("/kafka/topics/{topic_name}")
async def get_kafka_topic_metadata(topic_name: str):
    """Get metadata for a specific Kafka topic"""
    kafka_service = await get_kafka_service()
    if not kafka_service:
        raise HTTPException(status_code=503, detail="Kafka service not available")
    
    metadata = await kafka_service.get_topic_metadata(topic_name)
    if not metadata:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return metadata


class KafkaEventRequest(BaseModel):
    event_type: str
    event_data: Dict[str, Any]
    partition_key: Optional[str] = None


@app.post("/kafka/events")
async def publish_kafka_event(request: KafkaEventRequest):
    """Publish an event to Kafka"""
    kafka_service = await get_kafka_service()
    if not kafka_service:
        raise HTTPException(status_code=503, detail="Kafka service not available")
    
    success = await kafka_service.publish_event(
        event_type=request.event_type,
        event_data=request.event_data,
        partition_key=request.partition_key
    )
    
    if success:
        return {"status": "published", "event_type": request.event_type}
    else:
        raise HTTPException(status_code=500, detail="Failed to publish event")


class CreateTopicRequest(BaseModel):
    event_type: str
    num_partitions: Optional[int] = None
    replication_factor: Optional[int] = None


@app.post("/kafka/topics")
async def create_kafka_topic(request: CreateTopicRequest):
    """Create a new Kafka topic"""
    kafka_service = await get_kafka_service()
    if not kafka_service:
        raise HTTPException(status_code=503, detail="Kafka service not available")
    
    success = await kafka_service.create_topic(
        event_type=request.event_type,
        num_partitions=request.num_partitions,
        replication_factor=request.replication_factor
    )
    
    if success:
        return {"status": "created", "topic": kafka_service.get_config().get_topic_name(request.event_type)}
    else:
        raise HTTPException(status_code=500, detail="Failed to create topic")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
