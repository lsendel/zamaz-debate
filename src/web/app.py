#!/usr/bin/env python3
"""Web interface for Zamaz Debate System"""
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
try:
    from src.infrastructure.kafka import KafkaConfig, HybridEventBus, get_hybrid_event_bus
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Warning: Kafka support not available (missing confluent_kafka)")
from src.core.api_rate_limiting import create_rate_limit_middleware, rate_limit_manager
from src.core.rate_limit_config import get_rate_limit_config
try:
    from services.orchestration_service import OrchestrationService
    ORCHESTRATION_AVAILABLE = True
except ImportError:
    ORCHESTRATION_AVAILABLE = False
    print("Warning: Orchestration service not available")

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

# Initialize event bus - use HybridEventBus if Kafka is configured
kafka_enabled = os.getenv('KAFKA_ENABLED', 'false').lower() == 'true' and KAFKA_AVAILABLE
if kafka_enabled:
    # Use Kafka-enabled hybrid event bus
    kafka_config = KafkaConfig.from_env()
    event_bus = get_hybrid_event_bus(kafka_config)
    # Bridge all events automatically
    event_bus.kafka_bridge.bridge_all_events()
else:
    # Use standard in-memory event bus
    event_bus = EventBus()
    if os.getenv('KAFKA_ENABLED', 'false').lower() == 'true' and not KAFKA_AVAILABLE:
        print("Warning: Kafka enabled but dependencies not available, using in-memory event bus")

# Initialize webhook system
webhook_service = WebhookService()
webhook_event_handler = WebhookEventHandler(webhook_service, event_bus)

# Initialize main services with event bus
nucleus = DebateNucleus(event_bus=event_bus)
pr_review_service = PRReviewService()
if ORCHESTRATION_AVAILABLE:
    orchestration_service = OrchestrationService()
else:
    orchestration_service = None

# Initialize webhook API
init_webhook_api(webhook_service)

# Import and include error handling endpoints
from src.web.error_endpoints import router as error_router
from src.web.orchestration_endpoints import router as orchestration_router

app.include_router(error_router)
app.include_router(webhook_router)
app.include_router(orchestration_router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await webhook_service.start()
    await webhook_event_handler.start()
    
    # Start Kafka consumers if enabled
    if kafka_enabled and hasattr(event_bus, 'kafka_bridge'):
        # Start consumers in background task
        asyncio.create_task(
            event_bus.kafka_bridge.start_consumers(),
            name="kafka-consumers"
        )
        print("✅ Kafka event bridge started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    await webhook_event_handler.stop()
    await webhook_service.stop()
    
    # Stop Kafka bridge if enabled
    if kafka_enabled and hasattr(event_bus, 'kafka_bridge'):
        event_bus.kafka_bridge.stop()
        print("✅ Kafka event bridge stopped")


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
        "kafka_enabled": kafka_enabled,
    }
    
    # Add Kafka metrics if enabled
    if kafka_enabled and hasattr(event_bus, 'kafka_bridge'):
        stats["kafka_metrics"] = event_bus.kafka_bridge.get_metrics()
    
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


# Simple debate history endpoint
@app.get("/debates")
async def list_debates(limit: int = 50, offset: int = 0):
    """List all debates from the data directory"""
    debates_dir = Path("data/debates")
    if not debates_dir.exists():
        return {"debates": [], "total": 0}
    
    debate_files = sorted(debates_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
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
                    "created_at": datetime.fromtimestamp(debate_file.stat().st_mtime).isoformat()
                })
        except Exception:
            continue
    
    return {"debates": debates, "total": total, "limit": limit, "offset": offset}


# Orchestrator endpoints (only if available)
if ORCHESTRATION_AVAILABLE:
    @app.post("/orchestrate")
    async def orchestrate_debate(request: DecisionRequest):
        """Start an orchestrated debate with intelligent workflow selection"""
        result = await orchestration_service.orchestrate_debate(
        request.question,
        request.context,
        complexity="complex"  # Let orchestrator determine complexity
    )
    
    # Convert to format compatible with existing system
    from services.orchestration_service import create_orchestrated_debate_result
    debate_id = str(result.workflow_result.metadata.get("debate_id", "unknown"))
    formatted_result = await create_orchestrated_debate_result(result, debate_id)
    
    return formatted_result


@app.get("/workflows")
async def list_workflows():
    """List available workflow definitions"""
    workflows = orchestration_service.get_available_workflows()
    return {
        "workflows": [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "participants": wf.participants,
                "steps": len(wf.steps),
                "max_rounds": wf.config.max_rounds
            }
            for wf in workflows
        ]
    }


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get details of a specific workflow"""
    workflow = orchestration_service.workflow_engine.get_workflow_definition(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "version": workflow.version,
        "participants": workflow.participants,
        "config": {
            "max_rounds": workflow.config.max_rounds,
            "min_rounds": workflow.config.min_rounds,
            "consensus_threshold": workflow.config.consensus_threshold,
            "auto_consensus_check": workflow.config.auto_consensus_check
        },
        "steps": [
            {
                "id": step.id,
                "type": step.type.value,
                "name": step.name,
                "description": step.description,
                "required_participants": step.required_participants
            }
            for step in workflow.steps
        ]
    }


@app.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, request: DecisionRequest):
    """Execute a specific workflow"""
    result = await orchestration_service.orchestrate_debate(
        request.question,
        request.context,
        complexity="moderate",
        preferred_workflow=workflow_id
    )
    
    from services.orchestration_service import create_orchestrated_debate_result
    debate_id = str(result.workflow_result.metadata.get("debate_id", "unknown"))
    formatted_result = await create_orchestrated_debate_result(result, debate_id)
    
    return formatted_result


@app.get("/workflows/active")
async def list_active_workflows():
    """List currently active workflows"""
    active = orchestration_service.workflow_engine.list_active_workflows()
    return {
        "active_workflows": [
            {
                "id": str(wf.id),
                "definition_id": wf.definition.id,
                "definition_name": wf.definition.name,
                "state": wf.state.value,
                "current_step": wf.current_step,
                "total_steps": len(wf.definition.steps),
                "started_at": wf.start_time.isoformat() if wf.start_time else None
            }
            for wf in active
        ]
    }


@app.post("/workflows/{workflow_id}/pause")
async def pause_workflow(workflow_id: str):
    """Pause an active workflow"""
    success = await orchestration_service.pause_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found or not active")
    return {"message": "Workflow paused", "workflow_id": workflow_id}


@app.post("/workflows/{workflow_id}/resume")
async def resume_workflow(workflow_id: str):
    """Resume a paused workflow"""
    success = await orchestration_service.resume_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found or not paused")
    return {"message": "Workflow resumed", "workflow_id": workflow_id}


@app.post("/workflows/{workflow_id}/abort")
async def abort_workflow(workflow_id: str):
    """Abort an active workflow"""
    success = await orchestration_service.abort_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found or not active")
    return {"message": "Workflow aborted", "workflow_id": workflow_id}


@app.get("/orchestration/stats")
async def get_orchestration_stats():
    """Get orchestration service statistics"""
    return orchestration_service.get_workflow_stats()


# Manual debate endpoints
class ManualDebateRequest(BaseModel):
    question: str
    context: str = ""
    complexity: str = "moderate"
    claude_response: str
    gemini_response: str


@app.post("/debates/manual")
async def create_manual_debate(request: ManualDebateRequest):
    """Create a manual debate entry from Claude.ai conversation"""
    import uuid
    from datetime import datetime
    from domain.models import Debate, Decision, DecisionType
    
    # Create debate object
    debate_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    debate = Debate(
        id=debate_id,
        question=request.question,
        context=request.context,
        complexity=request.complexity,
        rounds=[
            {
                "claude": request.claude_response,
                "gemini": request.gemini_response
            }
        ],
        consensus=True,  # Manual debates assume consensus
        final_decision=request.claude_response.split('\n')[0][:200],  # First line as decision
        method="manual_debate",
        cost_estimate=0.0,  # No API cost
        time_taken="Manual entry",
        created_at=datetime.now().isoformat()
    )
    
    # Save debate
    debate_repository.save(debate)
    
    # Create and save decision
    decision = Decision(
        id=str(uuid.uuid4()),
        debate_id=debate_id,
        question=request.question,
        decision_text=debate.final_decision,
        decision_type=DecisionType.from_complexity(request.complexity),
        complexity=request.complexity,
        assignee="claude" if request.complexity == "complex" else "gemini",
        created_at=datetime.now()
    )
    
    decision_repository.save(decision)
    
    return {
        "debate_id": debate_id,
        "message": "Manual debate saved successfully",
        "decision": debate.final_decision,
        "method": "manual_debate"
    }


@app.get("/debates/manual/template")
async def get_manual_debate_template():
    """Get template for conducting debates in Claude.ai"""
    template = """
# Debate Template for Claude.ai

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


@app.post("/debates/manual/import")
async def import_manual_debate(content: Dict[str, str]):
    """Import a debate from Claude.ai by parsing the content"""
    try:
        # Parse the content to extract Claude and Gemini responses
        full_content = content.get("content", "")
        question = content.get("question", "")
        context = content.get("context", "")
        
        # Simple parsing - look for section markers
        claude_start = full_content.find("Claude's Perspective")
        gemini_start = full_content.find("Gemini's Perspective")
        consensus_start = full_content.find("Consensus")
        
        if claude_start == -1 or gemini_start == -1:
            raise ValueError("Could not find required sections in the debate content")
        
        claude_response = full_content[claude_start:gemini_start].strip()
        gemini_response = full_content[gemini_start:consensus_start if consensus_start != -1 else None].strip()
        
        # Create manual debate
        request = ManualDebateRequest(
            question=question,
            context=context,
            complexity="moderate",
            claude_response=claude_response,
            gemini_response=gemini_response
        )
        
        return await create_manual_debate(request)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse debate content: {str(e)}")


# Debate history endpoints
@app.get("/debates")
async def list_debates(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None
):
    """List all debates with pagination and filtering"""
    all_debates = debate_repository.list()
    
    # Apply filters
    filtered_debates = all_debates
    
    if search:
        search_lower = search.lower()
        filtered_debates = [
            d for d in filtered_debates 
            if search_lower in d.question.lower() or search_lower in d.context.lower()
        ]
    
    if start_date:
        from datetime import datetime
        start = datetime.fromisoformat(start_date)
        filtered_debates = [
            d for d in filtered_debates 
            if datetime.fromisoformat(d.created_at) >= start
        ]
    
    if end_date:
        from datetime import datetime
        end = datetime.fromisoformat(end_date)
        filtered_debates = [
            d for d in filtered_debates 
            if datetime.fromisoformat(d.created_at) <= end
        ]
    
    # Sort by created_at descending
    filtered_debates.sort(key=lambda d: d.created_at, reverse=True)
    
    # Apply pagination
    total = len(filtered_debates)
    paginated = filtered_debates[offset:offset + limit]
    
    return {
        "debates": [
            {
                "id": d.id,
                "question": d.question,
                "complexity": d.complexity,
                "method": d.method,
                "consensus": d.consensus,
                "rounds": len(d.rounds),
                "created_at": d.created_at,
                "final_decision": d.final_decision[:100] + "..." if len(d.final_decision) > 100 else d.final_decision
            }
            for d in paginated
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/debates/{debate_id}")
async def get_debate(debate_id: str):
    """Get details of a specific debate"""
    debate = debate_repository.get(debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    # Get associated decision if any
    decisions = decision_repository.list()
    associated_decision = next((d for d in decisions if d.debate_id == debate_id), None)
    
    return {
        "id": debate.id,
        "question": debate.question,
        "context": debate.context,
        "complexity": debate.complexity,
        "method": debate.method,
        "rounds": debate.rounds,
        "consensus": debate.consensus,
        "final_decision": debate.final_decision,
        "cost_estimate": debate.cost_estimate,
        "time_taken": debate.time_taken,
        "created_at": debate.created_at,
        "decision": {
            "id": associated_decision.id,
            "decision_type": associated_decision.decision_type.value,
            "assignee": associated_decision.assignee,
            "pr_id": getattr(associated_decision, "pr_id", None),
            "issue_id": getattr(associated_decision, "issue_id", None)
        } if associated_decision else None
    }


@app.get("/debates/by-origin/{origin_type}/{origin_id}")
async def get_debates_by_origin(origin_type: str, origin_id: str):
    """Get debates that originated from a specific PR or issue"""
    # This would require tracking origin in the debate model
    # For now, search through decisions that have PR/issue associations
    decisions = decision_repository.list()
    
    matching_debates = []
    
    for decision in decisions:
        if origin_type == "pr" and hasattr(decision, "pr_id") and decision.pr_id == origin_id:
            debate = debate_repository.get(decision.debate_id)
            if debate:
                matching_debates.append(debate)
        elif origin_type == "issue" and hasattr(decision, "issue_id") and decision.issue_id == origin_id:
            debate = debate_repository.get(decision.debate_id)
            if debate:
                matching_debates.append(debate)
    
    return {
        "origin_type": origin_type,
        "origin_id": origin_id,
        "debates": [
            {
                "id": d.id,
                "question": d.question,
                "created_at": d.created_at,
                "final_decision": d.final_decision[:100] + "..."
            }
            for d in matching_debates
        ]
    }


@app.get("/debates/{debate_id}/rounds")
async def get_debate_rounds(debate_id: str):
    """Get all rounds of a specific debate"""
    debate = debate_repository.get(debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    return {
        "debate_id": debate_id,
        "total_rounds": len(debate.rounds),
        "rounds": [
            {
                "round_number": i + 1,
                "arguments": round_data
            }
            for i, round_data in enumerate(debate.rounds)
        ]
    }


@app.post("/debates/search")
async def search_debates(query: Dict[str, Any]):
    """Search debates by various criteria"""
    search_term = query.get("search", "")
    complexity = query.get("complexity")
    method = query.get("method")
    has_consensus = query.get("has_consensus")
    
    all_debates = debate_repository.list()
    results = []
    
    for debate in all_debates:
        # Check search term
        if search_term:
            search_lower = search_term.lower()
            if not any([
                search_lower in debate.question.lower(),
                search_lower in debate.context.lower(),
                search_lower in debate.final_decision.lower()
            ]):
                continue
        
        # Check filters
        if complexity and debate.complexity != complexity:
            continue
        if method and debate.method != method:
            continue
        if has_consensus is not None and debate.consensus != has_consensus:
            continue
        
        results.append({
            "id": debate.id,
            "question": debate.question,
            "complexity": debate.complexity,
            "method": debate.method,
            "consensus": debate.consensus,
            "created_at": debate.created_at,
            "relevance_score": 1.0  # Could implement actual scoring
        })
    
    # Sort by created_at
    results.sort(key=lambda d: d["created_at"], reverse=True)
    
    return {
        "query": query,
        "total_results": len(results),
        "results": results[:100]  # Limit to 100 results
    }


# Kafka status endpoints (only if Kafka is enabled)
@app.get("/kafka/status")
async def get_kafka_status():
    """Get Kafka connection and consumer status"""
    if not kafka_enabled:
        return {"enabled": False, "message": "Kafka is not enabled"}
    
    if hasattr(event_bus, 'kafka_bridge'):
        metrics = event_bus.kafka_bridge.get_metrics()
        return {
            "enabled": True,
            "connected": True,  # Simplified - could check actual connection
            "metrics": metrics,
            "topics": list(metrics.get("topics", {}).keys()) if metrics else []
        }
    
    return {"enabled": True, "connected": False, "message": "Kafka bridge not initialized"}


@app.post("/kafka/test")
async def test_kafka_event():
    """Send a test event to Kafka"""
    if not kafka_enabled:
        raise HTTPException(status_code=400, detail="Kafka is not enabled")
    
    from src.contexts.debate.events import DebateRequested
    from datetime import datetime
    
    test_event = DebateRequested(
        debate_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        question="Test question from Kafka endpoint",
        context="Testing Kafka integration",
        complexity="simple",
        occurred_at=datetime.now()
    )
    
    await event_bus.publish(test_event)
    
    return {
        "message": "Test event sent",
        "event_type": "DebateRequested",
        "debate_id": test_event.debate_id
    }


# Implementation tracking endpoints
@app.get("/implementations")
async def list_implementations():
    """List all implementations from decisions"""
    decisions = decision_repository.list()
    implementations = []
    
    for decision in decisions:
        if decision.decision_type.value in ["COMPLEX", "EVOLUTION"]:
            debate = debate_repository.get(decision.debate_id)
            implementations.append({
                "decision_id": decision.id,
                "debate_id": decision.debate_id,
                "question": decision.question,
                "decision_type": decision.decision_type.value,
                "assignee": decision.assignee,
                "created_at": decision.created_at.isoformat(),
                "pr_id": getattr(decision, "pr_id", None),
                "issue_id": getattr(decision, "issue_id", None),
                "status": getattr(decision, "implementation_status", "pending")
            })
    
    return {"implementations": implementations}


@app.get("/implementations/{debate_id}")
async def get_implementation_for_debate(debate_id: str):
    """Get implementation details for a specific debate"""
    decisions = decision_repository.list()
    decision = next((d for d in decisions if d.debate_id == debate_id), None)
    
    if not decision:
        raise HTTPException(status_code=404, detail="No decision found for this debate")
    
    debate = debate_repository.get(debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    return {
        "debate_id": debate_id,
        "decision_id": decision.id,
        "question": decision.question,
        "decision_text": decision.decision_text,
        "assignee": decision.assignee,
        "pr_id": getattr(decision, "pr_id", None),
        "issue_id": getattr(decision, "issue_id", None),
        "created_at": decision.created_at.isoformat(),
        "implementation_status": getattr(decision, "implementation_status", "pending"),
        "implementation_notes": getattr(decision, "implementation_notes", "")
    }


@app.get("/implementations/pending")
async def get_pending_implementations():
    """List implementations that are pending"""
    decisions = decision_repository.list()
    pending = []
    
    for decision in decisions:
        if decision.decision_type.value in ["COMPLEX", "EVOLUTION"]:
            status = getattr(decision, "implementation_status", "pending")
            if status == "pending":
                pending.append({
                    "decision_id": decision.id,
                    "debate_id": decision.debate_id,
                    "question": decision.question,
                    "assignee": decision.assignee,
                    "created_at": decision.created_at.isoformat(),
                    "days_pending": (datetime.now() - decision.created_at).days
                })
    
    # Sort by days pending (oldest first)
    pending.sort(key=lambda x: x["days_pending"], reverse=True)
    
    return {"pending_implementations": pending}


# Evolution Quality Management Endpoints
@app.get("/evolution/quality-report")
async def get_evolution_quality_report():
    """Get comprehensive evolution quality report"""
    try:
        report = nucleus.evolution_tracker.get_evolution_quality_report()
        return {"quality_report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quality report: {str(e)}")


@app.post("/evolution/{evolution_id}/track-success")
async def track_evolution_success(evolution_id: str, success_metrics: Dict[str, Any]):
    """Track the success/failure metrics of an implemented evolution"""
    try:
        success = nucleus.evolution_tracker.track_evolution_success(evolution_id, success_metrics)
        if success:
            return {"message": "Evolution success metrics recorded", "evolution_id": evolution_id}
        else:
            raise HTTPException(status_code=404, detail=f"Evolution {evolution_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking evolution success: {str(e)}")


@app.get("/evolution/recommendations")
async def get_evolution_recommendations():
    """Get recommendations for improving evolution diversity and quality"""
    try:
        recommendations = nucleus.evolution_tracker.get_evolution_recommendations()
        summary = nucleus.evolution_tracker.get_evolution_summary()
        return {
            "recommendations": recommendations,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")


@app.post("/evolution/{evolution_id}/rollback")
async def rollback_evolution(evolution_id: str):
    """Rollback a specific evolution (mark as inactive)"""
    try:
        success = nucleus.evolution_tracker.rollback_evolution(evolution_id)
        if success:
            return {"message": "Evolution rolled back successfully", "evolution_id": evolution_id}
        else:
            raise HTTPException(status_code=404, detail=f"Evolution {evolution_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rolling back evolution: {str(e)}")


@app.get("/evolution/active")
async def get_active_evolutions():
    """Get all active (non-rolled-back) evolutions"""
    try:
        evolutions = nucleus.evolution_tracker.get_active_evolutions()
        return {"active_evolutions": evolutions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting active evolutions: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
