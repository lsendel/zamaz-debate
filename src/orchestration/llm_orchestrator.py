"""
LLM Orchestrator for Debate Workflows

This module provides intelligent orchestration using low-cost LLMs like Ollama (local models)
and Grok. It makes orchestration decisions, detects consensus, and selects appropriate
workflows while minimizing API costs.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID

from src.contexts.debate.aggregates import DebateSession
from src.contexts.debate.value_objects import Argument, Consensus
from src.workflows.debate_workflow import WorkflowDefinition

logger = logging.getLogger(__name__)


class OrchestrationDecisionType(Enum):
    """Types of orchestration decisions."""
    CONTINUE = "continue"
    PAUSE = "pause"
    REDIRECT = "redirect"
    COMPLETE = "complete"
    ESCALATE = "escalate"


class ConsensusLevel(Enum):
    """Levels of consensus detection."""
    NONE = "none"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass
class OrchestrationDecision:
    """Decision made by the orchestrator."""
    decision_type: OrchestrationDecisionType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[str] = field(default_factory=list)


@dataclass
class ConsensusResult:
    """Result of consensus detection."""
    level: ConsensusLevel
    confidence: float  # 0.0 to 1.0
    consensus_text: str
    rationale: str
    supporting_evidence: List[str] = field(default_factory=list)
    conflicting_evidence: List[str] = field(default_factory=list)


@dataclass
class WorkflowRecommendation:
    """Recommendation for workflow selection."""
    workflow_id: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    estimated_cost: float
    estimated_duration: int  # minutes
    participants: List[str] = field(default_factory=list)


class LLMOrchestrationClient(ABC):
    """Abstract base class for LLM orchestration clients."""
    
    @abstractmethod
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate a response using the LLM."""
        pass
    
    @abstractmethod
    def get_cost_per_token(self) -> float:
        """Get the cost per token for this LLM."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name."""
        pass


class OllamaClient(LLMOrchestrationClient):
    """Client for Ollama local models."""
    
    def __init__(self, model_name: str = "llama3.3", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.session = None
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate response using Ollama."""
        try:
            import aiohttp
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "")
                else:
                    logger.error(f"Ollama API error: {response.status}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return ""
    
    def get_cost_per_token(self) -> float:
        """Ollama is free for local models."""
        return 0.0
    
    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_name
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()


class GrokClient(LLMOrchestrationClient):
    """Client for Grok API."""
    
    def __init__(self, api_key: str, model_name: str = "grok-1"):
        self.api_key = api_key
        self.model_name = model_name
        self.session = None
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate response using Grok."""
        try:
            import aiohttp
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "model": self.model_name,
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            # Note: Grok API endpoint - adjust when available
            async with self.session.post(
                "https://api.x.ai/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"Grok API error: {response.status}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Error calling Grok: {e}")
            return ""
    
    def get_cost_per_token(self) -> float:
        """Estimated cost per token for Grok."""
        return 0.0001  # Estimated, adjust based on actual pricing
    
    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_name
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()


class MockOrchestrationClient(LLMOrchestrationClient):
    """Mock client for testing."""
    
    def __init__(self, model_name: str = "mock-orchestrator"):
        self.model_name = model_name
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate mock response."""
        if "consensus" in prompt.lower():
            return json.dumps({
                "level": "moderate",
                "confidence": 0.75,
                "consensus_text": "Proceed with implementation",
                "rationale": "Arguments show balanced support with reasonable confidence"
            })
        elif "workflow" in prompt.lower():
            return json.dumps({
                "workflow_id": "complex_debate",
                "confidence": 0.8,
                "reasoning": "Complex architectural question requires thorough analysis",
                "estimated_cost": 0.15,
                "estimated_duration": 10
            })
        else:
            return json.dumps({
                "decision_type": "continue",
                "confidence": 0.8,
                "reasoning": "Debate is progressing well with good arguments from both sides"
            })
    
    def get_cost_per_token(self) -> float:
        return 0.0
    
    def get_model_name(self) -> str:
        return self.model_name


class LLMOrchestrator:
    """Main orchestrator that uses LLMs for intelligent decision-making."""
    
    def __init__(
        self, 
        primary_client: LLMOrchestrationClient,
        fallback_client: Optional[LLMOrchestrationClient] = None
    ):
        self.primary_client = primary_client
        self.fallback_client = fallback_client
        self.prompt_templates = self._load_prompt_templates()
    
    async def make_orchestration_decision(
        self, 
        debate_session: DebateSession,
        context: Dict[str, Any] = None
    ) -> OrchestrationDecision:
        """Make an orchestration decision based on current debate state."""
        logger.info(f"Making orchestration decision for debate {debate_session.id}")
        
        # Prepare context for LLM
        debate_context = self._prepare_debate_context(debate_session, context)
        
        # Generate prompt
        prompt = self.prompt_templates["orchestration_decision"].format(**debate_context)
        
        # Get LLM response
        response = await self._get_llm_response(prompt)
        
        # Parse response
        try:
            decision_data = json.loads(response)
            
            return OrchestrationDecision(
                decision_type=OrchestrationDecisionType(decision_data.get("decision_type", "continue")),
                confidence=float(decision_data.get("confidence", 0.5)),
                reasoning=decision_data.get("reasoning", "No reasoning provided"),
                metadata=decision_data.get("metadata", {}),
                suggested_actions=decision_data.get("suggested_actions", [])
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing orchestration decision: {e}")
            
            # Fallback to default decision
            return OrchestrationDecision(
                decision_type=OrchestrationDecisionType.CONTINUE,
                confidence=0.5,
                reasoning="Unable to parse LLM response, continuing with default",
                metadata={"error": str(e)}
            )
    
    async def detect_consensus(
        self, 
        debate_session: DebateSession,
        arguments: List[Argument]
    ) -> ConsensusResult:
        """Detect consensus from debate arguments."""
        logger.info(f"Detecting consensus for debate {debate_session.id}")
        
        # Prepare arguments for analysis
        arguments_text = self._prepare_arguments_text(arguments)
        
        # Generate prompt
        prompt = self.prompt_templates["consensus_detection"].format(
            topic=debate_session.topic.value,
            arguments=arguments_text,
            participant_count=len(debate_session.participants),
            round_count=len(debate_session.rounds)
        )
        
        # Get LLM response
        response = await self._get_llm_response(prompt)
        
        # Parse response
        try:
            consensus_data = json.loads(response)
            
            return ConsensusResult(
                level=ConsensusLevel(consensus_data.get("level", "none")),
                confidence=float(consensus_data.get("confidence", 0.0)),
                consensus_text=consensus_data.get("consensus_text", "No consensus"),
                rationale=consensus_data.get("rationale", "Unable to determine consensus"),
                supporting_evidence=consensus_data.get("supporting_evidence", []),
                conflicting_evidence=consensus_data.get("conflicting_evidence", [])
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing consensus detection: {e}")
            
            # Fallback to basic consensus detection
            return self._basic_consensus_detection(arguments)
    
    async def select_workflow(
        self, 
        question: str, 
        complexity: str,
        available_workflows: List[WorkflowDefinition]
    ) -> WorkflowRecommendation:
        """Select the most appropriate workflow for a question."""
        logger.info(f"Selecting workflow for question: {question[:50]}...")
        
        # Prepare workflow options
        workflow_options = []
        for workflow in available_workflows:
            workflow_options.append({
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "participants": workflow.participants,
                "max_rounds": workflow.config.max_rounds,
                "consensus_threshold": workflow.config.consensus_threshold
            })
        
        # Generate prompt
        prompt = self.prompt_templates["workflow_selection"].format(
            question=question,
            complexity=complexity,
            workflows=json.dumps(workflow_options, indent=2)
        )
        
        # Get LLM response
        response = await self._get_llm_response(prompt)
        
        # Parse response
        try:
            recommendation_data = json.loads(response)
            
            return WorkflowRecommendation(
                workflow_id=recommendation_data.get("workflow_id", available_workflows[0].id),
                confidence=float(recommendation_data.get("confidence", 0.5)),
                reasoning=recommendation_data.get("reasoning", "Default selection"),
                estimated_cost=float(recommendation_data.get("estimated_cost", 0.1)),
                estimated_duration=int(recommendation_data.get("estimated_duration", 10)),
                participants=recommendation_data.get("participants", [])
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing workflow recommendation: {e}")
            
            # Fallback to default workflow
            return WorkflowRecommendation(
                workflow_id=available_workflows[0].id if available_workflows else "default",
                confidence=0.5,
                reasoning="Unable to parse LLM response, using default workflow",
                estimated_cost=0.1,
                estimated_duration=10
            )
    
    def _prepare_debate_context(self, debate_session: DebateSession, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Prepare debate context for LLM prompts."""
        total_arguments = sum(len(round_obj.arguments) for round_obj in debate_session.rounds)
        
        return {
            "topic": debate_session.topic.value,
            "participants": ", ".join(debate_session.participants),
            "current_round": len(debate_session.rounds),
            "max_rounds": debate_session.max_rounds,
            "total_arguments": total_arguments,
            "consensus_reached": debate_session.consensus is not None,
            "debate_status": debate_session.status.value,
            "additional_context": json.dumps(context or {})
        }
    
    def _prepare_arguments_text(self, arguments: List[Argument]) -> str:
        """Prepare arguments text for analysis."""
        arguments_text = []
        for i, arg in enumerate(arguments, 1):
            arguments_text.append(f"Argument {i} ({arg.participant}):\n{arg.content}\n")
        return "\n".join(arguments_text)
    
    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM with fallback."""
        try:
            response = await self.primary_client.generate_response(prompt)
            if response:
                return response
        except Exception as e:
            logger.warning(f"Primary LLM client failed: {e}")
        
        # Try fallback client
        if self.fallback_client:
            try:
                response = await self.fallback_client.generate_response(prompt)
                if response:
                    return response
            except Exception as e:
                logger.error(f"Fallback LLM client failed: {e}")
        
        # Return empty response if all fail
        return ""
    
    def _basic_consensus_detection(self, arguments: List[Argument]) -> ConsensusResult:
        """Basic consensus detection fallback."""
        if not arguments:
            return ConsensusResult(
                level=ConsensusLevel.NONE,
                confidence=0.0,
                consensus_text="No arguments to analyze",
                rationale="No arguments provided"
            )
        
        # Simple keyword-based analysis
        positive_keywords = ["yes", "should", "recommend", "beneficial", "agree", "support"]
        negative_keywords = ["no", "shouldn't", "avoid", "problematic", "disagree", "oppose"]
        
        positive_count = 0
        negative_count = 0
        
        for arg in arguments:
            content_lower = arg.content.lower()
            if any(keyword in content_lower for keyword in positive_keywords):
                positive_count += 1
            elif any(keyword in content_lower for keyword in negative_keywords):
                negative_count += 1
        
        total_indicators = positive_count + negative_count
        if total_indicators == 0:
            return ConsensusResult(
                level=ConsensusLevel.NONE,
                confidence=0.0,
                consensus_text="No clear position indicators",
                rationale="No clear positive or negative indicators found"
            )
        
        # Determine consensus
        if positive_count > negative_count:
            consensus_text = "Proceed with implementation"
            confidence = positive_count / total_indicators
        elif negative_count > positive_count:
            consensus_text = "Do not proceed"
            confidence = negative_count / total_indicators
        else:
            consensus_text = "No clear consensus"
            confidence = 0.5
        
        # Determine level
        if confidence >= 0.8:
            level = ConsensusLevel.STRONG
        elif confidence >= 0.6:
            level = ConsensusLevel.MODERATE
        elif confidence >= 0.4:
            level = ConsensusLevel.WEAK
        else:
            level = ConsensusLevel.NONE
        
        return ConsensusResult(
            level=level,
            confidence=confidence,
            consensus_text=consensus_text,
            rationale=f"Based on {total_indicators} indicators: {positive_count} positive, {negative_count} negative"
        )
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """Load prompt templates for different orchestration tasks."""
        return {
            "orchestration_decision": """
You are an intelligent debate orchestrator. Analyze the current debate state and make a decision about how to proceed.

Debate Topic: {topic}
Participants: {participants}
Current Round: {current_round}/{max_rounds}
Total Arguments: {total_arguments}
Consensus Reached: {consensus_reached}
Status: {debate_status}
Additional Context: {additional_context}

Based on this information, decide how to proceed with the debate. Consider:
1. Have enough arguments been presented?
2. Is the debate making progress toward consensus?
3. Are participants providing valuable insights?
4. Should the debate continue, pause, redirect, or complete?

Respond with a JSON object containing:
- decision_type: "continue", "pause", "redirect", "complete", or "escalate"
- confidence: float between 0.0 and 1.0
- reasoning: string explaining your decision
- suggested_actions: list of recommended next steps
- metadata: any additional relevant information

Example response:
{{"decision_type": "continue", "confidence": 0.8, "reasoning": "Debate is progressing well with good arguments from both sides", "suggested_actions": ["encourage more specific examples", "ask for implementation details"]}}
""",
            
            "consensus_detection": """
You are an expert at detecting consensus in debates. Analyze the following arguments and determine if consensus has been reached.

Topic: {topic}
Number of Participants: {participant_count}
Number of Rounds: {round_count}

Arguments:
{arguments}

Analyze these arguments and determine:
1. Is there consensus among participants?
2. What is the level of agreement?
3. What is the agreed-upon position?
4. What evidence supports this consensus?
5. What evidence contradicts it?

Respond with a JSON object containing:
- level: "none", "weak", "moderate", or "strong"
- confidence: float between 0.0 and 1.0
- consensus_text: the agreed-upon position
- rationale: explanation of your analysis
- supporting_evidence: list of supporting points
- conflicting_evidence: list of conflicting points

Example response:
{{"level": "moderate", "confidence": 0.75, "consensus_text": "Proceed with implementation using phased approach", "rationale": "Most participants agree on the general direction but have different opinions on implementation details"}}
""",
            
            "workflow_selection": """
You are a workflow selection expert. Choose the most appropriate debate workflow for the given question.

Question: {question}
Complexity: {complexity}

Available Workflows:
{workflows}

Consider:
1. The complexity and scope of the question
2. The number of participants needed
3. The expected duration and cost
4. The type of decision being made
5. The level of consensus required

Respond with a JSON object containing:
- workflow_id: the ID of the recommended workflow
- confidence: float between 0.0 and 1.0
- reasoning: explanation of your choice
- estimated_cost: estimated cost in dollars
- estimated_duration: estimated duration in minutes
- participants: recommended participants for this specific question

Example response:
{{"workflow_id": "complex_debate", "confidence": 0.9, "reasoning": "Complex architectural question requires thorough multi-round analysis", "estimated_cost": 0.15, "estimated_duration": 15, "participants": ["claude-opus-4", "gemini-2.5-pro"]}}
"""
        }


class OrchestrationConfig:
    """Configuration for LLM orchestration."""
    
    def __init__(self):
        self.primary_provider = "ollama"  # "ollama", "grok", "mock"
        self.fallback_provider = "mock"
        self.ollama_model = "llama3.3"
        self.ollama_url = "http://localhost:11434"
        self.grok_api_key = None
        self.grok_model = "grok-1"
        self.max_retries = 3
        self.timeout_seconds = 60
        self.enable_caching = True
        self.cache_ttl_seconds = 3600


class OrchestrationFactory:
    """Factory for creating orchestration components."""
    
    @staticmethod
    def create_orchestrator(config: OrchestrationConfig) -> LLMOrchestrator:
        """Create an orchestrator with configured clients."""
        # Create primary client
        primary_client = OrchestrationFactory._create_client(
            config.primary_provider, config
        )
        
        # Create fallback client
        fallback_client = None
        if config.fallback_provider != config.primary_provider:
            fallback_client = OrchestrationFactory._create_client(
                config.fallback_provider, config
            )
        
        return LLMOrchestrator(primary_client, fallback_client)
    
    @staticmethod
    def _create_client(provider: str, config: OrchestrationConfig) -> LLMOrchestrationClient:
        """Create a client for the specified provider."""
        if provider == "ollama":
            return OllamaClient(config.ollama_model, config.ollama_url)
        elif provider == "grok":
            if not config.grok_api_key:
                raise ValueError("Grok API key required for Grok provider")
            return GrokClient(config.grok_api_key, config.grok_model)
        elif provider == "mock":
            return MockOrchestrationClient()
        else:
            raise ValueError(f"Unknown provider: {provider}")


# Example usage and testing
async def test_orchestration():
    """Test the orchestration system."""
    import os
    
    # Create configuration
    config = OrchestrationConfig()
    config.primary_provider = "mock"  # Use mock for testing
    
    # Create orchestrator
    orchestrator = OrchestrationFactory.create_orchestrator(config)
    
    # Test workflow selection
    from src.workflows.debate_workflow import WorkflowDefinition, WorkflowConfig
    
    workflows = [
        WorkflowDefinition(
            id="simple_debate",
            name="Simple Debate",
            description="Basic two-round debate",
            version="1.0",
            participants=["claude", "gemini"],
            steps=[],
            config=WorkflowConfig(max_rounds=2)
        ),
        WorkflowDefinition(
            id="complex_debate",
            name="Complex Debate",
            description="Multi-round complex debate",
            version="1.0",
            participants=["claude", "gemini", "gpt-4"],
            steps=[],
            config=WorkflowConfig(max_rounds=5)
        )
    ]
    
    recommendation = await orchestrator.select_workflow(
        "Should we implement a microservices architecture?",
        "complex",
        workflows
    )
    
    print(f"Workflow recommendation: {recommendation.workflow_id}")
    print(f"Confidence: {recommendation.confidence}")
    print(f"Reasoning: {recommendation.reasoning}")


if __name__ == "__main__":
    asyncio.run(test_orchestration())