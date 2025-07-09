"""
AI Integration Context - Aggregates
Defines the aggregate roots for AI provider integration
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4


class AIProviderType(Enum):
    """Types of AI providers"""
    CLAUDE = "claude"
    GEMINI = "gemini"
    OPENAI = "openai"


class ConversationStatus(Enum):
    """Status of a conversation session"""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AIProvider:
    """AI Provider aggregate root"""
    id: UUID = field(default_factory=uuid4)
    provider_type: AIProviderType = AIProviderType.CLAUDE
    api_key_configured: bool = False
    is_active: bool = True
    rate_limit: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def activate(self):
        """Activate the AI provider"""
        self.is_active = True
        self.updated_at = datetime.now()
        
    def deactivate(self):
        """Deactivate the AI provider"""
        self.is_active = False
        self.updated_at = datetime.now()
        
    def update_rate_limit(self, rate_limit: int):
        """Update rate limit for the provider"""
        self.rate_limit = rate_limit
        self.updated_at = datetime.now()


@dataclass
class ConversationSession:
    """Conversation session aggregate root"""
    id: UUID = field(default_factory=uuid4)
    provider_id: UUID = field(default_factory=uuid4)
    debate_id: Optional[UUID] = None
    status: ConversationStatus = ConversationStatus.ACTIVE
    messages: List[Dict] = field(default_factory=list)
    token_count: int = 0
    cost_estimate: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def add_message(self, role: str, content: str, tokens: int = 0):
        """Add a message to the conversation"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "tokens": tokens
        })
        self.token_count += tokens
        
    def complete(self):
        """Mark the conversation as completed"""
        self.status = ConversationStatus.COMPLETED
        self.completed_at = datetime.now()
        
    def fail(self, reason: str):
        """Mark the conversation as failed"""
        self.status = ConversationStatus.FAILED
        self.completed_at = datetime.now()
        self.add_message("system", f"Conversation failed: {reason}")
        
    def timeout(self):
        """Mark the conversation as timed out"""
        self.status = ConversationStatus.TIMEOUT
        self.completed_at = datetime.now()
        
    def estimate_cost(self, cost_per_token: float):
        """Estimate the cost of the conversation"""
        self.cost_estimate = self.token_count * cost_per_token