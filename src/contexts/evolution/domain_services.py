"""
Evolution Context Domain Services

Domain services that orchestrate complex evolution workflows
and enforce business rules across multiple aggregates.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from .aggregates import (
    Evolution,
    EvolutionHistory,
    EvolutionStatus,
    EvolutionTrigger,
    Improvement,
)
from .repositories import (
    EvolutionHistoryRepository,
    EvolutionMetricsRepository,
    EvolutionRepository,
    ImprovementRepository,
)
from .value_objects import (
    EvolutionImpact,
    EvolutionMetrics,
    EvolutionPlan,
    EvolutionStep,
    ImprovementArea,
    ImprovementSuggestion,
    RiskLevel,
    ValidationResult,
)


class EvolutionAnalysisService:
    """
    Domain service for system analysis and improvement identification
    
    Analyzes the current system state to identify areas for improvement
    and suggests evolution strategies.
    """
    
    def __init__(
        self,
        evolution_repo: EvolutionRepository,
        history_repo: EvolutionHistoryRepository,
        metrics_repo: EvolutionMetricsRepository,
    ):
        self.evolution_repo = evolution_repo
        self.history_repo = history_repo
        self.metrics_repo = metrics_repo
    
    async def analyze_system(
        self,
        current_metrics: EvolutionMetrics,
    ) -> List[ImprovementSuggestion]:
        """
        Analyze the system and suggest improvements
        
        Args:
            current_metrics: Current system metrics
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Analyze performance
        if current_metrics.performance_score < 70:
            suggestions.extend(await self._analyze_performance(current_metrics))
        
        # Analyze reliability
        if current_metrics.reliability_score < 80:
            suggestions.extend(await self._analyze_reliability(current_metrics))
        
        # Analyze maintainability
        if current_metrics.maintainability_score < 75:
            suggestions.extend(await self._analyze_maintainability(current_metrics))
        
        # Analyze security
        if current_metrics.security_score < 85:
            suggestions.extend(await self._analyze_security(current_metrics))
        
        # Analyze technical debt
        if current_metrics.technical_debt_hours > 100:
            suggestions.extend(await self._analyze_technical_debt(current_metrics))
        
        # Check for regression areas
        regression_areas = await self.metrics_repo.identify_regression_areas()
        for area in regression_areas:
            suggestions.append(self._create_regression_fix_suggestion(area))
        
        # Filter out duplicates from history
        history = await self.history_repo.get()
        if history:
            filtered_suggestions = []
            for suggestion in suggestions:
                if not history.has_similar_improvement(suggestion):
                    filtered_suggestions.append(suggestion)
            suggestions = filtered_suggestions
        
        return suggestions
    
    async def _analyze_performance(
        self,
        metrics: EvolutionMetrics,
    ) -> List[ImprovementSuggestion]:
        """Analyze performance issues and suggest improvements"""
        suggestions = []
        
        if metrics.response_time_ms > 500:
            suggestions.append(
                ImprovementSuggestion(
                    area=ImprovementArea.PERFORMANCE,
                    title="Optimize Response Time",
                    description="Response times exceed 500ms threshold",
                    rationale="High response times impact user experience and system efficiency",
                    expected_benefits=[
                        "Improved user experience",
                        "Reduced server load",
                        "Better scalability",
                    ],
                    estimated_impact="high",
                    implementation_approach="Profile application, identify bottlenecks, implement caching",
                    complexity="moderate",
                    prerequisites=["Performance profiling tools setup"],
                )
            )
        
        if metrics.cpu_usage_percent > 70:
            suggestions.append(
                ImprovementSuggestion(
                    area=ImprovementArea.PERFORMANCE,
                    title="Reduce CPU Usage",
                    description="CPU usage consistently above 70%",
                    rationale="High CPU usage limits scalability and increases costs",
                    expected_benefits=[
                        "Improved scalability",
                        "Reduced infrastructure costs",
                        "Better resource utilization",
                    ],
                    estimated_impact="high",
                    implementation_approach="Optimize algorithms, implement async processing",
                    complexity="complex",
                    prerequisites=["CPU profiling", "Algorithm analysis"],
                )
            )
        
        return suggestions
    
    async def _analyze_reliability(
        self,
        metrics: EvolutionMetrics,
    ) -> List[ImprovementSuggestion]:
        """Analyze reliability issues and suggest improvements"""
        suggestions = []
        
        if metrics.error_rate > 0.1:  # More than 0.1 errors per hour
            suggestions.append(
                ImprovementSuggestion(
                    area=ImprovementArea.ARCHITECTURE,
                    title="Implement Circuit Breakers",
                    description="Error rate exceeds acceptable threshold",
                    rationale="High error rates impact system reliability and user trust",
                    expected_benefits=[
                        "Improved fault tolerance",
                        "Faster recovery from failures",
                        "Better error isolation",
                    ],
                    estimated_impact="high",
                    implementation_approach="Implement circuit breaker pattern for external services",
                    complexity="moderate",
                    prerequisites=["Service dependency mapping"],
                )
            )
        
        return suggestions
    
    async def _analyze_maintainability(
        self,
        metrics: EvolutionMetrics,
    ) -> List[ImprovementSuggestion]:
        """Analyze maintainability issues and suggest improvements"""
        suggestions = []
        
        if metrics.code_complexity > 10:  # High cyclomatic complexity
            suggestions.append(
                ImprovementSuggestion(
                    area=ImprovementArea.CODE_QUALITY,
                    title="Reduce Code Complexity",
                    description="Average cyclomatic complexity exceeds 10",
                    rationale="Complex code is harder to maintain and more prone to bugs",
                    expected_benefits=[
                        "Easier maintenance",
                        "Fewer bugs",
                        "Faster development",
                    ],
                    estimated_impact="medium",
                    implementation_approach="Refactor complex methods, extract classes",
                    complexity="moderate",
                    prerequisites=["Complexity analysis report"],
                )
            )
        
        if metrics.test_coverage < 80:
            suggestions.append(
                ImprovementSuggestion(
                    area=ImprovementArea.TESTING,
                    title="Increase Test Coverage",
                    description=f"Test coverage at {metrics.test_coverage}%, below 80% target",
                    rationale="Low test coverage increases risk of regressions",
                    expected_benefits=[
                        "Reduced regression risk",
                        "Safer refactoring",
                        "Better code confidence",
                    ],
                    estimated_impact="high",
                    implementation_approach="Add unit and integration tests for uncovered code",
                    complexity="simple",
                    prerequisites=["Coverage report analysis"],
                )
            )
        
        return suggestions
    
    async def _analyze_security(
        self,
        metrics: EvolutionMetrics,
    ) -> List[ImprovementSuggestion]:
        """Analyze security issues and suggest improvements"""
        suggestions = []
        
        if metrics.security_score < 85:
            suggestions.append(
                ImprovementSuggestion(
                    area=ImprovementArea.SECURITY,
                    title="Security Hardening",
                    description="Security score below recommended threshold",
                    rationale="Security vulnerabilities pose significant risks",
                    expected_benefits=[
                        "Reduced security risks",
                        "Compliance improvements",
                        "Better data protection",
                    ],
                    estimated_impact="high",
                    implementation_approach="Security audit, implement OWASP recommendations",
                    complexity="complex",
                    prerequisites=["Security audit"],
                )
            )
        
        return suggestions
    
    async def _analyze_technical_debt(
        self,
        metrics: EvolutionMetrics,
    ) -> List[ImprovementSuggestion]:
        """Analyze technical debt and suggest improvements"""
        suggestions = []
        
        suggestions.append(
            ImprovementSuggestion(
                area=ImprovementArea.MAINTAINABILITY,
                title="Technical Debt Reduction",
                description=f"Technical debt estimated at {metrics.technical_debt_hours} hours",
                rationale="High technical debt slows development and increases maintenance costs",
                expected_benefits=[
                    "Faster feature development",
                    "Reduced maintenance costs",
                    "Improved code quality",
                ],
                estimated_impact="medium",
                implementation_approach="Prioritize and tackle highest-impact debt items",
                complexity="moderate",
                prerequisites=["Technical debt inventory"],
            )
        )
        
        return suggestions
    
    def _create_regression_fix_suggestion(
        self,
        regression_area: Dict[str, Any],
    ) -> ImprovementSuggestion:
        """Create a suggestion to fix a regression"""
        return ImprovementSuggestion(
            area=ImprovementArea.PERFORMANCE,
            title=f"Fix {regression_area['metric']} Regression",
            description=f"{regression_area['metric']} has decreased by {regression_area['decrease']}%",
            rationale="Regressions indicate deteriorating system health",
            expected_benefits=[
                "Restore previous performance levels",
                "Prevent further degradation",
            ],
            estimated_impact="high",
            implementation_approach="Identify root cause and implement targeted fix",
            complexity="moderate",
            prerequisites=["Root cause analysis"],
        )
    
    async def determine_evolution_trigger(
        self,
        current_metrics: EvolutionMetrics,
    ) -> Tuple[bool, EvolutionTrigger, Dict[str, Any]]:
        """
        Determine if evolution should be triggered
        
        Args:
            current_metrics: Current system metrics
            
        Returns:
            Tuple of (should_trigger, trigger_type, trigger_details)
        """
        # Check for critical performance issues
        if current_metrics.performance_score < 50:
            return True, EvolutionTrigger.PERFORMANCE, {
                "reason": "Critical performance degradation",
                "performance_score": current_metrics.performance_score,
            }
        
        # Check for high error rates
        if current_metrics.error_rate > 1.0:  # More than 1 error per hour
            return True, EvolutionTrigger.ERROR_RATE, {
                "reason": "High error rate detected",
                "error_rate": current_metrics.error_rate,
            }
        
        # Check for security issues
        if current_metrics.security_score < 70:
            return True, EvolutionTrigger.SECURITY, {
                "reason": "Security score below threshold",
                "security_score": current_metrics.security_score,
            }
        
        # Check for architectural issues
        if current_metrics.code_complexity > 15:
            return True, EvolutionTrigger.ARCHITECTURAL, {
                "reason": "High code complexity",
                "complexity": current_metrics.code_complexity,
            }
        
        return False, EvolutionTrigger.MANUAL, {}


class EvolutionPlanningService:
    """
    Domain service for evolution planning
    
    Creates detailed evolution plans based on improvement suggestions
    and system constraints.
    """
    
    def create_evolution_plan(
        self,
        improvements: List[Improvement],
        constraints: Dict[str, Any],
    ) -> EvolutionPlan:
        """
        Create an evolution plan from approved improvements
        
        Args:
            improvements: List of approved improvements
            constraints: System constraints (time, resources, etc.)
            
        Returns:
            Evolution plan
        """
        # Filter and prioritize improvements
        prioritized = self._prioritize_improvements(improvements)
        
        # Create implementation steps
        steps = self._create_implementation_steps(prioritized)
        
        # Calculate total duration
        total_duration = sum(step.estimated_duration_hours for step in steps)
        
        # Assess risk level
        risk_level = self._assess_risk_level(improvements)
        
        # Define rollback strategy
        rollback_strategy = self._create_rollback_strategy(improvements)
        
        # Define success criteria
        success_criteria = self._define_success_criteria(improvements)
        
        # Create monitoring plan
        monitoring_plan = self._create_monitoring_plan(improvements)
        
        return EvolutionPlan(
            steps=steps,
            estimated_duration_hours=total_duration,
            risk_level=risk_level,
            rollback_strategy=rollback_strategy,
            success_criteria=success_criteria,
            monitoring_plan=monitoring_plan,
        )
    
    def _prioritize_improvements(
        self,
        improvements: List[Improvement],
    ) -> List[Improvement]:
        """Prioritize improvements based on impact and dependencies"""
        # Sort by impact (high > medium > low) and complexity (simple > moderate > complex)
        impact_scores = {"high": 3, "medium": 2, "low": 1}
        complexity_scores = {"simple": 3, "moderate": 2, "complex": 1}
        
        return sorted(
            improvements,
            key=lambda i: (
                impact_scores.get(i.suggestion.estimated_impact, 0) *
                complexity_scores.get(i.suggestion.complexity, 0)
            ),
            reverse=True,
        )
    
    def _create_implementation_steps(
        self,
        improvements: List[Improvement],
    ) -> List[EvolutionStep]:
        """Create implementation steps from improvements"""
        steps = []
        order = 1
        
        # Pre-implementation steps
        steps.append(
            EvolutionStep(
                order=order,
                action="Backup current state",
                description="Create full system backup for rollback",
                estimated_duration_hours=1.0,
                dependencies=[],
                validation_criteria=["Backup verified", "Restore tested"],
            )
        )
        order += 1
        
        steps.append(
            EvolutionStep(
                order=order,
                action="Run baseline tests",
                description="Execute full test suite to establish baseline",
                estimated_duration_hours=2.0,
                dependencies=[1],
                validation_criteria=["All tests passing", "Metrics recorded"],
            )
        )
        order += 1
        
        # Implementation steps for each improvement
        for improvement in improvements:
            # Analysis step
            steps.append(
                EvolutionStep(
                    order=order,
                    action=f"Analyze {improvement.suggestion.title}",
                    description=f"Detailed analysis for {improvement.suggestion.description}",
                    estimated_duration_hours=2.0,
                    dependencies=[2],
                    validation_criteria=["Analysis complete", "Approach validated"],
                )
            )
            analysis_order = order
            order += 1
            
            # Implementation step
            hours = self._estimate_implementation_hours(improvement.suggestion.complexity)
            steps.append(
                EvolutionStep(
                    order=order,
                    action=f"Implement {improvement.suggestion.title}",
                    description=improvement.suggestion.implementation_approach,
                    estimated_duration_hours=hours,
                    dependencies=[analysis_order],
                    validation_criteria=["Implementation complete", "Unit tests passing"],
                )
            )
            impl_order = order
            order += 1
            
            # Testing step
            steps.append(
                EvolutionStep(
                    order=order,
                    action=f"Test {improvement.suggestion.title}",
                    description="Run targeted tests for the improvement",
                    estimated_duration_hours=1.0,
                    dependencies=[impl_order],
                    validation_criteria=["Tests passing", "No regressions"],
                )
            )
            order += 1
        
        # Post-implementation steps
        steps.append(
            EvolutionStep(
                order=order,
                action="Run full test suite",
                description="Execute comprehensive tests",
                estimated_duration_hours=2.0,
                dependencies=list(range(3, order)),
                validation_criteria=["All tests passing", "Coverage maintained"],
            )
        )
        order += 1
        
        steps.append(
            EvolutionStep(
                order=order,
                action="Performance validation",
                description="Validate performance improvements",
                estimated_duration_hours=3.0,
                dependencies=[order - 1],
                validation_criteria=["Performance targets met", "No degradation"],
            )
        )
        
        return steps
    
    def _estimate_implementation_hours(self, complexity: str) -> float:
        """Estimate implementation hours based on complexity"""
        complexity_hours = {
            "simple": 4.0,
            "moderate": 8.0,
            "complex": 16.0,
        }
        return complexity_hours.get(complexity, 8.0)
    
    def _assess_risk_level(self, improvements: List[Improvement]) -> RiskLevel:
        """Assess overall risk level of the evolution"""
        # Count high-impact and complex improvements
        high_impact_count = sum(
            1 for i in improvements
            if i.suggestion.estimated_impact == "high"
        )
        complex_count = sum(
            1 for i in improvements
            if i.suggestion.complexity == "complex"
        )
        
        # Assess risk based on counts
        if complex_count >= 3 or high_impact_count >= 5:
            return RiskLevel.HIGH
        elif complex_count >= 1 or high_impact_count >= 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _create_rollback_strategy(self, improvements: List[Improvement]) -> str:
        """Create rollback strategy based on improvements"""
        strategies = []
        
        # Check improvement areas
        areas = {i.suggestion.area for i in improvements}
        
        if ImprovementArea.ARCHITECTURE in areas:
            strategies.append("Revert architectural changes using feature flags")
        
        if ImprovementArea.PERFORMANCE in areas:
            strategies.append("Restore previous configuration and caching settings")
        
        if ImprovementArea.INFRASTRUCTURE in areas:
            strategies.append("Use blue-green deployment for instant rollback")
        
        strategies.append("Restore from pre-evolution backup if needed")
        
        return "; ".join(strategies)
    
    def _define_success_criteria(self, improvements: List[Improvement]) -> List[str]:
        """Define success criteria based on improvements"""
        criteria = [
            "All tests passing with no new failures",
            "No performance regressions detected",
            "Error rate not increased",
        ]
        
        # Add improvement-specific criteria
        for improvement in improvements:
            if improvement.suggestion.area == ImprovementArea.PERFORMANCE:
                criteria.append(f"Performance improved for {improvement.suggestion.title}")
            elif improvement.suggestion.area == ImprovementArea.SECURITY:
                criteria.append("Security scan shows no new vulnerabilities")
            elif improvement.suggestion.area == ImprovementArea.TESTING:
                criteria.append("Test coverage increased")
        
        return criteria
    
    def _create_monitoring_plan(self, improvements: List[Improvement]) -> str:
        """Create monitoring plan for the evolution"""
        return (
            "1. Monitor key metrics every 15 minutes during implementation\n"
            "2. Set up alerts for error rate increases > 10%\n"
            "3. Track performance metrics in real-time\n"
            "4. Monitor resource usage (CPU, memory, disk)\n"
            "5. Check user feedback channels for issues\n"
            "6. Maintain communication with stakeholders"
        )


class EvolutionValidationService:
    """
    Domain service for evolution validation
    
    Validates that evolutions meet their objectives and don't
    introduce regressions.
    """
    
    def __init__(
        self,
        evolution_repo: EvolutionRepository,
        metrics_repo: EvolutionMetricsRepository,
    ):
        self.evolution_repo = evolution_repo
        self.metrics_repo = metrics_repo
    
    async def validate_evolution(
        self,
        evolution: Evolution,
        current_metrics: EvolutionMetrics,
    ) -> ValidationResult:
        """
        Validate an evolution
        
        Args:
            evolution: The evolution to validate
            current_metrics: Current system metrics
            
        Returns:
            Validation result
        """
        if not evolution.metrics_before:
            raise ValueError("No baseline metrics available for validation")
        
        # Run validation checks
        tests_passed = 0
        tests_failed = 0
        issues_found = []
        
        # Check for regressions
        metric_comparison = current_metrics.compare_to(evolution.metrics_before)
        
        for metric, change in metric_comparison.items():
            if metric.endswith("_change"):
                metric_name = metric.replace("_change", "")
                if change < -5.0:  # More than 5% degradation
                    tests_failed += 1
                    issues_found.append(f"{metric_name} degraded by {abs(change):.1f}%")
                else:
                    tests_passed += 1
        
        # Check success criteria
        if evolution.plan:
            for criterion in evolution.plan.success_criteria:
                # In a real implementation, this would check actual criteria
                # For now, we'll simulate
                if "performance improved" in criterion.lower():
                    if metric_comparison.get("performance_score_change", 0) > 0:
                        tests_passed += 1
                    else:
                        tests_failed += 1
                        issues_found.append(f"Criterion not met: {criterion}")
                else:
                    tests_passed += 1
        
        # Determine if rollback is needed
        rollback_required = (
            tests_failed > tests_passed or
            len(issues_found) > 3 or
            current_metrics.error_rate > evolution.metrics_before.error_rate * 2
        )
        
        # Calculate performance impact
        performance_impact = {
            "performance": metric_comparison.get("performance_score_change", 0),
            "reliability": metric_comparison.get("reliability_score_change", 0),
            "maintainability": metric_comparison.get("maintainability_score_change", 0),
            "security": metric_comparison.get("security_score_change", 0),
        }
        
        return ValidationResult(
            is_successful=not rollback_required,
            validation_timestamp=datetime.now(),
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            performance_impact=performance_impact,
            issues_found=issues_found,
            rollback_required=rollback_required,
            validator="EvolutionValidationService",
        )
    
    async def calculate_evolution_impact(
        self,
        evolution: Evolution,
    ) -> EvolutionImpact:
        """
        Calculate the overall impact of an evolution
        
        Args:
            evolution: The completed evolution
            
        Returns:
            Evolution impact analysis
        """
        if not evolution.is_completed:
            raise ValueError("Can only calculate impact for completed evolutions")
        
        if not evolution.metrics_before or not evolution.metrics_after:
            raise ValueError("Metrics required to calculate impact")
        
        # Calculate improvements
        metric_comparison = evolution.metrics_after.compare_to(evolution.metrics_before)
        
        # Count successful improvements
        improvements_applied = len([i for i in evolution.improvements if i.is_validated])
        
        # Identify new capabilities (simulated)
        new_capabilities = []
        for improvement in evolution.improvements:
            if improvement.is_validated and improvement.suggestion.area == ImprovementArea.ARCHITECTURE:
                new_capabilities.append(improvement.suggestion.title)
        
        # Calculate technical debt reduction
        debt_reduced = max(
            0,
            evolution.metrics_before.technical_debt_hours - evolution.metrics_after.technical_debt_hours
        )
        
        # Check for breaking changes (simulated)
        breaking_changes = []
        if any(i.suggestion.area == ImprovementArea.ARCHITECTURE for i in evolution.improvements):
            breaking_changes.append("API contract changes may be required")
        
        return EvolutionImpact(
            improvements_applied=improvements_applied,
            performance_improvement_percent=metric_comparison.get("performance_score_change", 0),
            reliability_improvement_percent=metric_comparison.get("reliability_score_change", 0),
            new_capabilities_added=new_capabilities,
            technical_debt_reduced_hours=debt_reduced,
            breaking_changes=breaking_changes,
            migration_required=len(breaking_changes) > 0,
            downtime_minutes=0.0,  # Would be tracked in real implementation
            rollback_count=0,  # Would be tracked in real implementation
        )


class EvolutionOrchestrationService:
    """
    Domain service for orchestrating the entire evolution process
    
    Coordinates between analysis, planning, implementation, and validation.
    """
    
    def __init__(
        self,
        analysis_service: EvolutionAnalysisService,
        planning_service: EvolutionPlanningService,
        validation_service: EvolutionValidationService,
        evolution_repo: EvolutionRepository,
        history_repo: EvolutionHistoryRepository,
    ):
        self.analysis_service = analysis_service
        self.planning_service = planning_service
        self.validation_service = validation_service
        self.evolution_repo = evolution_repo
        self.history_repo = history_repo
    
    async def trigger_evolution(
        self,
        trigger: EvolutionTrigger,
        trigger_details: Dict[str, Any],
        current_metrics: EvolutionMetrics,
    ) -> Evolution:
        """
        Trigger a new evolution cycle
        
        Args:
            trigger: What triggered the evolution
            trigger_details: Details about the trigger
            current_metrics: Current system metrics
            
        Returns:
            The triggered evolution
        """
        # Create new evolution
        evolution = Evolution(
            trigger=trigger,
            trigger_details=trigger_details,
        )
        
        # Save evolution
        await self.evolution_repo.save(evolution)
        
        # Start analysis
        evolution.start_analysis(current_metrics)
        
        # Get improvement suggestions
        suggestions = await self.analysis_service.analyze_system(current_metrics)
        
        # Create improvements from suggestions
        for suggestion in suggestions[:5]:  # Limit to top 5
            improvement = Improvement(
                evolution_id=evolution.id,
                suggestion=suggestion,
            )
            evolution.suggest_improvement(improvement)
        
        # Auto-approve high-impact improvements (in real system would require review)
        for improvement in evolution.improvements:
            if improvement.suggestion.estimated_impact == "high":
                improvement.approve("AutoApproval")
        
        # Create plan if we have approved improvements
        approved = [i for i in evolution.improvements if i.is_approved]
        if approved:
            plan = self.planning_service.create_evolution_plan(
                approved,
                constraints={"max_duration_hours": 40},
            )
            evolution.create_plan(plan)
        
        # Update evolution
        await self.evolution_repo.update(evolution)
        
        return evolution
    
    async def complete_evolution(
        self,
        evolution_id: UUID,
        current_metrics: EvolutionMetrics,
    ) -> Evolution:
        """
        Complete and validate an evolution
        
        Args:
            evolution_id: The evolution to complete
            current_metrics: Current system metrics after implementation
            
        Returns:
            The completed evolution
        """
        # Get evolution
        evolution = await self.evolution_repo.find_by_id(evolution_id)
        if not evolution:
            raise ValueError("Evolution not found")
        
        # Validate evolution
        validation_result = await self.validation_service.validate_evolution(
            evolution,
            current_metrics,
        )
        
        # Update evolution with validation
        evolution.validate(validation_result, current_metrics)
        
        # If successful, add to history
        if evolution.is_successful:
            history = await self.history_repo.get()
            if history:
                history.add_evolution(evolution)
                await self.history_repo.update(history)
            else:
                # Create new history
                history = EvolutionHistory()
                history.add_evolution(evolution)
                await self.history_repo.save(history)
        
        # Update evolution
        await self.evolution_repo.update(evolution)
        
        return evolution
    
    async def get_evolution_recommendations(
        self,
        days_ahead: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations for future evolutions
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of evolution recommendations
        """
        recommendations = []
        
        # Get recent evolution history
        history = await self.history_repo.get()
        if not history:
            return recommendations
        
        # Analyze evolution patterns
        recent_evolutions = history.get_recent_evolutions(days=90)
        
        # Calculate time since last evolution
        if history.last_evolution_at:
            days_since_last = (datetime.now() - history.last_evolution_at).days
            
            if days_since_last > 30:
                recommendations.append({
                    "type": "scheduled",
                    "urgency": "medium",
                    "reason": f"No evolution in {days_since_last} days",
                    "suggested_date": datetime.now() + timedelta(days=7),
                })
        
        # Check success rate
        success_rate = history.get_success_rate()
        if success_rate < 70:
            recommendations.append({
                "type": "process_improvement",
                "urgency": "high",
                "reason": f"Evolution success rate only {success_rate:.1f}%",
                "suggested_action": "Review evolution process and failure causes",
            })
        
        # Analyze improvement areas
        area_counts = {}
        for evolution in recent_evolutions:
            for improvement in evolution.improvements:
                area = improvement.suggestion.area
                area_counts[area] = area_counts.get(area, 0) + 1
        
        # Find neglected areas
        all_areas = set(ImprovementArea)
        covered_areas = set(area_counts.keys())
        neglected_areas = all_areas - covered_areas
        
        for area in neglected_areas:
            recommendations.append({
                "type": "area_focus",
                "urgency": "low",
                "reason": f"{area.value} not addressed recently",
                "suggested_area": area.value,
            })
        
        return recommendations