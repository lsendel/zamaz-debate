"""
Infrastructure Repository Implementations

Concrete implementations of repository interfaces using JSON file storage.
This provides a simple persistence layer for the domain models.
"""

from .debate_repositories import (
    JsonDebateRepository,
    JsonDebateResultRepository,
)
from .evolution_repositories import (
    JsonEvolutionHistoryRepository,
    JsonEvolutionMetricsRepository,
    JsonEvolutionRepository,
    JsonImprovementRepository,
)
from .implementation_repositories import (
    JsonDeploymentRepository,
    JsonImplementationMetricsRepository,
    JsonPullRequestRepository,
    JsonTaskRepository,
)
from .performance_repositories import (
    JsonBenchmarkRepository,
    JsonMetricRepository,
    JsonOptimizationStrategyRepository,
    JsonPerformanceAlertRepository,
)
from .testing_repositories import (
    JsonMockConfigurationRepository,
    JsonTestExecutionRepository,
    JsonTestMetricsRepository,
    JsonTestSuiteRepository,
)

__all__ = [
    # Debate repositories
    "JsonDebateRepository",
    "JsonDebateResultRepository",
    # Evolution repositories
    "JsonEvolutionRepository",
    "JsonImprovementRepository",
    "JsonEvolutionHistoryRepository",
    "JsonEvolutionMetricsRepository",
    # Implementation repositories
    "JsonTaskRepository",
    "JsonPullRequestRepository",
    "JsonDeploymentRepository",
    "JsonImplementationMetricsRepository",
    # Performance repositories
    "JsonMetricRepository",
    "JsonBenchmarkRepository",
    "JsonOptimizationStrategyRepository",
    "JsonPerformanceAlertRepository",
    # Testing repositories
    "JsonTestSuiteRepository",
    "JsonMockConfigurationRepository",
    "JsonTestExecutionRepository",
    "JsonTestMetricsRepository",
]