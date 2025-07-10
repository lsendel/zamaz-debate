"""
FastAPI routes for Evolution Effectiveness Dashboard

Provides web endpoints for accessing evolution effectiveness data and insights.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, List, Optional

from src.contexts.evolution_effectiveness.dashboard import EvolutionEffectivenessDashboard
from src.core.enhanced_evolution_tracker import EnhancedEvolutionTracker


# Create router for evolution effectiveness endpoints
effectiveness_router = APIRouter(prefix="/effectiveness", tags=["Evolution Effectiveness"])

# Initialize dashboard and tracker
dashboard = EvolutionEffectivenessDashboard()
enhanced_tracker = EnhancedEvolutionTracker(enable_effectiveness_framework=True)


@effectiveness_router.get("/", response_class=HTMLResponse)
async def get_effectiveness_dashboard():
    """Get the evolution effectiveness dashboard as HTML"""
    try:
        dashboard_data = await dashboard.get_dashboard_data()
        html_content = dashboard.render_dashboard_html(dashboard_data)
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")


@effectiveness_router.get("/api/summary")
async def get_effectiveness_summary() -> Dict:
    """Get summary of evolution effectiveness"""
    try:
        return await dashboard.get_effectiveness_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


@effectiveness_router.get("/api/health")
async def get_system_health() -> Dict:
    """Get system health metrics"""
    try:
        return await dashboard.get_system_health_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health metrics: {str(e)}")


@effectiveness_router.get("/api/patterns")
async def get_concerning_patterns() -> List[Dict]:
    """Get concerning evolution patterns"""
    try:
        return await dashboard.get_concerning_patterns()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get patterns: {str(e)}")


@effectiveness_router.get("/api/assessments")
async def get_recent_assessments(limit: int = 10) -> List[Dict]:
    """Get recent evolution effectiveness assessments"""
    try:
        return await dashboard.get_recent_assessments(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get assessments: {str(e)}")


@effectiveness_router.get("/api/problematic")
async def get_problematic_evolutions() -> List[Dict]:
    """Get evolutions with effectiveness problems"""
    try:
        return await dashboard.get_problematic_evolutions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get problematic evolutions: {str(e)}")


@effectiveness_router.get("/api/trends")
async def get_effectiveness_trends() -> Dict:
    """Get effectiveness trends over time"""
    try:
        return await dashboard.get_effectiveness_trends()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")


@effectiveness_router.get("/api/evolution/{evolution_id}")
async def get_evolution_details(evolution_id: str) -> Dict:
    """Get detailed information about a specific evolution"""
    try:
        return await dashboard.get_evolution_details(evolution_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get evolution details: {str(e)}")


@effectiveness_router.post("/api/assess/{evolution_id}")
async def assess_evolution_effectiveness(evolution_id: str) -> Dict:
    """Manually trigger effectiveness assessment for an evolution"""
    try:
        # Load evolution data
        evolution_history = enhanced_tracker.history.get("evolutions", [])
        evolution = None
        
        for evo in evolution_history:
            if evo.get("id") == evolution_id:
                evolution = evo
                break
        
        if not evolution:
            raise HTTPException(status_code=404, detail=f"Evolution {evolution_id} not found")
        
        # Assess effectiveness
        result = await enhanced_tracker._assess_evolution_effectiveness(evolution_id, evolution)
        
        return {
            "message": "Evolution effectiveness assessment completed",
            "evolution_id": evolution_id,
            "assessment": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


@effectiveness_router.get("/api/tracker/summary")
async def get_tracker_summary() -> Dict:
    """Get summary from the enhanced evolution tracker"""
    try:
        return await enhanced_tracker.get_evolution_effectiveness_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tracker summary: {str(e)}")


@effectiveness_router.get("/api/tracker/recommendations")
async def get_evolution_recommendations() -> List[Dict]:
    """Get recommendations for improving evolution effectiveness"""
    try:
        return enhanced_tracker.get_evolution_recommendations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@effectiveness_router.get("/api/tracker/should-evolve")
async def check_should_evolve() -> Dict:
    """Check if the system should evolve based on enhanced criteria"""
    try:
        return enhanced_tracker.should_evolve_enhanced()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check evolution status: {str(e)}")


@effectiveness_router.post("/api/validate-evolution")
async def validate_evolution_proposal(evolution: Dict) -> Dict:
    """Validate a proposed evolution before adding it"""
    try:
        # Use the enhanced tracker to validate
        result = await enhanced_tracker.add_evolution_with_validation(evolution)
        
        if result["success"]:
            return {
                "status": "validated",
                "message": "Evolution proposal is valid and has been added",
                "evolution_id": result["evolution_id"],
                "effectiveness_assessment": result["effectiveness_assessment"]
            }
        else:
            return {
                "status": "rejected",
                "message": f"Evolution proposal rejected: {result['reason']}",
                "details": result
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@effectiveness_router.get("/api/dashboard-data")
async def get_dashboard_data() -> Dict:
    """Get all dashboard data as JSON"""
    try:
        return await dashboard.get_dashboard_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


# Add a simple health check endpoint
@effectiveness_router.get("/health")
async def health_check() -> Dict:
    """Health check for the effectiveness framework"""
    try:
        # Basic health check
        summary = await dashboard.get_effectiveness_summary()
        
        return {
            "status": "healthy",
            "framework_enabled": True,
            "total_assessments": summary.get("total_assessments", 0),
            "timestamp": enhanced_tracker.history.get("created_at", "unknown")
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "framework_enabled": False
        }