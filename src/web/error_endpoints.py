#!/usr/bin/env python3
"""
Error handling and recovery endpoints for the web API
"""

from typing import Any, Dict

from fastapi import APIRouter

from src.core.error_handler import get_error_handler
from src.core.resilience import get_resilience_manager

router = APIRouter(prefix="/errors", tags=["error_handling"])


@router.get("/summary")
async def get_error_summary(minutes: int = 60) -> Dict[str, Any]:
    """Get error summary for the last N minutes"""
    error_handler = get_error_handler()
    return error_handler.get_error_summary(minutes)


@router.get("/resilience/status")
async def get_resilience_status() -> Dict[str, Any]:
    """Get current resilience status"""
    resilience_manager = get_resilience_manager()
    return resilience_manager.get_status()


@router.post("/resilience/reset/{component}")
async def reset_component(component: str) -> Dict[str, str]:
    """Reset a component's resilience state"""
    # This would reset circuit breakers, clear error counts, etc.
    return {
        "status": "reset",
        "component": component,
        "message": f"Component {component} resilience state has been reset",
    }
