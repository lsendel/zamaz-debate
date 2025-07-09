"""
AI Integration Context - Value Objects
Value objects for AI integration
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass(frozen=True)
class AIResponse:
    """Value object representing an AI response"""
    content: str
    tokens_used: int
    response_time_ms: int
    model: str
    temperature: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())


@dataclass(frozen=True)
class ProviderConfig:
    """Value object for AI provider configuration"""
    api_key: str
    endpoint_url: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 60
    retry_attempts: int = 3
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "endpoint_url": self.endpoint_url,
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts
        }