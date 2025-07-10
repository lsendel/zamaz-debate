"""
Evolution Context Repository Implementations

JSON-based implementations of Evolution context repositories.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.contexts.evolution import (
    Evolution,
    EvolutionHistory,
    EvolutionHistoryRepository,
    EvolutionMetricsRepository,
    EvolutionRepository,
    EvolutionStatus,
    Improvement,
    ImprovementArea,
    ImprovementRepository,
    ImprovementSuggestion,
)

from .base import JsonRepository


class JsonEvolutionRepository(JsonRepository, EvolutionRepository):
    """JSON-based implementation of EvolutionRepository"""
    
    def __init__(self, storage_path: str = "data/evolutions"):
        super().__init__(storage_path, "evolution")
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract evolution data for indexing"""
        return {
            "status": data.get("status"),
            "trigger": data.get("trigger"),
            "created_at": data.get("created_at"),
            "completed_at": data.get("completed_at"),
        }
    
    async def save(self, evolution: Evolution) -> None:
        """Save an evolution"""
        await self.save_entity(evolution, evolution.id)
    
    async def find_by_id(self, evolution_id: UUID) -> Optional[Evolution]:
        """Find an evolution by ID"""
        return await self.load_entity(evolution_id, Evolution)
    
    async def find_by_status(self, status: str) -> List[Evolution]:
        """Find evolutions by status"""
        return await self.find_by_criteria(Evolution, {"status": status})
    
    async def find_active(self) -> List[Evolution]:
        """Find all active evolutions"""
        active_statuses = [
            EvolutionStatus.TRIGGERED.value,
            EvolutionStatus.ANALYZING.value,
            EvolutionStatus.PLANNING.value,
            EvolutionStatus.IMPLEMENTING.value,
            EvolutionStatus.VALIDATING.value,
        ]
        
        all_evolutions = await self.find_all(Evolution)
        return [e for e in all_evolutions if e.status.value in active_statuses]
    
    async def find_by_trigger(self, trigger_type: str) -> List[Evolution]:
        """Find evolutions by trigger type"""
        return await self.find_by_criteria(Evolution, {"trigger": trigger_type})
    
    async def find_completed_between(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Evolution]:
        """Find evolutions completed between dates"""
        all_evolutions = await self.find_all(Evolution)
        
        completed = []
        for evolution in all_evolutions:
            if (evolution.status == EvolutionStatus.COMPLETED and
                evolution.completed_at and
                start_date <= evolution.completed_at <= end_date):
                completed.append(evolution)
        
        return completed
    
    async def find_with_improvement(self, improvement_area: ImprovementArea) -> List[Evolution]:
        """Find evolutions with improvements in a specific area"""
        all_evolutions = await self.find_all(Evolution)
        
        matching = []
        for evolution in all_evolutions:
            for improvement in evolution.improvements:
                if improvement.suggestion.area == improvement_area:
                    matching.append(evolution)
                    break
        
        return matching
    
    async def update(self, evolution: Evolution) -> bool:
        """Update an evolution"""
        if await self.exists(evolution.id):
            await self.save(evolution)
            return True
        return False
    
    async def delete(self, evolution_id: UUID) -> bool:
        """Delete an evolution"""
        return await self.delete_entity(evolution_id)
    
    async def count_by_status(self) -> Dict[str, int]:
        """Count evolutions by status"""
        all_evolutions = await self.find_all(Evolution)
        
        counts = {}
        for evolution in all_evolutions:
            status = evolution.status.value
            counts[status] = counts.get(status, 0) + 1
        
        return counts
    
    async def get_success_rate(self, days: int = 30) -> float:
        """Calculate evolution success rate"""
        end_date = datetime.now()
        start_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        start_date = datetime.fromtimestamp(start_date)
        
        recent_evolutions = await self.find_completed_between(start_date, end_date)
        
        if not recent_evolutions:
            return 0.0
        
        successful = sum(1 for e in recent_evolutions if e.is_successful)
        return (successful / len(recent_evolutions)) * 100


class JsonImprovementRepository(JsonRepository, ImprovementRepository):
    """JSON-based implementation of ImprovementRepository"""
    
    def __init__(self, storage_path: str = "data/improvements"):
        super().__init__(storage_path, "improvement")
        self.evolution_repo = JsonEvolutionRepository()
    
    async def find_by_id(self, improvement_id: UUID) -> Optional[Improvement]:
        """Find an improvement by ID"""
        # Since improvements are part of evolutions, we need to search through evolutions
        all_evolutions = await self.evolution_repo.find_all(Evolution)
        
        for evolution in all_evolutions:
            for improvement in evolution.improvements:
                if improvement.id == improvement_id:
                    return improvement
        
        return None
    
    async def find_by_area(self, area: ImprovementArea) -> List[Improvement]:
        """Find improvements by area"""
        all_evolutions = await self.evolution_repo.find_all(Evolution)
        
        improvements = []
        for evolution in all_evolutions:
            for improvement in evolution.improvements:
                if improvement.suggestion.area == area:
                    improvements.append(improvement)
        
        return improvements
    
    async def find_by_status(self, status: str) -> List[Improvement]:
        """Find improvements by status"""
        all_evolutions = await self.evolution_repo.find_all(Evolution)
        
        improvements = []
        for evolution in all_evolutions:
            for improvement in evolution.improvements:
                if improvement.status.value == status:
                    improvements.append(improvement)
        
        return improvements
    
    async def find_approved_not_implemented(self) -> List[Improvement]:
        """Find approved improvements not yet implemented"""
        all_evolutions = await self.evolution_repo.find_all(Evolution)
        
        improvements = []
        for evolution in all_evolutions:
            for improvement in evolution.improvements:
                if improvement.is_approved and not improvement.is_implemented:
                    improvements.append(improvement)
        
        return improvements
    
    async def find_similar(
        self,
        suggestion: ImprovementSuggestion,
        threshold: float = 0.8,
    ) -> List[Improvement]:
        """Find improvements similar to a suggestion"""
        all_evolutions = await self.evolution_repo.find_all(Evolution)
        
        similar = []
        for evolution in all_evolutions:
            for improvement in evolution.improvements:
                # Simple similarity check based on area and title
                if (improvement.suggestion.area == suggestion.area and
                    self._calculate_similarity(
                        improvement.suggestion.title,
                        suggestion.title
                    ) >= threshold):
                    similar.append(improvement)
        
        return similar
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity (0-1)"""
        # Very basic implementation - in reality would use proper NLP
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    async def get_implementation_rate(self, area: Optional[ImprovementArea] = None) -> float:
        """Calculate implementation rate"""
        all_evolutions = await self.evolution_repo.find_all(Evolution)
        
        approved_count = 0
        implemented_count = 0
        
        for evolution in all_evolutions:
            for improvement in evolution.improvements:
                if area and improvement.suggestion.area != area:
                    continue
                
                if improvement.is_approved:
                    approved_count += 1
                    if improvement.is_implemented:
                        implemented_count += 1
        
        if approved_count == 0:
            return 0.0
        
        return (implemented_count / approved_count) * 100
    
    async def get_impact_statistics(self) -> Dict[str, Any]:
        """Get improvement impact statistics"""
        all_evolutions = await self.evolution_repo.find_all(Evolution)
        
        impact_counts = {"low": 0, "medium": 0, "high": 0}
        area_counts = {}
        total_improvements = 0
        
        for evolution in all_evolutions:
            for improvement in evolution.improvements:
                total_improvements += 1
                
                # Count by impact
                impact = improvement.suggestion.estimated_impact
                impact_counts[impact] = impact_counts.get(impact, 0) + 1
                
                # Count by area
                area = improvement.suggestion.area.value
                area_counts[area] = area_counts.get(area, 0) + 1
        
        return {
            "total_improvements": total_improvements,
            "impact_distribution": impact_counts,
            "area_distribution": area_counts,
            "average_per_evolution": (
                total_improvements / len(all_evolutions)
                if all_evolutions else 0
            ),
        }


class JsonEvolutionHistoryRepository(JsonRepository, EvolutionHistoryRepository):
    """JSON-based implementation of EvolutionHistoryRepository"""
    
    def __init__(self, storage_path: str = "data/evolution_history"):
        super().__init__(storage_path, "history")
    
    async def save(self, history: EvolutionHistory) -> None:
        """Save the evolution history"""
        await self.save_entity(history, history.id)
    
    async def get(self) -> Optional[EvolutionHistory]:
        """Get the evolution history"""
        # There should only be one history record
        histories = await self.find_all(EvolutionHistory)
        return histories[0] if histories else None
    
    async def add_evolution(self, evolution: Evolution) -> None:
        """Add an evolution to the history"""
        history = await self.get()
        
        if not history:
            history = EvolutionHistory()
        
        history.add_evolution(evolution)
        await self.save(history)
    
    async def find_previous_improvements(
        self,
        area: ImprovementArea,
        limit: int = 10,
    ) -> List[Improvement]:
        """Find previous improvements in an area"""
        history = await self.get()
        
        if not history:
            return []
        
        improvements = history.get_improvements_by_area(area)
        return improvements[:limit]
    
    async def check_duplicate_improvement(
        self,
        suggestion: ImprovementSuggestion,
    ) -> bool:
        """Check if a similar improvement exists"""
        history = await self.get()
        
        if not history:
            return False
        
        return history.has_similar_improvement(suggestion)
    
    async def get_evolution_timeline(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get evolution timeline"""
        history = await self.get()
        
        if not history:
            return []
        
        timeline = []
        for evolution in history.evolutions:
            if start_date and evolution.created_at < start_date:
                continue
            if end_date and evolution.created_at > end_date:
                continue
            
            timeline.append({
                "date": evolution.created_at.isoformat(),
                "event": "evolution_completed",
                "evolution_id": str(evolution.id),
                "trigger": evolution.trigger.value,
                "improvements": len(evolution.improvements),
                "success": evolution.is_successful,
            })
        
        return sorted(timeline, key=lambda x: x["date"])
    
    async def get_improvement_trends(self, days: int = 90) -> Dict[str, Any]:
        """Analyze improvement trends"""
        history = await self.get()
        
        if not history:
            return {
                "popular_areas": [],
                "success_rate": 0.0,
                "average_improvements_per_evolution": 0.0,
            }
        
        recent_evolutions = history.get_recent_evolutions(days)
        
        # Count improvements by area
        area_counts = {}
        total_improvements = 0
        successful_improvements = 0
        
        for evolution in recent_evolutions:
            for improvement in evolution.improvements:
                area = improvement.suggestion.area.value
                area_counts[area] = area_counts.get(area, 0) + 1
                total_improvements += 1
                
                if improvement.is_validated:
                    successful_improvements += 1
        
        # Sort areas by popularity
        popular_areas = sorted(
            area_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "popular_areas": popular_areas[:5],
            "success_rate": (
                (successful_improvements / total_improvements) * 100
                if total_improvements > 0 else 0.0
            ),
            "average_improvements_per_evolution": (
                total_improvements / len(recent_evolutions)
                if recent_evolutions else 0.0
            ),
        }
    
    async def update(self, history: EvolutionHistory) -> bool:
        """Update the evolution history"""
        if await self.exists(history.id):
            await self.save(history)
            return True
        return False


class JsonEvolutionMetricsRepository(JsonRepository, EvolutionMetricsRepository):
    """JSON-based implementation of EvolutionMetricsRepository"""
    
    def __init__(self, storage_path: str = "data/evolution_metrics"):
        super().__init__(storage_path, "metrics")
    
    async def save_metrics_snapshot(
        self,
        evolution_id: UUID,
        metrics: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Save a metrics snapshot"""
        snapshot = {
            "id": str(UUID()),
            "evolution_id": str(evolution_id),
            "metrics": metrics,
            "timestamp": timestamp.isoformat(),
        }
        
        # Save with a unique ID
        await self.save_entity(snapshot, UUID(snapshot["id"]))
    
    async def get_metrics_history(
        self,
        metric_name: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get historical values for a metric"""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        all_snapshots = await self.find_all(dict)
        
        history = []
        for snapshot in all_snapshots:
            timestamp = datetime.fromisoformat(snapshot["timestamp"])
            if timestamp.timestamp() >= cutoff_date:
                if metric_name in snapshot["metrics"]:
                    history.append({
                        "timestamp": snapshot["timestamp"],
                        "value": snapshot["metrics"][metric_name],
                        "evolution_id": snapshot.get("evolution_id"),
                    })
        
        return sorted(history, key=lambda x: x["timestamp"])
    
    async def get_evolution_impact(self, evolution_id: UUID) -> Dict[str, Any]:
        """Calculate evolution impact"""
        all_snapshots = await self.find_all(dict)
        
        # Find before and after snapshots for this evolution
        evolution_snapshots = [
            s for s in all_snapshots
            if s.get("evolution_id") == str(evolution_id)
        ]
        
        if len(evolution_snapshots) < 2:
            return {"error": "Insufficient metrics data"}
        
        # Sort by timestamp
        evolution_snapshots.sort(key=lambda x: x["timestamp"])
        
        before = evolution_snapshots[0]["metrics"]
        after = evolution_snapshots[-1]["metrics"]
        
        impact = {}
        for metric in before:
            if metric in after:
                change = ((after[metric] - before[metric]) / before[metric]) * 100
                impact[f"{metric}_change"] = change
        
        return {
            "before": before,
            "after": after,
            "impact": impact,
        }
    
    async def get_cumulative_improvements(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, float]:
        """Get cumulative improvements"""
        all_snapshots = await self.find_all(dict)
        
        # Filter by date range
        filtered = []
        for snapshot in all_snapshots:
            timestamp = datetime.fromisoformat(snapshot["timestamp"])
            if start_date <= timestamp <= end_date:
                filtered.append(snapshot)
        
        if len(filtered) < 2:
            return {}
        
        # Sort by timestamp
        filtered.sort(key=lambda x: x["timestamp"])
        
        first = filtered[0]["metrics"]
        last = filtered[-1]["metrics"]
        
        improvements = {}
        for metric in first:
            if metric in last and first[metric] > 0:
                improvement = ((last[metric] - first[metric]) / first[metric]) * 100
                improvements[metric] = improvement
        
        return improvements
    
    async def identify_regression_areas(
        self,
        threshold: float = -5.0,
    ) -> List[Dict[str, Any]]:
        """Identify regression areas"""
        # Get recent metrics history
        recent_history = await self.get_metrics_history("performance_score", days=7)
        
        if len(recent_history) < 2:
            return []
        
        regressions = []
        
        # Compare recent values to identify downward trends
        for i in range(1, len(recent_history)):
            prev = recent_history[i-1]["value"]
            curr = recent_history[i]["value"]
            
            if prev > 0:
                change = ((curr - prev) / prev) * 100
                if change <= threshold:
                    regressions.append({
                        "metric": "performance_score",
                        "decrease": abs(change),
                        "from_value": prev,
                        "to_value": curr,
                        "timestamp": recent_history[i]["timestamp"],
                    })
        
        return regressions
    
    async def get_evolution_velocity(self, days: int = 30) -> Dict[str, Any]:
        """Calculate evolution velocity"""
        evolution_repo = JsonEvolutionRepository()
        
        end_date = datetime.now()
        start_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        start_date = datetime.fromtimestamp(start_date)
        
        recent_evolutions = await evolution_repo.find_completed_between(
            start_date,
            end_date
        )
        
        if not recent_evolutions:
            return {
                "evolutions_per_week": 0,
                "average_cycle_time_hours": 0,
                "average_improvements_per_evolution": 0,
            }
        
        # Calculate metrics
        total_cycle_time = 0
        total_improvements = 0
        
        for evolution in recent_evolutions:
            if evolution.duration_hours:
                total_cycle_time += evolution.duration_hours
            total_improvements += len(evolution.improvements)
        
        weeks = days / 7
        
        return {
            "evolutions_per_week": len(recent_evolutions) / weeks,
            "average_cycle_time_hours": (
                total_cycle_time / len(recent_evolutions)
                if recent_evolutions else 0
            ),
            "average_improvements_per_evolution": (
                total_improvements / len(recent_evolutions)
                if recent_evolutions else 0
            ),
        }
    
    async def predict_next_evolution_areas(
        self,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Predict next evolution areas"""
        # Simple prediction based on regression areas and time since last improvement
        regressions = await self.identify_regression_areas()
        
        predictions = []
        
        # Add regression areas as high priority
        for regression in regressions[:limit]:
            predictions.append({
                "area": "performance",
                "reason": f"Regression detected: {regression['metric']}",
                "confidence": 0.9,
                "urgency": "high",
            })
        
        # Add other predictions based on patterns
        # (In a real system, this would use ML models)
        if len(predictions) < limit:
            predictions.append({
                "area": "security",
                "reason": "Regular security review cycle",
                "confidence": 0.7,
                "urgency": "medium",
            })
        
        return predictions[:limit]