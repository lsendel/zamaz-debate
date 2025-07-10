"""
YAML Workflow Definition Loader

This module loads workflow definitions from YAML files and converts them
to WorkflowDefinition objects for use with the orchestration system.
"""

import yaml
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .debate_workflow import (
    WorkflowDefinition,
    WorkflowConfig,
    WorkflowStep,
    StepType
)


class WorkflowYAMLLoader:
    """Loads workflow definitions from YAML files."""
    
    @staticmethod
    def load_workflow_from_file(file_path: Path) -> WorkflowDefinition:
        """Load a workflow definition from a YAML file."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return WorkflowYAMLLoader.load_workflow_from_dict(data)
    
    @staticmethod
    def load_workflow_from_dict(data: Dict) -> WorkflowDefinition:
        """Load a workflow definition from a dictionary."""
        # Parse config
        config_data = data.get('config', {})
        config = WorkflowConfig(
            max_rounds=config_data.get('max_rounds', 5),
            min_rounds=config_data.get('min_rounds', 2),
            consensus_threshold=config_data.get('consensus_threshold', 0.8),
            max_execution_time=WorkflowYAMLLoader._parse_duration(
                config_data.get('max_execution_time', 'PT30M')
            ),
            auto_consensus_check=config_data.get('auto_consensus_check', True),
            allow_dynamic_participants=config_data.get('allow_dynamic_participants', False),
            require_all_participants=config_data.get('require_all_participants', True)
        )
        
        # Parse steps
        steps = []
        for step_data in data.get('steps', []):
            step = WorkflowStep(
                id=step_data['id'],
                type=StepType(step_data['type']),
                name=step_data['name'],
                description=step_data['description'],
                required_participants=step_data.get('required_participants', []),
                conditions=step_data.get('conditions', {}),
                timeout=WorkflowYAMLLoader._parse_duration(step_data.get('timeout')) if step_data.get('timeout') else None,
                max_retries=step_data.get('max_retries', 3)
            )
            steps.append(step)
        
        # Create workflow definition
        return WorkflowDefinition(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            version=data['version'],
            participants=data['participants'],
            steps=steps,
            config=config
        )
    
    @staticmethod
    def load_workflows_from_directory(directory: Path) -> List[WorkflowDefinition]:
        """Load all workflow definitions from a directory."""
        workflows = []
        
        if not directory.exists():
            return workflows
        
        for yaml_file in directory.glob('*.yaml'):
            try:
                workflow = WorkflowYAMLLoader.load_workflow_from_file(yaml_file)
                workflows.append(workflow)
            except Exception as e:
                print(f"Warning: Failed to load workflow from {yaml_file}: {e}")
        
        for yml_file in directory.glob('*.yml'):
            try:
                workflow = WorkflowYAMLLoader.load_workflow_from_file(yml_file)
                workflows.append(workflow)
            except Exception as e:
                print(f"Warning: Failed to load workflow from {yml_file}: {e}")
        
        return workflows
    
    @staticmethod
    def _parse_duration(duration_str: Optional[str]) -> Optional[timedelta]:
        """Parse ISO 8601 duration string to timedelta."""
        if not duration_str:
            return None
        
        # Simple parser for PT format (e.g., PT30M, PT5H, PT1H30M)
        if not duration_str.startswith('PT'):
            return None
        
        duration_str = duration_str[2:]  # Remove 'PT'
        
        hours = 0
        minutes = 0
        seconds = 0
        
        # Parse hours
        if 'H' in duration_str:
            hours_str, duration_str = duration_str.split('H', 1)
            try:
                hours = int(hours_str)
            except ValueError:
                pass
        
        # Parse minutes
        if 'M' in duration_str:
            minutes_str, duration_str = duration_str.split('M', 1)
            try:
                minutes = int(minutes_str)
            except ValueError:
                pass
        
        # Parse seconds
        if 'S' in duration_str:
            seconds_str = duration_str.split('S', 1)[0]
            try:
                seconds = int(seconds_str)
            except ValueError:
                pass
        
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def load_default_workflows() -> List[WorkflowDefinition]:
    """Load default workflow definitions from the definitions directory."""
    definitions_dir = Path(__file__).parent / 'definitions'
    return WorkflowYAMLLoader.load_workflows_from_directory(definitions_dir)


# Example usage and testing
if __name__ == "__main__":
    # Test loading workflows
    workflows = load_default_workflows()
    
    print(f"Loaded {len(workflows)} workflow definitions:")
    for workflow in workflows:
        print(f"  - {workflow.name} (ID: {workflow.id})")
        print(f"    Steps: {len(workflow.steps)}")
        print(f"    Max rounds: {workflow.config.max_rounds}")
        print(f"    Participants: {', '.join(workflow.participants)}")
        print()