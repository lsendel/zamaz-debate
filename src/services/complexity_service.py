
from typing import Dict

class ComplexityService:
    """Service for assessing the complexity of a question."""

    def __init__(self):
        self.complexity_keywords: Dict[str, list[str]] = {
            "simple": ["rename", "format", "typo", "spacing", "comment", "import"],
            "moderate": ["refactor", "optimize", "clean", "organize", "split", "merge"],
            "complex": [
                "architecture",
                "design",
                "pattern",
                "system",
                "structure",
                "integrate",
                "improve",
                "improvement",
                "evolve",
                "evolution",
                "enhance",
                "feature",
            ],
        }

    def assess_complexity(self, question: str) -> str:
        """Determine if debate is needed."""
        q_lower = question.lower()

        # Check from most complex to simplest to ensure proper categorization
        for level in ["complex", "moderate", "simple"]:
            keywords = self.complexity_keywords[level]
            if any(k in q_lower for k in keywords):
                return level

        return "moderate"
