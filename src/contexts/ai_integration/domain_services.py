"""
AI Integration Context - Domain Services
Provides domain services for AI provider management
"""

from typing import Dict, List, Optional
from uuid import UUID

from .aggregates import AIProvider, AIProviderType, ConversationSession


class ProviderSelection:
    """Domain service for selecting appropriate AI providers"""
    
    def __init__(self):
        self._providers: Dict[AIProviderType, AIProvider] = {}
        
    def register_provider(self, provider: AIProvider):
        """Register an AI provider"""
        self._providers[provider.provider_type] = provider
        
    def select_provider(self, preferred_type: Optional[AIProviderType] = None) -> Optional[AIProvider]:
        """Select an appropriate AI provider"""
        # If preferred type is specified and available
        if preferred_type and preferred_type in self._providers:
            provider = self._providers[preferred_type]
            if provider.is_active and provider.api_key_configured:
                return provider
                
        # Otherwise, return first available active provider
        for provider in self._providers.values():
            if provider.is_active and provider.api_key_configured:
                return provider
                
        return None
        
    def get_available_providers(self) -> List[AIProvider]:
        """Get list of available providers"""
        return [p for p in self._providers.values() if p.is_active and p.api_key_configured]


class ResponseCaching:
    """Domain service for caching AI responses"""
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        
    def cache_response(self, prompt_hash: str, response: Dict):
        """Cache an AI response"""
        self._cache[prompt_hash] = {
            "response": response,
            "cached_at": datetime.now()
        }
        
    def get_cached_response(self, prompt_hash: str) -> Optional[Dict]:
        """Get a cached response if available"""
        if prompt_hash in self._cache:
            return self._cache[prompt_hash]["response"]
        return None
        
    def clear_cache(self):
        """Clear all cached responses"""
        self._cache.clear()
        
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "entries": len(self._cache),
            "size_estimate": sum(len(str(v)) for v in self._cache.values())
        }


# Import datetime for the caching service
from datetime import datetime