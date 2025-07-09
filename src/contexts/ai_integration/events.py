"""
AI Integration Context - Events
Domain events for AI integration
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass
class AIResponseReceived:
    """Event raised when an AI response is received"""
    event_id: UUID = None
    session_id: UUID = None
    provider_type: str = ""
    prompt: str = ""
    response: str = ""
    tokens_used: int = 0
    response_time_ms: int = 0
    occurred_at: datetime = None
    
    def __post_init__(self):
        if self.event_id is None:
            self.event_id = uuid4()
        if self.occurred_at is None:
            self.occurred_at = datetime.now()
    
    @property
    def event_type(self) -> str:
        return "AIResponseReceived"
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "session_id": str(self.session_id),
            "provider_type": self.provider_type,
            "prompt": self.prompt,
            "response": self.response,
            "tokens_used": self.tokens_used,
            "response_time_ms": self.response_time_ms,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass
class ConversationStarted:
    """Event raised when a new conversation is started"""
    event_id: UUID = None
    session_id: UUID = None
    provider_type: str = ""
    debate_id: Optional[UUID] = None
    occurred_at: datetime = None
    
    def __post_init__(self):
        if self.event_id is None:
            self.event_id = uuid4()
        if self.occurred_at is None:
            self.occurred_at = datetime.now()
    
    @property
    def event_type(self) -> str:
        return "ConversationStarted"
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "session_id": str(self.session_id),
            "provider_type": self.provider_type,
            "debate_id": str(self.debate_id) if self.debate_id else None,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass
class ProviderSwitched:
    """Event raised when switching between AI providers"""
    event_id: UUID = None
    from_provider: str = ""
    to_provider: str = ""
    reason: str = ""
    session_id: Optional[UUID] = None
    occurred_at: datetime = None
    
    def __post_init__(self):
        if self.event_id is None:
            self.event_id = uuid4()
        if self.occurred_at is None:
            self.occurred_at = datetime.now()
    
    @property
    def event_type(self) -> str:
        return "ProviderSwitched"
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "from_provider": self.from_provider,
            "to_provider": self.to_provider,
            "reason": self.reason,
            "session_id": str(self.session_id) if self.session_id else None,
            "occurred_at": self.occurred_at.isoformat(),
        }