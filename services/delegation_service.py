"""
Delegation Service for Zamaz Debate System
Determines who should implement decisions based on complexity
"""

from typing import Any, Tuple, Optional
from domain.models import Decision, Debate, ImplementationAssignee, DecisionType


class DelegationService:
    """Service for determining implementation assignments"""

    def __init__(self):
        # Keywords that indicate complex implementation
        self.complex_keywords = [
            "architecture",
            "redesign",
            "migration",
            "refactor entire",
            "security",
            "authentication",
            "infrastructure",
            "database schema",
            "performance optimization",
            "scalability",
            "distributed",
        ]

        # Keywords that indicate simple implementation
        self.simple_keywords = [
            "rename",
            "typo",
            "comment",
            "documentation",
            "readme",
            "format",
            "style",
            "indent",
            "whitespace",
            "import",
        ]

        # Keywords that suggest Gemini can handle it
        self.gemini_capable_keywords = [
            "implement",
            "add feature",
            "create",
            "build",
            "develop",
            "integrate",
            "api",
            "endpoint",
            "function",
            "method",
            "test",
            "unit test",
            "validation",
            "error handling",
        ]

    def determine_implementation_assignment(
        self, decision: Decision, debate: Optional[Debate] = None
    ) -> Tuple[ImplementationAssignee, str]:
        """
        Determine who should implement the decision and complexity
        Returns: (assignee, implementation_complexity)
        """

        # First, assess implementation complexity
        impl_complexity = self._assess_implementation_complexity(decision, debate)

        # Then determine assignee based on rules
        assignee = self._determine_assignee(decision, impl_complexity, debate)

        return assignee, impl_complexity

    def determine_reviewer(self, implementer: ImplementationAssignee) -> str:
        """
        Determine who should review the PR based on the implementer
        
        Rules:
        - If Claude implements → Gemini reviews
        - If Gemini implements → Codex reviews and commits
        """
        if implementer == ImplementationAssignee.CLAUDE:
            return "gemini-bot"  # Gemini reviews Claude's work
        elif implementer == ImplementationAssignee.GEMINI:
            return "codex"  # Codex reviews and commits Gemini's work
        else:
            return "human"  # Human reviews human work

    def _assess_implementation_complexity(
        self, decision: Decision, debate: Optional[Debate] = None
    ) -> str:
        """Assess how complex the implementation would be"""

        # Combine question and decision text for analysis
        full_text = f"{decision.question} {decision.decision_text}".lower()

        # Check for complex indicators
        complex_count = sum(
            1 for keyword in self.complex_keywords if keyword in full_text
        )
        simple_count = sum(
            1 for keyword in self.simple_keywords if keyword in full_text
        )

        # If debate exists, check if there was significant disagreement
        if debate and len(debate.rounds) > 1:
            # Multiple rounds suggest complexity
            complex_count += 1

        # Decision rules
        # Evolution and Complex decision types are always complex
        if complex_count >= 2 or decision.decision_type in [DecisionType.EVOLUTION, DecisionType.COMPLEX]:
            return "complex"
        elif simple_count >= 2:
            return "simple"
        else:
            return "moderate"

    def _determine_assignee(
        self, decision: Decision, impl_complexity: str, debate: Optional[Debate] = None
    ) -> ImplementationAssignee:
        """Determine who should implement based on complexity and content
        
        New Rules:
        - Complex tasks → Claude (with Gemini as reviewer)
        - Regular tasks → Gemini (with Codex as reviewer and committer)
        """

        # Rule 1: Complex implementations go to Claude
        if impl_complexity == "complex":
            return ImplementationAssignee.CLAUDE

        # Rule 2: Regular (simple and moderate) tasks go to Gemini
        if impl_complexity in ["simple", "moderate"]:
            return ImplementationAssignee.GEMINI

        # Default to Claude for any edge cases
        return ImplementationAssignee.CLAUDE

    def get_implementation_instructions(
        self, decision: Decision, assignee: ImplementationAssignee
    ) -> str:
        """Generate implementation instructions for the assignee"""

        if assignee == ImplementationAssignee.GEMINI:
            return f"""
## Implementation Task for Gemini

**Decision**: {decision.decision_text[:200]}...

**Implementation Guidelines**:
1. Follow the decision exactly as specified
2. Write clean, well-documented code
3. Include appropriate error handling
4. Add unit tests for new functionality
5. Follow existing code patterns and conventions

**Complexity**: {decision.implementation_complexity}
**Priority**: {"High" if decision.decision_type == DecisionType.EVOLUTION else "Normal"}
**Reviewer**: Codex (will review and commit the code)
"""

        elif assignee == ImplementationAssignee.CLAUDE:
            return f"""
## Implementation Task for Claude

**Decision**: {decision.decision_text[:200]}...

**Implementation Guidelines**:
1. Consider architectural implications
2. Ensure backward compatibility
3. Document design decisions
4. Create comprehensive tests
5. Consider edge cases and error scenarios

**Complexity**: {decision.implementation_complexity}
**Reviewer**: Gemini (will review the implementation)
"""

        else:  # HUMAN
            return f"""
## Implementation Task Requires Human Intervention

**Decision**: {decision.decision_text[:200]}...

**Why Human Review Required**:
- High complexity implementation
- Potential security implications
- Major architectural changes
- Requires business decision

**Complexity**: {decision.implementation_complexity}
"""


class DelegationRules:
    """Business rules for delegation decisions"""

    @staticmethod
    def can_delegate_to_gemini(decision: Decision, impl_complexity: str) -> bool:
        """Check if a decision can be delegated to Gemini"""
        # Don't delegate evolution decisions to Gemini
        if decision.decision_type == DecisionType.EVOLUTION:
            return False

        # Don't delegate complex implementations
        if impl_complexity == "complex":
            return False

        # Check if it's a straightforward implementation task
        keywords = ["implement", "add", "create", "test", "validate"]
        question_lower = decision.question.lower()

        return any(keyword in question_lower for keyword in keywords)

    @staticmethod
    def requires_human_review(decision: Decision) -> bool:
        """Check if human review is required"""
        # Security-related decisions
        security_keywords = [
            "security",
            "authentication",
            "authorization",
            "encryption",
        ]

        # Database schema changes
        db_keywords = ["database", "schema", "migration", "data model"]

        # Major architectural changes
        arch_keywords = ["architecture", "redesign", "rewrite", "major refactor"]

        full_text = f"{decision.question} {decision.decision_text}".lower()

        return any(
            keyword in full_text
            for keyword in security_keywords + db_keywords + arch_keywords
        )
