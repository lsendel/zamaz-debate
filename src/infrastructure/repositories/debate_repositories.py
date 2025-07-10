"""
Debate Context Repository Implementations

JSON-based implementations of Debate context repositories.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.contexts.debate import (
    Debate,
    DebateRepository,
    DebateResult,
    DebateResultRepository,
    DebateStatus,
)

from .base import JsonRepository


class JsonDebateRepository(JsonRepository, DebateRepository):
    """JSON-based implementation of DebateRepository"""
    
    def __init__(self, storage_path: str = "data/debates"):
        super().__init__(storage_path, "debate")
        # Also ensure the legacy debates directory exists for backward compatibility
        Path("debates").mkdir(exist_ok=True)
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract debate data for indexing"""
        return {
            "topic": data.get("topic"),
            "status": data.get("status"),
            "decision_id": data.get("decision_id"),
            "created_at": data.get("created_at"),
            "completed_at": data.get("completed_at"),
        }
    
    async def save(self, debate: Debate) -> None:
        """Save a debate"""
        await self.save_entity(debate, debate.id)
        
        # Also save to legacy format for backward compatibility
        await self._save_legacy_format(debate)
    
    async def _save_legacy_format(self, debate: Debate) -> None:
        """Save debate in legacy format for backward compatibility"""
        legacy_path = Path("debates") / f"debate_{debate.id}.json"
        
        legacy_data = {
            "id": str(debate.id),
            "topic": debate.topic,
            "context": debate.context,
            "status": debate.status.value,
            "created_at": debate.created_at.isoformat() if debate.created_at else None,
            "completed_at": debate.completed_at.isoformat() if debate.completed_at else None,
            "participants": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "model": p.model,
                    "role": p.role.value,
                }
                for p in debate.participants
            ],
            "rounds": [
                {
                    "round_number": r.round_number,
                    "arguments": [
                        {
                            "participant_id": str(a.participant_id),
                            "content": a.content,
                            "supporting_evidence": a.supporting_evidence,
                            "timestamp": a.timestamp.isoformat(),
                        }
                        for a in r.arguments
                    ],
                }
                for r in debate.rounds
            ],
            "result": {
                "winner": debate.result.winner if debate.result else None,
                "consensus": debate.result.consensus if debate.result else None,
                "summary": debate.result.summary if debate.result else None,
                "decision_rationale": debate.result.decision_rationale if debate.result else None,
            } if debate.result else None,
        }
        
        with open(legacy_path, "w") as f:
            json.dump(legacy_data, f, indent=2)
    
    async def find_by_id(self, debate_id: UUID) -> Optional[Debate]:
        """Find a debate by ID"""
        # Try new format first
        debate = await self.load_entity(debate_id, Debate)
        
        if debate:
            return debate
        
        # Fall back to legacy format
        legacy_path = Path("debates") / f"debate_{debate_id}.json"
        if legacy_path.exists():
            with open(legacy_path, "r") as f:
                data = json.load(f)
            
            # Convert legacy format to new format
            # This is simplified - in reality would need proper conversion
            return self._deserialize(data, Debate)
        
        return None
    
    async def find_by_status(self, status: DebateStatus) -> List[Debate]:
        """Find debates by status"""
        all_debates = await self.find_all(Debate)
        return [d for d in all_debates if d.status == status]
    
    async def find_by_decision_id(self, decision_id: UUID) -> Optional[Debate]:
        """Find a debate by decision ID"""
        all_debates = await self.find_all(Debate)
        
        for debate in all_debates:
            if debate.decision_id == decision_id:
                return debate
        
        return None
    
    async def find_active(self) -> List[Debate]:
        """Find all active debates"""
        active_statuses = [
            DebateStatus.CREATED,
            DebateStatus.IN_PROGRESS,
        ]
        
        all_debates = await self.find_all(Debate)
        return [d for d in all_debates if d.status in active_statuses]
    
    async def find_completed_between(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Debate]:
        """Find debates completed within a time range"""
        all_debates = await self.find_all(Debate)
        
        completed = []
        for debate in all_debates:
            if (debate.status == DebateStatus.COMPLETED and
                debate.completed_at and
                start_date <= debate.completed_at <= end_date):
                completed.append(debate)
        
        return completed
    
    async def find_by_participant(self, participant_name: str) -> List[Debate]:
        """Find debates involving a specific participant"""
        all_debates = await self.find_all(Debate)
        
        matching = []
        for debate in all_debates:
            for participant in debate.participants:
                if participant.name == participant_name:
                    matching.append(debate)
                    break
        
        return matching
    
    async def update(self, debate: Debate) -> bool:
        """Update a debate"""
        if await self.exists(debate.id):
            await self.save(debate)
            return True
        return False
    
    async def delete(self, debate_id: UUID) -> bool:
        """Delete a debate"""
        # Delete from new format
        deleted = await self.delete_entity(debate_id)
        
        # Also delete legacy format
        legacy_path = Path("debates") / f"debate_{debate_id}.json"
        if legacy_path.exists():
            legacy_path.unlink()
        
        return deleted
    
    async def count_by_status(self) -> Dict[str, int]:
        """Count debates by status"""
        all_debates = await self.find_all(Debate)
        
        counts = {}
        for debate in all_debates:
            status = debate.status.value
            counts[status] = counts.get(status, 0) + 1
        
        return counts
    
    async def get_debate_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get debate statistics"""
        end_date = datetime.now()
        start_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        start_date = datetime.fromtimestamp(start_date)
        
        recent_debates = await self.find_completed_between(start_date, end_date)
        
        if not recent_debates:
            return {
                "total_debates": 0,
                "average_rounds": 0,
                "consensus_rate": 0,
                "average_duration_minutes": 0,
            }
        
        total_rounds = sum(len(d.rounds) for d in recent_debates)
        consensus_count = sum(1 for d in recent_debates if d.result and d.result.consensus)
        
        total_duration = 0
        duration_count = 0
        
        for debate in recent_debates:
            if debate.created_at and debate.completed_at:
                duration = (debate.completed_at - debate.created_at).total_seconds() / 60
                total_duration += duration
                duration_count += 1
        
        return {
            "total_debates": len(recent_debates),
            "average_rounds": total_rounds / len(recent_debates),
            "consensus_rate": (consensus_count / len(recent_debates)) * 100,
            "average_duration_minutes": (
                total_duration / duration_count
                if duration_count > 0 else 0
            ),
        }


class JsonDebateResultRepository(JsonRepository, DebateResultRepository):
    """JSON-based implementation of DebateResultRepository"""
    
    def __init__(self, storage_path: str = "data/debate_results"):
        super().__init__(storage_path, "debate_result")
        self.debate_repo = JsonDebateRepository()
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract debate result data for indexing"""
        return {
            "debate_id": data.get("debate_id"),
            "winner": data.get("winner"),
            "consensus": data.get("consensus"),
            "created_at": data.get("created_at"),
        }
    
    async def save(self, result: DebateResult) -> None:
        """Save a debate result"""
        await self.save_entity(result, result.id)
    
    async def find_by_id(self, result_id: UUID) -> Optional[DebateResult]:
        """Find a debate result by ID"""
        return await self.load_entity(result_id, DebateResult)
    
    async def find_by_debate_id(self, debate_id: UUID) -> Optional[DebateResult]:
        """Find a debate result by debate ID"""
        # First check if the debate has a result
        debate = await self.debate_repo.find_by_id(debate_id)
        if debate and debate.result:
            return debate.result
        
        # Otherwise, search through saved results
        all_results = await self.find_all(DebateResult)
        
        for result in all_results:
            if result.debate_id == debate_id:
                return result
        
        return None
    
    async def find_by_consensus(self, has_consensus: bool) -> List[DebateResult]:
        """Find debate results by consensus status"""
        all_results = await self.find_all(DebateResult)
        return [r for r in all_results if r.consensus == has_consensus]
    
    async def find_by_winner(self, participant_name: str) -> List[DebateResult]:
        """Find debate results won by a participant"""
        all_results = await self.find_all(DebateResult)
        return [r for r in all_results if r.winner == participant_name]
    
    async def update(self, result: DebateResult) -> bool:
        """Update a debate result"""
        if await self.exists(result.id):
            await self.save(result)
            return True
        return False
    
    async def delete(self, result_id: UUID) -> bool:
        """Delete a debate result"""
        return await self.delete_entity(result_id)
    
    async def get_win_statistics(self) -> Dict[str, Any]:
        """Get win statistics by participant"""
        all_results = await self.find_all(DebateResult)
        
        win_counts = {}
        participation_counts = {}
        
        for result in all_results:
            # Count wins
            if result.winner:
                win_counts[result.winner] = win_counts.get(result.winner, 0) + 1
            
            # Count participations (would need to check debate for full accuracy)
            if result.debate_id:
                debate = await self.debate_repo.find_by_id(result.debate_id)
                if debate:
                    for participant in debate.participants:
                        name = participant.name
                        participation_counts[name] = participation_counts.get(name, 0) + 1
        
        # Calculate win rates
        win_rates = {}
        for participant, participations in participation_counts.items():
            wins = win_counts.get(participant, 0)
            win_rates[participant] = (wins / participations) * 100 if participations > 0 else 0
        
        return {
            "win_counts": win_counts,
            "participation_counts": participation_counts,
            "win_rates": win_rates,
            "total_debates": len(all_results),
        }
    
    async def get_consensus_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get consensus trends over time"""
        end_date = datetime.now()
        start_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        start_date = datetime.fromtimestamp(start_date)
        
        # Get debates completed in the time range
        recent_debates = await self.debate_repo.find_completed_between(start_date, end_date)
        
        # Group by day
        daily_stats = {}
        
        for debate in recent_debates:
            if debate.completed_at and debate.result:
                date_key = debate.completed_at.date().isoformat()
                
                if date_key not in daily_stats:
                    daily_stats[date_key] = {
                        "total": 0,
                        "consensus": 0,
                    }
                
                daily_stats[date_key]["total"] += 1
                if debate.result.consensus:
                    daily_stats[date_key]["consensus"] += 1
        
        # Convert to list format
        trends = []
        for date, stats in sorted(daily_stats.items()):
            consensus_rate = (stats["consensus"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            
            trends.append({
                "date": date,
                "total_debates": stats["total"],
                "consensus_count": stats["consensus"],
                "consensus_rate": consensus_rate,
            })
        
        return trends