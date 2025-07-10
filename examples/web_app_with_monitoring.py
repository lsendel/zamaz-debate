#!/usr/bin/env python3
"""
Example: Web Application with Monitoring Integration

This example shows how to integrate the monitoring system into the existing
Zamaz Debate System FastAPI application.

This demonstrates the changes needed to add comprehensive monitoring to src/web/app.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

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

# MONITORING INTEGRATION IMPORTS
from src.infrastructure.monitoring.web_integration import MonitoringIntegration
from src.infrastructure.monitoring.config import MonitoringConfig
from src.infrastructure.kafka.event_bridge import KafkaEventBridge, get_hybrid_event_bus

app = FastAPI(title="Debate Nucleus API")

# Initialize monitoring EARLY in the app setup
monitoring_config = MonitoringConfig.from_env()
monitoring = MonitoringIntegration(monitoring_config)

# Add monitoring router
app.include_router(monitoring.router)

# Add monitoring middleware for response time tracking
if monitoring.prometheus_exporter.is_enabled():
    app.add_middleware(type(monitoring.middleware), prometheus_exporter=monitoring.prometheus_exporter)

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

# Initialize event bus with Kafka integration for monitoring
kafka_bridge = None
event_bus = EventBus()

# Try to initialize Kafka if configured
try:
    if monitoring_config.kafka_monitoring:
        # Create hybrid event bus with Kafka support
        event_bus = get_hybrid_event_bus()
        kafka_bridge = event_bus.kafka_bridge if hasattr(event_bus, 'kafka_bridge') else None
        
        # Connect monitoring to Kafka bridge
        if kafka_bridge:
            monitoring.set_kafka_bridge(kafka_bridge)
            print("✓ Kafka monitoring integrated")
except Exception as e:
    print(f"⚠️  Kafka integration failed, using in-memory event bus: {e}")
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
    
    # Start monitoring services
    await monitoring.start()
    
    # Start Kafka consumers if available
    if kafka_bridge:
        try:
            # Start Kafka consumers in background
            asyncio.create_task(kafka_bridge.start_consumers())
            print("✓ Kafka consumers started")
        except Exception as e:
            print(f"⚠️  Failed to start Kafka consumers: {e}")
    
    print("🚀 Zamaz Debate System started with monitoring")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    await webhook_event_handler.stop()
    await event_bus.stop()
    await webhook_service.stop()
    
    # Stop monitoring services
    await monitoring.stop()
    
    # Stop Kafka bridge if available
    if kafka_bridge:
        try:
            kafka_bridge.stop()
            print("✓ Kafka bridge stopped")
        except Exception as e:
            print(f"⚠️  Error stopping Kafka bridge: {e}")


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

    # Update error rate metrics
    if monitoring.prometheus_exporter.is_enabled():
        # This would increment error counter
        pass

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
    return {"message": "Welcome to Debate Nucleus API with Monitoring"}


@app.post("/decide", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest):
    """Make a decision using the debate system"""
    
    # Record debate start for monitoring
    if monitoring.prometheus_exporter.is_enabled():
        monitoring.prometheus_exporter.record_debate_started("unknown")  # complexity determined later
    
    result = await nucleus.decide(request.question, request.context)
    
    # Record debate completion
    if monitoring.prometheus_exporter.is_enabled():
        complexity = result.get("implementation_complexity", "unknown")
        outcome = "success"  # could be determined from result
        duration = 0.0  # would need to be tracked
        monitoring.prometheus_exporter.record_debate_completed(complexity, outcome, duration)
    
    return DecisionResponse(**result)


@app.get("/stats")
async def get_stats():
    """Get system statistics (enhanced with monitoring data)"""
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
    
    # Add monitoring stats if available
    if monitoring.metrics_collector:
        try:
            monitoring_stats = monitoring.metrics_collector.get_current_metrics()
            stats["monitoring"] = monitoring_stats
        except Exception as e:
            stats["monitoring_error"] = str(e)
    
    return stats


@app.post("/evolve")
async def trigger_evolution():
    """Trigger self-improvement"""
    result = await nucleus.evolve_self()
    return result


# Include all existing endpoints...
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


# NEW MONITORING ENDPOINTS are automatically included via monitoring.router

# Additional endpoint to demonstrate monitoring integration
@app.get("/monitoring-demo")
async def monitoring_demo():
    """Demonstrate monitoring capabilities"""
    
    demo_info = {
        "message": "Zamaz Debate System with Comprehensive Monitoring",
        "monitoring_endpoints": {
            "metrics": "/monitoring/metrics",
            "health": "/monitoring/health", 
            "health_summary": "/monitoring/health/summary",
            "status": "/monitoring/status",
            "config": "/monitoring/config",
        },
        "external_services": {
            "prometheus": f"http://localhost:{monitoring_config.prometheus.port}",
            "grafana": f"http://localhost:{monitoring_config.grafana.port}",
            "metrics_endpoint": f"http://localhost:{monitoring_config.prometheus.port}/metrics"
        },
        "features": {
            "kafka_monitoring": monitoring_config.kafka_monitoring,
            "performance_monitoring": monitoring_config.performance_monitoring,
            "health_checks": monitoring_config.health_checks,
            "prometheus_enabled": monitoring.prometheus_exporter.is_enabled(),
        }
    }
    
    return demo_info


if __name__ == "__main__":
    import uvicorn

    # Print startup information
    print("🎯 Starting Zamaz Debate System with Monitoring")
    print("=" * 50)
    print(f"📊 Prometheus metrics: http://localhost:{monitoring_config.prometheus.port}/metrics")
    print(f"🔍 Health checks: http://localhost:8000/monitoring/health")
    print(f"📈 Monitoring status: http://localhost:8000/monitoring/status")
    print(f"🐳 Start monitoring stack: cd monitoring && docker-compose up -d")
    print("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=8000)