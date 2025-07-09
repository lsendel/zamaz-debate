"""
AI Integration Context - Repositories
Repository interfaces for AI integration
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from .aggregates import AIProvider, AIProviderType, ConversationSession


class AIProviderRepository(ABC):
    """Repository interface for AI providers"""
    
    @abstractmethod
    async def save(self, provider: AIProvider) -> None:
        """Save an AI provider"""
        pass
        
    @abstractmethod
    async def get_by_id(self, provider_id: UUID) -> Optional[AIProvider]:
        """Get provider by ID"""
        pass
        
    @abstractmethod
    async def get_by_type(self, provider_type: AIProviderType) -> Optional[AIProvider]:
        """Get provider by type"""
        pass
        
    @abstractmethod
    async def get_all_active(self) -> List[AIProvider]:
        """Get all active providers"""
        pass


class ConversationRepository(ABC):
    """Repository interface for conversation sessions"""
    
    @abstractmethod
    async def save(self, session: ConversationSession) -> None:
        """Save a conversation session"""
        pass
        
    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> Optional[ConversationSession]:
        """Get session by ID"""
        pass
        
    @abstractmethod
    async def get_by_debate_id(self, debate_id: UUID) -> List[ConversationSession]:
        """Get all sessions for a debate"""
        pass
        
    @abstractmethod
    async def get_active_sessions(self) -> List[ConversationSession]:
        """Get all active sessions"""
        pass