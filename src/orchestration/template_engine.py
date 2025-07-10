"""
Template Engine for Debate Orchestration

This module provides a flexible template system for defining and composing debate workflows,
building on the existing workflow definitions while adding dynamic composition capabilities.
"""

import json
import logging
import yaml
from dataclasses import dataclass, field, asdict
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

from src.workflows.debate_workflow import WorkflowDefinition, WorkflowConfig, WorkflowStep, StepType

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Types of debate templates."""
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"
    CUSTOM = "custom"


class ParticipantRole(Enum):
    """Roles that participants can play in debates."""
    PROPOSER = "proposer"  # Argues for the proposal
    OPPONENT = "opponent"  # Argues against the proposal
    MODERATOR = "moderator"  # Guides the debate
    REVIEWER = "reviewer"  # Reviews and provides feedback
    OBSERVER = "observer"  # Observes without participating


@dataclass
class ParticipantConfig:
    """Configuration for a debate participant."""
    id: str
    name: str
    role: ParticipantRole
    ai_model: str  # e.g., "claude-sonnet-4", "gemini-2.5-pro"
    prompt_template: Optional[str] = None
    max_argument_length: int = 1000
    min_argument_length: int = 100
    expertise_areas: Set[str] = field(default_factory=set)
    personality_traits: Dict[str, Any] = field(default_factory=dict)
    
    def get_prompt_variables(self) -> Dict[str, Any]:
        """Get variables for prompt templating."""
        return {
            'role': self.role.value,
            'expertise_areas': list(self.expertise_areas),
            'personality_traits': self.personality_traits,
            'max_length': self.max_argument_length,
            'min_length': self.min_argument_length
        }


@dataclass
class TemplateMetadata:
    """Metadata for debate templates."""
    name: str
    description: str
    version: str
    author: str = "system"
    created_at: str = ""
    updated_at: str = ""
    tags: Set[str] = field(default_factory=set)
    use_cases: List[str] = field(default_factory=list)
    estimated_duration_minutes: int = 15
    estimated_cost_usd: float = 0.1
    complexity_level: int = 1  # 1-5 scale
    min_participants: int = 2
    max_participants: int = 4


@dataclass
class DebateTemplate:
    """A complete debate template."""
    id: str
    type: TemplateType
    metadata: TemplateMetadata
    participants: List[ParticipantConfig]
    workflow_config: WorkflowConfig
    steps: List[WorkflowStep]
    rules: List[str] = field(default_factory=list)  # Rule IDs to apply
    custom_variables: Dict[str, Any] = field(default_factory=dict)
    
    def to_workflow_definition(self) -> WorkflowDefinition:
        """Convert template to workflow definition."""
        return WorkflowDefinition(
            id=self.id,
            name=self.metadata.name,
            description=self.metadata.description,
            version=self.metadata.version,
            participants=[p.id for p in self.participants],
            steps=self.steps,
            config=self.workflow_config
        )
    
    def get_participant_by_role(self, role: ParticipantRole) -> Optional[ParticipantConfig]:
        """Get participant by role."""
        for participant in self.participants:
            if participant.role == role:
                return participant
        return None
    
    def get_participants_by_model(self, model: str) -> List[ParticipantConfig]:
        """Get participants using a specific AI model."""
        return [p for p in self.participants if p.ai_model == model]


class TemplateComposer:
    """Composes templates from building blocks and parameters."""
    
    def __init__(self):
        self.step_library: Dict[str, WorkflowStep] = {}
        self.participant_library: Dict[str, ParticipantConfig] = {}
        self.template_fragments: Dict[str, Dict[str, Any]] = {}
        self._load_standard_components()
    
    def _load_standard_components(self):
        """Load standard step and participant components."""
        # Standard workflow steps
        self.step_library.update({
            "opening_arguments": WorkflowStep(
                id="opening_arguments",
                type=StepType.INITIAL_ARGUMENTS,
                name="Opening Arguments",
                description="Each participant presents their opening argument",
                timeout=timedelta(minutes=5),
                max_retries=2
            ),
            
            "counter_arguments": WorkflowStep(
                id="counter_arguments", 
                type=StepType.COUNTER_ARGUMENTS,
                name="Counter Arguments",
                description="Participants respond to each other's arguments",
                timeout=timedelta(minutes=4),
                max_retries=2
            ),
            
            "clarification_round": WorkflowStep(
                id="clarification_round",
                type=StepType.CLARIFICATION,
                name="Clarification Round",
                description="Participants clarify their positions and address questions",
                timeout=timedelta(minutes=3),
                max_retries=1
            ),
            
            "consensus_check": WorkflowStep(
                id="consensus_check",
                type=StepType.CONSENSUS_CHECK,
                name="Consensus Check",
                description="Evaluate if consensus has been reached",
                timeout=timedelta(minutes=1),
                max_retries=1,
                conditions={"threshold": 0.8}
            ),
            
            "final_decision": WorkflowStep(
                id="final_decision",
                type=StepType.FINAL_DECISION,
                name="Final Decision",
                description="Make final decision based on debate",
                timeout=timedelta(minutes=2),
                max_retries=1
            )
        })
        
        # Standard participant configurations
        self.participant_library.update({
            "claude_proposer": ParticipantConfig(
                id="claude_proposer",
                name="Claude (Proposer)",
                role=ParticipantRole.PROPOSER,
                ai_model="claude-sonnet-4",
                expertise_areas={"architecture", "design", "analysis"},
                personality_traits={"analytical": 0.9, "thorough": 0.8}
            ),
            
            "gemini_opponent": ParticipantConfig(
                id="gemini_opponent",
                name="Gemini (Opponent)",
                role=ParticipantRole.OPPONENT,
                ai_model="gemini-2.5-pro",
                expertise_areas={"critique", "risk_analysis", "alternatives"},
                personality_traits={"skeptical": 0.9, "detail_oriented": 0.8}
            ),
            
            "claude_reviewer": ParticipantConfig(
                id="claude_reviewer",
                name="Claude (Reviewer)",
                role=ParticipantRole.REVIEWER,
                ai_model="claude-sonnet-4",
                expertise_areas={"evaluation", "synthesis", "decision_making"},
                personality_traits={"balanced": 0.9, "objective": 0.8}
            )
        })
    
    def compose_simple_template(
        self,
        template_id: str,
        question_complexity: str = "simple",
        participants: Optional[List[str]] = None
    ) -> DebateTemplate:
        """Compose a simple debate template."""
        participants = participants or ["claude_proposer", "gemini_opponent"]
        
        metadata = TemplateMetadata(
            name="Simple Debate",
            description="Quick two-round debate for straightforward decisions",
            version="1.0",
            tags={"simple", "fast", "basic"},
            use_cases=["feature decisions", "configuration choices", "tool selection"],
            estimated_duration_minutes=8,
            estimated_cost_usd=0.05,
            complexity_level=1
        )
        
        config = WorkflowConfig(
            max_rounds=2,
            min_rounds=1,
            consensus_threshold=0.7,
            max_execution_time=timedelta(minutes=10),
            auto_consensus_check=True
        )
        
        steps = [
            self.step_library["opening_arguments"],
            self.step_library["consensus_check"],
            self.step_library["final_decision"]
        ]
        
        template_participants = [
            self.participant_library[pid] for pid in participants
            if pid in self.participant_library
        ]
        
        return DebateTemplate(
            id=template_id,
            type=TemplateType.SIMPLE,
            metadata=metadata,
            participants=template_participants,
            workflow_config=config,
            steps=steps,
            rules=["start_new_round", "complete_on_consensus", "complete_max_rounds"]
        )
    
    def compose_standard_template(
        self,
        template_id: str,
        question_complexity: str = "moderate",
        participants: Optional[List[str]] = None
    ) -> DebateTemplate:
        """Compose a standard debate template."""
        participants = participants or ["claude_proposer", "gemini_opponent"]
        
        metadata = TemplateMetadata(
            name="Standard Debate",
            description="Comprehensive debate with multiple rounds and clarification",
            version="1.0",
            tags={"standard", "comprehensive", "balanced"},
            use_cases=["architectural decisions", "process improvements", "technology choices"],
            estimated_duration_minutes=15,
            estimated_cost_usd=0.12,
            complexity_level=3
        )
        
        config = WorkflowConfig(
            max_rounds=3,
            min_rounds=2,
            consensus_threshold=0.75,
            max_execution_time=timedelta(minutes=20),
            auto_consensus_check=True
        )
        
        steps = [
            self.step_library["opening_arguments"],
            self.step_library["counter_arguments"],
            self.step_library["clarification_round"],
            self.step_library["consensus_check"],
            self.step_library["final_decision"]
        ]
        
        template_participants = [
            self.participant_library[pid] for pid in participants
            if pid in self.participant_library
        ]
        
        return DebateTemplate(
            id=template_id,
            type=TemplateType.STANDARD,
            metadata=metadata,
            participants=template_participants,
            workflow_config=config,
            steps=steps,
            rules=["start_new_round", "complete_on_consensus", "complete_max_rounds", "pause_idle"]
        )
    
    def compose_complex_template(
        self,
        template_id: str,
        question_complexity: str = "complex",
        participants: Optional[List[str]] = None
    ) -> DebateTemplate:
        """Compose a complex debate template."""
        participants = participants or ["claude_proposer", "gemini_opponent", "claude_reviewer"]
        
        metadata = TemplateMetadata(
            name="Complex Debate",
            description="Multi-round debate with reviewer and extensive analysis",
            version="1.0",
            tags={"complex", "thorough", "multi_participant"},
            use_cases=["system architecture", "major changes", "strategic decisions"],
            estimated_duration_minutes=25,
            estimated_cost_usd=0.25,
            complexity_level=5
        )
        
        config = WorkflowConfig(
            max_rounds=5,
            min_rounds=3,
            consensus_threshold=0.8,
            max_execution_time=timedelta(minutes=30),
            auto_consensus_check=True,
            allow_dynamic_participants=True
        )
        
        steps = [
            self.step_library["opening_arguments"],
            self.step_library["counter_arguments"],
            self.step_library["clarification_round"],
            self.step_library["counter_arguments"],  # Second round
            self.step_library["consensus_check"],
            self.step_library["final_decision"]
        ]
        
        template_participants = [
            self.participant_library[pid] for pid in participants
            if pid in self.participant_library
        ]
        
        return DebateTemplate(
            id=template_id,
            type=TemplateType.COMPLEX,
            metadata=metadata,
            participants=template_participants,
            workflow_config=config,
            steps=steps,
            rules=["start_new_round", "complete_on_consensus", "complete_max_rounds", "pause_idle", "escalate_complex"]
        )
    
    def compose_custom_template(
        self,
        template_id: str,
        metadata: TemplateMetadata,
        participants: List[str],
        step_sequence: List[str],
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> DebateTemplate:
        """Compose a custom template from specified components."""
        config = WorkflowConfig()
        
        # Apply config overrides
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # Build steps from sequence
        steps = []
        for step_id in step_sequence:
            if step_id in self.step_library:
                steps.append(self.step_library[step_id])
            else:
                logger.warning(f"Step {step_id} not found in library")
        
        # Build participants
        template_participants = []
        for pid in participants:
            if pid in self.participant_library:
                template_participants.append(self.participant_library[pid])
            else:
                logger.warning(f"Participant {pid} not found in library")
        
        return DebateTemplate(
            id=template_id,
            type=TemplateType.CUSTOM,
            metadata=metadata,
            participants=template_participants,
            workflow_config=config,
            steps=steps
        )
    
    def add_step_to_library(self, step: WorkflowStep):
        """Add a custom step to the library."""
        self.step_library[step.id] = step
        logger.info(f"Added step {step.id} to library")
    
    def add_participant_to_library(self, participant: ParticipantConfig):
        """Add a custom participant to the library."""
        self.participant_library[participant.id] = participant
        logger.info(f"Added participant {participant.id} to library")


class TemplateRegistry:
    """Registry for managing debate templates."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/templates")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.templates: Dict[str, DebateTemplate] = {}
        self.composer = TemplateComposer()
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default templates."""
        # Create default templates using composer
        templates = [
            self.composer.compose_simple_template("simple_debate"),
            self.composer.compose_standard_template("standard_debate"),
            self.composer.compose_complex_template("complex_debate")
        ]
        
        for template in templates:
            self.templates[template.id] = template
        
        logger.info(f"Loaded {len(templates)} default templates")
    
    def register_template(self, template: DebateTemplate, save_to_disk: bool = True):
        """Register a template in the registry."""
        self.templates[template.id] = template
        
        if save_to_disk:
            self.save_template(template)
        
        logger.info(f"Registered template: {template.metadata.name}")
    
    def get_template(self, template_id: str) -> Optional[DebateTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)
    
    def list_templates(self, template_type: Optional[TemplateType] = None) -> List[DebateTemplate]:
        """List templates, optionally filtered by type."""
        templates = list(self.templates.values())
        
        if template_type:
            templates = [t for t in templates if t.type == template_type]
        
        return sorted(templates, key=lambda t: t.metadata.name)
    
    def find_templates_by_criteria(
        self,
        complexity: Optional[str] = None,
        max_duration: Optional[int] = None,
        max_cost: Optional[float] = None,
        tags: Optional[Set[str]] = None
    ) -> List[DebateTemplate]:
        """Find templates matching specific criteria."""
        results = []
        
        for template in self.templates.values():
            # Check complexity
            if complexity:
                complexity_map = {"simple": 1, "moderate": 3, "complex": 5}
                target_level = complexity_map.get(complexity, 3)
                if template.metadata.complexity_level > target_level + 1:
                    continue
            
            # Check duration
            if max_duration and template.metadata.estimated_duration_minutes > max_duration:
                continue
            
            # Check cost
            if max_cost and template.metadata.estimated_cost_usd > max_cost:
                continue
            
            # Check tags
            if tags and not tags.intersection(template.metadata.tags):
                continue
            
            results.append(template)
        
        return sorted(results, key=lambda t: (t.metadata.complexity_level, t.metadata.estimated_duration_minutes))
    
    def save_template(self, template: DebateTemplate):
        """Save template to disk."""
        template_file = self.storage_path / f"{template.id}.json"
        
        # Convert to serializable format
        template_data = {
            'id': template.id,
            'type': template.type.value,
            'metadata': asdict(template.metadata),
            'participants': [asdict(p) for p in template.participants],
            'workflow_config': asdict(template.workflow_config),
            'steps': [asdict(step) for step in template.steps],
            'rules': template.rules,
            'custom_variables': template.custom_variables
        }
        
        with open(template_file, 'w') as f:
            json.dump(template_data, f, indent=2, default=str)
        
        logger.info(f"Saved template {template.id} to {template_file}")
    
    def load_template_from_file(self, file_path: Path) -> Optional[DebateTemplate]:
        """Load template from file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Reconstruct template
            metadata = TemplateMetadata(**data['metadata'])
            participants = [ParticipantConfig(**p) for p in data['participants']]
            config = WorkflowConfig(**data['workflow_config'])
            steps = [WorkflowStep(**step) for step in data['steps']]
            
            template = DebateTemplate(
                id=data['id'],
                type=TemplateType(data['type']),
                metadata=metadata,
                participants=participants,
                workflow_config=config,
                steps=steps,
                rules=data.get('rules', []),
                custom_variables=data.get('custom_variables', {})
            )
            
            return template
            
        except Exception as e:
            logger.error(f"Error loading template from {file_path}: {e}")
            return None
    
    def load_templates_from_directory(self, directory: Path):
        """Load all templates from a directory."""
        if not directory.exists():
            logger.warning(f"Template directory {directory} does not exist")
            return
        
        for template_file in directory.glob("*.json"):
            template = self.load_template_from_file(template_file)
            if template:
                self.templates[template.id] = template
        
        logger.info(f"Loaded templates from {directory}")
    
    def create_template_from_yaml(self, yaml_file: Path) -> Optional[DebateTemplate]:
        """Create template from YAML definition (similar to existing workflow definitions)."""
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            # Convert YAML data to template
            metadata = TemplateMetadata(
                name=data.get('name', 'Unnamed Template'),
                description=data.get('description', ''),
                version=data.get('version', '1.0'),
                tags=set(data.get('metadata', {}).get('tags', [])),
                use_cases=data.get('metadata', {}).get('use_cases', []),
                estimated_duration_minutes=data.get('metadata', {}).get('estimated_duration', 15),
                estimated_cost_usd=data.get('metadata', {}).get('estimated_cost', 0.1)
            )
            
            # Use composer to create template based on data
            if 'simple' in data.get('name', '').lower():
                template = self.composer.compose_simple_template(data['id'])
            elif 'complex' in data.get('name', '').lower():
                template = self.composer.compose_complex_template(data['id'])
            else:
                template = self.composer.compose_standard_template(data['id'])
            
            # Override with YAML metadata
            template.metadata = metadata
            
            return template
            
        except Exception as e:
            logger.error(f"Error creating template from YAML {yaml_file}: {e}")
            return None
    
    def get_template_stats(self) -> Dict[str, Any]:
        """Get statistics about registered templates."""
        total = len(self.templates)
        by_type = {}
        by_complexity = {}
        
        for template in self.templates.values():
            # Count by type
            type_name = template.type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
            
            # Count by complexity
            complexity = template.metadata.complexity_level
            by_complexity[complexity] = by_complexity.get(complexity, 0) + 1
        
        return {
            'total_templates': total,
            'by_type': by_type,
            'by_complexity': by_complexity,
            'avg_duration': sum(t.metadata.estimated_duration_minutes for t in self.templates.values()) / max(total, 1),
            'avg_cost': sum(t.metadata.estimated_cost_usd for t in self.templates.values()) / max(total, 1)
        }


# Global template registry instance
_template_registry: Optional[TemplateRegistry] = None


def get_template_registry() -> TemplateRegistry:
    """Get the global template registry."""
    global _template_registry
    if _template_registry is None:
        _template_registry = TemplateRegistry()
    return _template_registry


def initialize_template_registry(storage_path: Optional[Path] = None) -> TemplateRegistry:
    """Initialize the global template registry."""
    global _template_registry
    _template_registry = TemplateRegistry(storage_path)
    return _template_registry