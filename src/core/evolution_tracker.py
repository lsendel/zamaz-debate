#!/usr/bin/env python3
"""
Evolution History Tracker for Zamaz Debate System
Prevents repetition of previous evolutions and tracks system changes
"""

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from difflib import SequenceMatcher
from collections import defaultdict


class EvolutionTracker:
    def __init__(self, evolutions_dir: str = None):
        if evolutions_dir is None:
            # Default to data/evolutions relative to project root
            evolutions_dir = Path(__file__).parent.parent.parent / "data" / "evolutions"
        self.evolutions_dir = Path(evolutions_dir)
        self.evolutions_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.evolutions_dir / "evolution_history.json"
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load evolution history from file"""
        if self.history_file.exists():
            with open(self.history_file, "r") as f:
                data = json.load(f)
                # Convert fingerprints list back to set
                if "fingerprints" in data and isinstance(data["fingerprints"], list):
                    data["fingerprints"] = set(data["fingerprints"])
                return data
        return {
            "evolutions": [],
            "fingerprints": set(),
            "created_at": datetime.now().isoformat(),
        }

    def _save_history(self):
        """Save evolution history to file"""
        # Convert set to list for JSON serialization
        history_copy = self.history.copy()
        history_copy["fingerprints"] = list(self.history["fingerprints"])

        with open(self.history_file, "w") as f:
            json.dump(history_copy, f, indent=2)

    def _generate_fingerprint(self, evolution: Dict) -> str:
        """Generate unique fingerprint for an evolution with enhanced uniqueness"""
        # Create fingerprint from key aspects of the evolution
        key_parts = [
            evolution.get("type", "").lower().strip(),
            evolution.get("feature", "").lower().strip(),
        ]

        # Include more content for better uniqueness (increased from 200 to 1000 chars)
        description = evolution.get("description", "").lower()
        decision_text = evolution.get("decision_text", "").lower()

        # Include first 1000 chars of description and decision text for better uniqueness
        if description:
            key_parts.append(description[:1000])
        if decision_text:
            key_parts.append(decision_text[:1000])

        # Include debate_id if available for extra uniqueness
        if evolution.get("debate_id"):
            key_parts.append(evolution["debate_id"])

        # Add time-window grouping to prevent rapid duplicates
        timestamp = evolution.get("timestamp", datetime.now().isoformat())
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            # Group by hour to prevent rapid duplicates
            time_window = dt.replace(minute=0, second=0, microsecond=0).isoformat()
            key_parts.append(time_window)
        except:
            pass

        # Enhanced key phrases for better specificity
        key_phrases = [
            "performance", "security", "monitoring", "observability", "refactor", "optimization",
            "caching", "logging", "testing", "documentation", "api", "ui", "validation",
            "error handling", "metrics", "profiling", "debugging", "adr", "architectural",
            "usability", "ux", "testing framework", "database", "kafka", "docker", "kubernetes",
            "microservices", "authentication", "authorization", "deployment", "ci/cd",
            "backup", "recovery", "scaling", "load balancing", "rate limiting"
        ]

        # Add found key phrases to fingerprint
        combined_text = (description + " " + decision_text).lower()
        found_phrases = []
        for phrase in key_phrases:
            if phrase in combined_text:
                found_phrases.append(phrase)
        
        # For generic features, extract more specific content
        if evolution.get("feature") in ["performance_optimization", "general_improvement", "enhancement"]:
            # Extract first 50 words for better specificity
            words = re.findall(r'\b\w+\b', combined_text)
            if len(words) > 5:
                specific_content = " ".join(words[:50])
                key_parts.append(specific_content)
        
        key_parts.extend(found_phrases)

        content = "|".join(sorted(set(filter(None, key_parts))))  # Sort and dedupe for consistency
        # Use longer hash (64 chars) to reduce collision probability
        return hashlib.sha256(content.encode()).hexdigest()[:64]

    def is_duplicate(self, evolution: Dict) -> bool:
        """Check if evolution is similar to previous ones using multi-layer detection"""
        # Primary check: fingerprint-based
        fingerprint = self._generate_fingerprint(evolution)
        if fingerprint in self.history["fingerprints"]:
            return True
            
        # Secondary check: time-based duplicate detection
        if self._is_time_based_duplicate(evolution):
            return True
            
        # Tertiary check: semantic similarity detection
        if self._is_semantically_similar(evolution):
            return True
            
        # Quaternary check: text similarity using Jaccard coefficient
        if self._is_text_similar(evolution):
            return True
            
        return False

    def add_evolution(self, evolution: Dict) -> bool:
        """Add new evolution if it's not a duplicate"""
        if self.is_duplicate(evolution):
            return False

        fingerprint = self._generate_fingerprint(evolution)

        # Add metadata
        evolution["id"] = f"evo_{len(self.history['evolutions']) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        evolution["timestamp"] = datetime.now().isoformat()
        evolution["fingerprint"] = fingerprint

        # Add to history
        self.history["evolutions"].append(evolution)
        self.history["fingerprints"].add(fingerprint)

        # Save to file
        self._save_history()
        self._save_evolution_detail(evolution)

        return True

    def _save_evolution_detail(self, evolution: Dict):
        """Save detailed evolution record"""
        filename = self.evolutions_dir / f"{evolution['id']}.json"
        with open(filename, "w") as f:
            json.dump(evolution, f, indent=2)

    def get_recent_evolutions(self, limit: int = 10) -> List[Dict]:
        """Get most recent evolutions"""
        return self.history["evolutions"][-limit:]

    def should_evolve(self) -> bool:
        """Check if evolution should proceed based on throttling rules"""
        recent_evolutions = self.get_recent_evolutions(10)

        # Check time since last evolution (5 minute cooldown)
        if recent_evolutions:
            last_evolution = recent_evolutions[-1]
            last_time = datetime.fromisoformat(last_evolution["timestamp"])
            time_since_last = (datetime.now() - last_time).seconds
            if time_since_last < 300:  # 5 minutes
                print(f"⏳ Evolution throttled: Only {time_since_last}s since last evolution (need 300s)")
                return False

        # Check for too many recent evolutions (max 5 in last hour)
        one_hour_ago = datetime.now().timestamp() - 3600
        recent_count = sum(
            1 for evo in recent_evolutions if datetime.fromisoformat(evo["timestamp"]).timestamp() > one_hour_ago
        )
        if recent_count >= 5:
            print(f"⏳ Evolution throttled: {recent_count} evolutions in last hour (max 5)")
            return False

        return True

    def get_evolution_summary(self) -> Dict:
        """Get summary of evolution history"""
        evolutions = self.history["evolutions"]

        if not evolutions:
            return {
                "total_evolutions": 0,
                "evolution_types": {},
                "last_evolution": None,
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
        }

    def suggest_next_evolution(self, debate_results: Dict) -> Optional[Dict]:
        """Analyze debate results and suggest next evolution"""
        # Extract key suggestions from debate
        claude_suggestion = debate_results.get("claude", "")
        gemini_suggestion = debate_results.get("gemini", "")

        # Parse suggestions to extract evolution type and feature
        evolution = {
            "type": self._extract_evolution_type(claude_suggestion, gemini_suggestion),
            "feature": self._extract_feature(claude_suggestion, gemini_suggestion),
            "description": f"Based on debate consensus: {debate_results.get('final_decision', '')}",
            "debate_id": debate_results.get("id", ""),
            "priority": self._determine_priority(claude_suggestion, gemini_suggestion),
        }

        # Check if it's a duplicate
        if not self.is_duplicate(evolution):
            return evolution

        return None

    def _extract_evolution_type(self, claude: str, gemini: str) -> str:
        """Extract evolution type from AI suggestions"""
        types = [
            "feature",
            "enhancement",
            "refactor",
            "fix",
            "optimization",
            "architecture",
        ]

        combined_text = (claude + " " + gemini).lower()

        for evo_type in types:
            if evo_type in combined_text:
                return evo_type

        return "feature"  # default

    def _extract_feature(self, claude: str, gemini: str) -> str:
        """Extract main feature from suggestions"""
        # Simple extraction - look for common patterns
        if "performance tracking" in claude.lower():
            return "performance_tracking"
        elif "automated testing" in gemini.lower():
            return "automated_testing"
        elif "plugin" in claude.lower() or "plugin" in gemini.lower():
            return "plugin_architecture"

        # Extract first significant noun phrase
        return "general_improvement"

    def _determine_priority(self, claude: str, gemini: str) -> str:
        """Determine priority based on AI emphasis"""
        high_priority_words = ["critical", "essential", "must", "immediately", "urgent"]
        medium_priority_words = ["should", "important", "beneficial", "recommended"]

        combined = (claude + " " + gemini).lower()

        if any(word in combined for word in high_priority_words):
            return "high"
        elif any(word in combined for word in medium_priority_words):
            return "medium"

        return "low"
    
    def _is_time_based_duplicate(self, evolution: Dict) -> bool:
        """Check for time-based duplicates (same feature within time window)"""
        feature = evolution.get("feature", "").lower()
        evolution_type = evolution.get("type", "").lower()
        
        # Check recent evolutions for same feature within 60 minutes
        recent_evolutions = self.get_recent_evolutions(20)
        cutoff_time = datetime.now() - timedelta(minutes=60)
        
        for recent_evo in recent_evolutions:
            try:
                recent_time = datetime.fromisoformat(recent_evo.get("timestamp", ""))
                if recent_time > cutoff_time:
                    if (recent_evo.get("feature", "").lower() == feature and 
                        recent_evo.get("type", "").lower() == evolution_type):
                        return True
            except:
                continue
        
        return False
    
    def _is_semantically_similar(self, evolution: Dict) -> bool:
        """Check for semantic similarity using keyword overlap"""
        current_desc = evolution.get("description", "").lower()
        current_feature = evolution.get("feature", "").lower()
        
        # Extract keywords from current evolution
        current_keywords = set(re.findall(r'\b\w{4,}\b', current_desc))
        
        # Check against recent evolutions
        recent_evolutions = self.get_recent_evolutions(10)
        
        for recent_evo in recent_evolutions:
            recent_desc = recent_evo.get("description", "").lower()
            recent_feature = recent_evo.get("feature", "").lower()
            
            # Same feature type is a strong indicator
            if current_feature == recent_feature:
                recent_keywords = set(re.findall(r'\b\w{4,}\b', recent_desc))
                
                # Calculate keyword overlap
                if current_keywords and recent_keywords:
                    overlap = len(current_keywords.intersection(recent_keywords))
                    total = len(current_keywords.union(recent_keywords))
                    similarity = overlap / total if total > 0 else 0
                    
                    # 70% keyword overlap indicates semantic similarity
                    if similarity >= 0.7:
                        return True
        
        return False
    
    def _is_text_similar(self, evolution: Dict) -> bool:
        """Check for text similarity using sequence matching"""
        current_text = (evolution.get("description", "") + " " + 
                       evolution.get("decision_text", "")).lower()
        
        # Skip if text is too short
        if len(current_text.strip()) < 50:
            return False
            
        recent_evolutions = self.get_recent_evolutions(5)
        
        for recent_evo in recent_evolutions:
            recent_text = (recent_evo.get("description", "") + " " + 
                          recent_evo.get("decision_text", "")).lower()
            
            if len(recent_text.strip()) < 50:
                continue
                
            # Calculate text similarity using SequenceMatcher
            similarity = SequenceMatcher(None, current_text, recent_text).ratio()
            
            # 80% text similarity indicates likely duplicate
            if similarity >= 0.8:
                return True
        
        return False
    
    def analyze_evolution_duplicates(self) -> Dict:
        """Analyze evolution history for duplicate patterns"""
        evolutions = self.history["evolutions"]
        
        # Group evolutions by feature
        feature_groups = defaultdict(list)
        for evo in evolutions:
            feature = evo.get("feature", "unknown")
            feature_groups[feature].append(evo)
        
        duplicate_analysis = {
            "total_evolutions": len(evolutions),
            "unique_features": len(feature_groups),
            "duplicate_groups": {},
            "similarity_analysis": [],
            "time_clustering": {}
        }
        
        # Analyze each feature group
        for feature, feature_evos in feature_groups.items():
            if len(feature_evos) > 1:
                duplicate_analysis["duplicate_groups"][feature] = {
                    "count": len(feature_evos),
                    "evolutions": [{
                        "id": evo.get("id", "unknown"),
                        "timestamp": evo.get("timestamp", ""),
                        "fingerprint": evo.get("fingerprint", ""),
                        "description_length": len(evo.get("description", ""))
                    } for evo in feature_evos]
                }
        
        # Analyze similarity patterns
        for i, evo1 in enumerate(evolutions):
            for j, evo2 in enumerate(evolutions[i+1:], i+1):
                if evo1.get("feature") == evo2.get("feature"):
                    text1 = evo1.get("description", "").lower()
                    text2 = evo2.get("description", "").lower()
                    
                    if text1 and text2:
                        similarity = SequenceMatcher(None, text1, text2).ratio()
                        if similarity > 0.6:  # 60% similarity threshold for analysis
                            duplicate_analysis["similarity_analysis"].append({
                                "evo1_id": evo1.get("id", "unknown"),
                                "evo2_id": evo2.get("id", "unknown"),
                                "feature": evo1.get("feature", "unknown"),
                                "similarity": round(similarity, 3),
                                "time_diff_hours": self._calculate_time_diff(evo1, evo2)
                            })
        
        # Time clustering analysis
        for feature, feature_evos in feature_groups.items():
            if len(feature_evos) > 1:
                timestamps = []
                for evo in feature_evos:
                    try:
                        ts = datetime.fromisoformat(evo.get("timestamp", ""))
                        timestamps.append(ts)
                    except:
                        continue
                
                if len(timestamps) > 1:
                    timestamps.sort()
                    time_diffs = []
                    for i in range(1, len(timestamps)):
                        diff = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600
                        time_diffs.append(diff)
                    
                    duplicate_analysis["time_clustering"][feature] = {
                        "evolution_count": len(feature_evos),
                        "time_span_hours": (timestamps[-1] - timestamps[0]).total_seconds() / 3600,
                        "avg_time_between_hours": sum(time_diffs) / len(time_diffs) if time_diffs else 0,
                        "min_time_between_hours": min(time_diffs) if time_diffs else 0,
                        "rapid_duplicates": len([diff for diff in time_diffs if diff < 1])  # Within 1 hour
                    }
        
        return duplicate_analysis
    
    def _calculate_time_diff(self, evo1: Dict, evo2: Dict) -> float:
        """Calculate time difference between two evolutions in hours"""
        try:
            ts1 = datetime.fromisoformat(evo1.get("timestamp", ""))
            ts2 = datetime.fromisoformat(evo2.get("timestamp", ""))
            diff = abs((ts2 - ts1).total_seconds() / 3600)
            return round(diff, 2)
        except:
            return 0.0
    
    def cleanup_duplicate_evolutions(self, dry_run: bool = True) -> Dict:
        """Identify and optionally remove duplicate evolutions"""
        analysis = self.analyze_evolution_duplicates()
        
        cleanup_plan = {
            "duplicates_found": 0,
            "evolutions_to_remove": [],
            "feature_groups_affected": [],
            "dry_run": dry_run
        }
        
        # Find duplicates to remove (keep the first occurrence)
        for feature, group_info in analysis["duplicate_groups"].items():
            if group_info["count"] > 1:
                evolutions = group_info["evolutions"]
                # Sort by timestamp to keep the earliest
                evolutions.sort(key=lambda x: x.get("timestamp", ""))
                
                # Mark all but the first for removal
                for evo in evolutions[1:]:
                    cleanup_plan["evolutions_to_remove"].append({
                        "id": evo["id"],
                        "feature": feature,
                        "timestamp": evo["timestamp"],
                        "reason": "duplicate_feature"
                    })
                    cleanup_plan["duplicates_found"] += 1
                
                cleanup_plan["feature_groups_affected"].append(feature)
        
        # Also look for high-similarity evolutions within short time windows
        for sim_info in analysis["similarity_analysis"]:
            if sim_info["similarity"] > 0.9 and sim_info["time_diff_hours"] < 2:
                cleanup_plan["evolutions_to_remove"].append({
                    "id": sim_info["evo2_id"],
                    "feature": sim_info["feature"],
                    "similarity": sim_info["similarity"],
                    "reason": "high_similarity"
                })
        
        if not dry_run:
            # Actually remove duplicates (implementation would go here)
            # For now, just log what would be removed
            pass
        
        return cleanup_plan
    
    def suggest_evolution_with_anti_duplicate(self, debate_results: Dict) -> Optional[Dict]:
        """Suggest evolution with enhanced anti-duplicate logic"""
        # Extract key suggestions from debate
        claude_suggestion = debate_results.get("claude", "")
        gemini_suggestion = debate_results.get("gemini", "")
        
        # Parse suggestions to extract evolution type and feature
        base_evolution = {
            "type": self._extract_evolution_type(claude_suggestion, gemini_suggestion),
            "feature": self._extract_feature(claude_suggestion, gemini_suggestion),
            "description": f"Based on debate consensus: {debate_results.get('final_decision', '')}",
            "debate_id": debate_results.get("id", ""),
            "priority": self._determine_priority(claude_suggestion, gemini_suggestion),
        }
        
        # Check if it's a duplicate
        if self.is_duplicate(base_evolution):
            # Try to create a variation that's not a duplicate
            for i in range(3):  # Try up to 3 variations
                variation = base_evolution.copy()
                variation["feature"] = f"{base_evolution['feature']}_{datetime.now().strftime('%H%M%S')}"
                variation["description"] = f"{base_evolution['description']} (variation {i+1})"
                
                if not self.is_duplicate(variation):
                    return variation
            
            # If all variations are duplicates, return None
            return None
        
        return base_evolution


if __name__ == "__main__":
    # Test the tracker
    tracker = EvolutionTracker()

    # Example evolution
    test_evolution = {
        "type": "feature",
        "feature": "performance_tracking",
        "description": "Add performance tracking with outcome measurement",
    }

    if tracker.add_evolution(test_evolution):
        print("Evolution added successfully!")
    else:
        print("Duplicate evolution detected!")

    print(f"\nEvolution Summary: {json.dumps(tracker.get_evolution_summary(), indent=2)}")
