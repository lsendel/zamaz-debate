"""
AI Integration Context

This bounded context handles AI provider integration and conversation management.
"""

from .aggregates import AIProvider, ConversationSession
from .domain_services import ProviderSelection, ResponseCaching
from .events import AIResponseReceived, ConversationStarted, ProviderSwitched
from .repositories import AIProviderRepository, ConversationRepository
from .value_objects import AIResponse, ProviderConfig


class AIIntegrationContext:
    """Main context class for AI Integration"""
    pass


__all__ = [
    "AIIntegrationContext",
    "AIProvider",
    "ConversationSession",
    "ProviderSelection",
    "ResponseCaching",
    "AIResponse",
    "ProviderConfig",
    "AIProviderRepository",
    "ConversationRepository",
    "AIResponseReceived",
    "ConversationStarted",
    "ProviderSwitched",
]
