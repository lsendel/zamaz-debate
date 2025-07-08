#!/usr/bin/env python3
"""
Evolution History Tracker v2 for Zamaz Debate System
Improved duplicate detection, data integrity, and version management
"""

import json
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from src.core.version_manager import VersionManager, VersionBump


class EvolutionTrackerV2:
    """Enhanced evolution tracker with better duplicate detection and data integrity"""
    
    def __init__(self, evolutions_dir: str = None):
        if evolutions_dir is None:
            # Default to data/evolutions relative to project root
            evolutions_dir = Path(__file__).parent.parent.parent / "data" / "evolutions"
        
        self.evolutions_dir = Path(evolutions_dir)
        self.evolutions_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.evolutions_dir / "evolution_history.json"
        
        # Thread lock for concurrent access protection (reentrant to avoid deadlocks)
        self._lock = threading.RLock()
        
        # Version manager integration
        version_file = self.evolutions_dir / "version.json"
        self.version_manager = VersionManager(version_file)
        
        # Load history with migration support
        self.history = self._load_history()
        
        # Perform data integrity check on startup
        self._validate_and_cleanup()
    
    def _load_history(self) -> Dict:
        """Load evolution history from file with migration support"""
        if self.history_file.exists():
            with open(self.history_file, "r") as f:
                data = json.load(f)
                
                # Convert fingerprints list back to set
                if "fingerprints" in data and isinstance(data["fingerprints"], list):
                    data["fingerprints"] = set(data["fingerprints"])
                
                # Migrate old data format if needed
                if "version" not in data:
                    data["version"] = "2.0"
                    data["duplicate_prevention"] = True
                    data["last_cleanup"] = datetime.now().isoformat()
                
                return data
        
        return {
            "version": "2.0",
            "evolutions": [],
            "fingerprints": set(),
            "feature_timestamps": {},  # Track when each feature was last added
            "created_at": datetime.now().isoformat(),
            "duplicate_prevention": True,
            "last_cleanup": datetime.now().isoformat(),
        }
    
    def _save_history(self):
        """Save evolution history to file with thread safety"""
        with self._lock:
            # Convert set to list for JSON serialization
            history_copy = self.history.copy()
            history_copy["fingerprints"] = list(self.history["fingerprints"])
            
            # Ensure feature_timestamps are serializable
            if "feature_timestamps" in history_copy:
                history_copy["feature_timestamps"] = {
                    k: v.isoformat() if isinstance(v, datetime) else v
                    for k, v in history_copy["feature_timestamps"].items()
                }
            
            with open(self.history_file, "w") as f:
                json.dump(history_copy, f, indent=2)
    
    def _generate_fingerprint(self, evolution: Dict) -> str:
        """Generate improved fingerprint for better duplicate detection"""
        # Create comprehensive fingerprint including more context
        key_parts = [
            evolution.get("type", "").lower().strip(),
            evolution.get("feature", "").lower().strip(),
        ]
        
        # Include description for better uniqueness
        description = evolution.get("description", "").lower()
        if description:
            # Include first 100 chars of description
            key_parts.append(description[:100])
        
        # Include decision text if available
        decision_text = evolution.get("decision_text", "").lower()
        if decision_text:
            # Extract key phrases from decision
            key_phrases = self._extract_key_phrases(decision_text)
            key_parts.extend(key_phrases[:5])  # Limit to 5 key phrases
        
        # Include debate_id for extra uniqueness
        if evolution.get("debate_id"):
            key_parts.append(evolution["debate_id"])
        
        content = "|".join(sorted(set(filter(None, key_parts))))
        # Use longer hash for better collision resistance
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text for fingerprinting"""
        key_phrases = []
        
        # Common improvement keywords
        keywords = [
            "performance", "security", "monitoring", "observability",
            "refactor", "optimization", "caching", "logging",
            "testing", "documentation", "api", "ui", "validation",
            "error handling", "metrics", "profiling", "debugging",
            "version", "duplicate", "integrity", "recovery",
            "usability", "architecture", "consolidation"
        ]
        
        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                key_phrases.append(keyword)
        
        return key_phrases
    
    def _is_recent_duplicate(self, evolution: Dict) -> bool:
        """Check if this is a recent duplicate (same feature within 24 hours)"""
        feature = evolution.get("feature", "").lower().strip()
        if not feature:
            return False
        
        # Check feature timestamps
        if feature in self.history.get("feature_timestamps", {}):
            last_added = self.history["feature_timestamps"][feature]
            if isinstance(last_added, str):
                last_added = datetime.fromisoformat(last_added)
            
            # If same feature was added within 24 hours, it's likely a duplicate
            if datetime.now() - last_added < timedelta(hours=24):
                pass  # Feature already added recently
                return True
        
        return False
    
    def is_duplicate(self, evolution: Dict) -> bool:
        """Enhanced duplicate detection with multiple checks"""
        # Check fingerprint
        fingerprint = self._generate_fingerprint(evolution)
        if fingerprint in self.history["fingerprints"]:
            return True
        
        # Check for recent duplicates
        if self._is_recent_duplicate(evolution):
            return True
        
        # Check for exact feature+type match in recent evolutions
        recent_evolutions = self.get_recent_evolutions(20)
        evolution_key = f"{evolution.get('type', '')}|{evolution.get('feature', '')}"
        
        for recent in recent_evolutions:
            recent_key = f"{recent.get('type', '')}|{recent.get('feature', '')}"
            if evolution_key == recent_key:
                # Check if they're too similar (within 1 hour)
                if "timestamp" in recent:
                    recent_time = datetime.fromisoformat(recent["timestamp"])
                    if datetime.now() - recent_time < timedelta(hours=1):
                        return True
        
        return False
    
    def add_evolution(self, evolution: Dict) -> bool:
        """Add new evolution with enhanced validation and version management"""
        # Validate evolution data
        if not self._validate_evolution(evolution):
            return False
        
        # Check for duplicates
        if self.is_duplicate(evolution):
            return False
        
        with self._lock:
            fingerprint = self._generate_fingerprint(evolution)
            
            # Add metadata
            evolution["id"] = (
                f"evo_{len(self.history['evolutions']) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            evolution["timestamp"] = datetime.now().isoformat()
            evolution["fingerprint"] = fingerprint
            evolution["version"] = self.version_manager.get_current_version()
            
            # Add to history
            self.history["evolutions"].append(evolution)
            self.history["fingerprints"].add(fingerprint)
            
            # Update feature timestamp
            feature = evolution.get("feature", "").lower().strip()
            if feature:
                if "feature_timestamps" not in self.history:
                    self.history["feature_timestamps"] = {}
                self.history["feature_timestamps"][feature] = datetime.now().isoformat()
            
            # Bump version if appropriate
            evolution_type = evolution.get("type", "feature")
            bump_type = self.version_manager.should_bump_version(evolution_type)
            
            if bump_type:
                changes = [f"Added {evolution_type}: {evolution.get('feature', 'unnamed')}"]
                if evolution.get("description"):
                    changes.append(evolution["description"][:100])
                
                new_version = self.version_manager.bump_version(
                    bump_type, 
                    changes, 
                    evolution_id=evolution["id"]
                )
                evolution["version"] = new_version
                pass  # Version bumped
            
            # Save to file
            self._save_history()
            self._save_evolution_detail(evolution)
            
            return True
    
    def _validate_evolution(self, evolution: Dict) -> bool:
        """Validate evolution data structure"""
        required_fields = ["type", "feature"]
        
        for field in required_fields:
            if field not in evolution or not evolution[field]:
                pass  # Missing required field
                return False
        
        # Validate type
        valid_types = ["feature", "enhancement", "fix", "refactor", "optimization", "architecture"]
        if evolution["type"] not in valid_types:
            pass  # Invalid evolution type
            return False
        
        return True
    
    def _validate_and_cleanup(self):
        """Validate data integrity and clean up duplicates"""
        if not self.history.get("evolutions"):
            return
        
        # Skip print during tests to avoid potential output issues
        pass  # Data integrity check in progress
        
        # Remove exact duplicates
        seen_fingerprints = set()
        cleaned_evolutions = []
        removed_count = 0
        
        for evo in self.history["evolutions"]:
            fp = self._generate_fingerprint(evo)
            if fp not in seen_fingerprints:
                seen_fingerprints.add(fp)
                cleaned_evolutions.append(evo)
            else:
                removed_count += 1
        
        if removed_count > 0:
            pass  # Removed duplicates
            self.history["evolutions"] = cleaned_evolutions
            self.history["fingerprints"] = seen_fingerprints
            self.history["last_cleanup"] = datetime.now().isoformat()
            self._save_history()
    
    def _save_evolution_detail(self, evolution: Dict):
        """Save detailed evolution record"""
        filename = self.evolutions_dir / f"{evolution['id']}.json"
        with open(filename, "w") as f:
            json.dump(evolution, f, indent=2)
    
    def get_recent_evolutions(self, limit: int = 10) -> List[Dict]:
        """Get most recent evolutions"""
        return self.history["evolutions"][-limit:]
    
    def get_evolution_summary(self) -> Dict:
        """Get enhanced summary of evolution history"""
        evolutions = self.history["evolutions"]
        
        if not evolutions:
            return {
                "total_evolutions": 0,
                "evolution_types": {},
                "last_evolution": None,
                "current_version": self.version_manager.get_current_version(),
                "duplicate_prevention": True,
            }
        
        # Count evolution types
        type_counts = {}
        for evo in evolutions:
            evo_type = evo.get("type", "unknown")
            type_counts[evo_type] = type_counts.get(evo_type, 0) + 1
        
        return {
            "total_evolutions": len(evolutions),
            "evolution_types": type_counts,
            "last_evolution": evolutions[-1],
            "first_evolution": evolutions[0] if evolutions else None,
            "current_version": self.version_manager.get_current_version(),
            "duplicate_prevention": True,
            "unique_features": len(self.history.get("feature_timestamps", {})),
        }
    
    def migrate_from_v1(self, old_tracker):
        """Migrate data from old evolution tracker"""
        pass  # Migrating evolution data
        
        migrated_count = 0
        for evo in old_tracker.history.get("evolutions", []):
            # Try to add with new validation
            if self.add_evolution(evo):
                migrated_count += 1
        
        pass  # Migration completed
        return migrated_count