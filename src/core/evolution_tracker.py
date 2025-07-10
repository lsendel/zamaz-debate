#!/usr/bin/env python3
"""
Evolution History Tracker for Zamaz Debate System
Prevents repetition of previous evolutions and tracks system changes
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


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
        """Generate unique fingerprint for an evolution with enhanced deduplication"""
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

        # Add time window to prevent rapid duplicates (group by 1-hour windows)
        current_time = datetime.now()
        time_window = f"{current_time.strftime('%Y%m%d_%H')}"  # Hour-based grouping
        key_parts.append(time_window)

        # Extract key phrases from description to make fingerprint more specific
        key_phrases = [
            "performance",
            "security",
            "monitoring",
            "observability",
            "refactor",
            "optimization",
            "caching",
            "logging",
            "testing",
            "documentation",
            "api",
            "ui",
            "validation",
            "error handling",
            "metrics",
            "profiling",
            "debugging",
            "adr",
            "architectural",
            "usability",
            "ux",
            "testing framework",
            "webhook",
            "automation",
            "deployment",
            "ci/cd",
            "database",
            "storage",
            "configuration",
            "environment",
        ]

        # Add found key phrases to fingerprint
        combined_text = (description + " " + decision_text).lower()
        found_phrases = []
        for phrase in key_phrases:
            if phrase in combined_text:
                found_phrases.append(phrase)
        
        # Add phrases in sorted order for consistency
        key_parts.extend(sorted(found_phrases))

        # Create more specific fingerprint for generic features
        feature = evolution.get("feature", "")
        if feature in ["performance_optimization", "general_improvement", "enhancement"]:
            # For generic features, include more specific content
            specific_content = self._extract_specific_content(combined_text)
            key_parts.extend(specific_content)

        content = "|".join(sorted(set(filter(None, key_parts))))  # Sort and dedupe for consistency
        # Use longer hash (64 chars) to reduce collision probability
        return hashlib.sha256(content.encode()).hexdigest()[:64]

    def _extract_specific_content(self, text: str) -> List[str]:
        """Extract specific content from generic feature descriptions"""
        specific_terms = []
        
        # Extract specific technical terms and concepts
        technical_patterns = [
            r'implement\s+(\w+)',
            r'add\s+(\w+)',
            r'create\s+(\w+)',
            r'build\s+(\w+)',
            r'develop\s+(\w+)',
            r'integrate\s+(\w+)',
            r'optimize\s+(\w+)',
            r'improve\s+(\w+)',
            r'enhance\s+(\w+)',
            r'refactor\s+(\w+)',
        ]
        
        for pattern in technical_patterns:
            matches = re.findall(pattern, text)
            specific_terms.extend(matches)
        
        # Extract technology/framework names
        tech_keywords = [
            'kafka', 'redis', 'postgresql', 'mongodb', 'elasticsearch',
            'docker', 'kubernetes', 'prometheus', 'grafana', 'nginx',
            'fastapi', 'flask', 'django', 'react', 'vue', 'angular',
            'typescript', 'javascript', 'python', 'java', 'golang',
            'microservices', 'serverless', 'lambda', 'aws', 'gcp', 'azure',
            'terraform', 'ansible', 'jenkins', 'github actions',
            'websocket', 'grpc', 'graphql', 'rest api', 'oauth',
            'jwt', 'ssl', 'tls', 'https', 'cors', 'csrf'
        ]
        
        for keyword in tech_keywords:
            if keyword in text:
                specific_terms.append(keyword)
        
        # Return unique terms, limited to avoid oversized fingerprints
        return list(set(specific_terms))[:10]

    def is_duplicate(self, evolution: Dict) -> bool:
        """Check if evolution is similar to previous ones with enhanced detection"""
        # Primary fingerprint check
        fingerprint = self._generate_fingerprint(evolution)
        if fingerprint in self.history["fingerprints"]:
            return True
        
        # Additional time-based duplicate check
        if self.is_recent_duplicate(evolution):
            return True
            
        # Semantic similarity check for generic features
        if self.is_semantic_duplicate(evolution):
            return True
            
        return False
    
    def is_recent_duplicate(self, evolution: Dict, window_minutes: int = 60) -> bool:
        """Check for duplicates within a time window"""
        current_time = datetime.now()
        feature = evolution.get("feature", "")
        evolution_type = evolution.get("type", "")
        
        # Check recent evolutions for similar feature/type combinations
        recent_evolutions = self.get_recent_evolutions(50)  # Check more recent evolutions
        
        for existing in recent_evolutions:
            try:
                existing_time = datetime.fromisoformat(existing.get("timestamp", ""))
                time_diff = (current_time - existing_time).total_seconds() / 60
                
                if (time_diff <= window_minutes and 
                    existing.get("feature") == feature and
                    existing.get("type") == evolution_type):
                    return True
            except (ValueError, TypeError):
                # Skip evolutions with invalid timestamps
                continue
                
        return False
    
    def is_semantic_duplicate(self, evolution: Dict) -> bool:
        """Check for semantic similarity using text comparison"""
        feature = evolution.get("feature", "")
        description = evolution.get("description", "").lower()
        decision_text = evolution.get("decision_text", "").lower()
        
        # Only apply semantic checking to generic features
        if feature not in ["performance_optimization", "general_improvement", "enhancement"]:
            return False
            
        # Get recent evolutions for comparison
        recent_evolutions = self.get_recent_evolutions(30)
        
        for existing in recent_evolutions:
            if existing.get("feature") == feature:
                existing_desc = existing.get("description", "").lower()
                existing_decision = existing.get("decision_text", "").lower()
                
                # Simple similarity check using common words
                similarity = self._calculate_text_similarity(
                    description + " " + decision_text,
                    existing_desc + " " + existing_decision
                )
                
                if similarity > 0.7:  # 70% similarity threshold
                    return True
                    
        return False
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using word overlap"""
        if not text1 or not text2:
            return 0.0
            
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Filter out common words
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
            'with', 'by', 'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'can', 'may', 'might', 'must', 'shall'
        }
        
        words1 = words1 - common_words
        words2 = words2 - common_words
        
        if not words1 or not words2:
            return 0.0
            
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0

    def analyze_duplicates(self) -> Dict:
        """Analyze existing evolution history for duplicates"""
        duplicates_found = []
        feature_groups = {}
        
        # Group evolutions by feature
        for evolution in self.history["evolutions"]:
            feature = evolution.get("feature", "unknown")
            if feature not in feature_groups:
                feature_groups[feature] = []
            feature_groups[feature].append(evolution)
        
        # Find potential duplicates within each feature group
        for feature, evolutions in feature_groups.items():
            if len(evolutions) > 1:
                # Check for duplicates within this feature group
                for i, evo1 in enumerate(evolutions):
                    for j, evo2 in enumerate(evolutions[i+1:], i+1):
                        # Check time proximity
                        try:
                            time1 = datetime.fromisoformat(evo1.get("timestamp", ""))
                            time2 = datetime.fromisoformat(evo2.get("timestamp", ""))
                            time_diff = abs((time2 - time1).total_seconds() / 60)  # minutes
                            
                            if time_diff <= 120:  # Within 2 hours
                                # Check text similarity
                                desc1 = evo1.get("description", "")
                                desc2 = evo2.get("description", "")
                                similarity = self._calculate_text_similarity(desc1, desc2)
                                
                                if similarity > 0.6:  # 60% similarity
                                    duplicates_found.append({
                                        "feature": feature,
                                        "evolution1": evo1.get("id", "unknown"),
                                        "evolution2": evo2.get("id", "unknown"),
                                        "time_diff_minutes": time_diff,
                                        "similarity": similarity,
                                        "timestamp1": evo1.get("timestamp", ""),
                                        "timestamp2": evo2.get("timestamp", "")
                                    })
                        except (ValueError, TypeError):
                            continue
        
        # Summary statistics
        feature_counts = {feature: len(evolutions) for feature, evolutions in feature_groups.items()}
        
        return {
            "total_evolutions": len(self.history["evolutions"]),
            "duplicate_pairs": len(duplicates_found),
            "duplicates_detail": duplicates_found,
            "feature_counts": feature_counts,
            "most_duplicated_features": sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }

    def clean_duplicates(self, dry_run: bool = True) -> Dict:
        """Clean up duplicate evolutions from history"""
        if dry_run:
            return self.analyze_duplicates()
        
        # TODO: Implement actual cleanup logic
        # This would require careful consideration of which duplicates to remove
        # For now, just return analysis
        return {"message": "Cleanup not implemented yet - use dry_run=True for analysis"}

    def add_evolution(self, evolution: Dict) -> bool:
        """Add new evolution if it's not a duplicate"""
        if self.is_duplicate(evolution):
            print(f"⚠️  Duplicate evolution detected: {evolution.get('feature', 'unknown')} - {evolution.get('type', 'unknown')}")
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

    def suggest_unique_evolution(self, debate_results: Dict, alternatives: List[str] = None) -> Optional[Dict]:
        """Suggest evolution with enhanced uniqueness checking"""
        base_evolution = self.suggest_next_evolution(debate_results)
        
        if not base_evolution:
            return None
        
        # If it's not a duplicate, return as-is
        if not self.is_duplicate(base_evolution):
            return base_evolution
        
        # If it's a duplicate, try to make it more specific
        feature = base_evolution.get("feature", "")
        description = base_evolution.get("description", "")
        
        # Add timestamp-based uniqueness
        timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Create variations for common generic features
        if feature == "performance_optimization":
            variations = [
                f"performance_monitoring_{timestamp_suffix}",
                f"performance_profiling_{timestamp_suffix}",
                f"performance_caching_{timestamp_suffix}",
                f"performance_metrics_{timestamp_suffix}",
            ]
        elif feature == "general_improvement":
            variations = [
                f"usability_enhancement_{timestamp_suffix}",
                f"code_quality_{timestamp_suffix}",
                f"architecture_improvement_{timestamp_suffix}",
                f"developer_experience_{timestamp_suffix}",
            ]
        else:
            variations = [f"{feature}_{timestamp_suffix}"]
        
        # Try each variation
        for variation in variations:
            modified_evolution = base_evolution.copy()
            modified_evolution["feature"] = variation
            modified_evolution["description"] = f"{description} (Enhanced implementation - {timestamp_suffix})"
            
            if not self.is_duplicate(modified_evolution):
                return modified_evolution
        
        # If all variations are duplicates, return None to prevent duplicate creation
        print(f"⚠️  All evolution variations are duplicates for feature: {feature}")
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
