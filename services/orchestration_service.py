"""
Orchestration Service for Zamaz Debate System

This service provides integration between the workflow engine, LLM orchestrator,
and the existing debate system. It manages workflow selection, execution, and
intelligent orchestration decisions.
"""

import asyncio
import logging
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from src.workflows.debate_workflow import (
    WorkflowEngine, 
    WorkflowDefinition, 
    WorkflowConfig, 
    WorkflowStep, 
    StepType,
    WorkflowResult
)
from src.orchestration.llm_orchestrator import (
    LLMOrchestrator,
    OrchestrationConfig,
    OrchestrationFactory,
    WorkflowRecommendation,
    OrchestrationDecision
)
from services.ai_client_factory import AIClientFactory

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """Result of orchestrated debate execution."""
    workflow_result: WorkflowResult
    orchestration_decisions: List[OrchestrationDecision]
    total_cost: float
    execution_summary: Dict[str, Any]


class OrchestrationService:
    """Main service for orchestrating debates with intelligent workflow management."""
    
    def __init__(self, ai_client_factory: Optional[AIClientFactory] = None):
        self.ai_client_factory = ai_client_factory or AIClientFactory()
        
        # Initialize components
        self.workflow_engine = WorkflowEngine()
        self.orchestrator = self._create_orchestrator()
        self.workflow_definitions = {}
        
        # Load workflow definitions
        self._load_workflow_definitions()
        
        # Configuration
        self.config = {
            "enable_intelligent_orchestration": True,
            "enable_cost_optimization": True,
            "max_workflow_execution_time": 1800,  # 30 minutes
            "fallback_to_simple_debate": True,
            "enable_workflow_caching": True
        }
        
        logger.info("OrchestrationService initialized")
    
    async def orchestrate_debate(
        self, 
        question: str, 
        context: str = "",
        complexity: str = "moderate",
        preferred_workflow: Optional[str] = None
    ) -> OrchestrationResult:
        """Orchestrate a complete debate using intelligent workflow selection."""
        logger.info(f"Starting orchestrated debate: {question[:50]}...")
        
        start_time = datetime.now()
        orchestration_decisions = []
        total_cost = 0.0
        
        try:
            # Step 1: Select appropriate workflow
            if preferred_workflow:
                workflow_id = preferred_workflow
                logger.info(f"Using preferred workflow: {workflow_id}")
            else:
                workflow_recommendation = await self._select_workflow(question, complexity)
                workflow_id = workflow_recommendation.workflow_id
                total_cost += workflow_recommendation.estimated_cost
                
                logger.info(f"Selected workflow: {workflow_id} (confidence: {workflow_recommendation.confidence:.2f})")
            
            # Step 2: Execute workflow with intelligent orchestration
            workflow_result = await self._execute_workflow_with_orchestration(
                workflow_id, question, complexity, orchestration_decisions
            )
            
            # Step 3: Calculate final costs and summary
            execution_time = (datetime.now() - start_time).total_seconds()
            
            execution_summary = {
                "workflow_id": workflow_id,
                "execution_time_seconds": execution_time,
                "steps_completed": workflow_result.steps_completed,
                "total_steps": workflow_result.total_steps,
                "consensus_reached": workflow_result.consensus is not None,
                "orchestration_decisions_count": len(orchestration_decisions),
                "final_state": workflow_result.state.value
            }
            
            # Update total cost with actual execution cost
            total_cost += self._calculate_execution_cost(workflow_result, orchestration_decisions)
            
            logger.info(f"Debate orchestration completed in {execution_time:.1f}s with cost ${total_cost:.4f}")
            
            return OrchestrationResult(
                workflow_result=workflow_result,
                orchestration_decisions=orchestration_decisions,
                total_cost=total_cost,
                execution_summary=execution_summary
            )
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            
            # Fallback to simple debate if enabled
            if self.config["fallback_to_simple_debate"]:
                logger.info("Falling back to simple debate execution")
                return await self._fallback_execution(question, context, complexity)
            else:
                raise
    
    async def _select_workflow(self, question: str, complexity: str) -> WorkflowRecommendation:
        """Select the most appropriate workflow for the question."""
        if not self.config["enable_intelligent_orchestration"]:
            # Default selection based on complexity
            if complexity in ["complex", "high"]:
                return WorkflowRecommendation(
                    workflow_id="complex_debate",
                    confidence=0.8,
                    reasoning="Complex question requires thorough analysis",
                    estimated_cost=0.25,
                    estimated_duration=20
                )
            else:
                return WorkflowRecommendation(
                    workflow_id="simple_debate",
                    confidence=0.8,
                    reasoning="Simple question can use basic workflow",
                    estimated_cost=0.05,
                    estimated_duration=8
                )
        
        # Use LLM orchestrator for intelligent selection
        available_workflows = list(self.workflow_definitions.values())
        return await self.orchestrator.select_workflow(question, complexity, available_workflows)
    
    async def _execute_workflow_with_orchestration(
        self, 
        workflow_id: str, 
        question: str, 
        complexity: str,
        orchestration_decisions: List[OrchestrationDecision]
    ) -> WorkflowResult:
        """Execute workflow with intelligent orchestration decisions."""
        
        # Create and start workflow
        workflow = await self.workflow_engine.create_workflow(
            workflow_id,
            ai_client_factory=self.ai_client_factory,
            orchestrator=self.orchestrator if self.config["enable_intelligent_orchestration"] else None
        )
        
        # Execute workflow
        # Note: In a more advanced implementation, we would intercept workflow execution
        # to make orchestration decisions during execution. For now, we'll execute
        # the complete workflow and let the orchestrator handle decisions within steps.
        
        result = await workflow.execute(question, complexity)
        
        return result
    
    def _calculate_execution_cost(
        self, 
        workflow_result: WorkflowResult, 
        orchestration_decisions: List[OrchestrationDecision]
    ) -> float:
        """Calculate the cost of workflow execution."""
        base_cost = 0.0
        
        # Estimate cost based on workflow steps and complexity
        if workflow_result.total_steps <= 3:
            base_cost = 0.05  # Simple workflow
        elif workflow_result.total_steps <= 6:
            base_cost = 0.15  # Medium workflow
        else:
            base_cost = 0.25  # Complex workflow
        
        # Add orchestration decisions cost (very low with local LLMs)
        orchestration_cost = len(orchestration_decisions) * 0.001  # $0.001 per decision
        
        # Apply cost optimization if enabled
        if self.config["enable_cost_optimization"]:
            # Reduce cost by using low-cost LLMs for orchestration
            base_cost *= 0.7  # 30% cost reduction
        
        return base_cost + orchestration_cost
    
    async def _fallback_execution(self, question: str, context: str, complexity: str) -> OrchestrationResult:
        """Fallback to simple execution if orchestration fails."""
        logger.info("Executing fallback simple debate")
        
        try:
            # Use simple debate workflow
            workflow_result = await self.workflow_engine.execute_workflow(
                "simple_debate",
                question,
                complexity,
                ai_client_factory=self.ai_client_factory
            )
            
            return OrchestrationResult(
                workflow_result=workflow_result,
                orchestration_decisions=[],
                total_cost=0.05,  # Fixed simple cost
                execution_summary={
                    "workflow_id": "simple_debate",
                    "fallback_execution": True,
                    "execution_time_seconds": 300,  # Estimated
                    "final_state": workflow_result.state.value
                }
            )
            
        except Exception as e:
            logger.error(f"Fallback execution also failed: {e}")
            raise
    
    def _create_orchestrator(self) -> LLMOrchestrator:
        """Create and configure the LLM orchestrator."""
        config = OrchestrationConfig()
        
        # Configure based on environment
        if os.getenv("USE_OLLAMA_ORCHESTRATION", "false").lower() == "true":
            config.primary_provider = "ollama"
            config.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.3")
            config.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        elif os.getenv("GROK_API_KEY"):
            config.primary_provider = "grok"
            config.grok_api_key = os.getenv("GROK_API_KEY")
            config.grok_model = os.getenv("GROK_MODEL", "grok-1")
        else:
            config.primary_provider = "mock"
            logger.info("Using mock orchestrator (set USE_OLLAMA_ORCHESTRATION=true or GROK_API_KEY for real LLM)")
        
        config.fallback_provider = "mock"
        
        return OrchestrationFactory.create_orchestrator(config)
    
    def _load_workflow_definitions(self) -> None:
        """Load workflow definitions from YAML files."""
        definitions_dir = Path(__file__).parent.parent / "src" / "workflows" / "definitions"
        
        if not definitions_dir.exists():
            logger.warning(f"Workflow definitions directory not found: {definitions_dir}")
            self._create_default_workflows()
            return
        
        # Load YAML workflow definitions
        for yaml_file in definitions_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    yaml_data = yaml.safe_load(f)
                
                workflow_def = self._parse_yaml_workflow(yaml_data)
                self.workflow_definitions[workflow_def.id] = workflow_def
                self.workflow_engine.register_workflow_definition(workflow_def)
                
                logger.info(f"Loaded workflow definition: {workflow_def.name}")
                
            except Exception as e:
                logger.error(f"Error loading workflow definition {yaml_file}: {e}")
        
        # Create default workflows if none loaded
        if not self.workflow_definitions:
            self._create_default_workflows()
    
    def _parse_yaml_workflow(self, yaml_data: Dict[str, Any]) -> WorkflowDefinition:
        """Parse YAML workflow definition into WorkflowDefinition object."""
        # Parse configuration
        config_data = yaml_data.get("config", {})
        config = WorkflowConfig(
            max_rounds=config_data.get("max_rounds", 3),
            min_rounds=config_data.get("min_rounds", 2),
            consensus_threshold=config_data.get("consensus_threshold", 0.8),
            auto_consensus_check=config_data.get("auto_consensus_check", True),
            allow_dynamic_participants=config_data.get("allow_dynamic_participants", False),
            require_all_participants=config_data.get("require_all_participants", True)
        )
        
        # Parse steps
        steps = []
        for step_data in yaml_data.get("steps", []):
            step = WorkflowStep(
                id=step_data["id"],
                type=StepType(step_data["type"]),
                name=step_data["name"],
                description=step_data["description"],
                required_participants=step_data.get("required_participants", []),
                conditions=step_data.get("conditions", {}),
                max_retries=step_data.get("max_retries", 3)
            )
            steps.append(step)
        
        return WorkflowDefinition(
            id=yaml_data["id"],
            name=yaml_data["name"],
            description=yaml_data["description"],
            version=yaml_data.get("version", "1.0"),
            participants=yaml_data.get("participants", []),
            steps=steps,
            config=config
        )
    
    def _create_default_workflows(self) -> None:
        """Create default workflow definitions if none are loaded."""
        logger.info("Creating default workflow definitions")
        
        # Simple debate workflow
        simple_config = WorkflowConfig(max_rounds=2, min_rounds=1, consensus_threshold=0.7)
        simple_steps = [
            WorkflowStep(
                id="initial_arguments",
                type=StepType.INITIAL_ARGUMENTS,
                name="Initial Arguments",
                description="Present initial arguments",
                required_participants=["claude-sonnet-4", "gemini-2.5-pro"]
            ),
            WorkflowStep(
                id="consensus_check",
                type=StepType.CONSENSUS_CHECK,
                name="Consensus Check",
                description="Check for consensus",
                conditions={"threshold": 0.7}
            )
        ]
        
        simple_workflow = WorkflowDefinition(
            id="simple_debate",
            name="Simple Debate",
            description="Basic two-round debate",
            version="1.0",
            participants=["claude-sonnet-4", "gemini-2.5-pro"],
            steps=simple_steps,
            config=simple_config
        )
        
        # Complex debate workflow
        complex_config = WorkflowConfig(max_rounds=5, min_rounds=3, consensus_threshold=0.8)
        complex_steps = [
            WorkflowStep(
                id="initial_arguments",
                type=StepType.INITIAL_ARGUMENTS,
                name="Initial Arguments",
                description="Present detailed initial arguments",
                required_participants=["claude-sonnet-4", "gemini-2.5-pro"]
            ),
            WorkflowStep(
                id="counter_arguments",
                type=StepType.COUNTER_ARGUMENTS,
                name="Counter Arguments",
                description="Present counter arguments",
                required_participants=["claude-sonnet-4", "gemini-2.5-pro"]
            ),
            WorkflowStep(
                id="consensus_check",
                type=StepType.CONSENSUS_CHECK,
                name="Consensus Check",
                description="Check for consensus",
                conditions={"threshold": 0.8}
            )
        ]
        
        complex_workflow = WorkflowDefinition(
            id="complex_debate",
            name="Complex Debate",
            description="Multi-round complex debate",
            version="1.0",
            participants=["claude-sonnet-4", "gemini-2.5-pro"],
            steps=complex_steps,
            config=complex_config
        )
        
        # Register workflows
        self.workflow_definitions["simple_debate"] = simple_workflow
        self.workflow_definitions["complex_debate"] = complex_workflow
        self.workflow_engine.register_workflow_definition(simple_workflow)
        self.workflow_engine.register_workflow_definition(complex_workflow)
    
    def get_available_workflows(self) -> List[WorkflowDefinition]:
        """Get list of available workflow definitions."""
        return list(self.workflow_definitions.values())
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """Get orchestration service statistics."""
        return {
            "available_workflows": len(self.workflow_definitions),
            "active_workflows": len(self.workflow_engine.list_active_workflows()),
            "intelligent_orchestration_enabled": self.config["enable_intelligent_orchestration"],
            "cost_optimization_enabled": self.config["enable_cost_optimization"],
            "orchestrator_model": self.orchestrator.primary_client.get_model_name(),
            "workflow_definitions": [
                {
                    "id": wf.id,
                    "name": wf.name,
                    "max_rounds": wf.config.max_rounds,
                    "participants": len(wf.participants)
                }
                for wf in self.workflow_definitions.values()
            ]
        }
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause an active workflow."""
        # Find workflow by any means (this is simplified)
        for workflow in self.workflow_engine.list_active_workflows():
            if str(workflow.id) == workflow_id:
                await workflow.pause()
                return True
        return False
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        for workflow in self.workflow_engine.list_active_workflows():
            if str(workflow.id) == workflow_id:
                await workflow.resume()
                return True
        return False
    
    async def abort_workflow(self, workflow_id: str) -> bool:
        """Abort an active workflow."""
        for workflow in self.workflow_engine.list_active_workflows():
            if str(workflow.id) == workflow_id:
                await workflow.abort()
                return True
        return False


# Integration function for existing DebateNucleus
async def create_orchestrated_debate_result(
    orchestration_result: OrchestrationResult,
    debate_id: str
) -> Dict[str, Any]:
    """Convert orchestration result to format expected by existing system."""
    workflow_result = orchestration_result.workflow_result
    
    # Build decision text from workflow result
    decision_parts = []
    
    if workflow_result.consensus:
        decision_parts.append(f"Consensus Reached: {workflow_result.consensus.value}")
        decision_parts.append(f"Confidence: {workflow_result.consensus.confidence:.2f}")
        decision_parts.append(f"Rationale: {workflow_result.consensus.rationale}")
    
    if workflow_result.decision:
        decision_parts.append(f"Final Decision: {workflow_result.decision.recommendation}")
    
    # Add orchestration summary
    if orchestration_result.orchestration_decisions:
        decision_parts.append("\nOrchestration Summary:")
        for i, decision in enumerate(orchestration_result.orchestration_decisions, 1):
            decision_parts.append(f"{i}. {decision.decision_type.value}: {decision.reasoning}")
    
    decision_text = "\n\n".join(decision_parts) if decision_parts else "Workflow completed"
    
    # Format result for existing system
    return {
        "decision": decision_text,
        "method": "orchestrated_workflow",
        "rounds": workflow_result.metadata.get("rounds_executed", 0),
        "complexity": "complex" if workflow_result.total_steps > 3 else "moderate",
        "debate_id": debate_id,
        "time": datetime.now().isoformat(),
        "workflow_id": workflow_result.metadata.get("definition_id"),
        "orchestration_cost": orchestration_result.total_cost,
        "execution_summary": orchestration_result.execution_summary
    }


# Example usage
async def test_orchestration_service():
    """Test the orchestration service."""
    service = OrchestrationService()
    
    # Test workflow selection and execution
    result = await service.orchestrate_debate(
        "Should we implement a microservices architecture for our application?",
        "We currently have a monolithic application with performance issues",
        "complex"
    )
    
    print(f"Workflow executed: {result.execution_summary['workflow_id']}")
    print(f"Final state: {result.execution_summary['final_state']}")
    print(f"Total cost: ${result.total_cost:.4f}")
    print(f"Consensus reached: {result.execution_summary['consensus_reached']}")
    
    # Get service stats
    stats = service.get_workflow_stats()
    print(f"Available workflows: {stats['available_workflows']}")
    print(f"Orchestration enabled: {stats['intelligent_orchestration_enabled']}")


if __name__ == "__main__":
    asyncio.run(test_orchestration_service())