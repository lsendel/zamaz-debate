#!/usr/bin/env python3
"""Track the evolution of the nucleus system"""

import hashlib
import json
from datetime import datetime
from pathlib import Path


class EvolutionTracker:
    def __init__(self):
        self.evolution_file = "evolution_history.json"
        self.history = self._load_history()

    def _load_history(self):
        if Path(self.evolution_file).exists():
            with open(self.evolution_file) as f:
                return json.load(f)
        return []

    def record_evolution(self, version, changes, reason):
        """Record a new evolution of the system"""

        # Read current nucleus code if it exists
        nucleus_path = Path("nucleus.py")
        if nucleus_path.exists():
            with open("nucleus.py", "r") as f:
                code = f.read()
            code_hash = hashlib.sha256(code.encode()).hexdigest()[:8]
            code_size = len(code)
        else:
            code_hash = "N/A"
            code_size = 0

        evolution = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "changes": changes,
            "reason": reason,
            "code_hash": code_hash,
            "code_size": code_size,
        }

        self.history.append(evolution)

        with open(self.evolution_file, "w") as f:
            json.dump(self.history, f, indent=2)

        print(f"📝 Recorded evolution to v{version}")

    def show_history(self):
        """Display evolution history"""
        if not self.history:
            print("No evolution history yet. Run bootstrap.py first!")
            return

        print("\n🧬 Evolution History:\n")
        for evo in self.history:
            print(f"v{evo['version']} - {evo['timestamp']}")
            print(f"  Changes: {evo['changes']}")
            print(f"  Reason: {evo['reason']}")
            print(f"  Code size: {evo['code_size']} bytes\n")


if __name__ == "__main__":
    tracker = EvolutionTracker()
    tracker.show_history()
