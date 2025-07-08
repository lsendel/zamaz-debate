#!/usr/bin/env python3
"""
Evolution History Tracker for Zamaz Debate System
Prevents repetition of previous evolutions and tracks system changes
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
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
        """Generate unique fingerprint for an evolution"""
        # Create fingerprint from key aspects of the evolution
        # Use only type and feature for fingerprint to catch duplicates
        key_parts = [
            evolution.get("type", "").lower().strip(),
            evolution.get("feature", "").lower().strip(),
        ]
        content = "|".join(key_parts)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def is_duplicate(self, evolution: Dict) -> bool:
        """Check if evolution is similar to previous ones"""
        fingerprint = self._generate_fingerprint(evolution)
        return fingerprint in self.history["fingerprints"]

    def add_evolution(self, evolution: Dict) -> bool:
        """Add new evolution if it's not a duplicate"""
        if self.is_duplicate(evolution):
            return False

        fingerprint = self._generate_fingerprint(evolution)

        # Add metadata
        evolution["id"] = (
            f"evo_{len(self.history['evolutions']) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
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

    print(
        f"\nEvolution Summary: {json.dumps(tracker.get_evolution_summary(), indent=2)}"
    )
