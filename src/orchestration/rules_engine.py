"""
Rules Engine for Deterministic Debate Orchestration

This module provides a rules-based approach to debate orchestration, replacing the LLM-based
orchestrator with deterministic rules that are predictable, fast, and debuggable.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union
from uuid import UUID

logger = logging.getLogger(__name__)


class RuleConditionType(Enum):
    """Types of rule conditions."""
    EQUALS = "equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    IN_LIST = "in_list"
    REGEX_MATCH = "regex_match"
    TIME_ELAPSED = "time_elapsed"
    COUNT_THRESHOLD = "count_threshold"


class RuleActionType(Enum):
    """Types of rule actions."""
    CONTINUE_DEBATE = "continue_debate"
    PAUSE_DEBATE = "pause_debate"
    COMPLETE_DEBATE = "complete_debate"
    START_NEW_ROUND = "start_new_round"
    REQUEST_CLARIFICATION = "request_clarification"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    APPLY_TEMPLATE = "apply_template"
    EMIT_EVENT = "emit_event"
    SET_VARIABLE = "set_variable"


@dataclass
class RuleCondition:
    """A condition that must be met for a rule to trigger."""
    type: RuleConditionType
    field: str  # Field to check (e.g., "debate.round_count", "arguments.length")
    value: Any  # Value to compare against
    operator: str = "and"  # "and" or "or" for combining with other conditions


@dataclass
class RuleAction:
    """An action to take when a rule triggers."""
    type: RuleActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher priority actions execute first


@dataclass
class DebateRule:
    """A rule that governs debate orchestration."""
    id: str
    name: str
    description: str
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    enabled: bool = True
    priority: int = 0  # Higher priority rules are evaluated first
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


@dataclass
class DebateContext:
    """Context information for rule evaluation."""
    debate_id: UUID
    round_count: int
    argument_count: int
    participant_count: int
    start_time: datetime
    last_activity: datetime
    complexity: str
    question_keywords: Set[str]
    consensus_indicators: Dict[str, float]
    custom_variables: Dict[str, Any] = field(default_factory=dict)
    
    def get_elapsed_time(self) -> timedelta:
        """Get elapsed time since debate start."""
        return datetime.now() - self.start_time
    
    def get_idle_time(self) -> timedelta:
        """Get time since last activity."""
        return datetime.now() - self.last_activity
    
    def get_arguments_per_participant(self) -> float:
        """Get average arguments per participant."""
        return self.argument_count / max(self.participant_count, 1)


@dataclass
class RuleEvaluationResult:
    """Result of rule evaluation."""
    rule_triggered: bool
    rule: Optional[DebateRule] = None
    actions: List[RuleAction] = field(default_factory=list)
    evaluation_time: timedelta = field(default_factory=lambda: timedelta(0))
    error: Optional[str] = None


class RuleConditionEvaluator:
    """Evaluates rule conditions against debate context."""
    
    @staticmethod
    def evaluate_condition(condition: RuleCondition, context: DebateContext) -> bool:
        """Evaluate a single condition."""
        try:
            field_value = RuleConditionEvaluator._get_field_value(condition.field, context)
            
            if condition.type == RuleConditionType.EQUALS:
                return field_value == condition.value
            elif condition.type == RuleConditionType.GREATER_THAN:
                return float(field_value) > float(condition.value)
            elif condition.type == RuleConditionType.LESS_THAN:
                return float(field_value) < float(condition.value)
            elif condition.type == RuleConditionType.CONTAINS:
                return str(condition.value).lower() in str(field_value).lower()
            elif condition.type == RuleConditionType.IN_LIST:
                return field_value in condition.value
            elif condition.type == RuleConditionType.REGEX_MATCH:
                import re
                return bool(re.search(condition.value, str(field_value)))
            elif condition.type == RuleConditionType.TIME_ELAPSED:
                elapsed = context.get_elapsed_time()
                return elapsed.total_seconds() > float(condition.value)
            elif condition.type == RuleConditionType.COUNT_THRESHOLD:
                return int(field_value) >= int(condition.value)
            else:
                logger.warning(f"Unknown condition type: {condition.type}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating condition {condition.field}: {e}")
            return False
    
    @staticmethod
    def _get_field_value(field_path: str, context: DebateContext) -> Any:
        """Get field value from context using dot notation."""
        parts = field_path.split('.')
        value = context
        
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                raise ValueError(f"Field not found: {field_path}")
        
        return value


class RulesEngine:
    """Deterministic rules engine for debate orchestration."""
    
    def __init__(self):
        self.rules: Dict[str, DebateRule] = {}
        self.rule_sets: Dict[str, Set[str]] = {}  # Named sets of rule IDs
        self.metrics = {
            'total_evaluations': 0,
            'rules_triggered': 0,
            'average_evaluation_time': 0.0,
            'error_count': 0
        }
    
    def add_rule(self, rule: DebateRule) -> None:
        """Add a rule to the engine."""
        self.rules[rule.id] = rule
        logger.info(f"Added rule: {rule.name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the engine."""
        if rule_id in self.rules:
            rule = self.rules.pop(rule_id)
            logger.info(f"Removed rule: {rule.name}")
            return True
        return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False
    
    def create_rule_set(self, name: str, rule_ids: Set[str]) -> None:
        """Create a named set of rules."""
        self.rule_sets[name] = rule_ids
        logger.info(f"Created rule set '{name}' with {len(rule_ids)} rules")
    
    def evaluate_rules(self, context: DebateContext, rule_set: Optional[str] = None) -> List[RuleEvaluationResult]:
        """Evaluate rules against the given context."""
        start_time = datetime.now()
        self.metrics['total_evaluations'] += 1
        
        # Determine which rules to evaluate
        rules_to_evaluate = []
        if rule_set and rule_set in self.rule_sets:
            rule_ids = self.rule_sets[rule_set]
            rules_to_evaluate = [self.rules[rid] for rid in rule_ids if rid in self.rules]
        else:
            rules_to_evaluate = list(self.rules.values())
        
        # Filter enabled rules and sort by priority
        enabled_rules = [r for r in rules_to_evaluate if r.enabled]
        enabled_rules.sort(key=lambda r: r.priority, reverse=True)
        
        results = []
        for rule in enabled_rules:
            result = self._evaluate_single_rule(rule, context)
            results.append(result)
            
            if result.rule_triggered:
                self.metrics['rules_triggered'] += 1
                rule.last_triggered = datetime.now()
                rule.trigger_count += 1
        
        # Update metrics
        evaluation_time = datetime.now() - start_time
        self._update_average_evaluation_time(evaluation_time)
        
        logger.debug(f"Evaluated {len(enabled_rules)} rules in {evaluation_time.total_seconds():.3f}s")
        return results
    
    def _evaluate_single_rule(self, rule: DebateRule, context: DebateContext) -> RuleEvaluationResult:
        """Evaluate a single rule."""
        try:
            start_time = datetime.now()
            
            # Evaluate conditions
            if not rule.conditions:
                # Rule with no conditions always triggers
                triggered = True
            else:
                condition_results = []
                for condition in rule.conditions:
                    result = RuleConditionEvaluator.evaluate_condition(condition, context)
                    condition_results.append((condition, result))
                
                # Combine conditions based on operators
                triggered = self._combine_condition_results(condition_results)
            
            evaluation_time = datetime.now() - start_time
            
            if triggered:
                # Sort actions by priority
                actions = sorted(rule.actions, key=lambda a: a.priority, reverse=True)
                logger.info(f"Rule triggered: {rule.name}")
                return RuleEvaluationResult(
                    rule_triggered=True,
                    rule=rule,
                    actions=actions,
                    evaluation_time=evaluation_time
                )
            else:
                return RuleEvaluationResult(
                    rule_triggered=False,
                    evaluation_time=evaluation_time
                )
                
        except Exception as e:
            self.metrics['error_count'] += 1
            logger.error(f"Error evaluating rule {rule.name}: {e}")
            return RuleEvaluationResult(
                rule_triggered=False,
                error=str(e)
            )
    
    def _combine_condition_results(self, condition_results: List[tuple]) -> bool:
        """Combine condition results based on operators."""
        if not condition_results:
            return True
        
        # Simple implementation: all conditions with "and" operator must be true
        # Any condition with "or" operator can make the rule true
        has_or = any(cond.operator == "or" for cond, _ in condition_results)
        
        if has_or:
            # If any OR conditions exist, check if any are true
            or_results = [result for cond, result in condition_results if cond.operator == "or"]
            and_results = [result for cond, result in condition_results if cond.operator == "and"]
            
            return any(or_results) or (and_results and all(and_results))
        else:
            # All AND conditions must be true
            return all(result for _, result in condition_results)
    
    def _update_average_evaluation_time(self, evaluation_time: timedelta) -> None:
        """Update average evaluation time metric."""
        current_avg = self.metrics['average_evaluation_time']
        total_evaluations = self.metrics['total_evaluations']
        
        new_avg = ((current_avg * (total_evaluations - 1)) + evaluation_time.total_seconds()) / total_evaluations
        self.metrics['average_evaluation_time'] = new_avg
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics."""
        return self.metrics.copy()
    
    def get_rule_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all rules."""
        stats = {}
        for rule in self.rules.values():
            stats[rule.id] = {
                'name': rule.name,
                'enabled': rule.enabled,
                'trigger_count': rule.trigger_count,
                'last_triggered': rule.last_triggered,
                'tags': list(rule.tags)
            }
        return stats


class StandardRuleFactory:
    """Factory for creating standard debate orchestration rules."""
    
    @staticmethod
    def create_basic_orchestration_rules() -> List[DebateRule]:
        """Create basic orchestration rules for debate management."""
        rules = []
        
        # Rule: Start new round if current round has enough arguments
        rules.append(DebateRule(
            id="start_new_round",
            name="Start New Round",
            description="Start a new round when current round has arguments from all participants",
            conditions=[
                RuleCondition(
                    type=RuleConditionType.GREATER_THAN,
                    field="arguments_per_participant",
                    value=0.9  # Each participant has contributed
                ),
                RuleCondition(
                    type=RuleConditionType.LESS_THAN,
                    field="round_count",
                    value=5  # Don't exceed max rounds
                )
            ],
            actions=[
                RuleAction(
                    type=RuleActionType.START_NEW_ROUND,
                    priority=10
                )
            ],
            priority=100,
            tags={"orchestration", "rounds"}
        ))
        
        # Rule: Complete debate if consensus reached
        rules.append(DebateRule(
            id="complete_on_consensus",
            name="Complete on Consensus",
            description="Complete debate when strong consensus is detected",
            conditions=[
                RuleCondition(
                    type=RuleConditionType.GREATER_THAN,
                    field="consensus_indicators.confidence",
                    value=0.8
                ),
                RuleCondition(
                    type=RuleConditionType.GREATER_THAN,
                    field="round_count",
                    value=1  # At least 2 rounds
                )
            ],
            actions=[
                RuleAction(
                    type=RuleActionType.COMPLETE_DEBATE,
                    parameters={"reason": "consensus_reached"},
                    priority=20
                )
            ],
            priority=90,
            tags={"completion", "consensus"}
        ))
        
        # Rule: Complete debate if max rounds reached
        rules.append(DebateRule(
            id="complete_max_rounds",
            name="Complete at Max Rounds",
            description="Complete debate when maximum rounds are reached",
            conditions=[
                RuleCondition(
                    type=RuleConditionType.GREATER_THAN,
                    field="round_count",
                    value=4  # 5 rounds total
                )
            ],
            actions=[
                RuleAction(
                    type=RuleActionType.COMPLETE_DEBATE,
                    parameters={"reason": "max_rounds_reached"},
                    priority=15
                )
            ],
            priority=80,
            tags={"completion", "limits"}
        ))
        
        # Rule: Pause if no activity for too long
        rules.append(DebateRule(
            id="pause_idle",
            name="Pause on Idle",
            description="Pause debate if no activity for extended period",
            conditions=[
                RuleCondition(
                    type=RuleConditionType.GREATER_THAN,
                    field="idle_time",
                    value=600  # 10 minutes
                )
            ],
            actions=[
                RuleAction(
                    type=RuleActionType.PAUSE_DEBATE,
                    parameters={"reason": "idle_timeout"},
                    priority=10
                )
            ],
            priority=70,
            tags={"timeout", "pause"}
        ))
        
        # Rule: Escalate complex debates
        rules.append(DebateRule(
            id="escalate_complex",
            name="Escalate Complex Debates",
            description="Escalate to human review for complex debates with many rounds",
            conditions=[
                RuleCondition(
                    type=RuleConditionType.EQUALS,
                    field="complexity",
                    value="complex"
                ),
                RuleCondition(
                    type=RuleConditionType.GREATER_THAN,
                    field="round_count",
                    value=3
                ),
                RuleCondition(
                    type=RuleConditionType.LESS_THAN,
                    field="consensus_indicators.confidence",
                    value=0.6
                )
            ],
            actions=[
                RuleAction(
                    type=RuleActionType.ESCALATE_TO_HUMAN,
                    parameters={"reason": "complex_without_consensus"},
                    priority=25
                )
            ],
            priority=60,
            tags={"escalation", "complex"}
        ))
        
        return rules
    
    @staticmethod
    def create_template_selection_rules() -> List[DebateRule]:
        """Create rules for template selection based on debate characteristics."""
        rules = []
        
        # Rule: Use simple template for simple questions
        rules.append(DebateRule(
            id="simple_template",
            name="Simple Template Selection",
            description="Use simple debate template for basic questions",
            conditions=[
                RuleCondition(
                    type=RuleConditionType.EQUALS,
                    field="complexity",
                    value="simple"
                )
            ],
            actions=[
                RuleAction(
                    type=RuleActionType.APPLY_TEMPLATE,
                    parameters={"template": "simple_debate"},
                    priority=20
                )
            ],
            priority=50,
            tags={"template", "simple"}
        ))
        
        # Rule: Use complex template for complex questions
        rules.append(DebateRule(
            id="complex_template",
            name="Complex Template Selection",
            description="Use complex debate template for architectural questions",
            conditions=[
                RuleCondition(
                    type=RuleConditionType.EQUALS,
                    field="complexity",
                    value="complex"
                )
            ],
            actions=[
                RuleAction(
                    type=RuleActionType.APPLY_TEMPLATE,
                    parameters={"template": "complex_debate"},
                    priority=20
                )
            ],
            priority=50,
            tags={"template", "complex"}
        ))
        
        return rules
    
    @staticmethod
    def create_all_standard_rules() -> List[DebateRule]:
        """Create all standard rules."""
        rules = []
        rules.extend(StandardRuleFactory.create_basic_orchestration_rules())
        rules.extend(StandardRuleFactory.create_template_selection_rules())
        return rules