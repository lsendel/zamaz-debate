"""
Repository interfaces and implementations for Evolution Effectiveness Context

These repositories handle persistence of evolution effectiveness aggregates.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from src.infrastructure.repositories.base import JsonRepository
from .aggregates import EvolutionEffectiveness, EvolutionMetrics, EvolutionValidation
from .value_objects import ValidationResult, EffectivenessScore


class EvolutionEffectivenessRepository(ABC):
    """Abstract repository for EvolutionEffectiveness aggregates"""
    
    @abstractmethod
    async def save(self, evolution_effectiveness: EvolutionEffectiveness) -> None:
        """Save an evolution effectiveness aggregate"""
        pass
    
    @abstractmethod
    async def find_by_id(self, effectiveness_id: UUID) -> Optional[EvolutionEffectiveness]:
        """Find evolution effectiveness by ID"""
        pass
    
    @abstractmethod
    async def find_by_evolution_id(self, evolution_id: str) -> Optional[EvolutionEffectiveness]:
        """Find evolution effectiveness by evolution ID"""
        pass
    
    @abstractmethod
    async def find_all(self) -> List[EvolutionEffectiveness]:
        """Find all evolution effectiveness records"""
        pass
    
    @abstractmethod
    async def delete(self, effectiveness_id: UUID) -> bool:
        """Delete an evolution effectiveness record"""
        pass


class MetricsRepository(ABC):
    """Abstract repository for EvolutionMetrics aggregates"""
    
    @abstractmethod
    async def save(self, metrics: EvolutionMetrics) -> None:
        """Save evolution metrics"""
        pass
    
    @abstractmethod
    async def find_by_id(self, metrics_id: UUID) -> Optional[EvolutionMetrics]:
        """Find metrics by ID"""
        pass
    
    @abstractmethod
    async def find_by_evolution_id(self, evolution_id: str) -> Optional[EvolutionMetrics]:
        """Find metrics by evolution ID"""
        pass
    
    @abstractmethod
    async def find_all(self) -> List[EvolutionMetrics]:
        """Find all metrics"""
        pass


class JsonEvolutionEffectivenessRepository(JsonRepository, EvolutionEffectivenessRepository):
    """JSON file-based repository for EvolutionEffectiveness aggregates"""
    
    def __init__(self, storage_path: str = "data/effectiveness"):
        super().__init__(storage_path, "evolution_effectiveness")
    
    async def save(self, evolution_effectiveness: EvolutionEffectiveness) -> None:
        """Save an evolution effectiveness aggregate"""
        await self.save_entity(evolution_effectiveness, evolution_effectiveness.id)
    
    async def find_by_id(self, effectiveness_id: UUID) -> Optional[EvolutionEffectiveness]:
        """Find evolution effectiveness by ID"""
        return await self.load_entity(effectiveness_id, EvolutionEffectiveness)
    
    async def find_by_evolution_id(self, evolution_id: str) -> Optional[EvolutionEffectiveness]:
        """Find evolution effectiveness by evolution ID"""
        all_records = await self.find_all()
        for record in all_records:
            if record.evolution_id == evolution_id:
                return record
        return None
    
    async def find_all(self) -> List[EvolutionEffectiveness]:
        """Find all evolution effectiveness records"""
        return await self.find_all_entities(EvolutionEffectiveness)
    
    async def delete(self, effectiveness_id: UUID) -> bool:
        """Delete an evolution effectiveness record"""
        return await self.delete_entity(effectiveness_id)
    
    def _extract_index_data(self, data: Dict) -> Dict:
        """Extract data for indexing"""
        return {
            "evolution_id": data.get("evolution_id", ""),
            "status": data.get("status", ""),
            "creation_date": data.get("creation_date", "")
        }


class JsonMetricsRepository(JsonRepository, MetricsRepository):
    """JSON file-based repository for EvolutionMetrics aggregates"""
    
    def __init__(self, storage_path: str = "data/effectiveness"):
        super().__init__(storage_path, "evolution_metrics")
    
    async def save(self, metrics: EvolutionMetrics) -> None:
        """Save evolution metrics"""
        await self.save_entity(metrics, metrics.id)
    
    async def find_by_id(self, metrics_id: UUID) -> Optional[EvolutionMetrics]:
        """Find metrics by ID"""
        return await self.load_entity(metrics_id, EvolutionMetrics)
    
    async def find_by_evolution_id(self, evolution_id: str) -> Optional[EvolutionMetrics]:
        """Find metrics by evolution ID"""
        all_metrics = await self.find_all()
        for metrics in all_metrics:
            if metrics.evolution_id == evolution_id:
                return metrics
        return None
    
    async def find_all(self) -> List[EvolutionMetrics]:
        """Find all metrics"""
        return await self.find_all_entities(EvolutionMetrics)
    
    def _extract_index_data(self, data: Dict) -> Dict:
        """Extract data for indexing"""
        return {
            "evolution_id": data.get("evolution_id", ""),
            "automated_collection_enabled": data.get("automated_collection_enabled", False),
            "last_collection": data.get("last_collection", "")
        }


class EvolutionEffectivenessReportRepository:
    """Repository for storing and retrieving evolution effectiveness reports"""
    
    def __init__(self, storage_path: str = "data/effectiveness/reports"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def save_report(self, report_id: str, report_data: Dict) -> None:
        """Save an effectiveness report"""
        report_file = self.storage_path / f"effectiveness_report_{report_id}.json"
        
        report_with_metadata = {
            "report_id": report_id,
            "generated_at": datetime.now().isoformat(),
            "report_version": "1.0",
            **report_data
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_with_metadata, f, indent=2, default=str)
    
    async def find_report(self, report_id: str) -> Optional[Dict]:
        """Find a report by ID"""
        report_file = self.storage_path / f"effectiveness_report_{report_id}.json"
        
        if not report_file.exists():
            return None
        
        with open(report_file, 'r') as f:
            return json.load(f)
    
    async def find_latest_reports(self, limit: int = 10) -> List[Dict]:
        """Find the latest effectiveness reports"""
        report_files = list(self.storage_path.glob("effectiveness_report_*.json"))
        
        # Sort by modification time (most recent first)
        report_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        reports = []
        for report_file in report_files[:limit]:
            try:
                with open(report_file, 'r') as f:
                    report_data = json.load(f)
                    reports.append(report_data)
            except Exception:
                continue
        
        return reports
    
    async def find_reports_by_evolution(self, evolution_id: str) -> List[Dict]:
        """Find all reports related to a specific evolution"""
        all_reports = await self.find_latest_reports(100)  # Get more reports to search
        
        evolution_reports = []
        for report in all_reports:
            if evolution_id in report.get("evolution_ids_analyzed", []):
                evolution_reports.append(report)
        
        return evolution_reports


class EvolutionEffectivenessQueryService:
    """Service for complex queries across evolution effectiveness data"""
    
    def __init__(self, 
                 effectiveness_repo: EvolutionEffectivenessRepository,
                 metrics_repo: MetricsRepository,
                 reports_repo: EvolutionEffectivenessReportRepository):
        self.effectiveness_repo = effectiveness_repo
        self.metrics_repo = metrics_repo
        self.reports_repo = reports_repo
    
    async def get_effectiveness_summary(self) -> Dict:
        """Get a summary of evolution effectiveness"""
        all_effectiveness = await self.effectiveness_repo.find_all()
        
        if not all_effectiveness:
            return {
                "total_assessments": 0,
                "effective_count": 0,
                "ineffective_count": 0,
                "rolled_back_count": 0,
                "average_score": 0.0
            }
        
        effective_count = sum(1 for e in all_effectiveness 
                            if e.effectiveness_scores and 
                            e.effectiveness_scores[-1].is_effective())
        
        ineffective_count = sum(1 for e in all_effectiveness 
                              if e.effectiveness_scores and 
                              not e.effectiveness_scores[-1].is_effective())
        
        rolled_back_count = sum(1 for e in all_effectiveness 
                              if e.status.value == "rolled_back")
        
        # Calculate average score
        scores = []
        for e in all_effectiveness:
            if e.effectiveness_scores:
                scores.append(e.effectiveness_scores[-1].overall_score)
        
        average_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            "total_assessments": len(all_effectiveness),
            "effective_count": effective_count,
            "ineffective_count": ineffective_count,
            "rolled_back_count": rolled_back_count,
            "average_score": average_score,
            "effectiveness_rate": (effective_count / len(all_effectiveness)) * 100 if all_effectiveness else 0
        }
    
    async def get_evolution_timeline(self, evolution_id: str) -> Dict:
        """Get the complete timeline for an evolution's effectiveness assessment"""
        effectiveness = await self.effectiveness_repo.find_by_evolution_id(evolution_id)
        metrics = await self.metrics_repo.find_by_evolution_id(evolution_id)
        reports = await self.reports_repo.find_reports_by_evolution(evolution_id)
        
        timeline = {
            "evolution_id": evolution_id,
            "effectiveness_assessment": effectiveness,
            "metrics_collection": metrics,
            "reports": reports,
            "status": effectiveness.status.value if effectiveness else "not_assessed"
        }
        
        return timeline
    
    async def find_problematic_evolutions(self) -> List[Dict]:
        """Find evolutions that have effectiveness problems"""
        all_effectiveness = await self.effectiveness_repo.find_all()
        
        problematic = []
        for effectiveness in all_effectiveness:
            if not effectiveness.effectiveness_scores:
                continue
            
            latest_score = effectiveness.effectiveness_scores[-1]
            
            if (latest_score.requires_attention() or 
                effectiveness.status.value in ["failed", "rolled_back"]):
                
                problematic.append({
                    "evolution_id": effectiveness.evolution_id,
                    "effectiveness_score": latest_score.overall_score,
                    "effectiveness_level": latest_score.effectiveness_level.value,
                    "status": effectiveness.status.value,
                    "issues": effectiveness.validation_results[-1].issues_found if effectiveness.validation_results else [],
                    "last_assessed": effectiveness.validation_results[-1].validation_timestamp if effectiveness.validation_results else None
                })
        
        return problematic