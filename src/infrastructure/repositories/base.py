"""
Base Repository Implementation

Provides common functionality for JSON-based repository implementations.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar
from uuid import UUID

T = TypeVar("T")


class JsonRepository:
    """
    Base class for JSON file-based repositories
    
    Provides common CRUD operations using JSON files for persistence.
    """
    
    def __init__(self, storage_path: str, entity_name: str):
        """
        Initialize the repository
        
        Args:
            storage_path: Base path for storing JSON files
            entity_name: Name of the entity type (used for file naming)
        """
        self.storage_path = Path(storage_path)
        self.entity_name = entity_name
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, entity_id: UUID) -> Path:
        """Get the file path for an entity"""
        return self.storage_path / f"{self.entity_name}_{entity_id}.json"
    
    def _get_index_file_path(self) -> Path:
        """Get the file path for the entity index"""
        return self.storage_path / f"{self.entity_name}_index.json"
    
    def _serialize(self, entity: Any) -> Dict[str, Any]:
        """
        Serialize an entity to a dictionary
        
        Args:
            entity: The entity to serialize
            
        Returns:
            Dictionary representation of the entity
        """
        # Handle different types of serialization
        if hasattr(entity, "to_dict"):
            return entity.to_dict()
        elif hasattr(entity, "__dict__"):
            return self._serialize_object(entity)
        else:
            raise ValueError(f"Cannot serialize entity of type {type(entity)}")
    
    def _serialize_object(self, obj: Any) -> Dict[str, Any]:
        """Recursively serialize an object"""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, list):
            return [self._serialize_object(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._serialize_object(v) for k, v in obj.items()}
        elif hasattr(obj, "__dict__"):
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith("_"):  # Skip private attributes
                    result[key] = self._serialize_object(value)
            return result
        else:
            return str(obj)
    
    def _deserialize(self, data: Dict[str, Any], entity_class: type) -> Any:
        """
        Deserialize a dictionary to an entity
        
        Args:
            data: The dictionary to deserialize
            entity_class: The class to deserialize to
            
        Returns:
            Instance of entity_class
        """
        # This is a simplified deserialization
        # In a real implementation, you'd handle this more robustly
        return entity_class(**data)
    
    async def save_entity(self, entity: Any, entity_id: UUID) -> None:
        """Save an entity to JSON file"""
        file_path = self._get_file_path(entity_id)
        data = self._serialize(entity)
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        # Update index
        await self._update_index(entity_id, data)
    
    async def load_entity(self, entity_id: UUID, entity_class: type) -> Optional[Any]:
        """Load an entity from JSON file"""
        file_path = self._get_file_path(entity_id)
        
        if not file_path.exists():
            return None
        
        with open(file_path, "r") as f:
            data = json.load(f)
        
        return self._deserialize(data, entity_class)
    
    async def delete_entity(self, entity_id: UUID) -> bool:
        """Delete an entity"""
        file_path = self._get_file_path(entity_id)
        
        if not file_path.exists():
            return False
        
        file_path.unlink()
        await self._remove_from_index(entity_id)
        return True
    
    async def exists(self, entity_id: UUID) -> bool:
        """Check if an entity exists"""
        return self._get_file_path(entity_id).exists()
    
    async def _update_index(self, entity_id: UUID, data: Dict[str, Any]) -> None:
        """Update the entity index"""
        index = await self._load_index()
        
        # Store basic info in index for faster queries
        index[str(entity_id)] = {
            "id": str(entity_id),
            "updated_at": datetime.now().isoformat(),
            **self._extract_index_data(data),
        }
        
        await self._save_index(index)
    
    async def _remove_from_index(self, entity_id: UUID) -> None:
        """Remove an entity from the index"""
        index = await self._load_index()
        index.pop(str(entity_id), None)
        await self._save_index(index)
    
    async def _load_index(self) -> Dict[str, Any]:
        """Load the entity index"""
        index_path = self._get_index_file_path()
        
        if not index_path.exists():
            return {}
        
        with open(index_path, "r") as f:
            return json.load(f)
    
    async def _save_index(self, index: Dict[str, Any]) -> None:
        """Save the entity index"""
        index_path = self._get_index_file_path()
        
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data to store in the index
        
        Override this method in subclasses to customize index data
        """
        return {}
    
    async def find_all(self, entity_class: type) -> List[Any]:
        """Find all entities"""
        entities = []
        
        for file_path in self.storage_path.glob(f"{self.entity_name}_*.json"):
            if file_path.name == f"{self.entity_name}_index.json":
                continue
            
            with open(file_path, "r") as f:
                data = json.load(f)
            
            entity = self._deserialize(data, entity_class)
            entities.append(entity)
        
        return entities
    
    async def find_by_criteria(
        self,
        entity_class: type,
        criteria: Dict[str, Any],
    ) -> List[Any]:
        """
        Find entities matching criteria
        
        This is a simple implementation that loads all entities and filters.
        In a real system, you'd use a proper database with indexes.
        """
        all_entities = await self.find_all(entity_class)
        
        filtered = []
        for entity in all_entities:
            match = True
            for key, value in criteria.items():
                if not hasattr(entity, key) or getattr(entity, key) != value:
                    match = False
                    break
            
            if match:
                filtered.append(entity)
        
        return filtered
    
    async def count(self) -> int:
        """Count total entities"""
        count = 0
        for file_path in self.storage_path.glob(f"{self.entity_name}_*.json"):
            if file_path.name != f"{self.entity_name}_index.json":
                count += 1
        return count
    
    async def count_by_criteria(self, criteria: Dict[str, Any]) -> int:
        """Count entities matching criteria"""
        index = await self._load_index()
        
        count = 0
        for entity_data in index.values():
            match = True
            for key, value in criteria.items():
                if entity_data.get(key) != value:
                    match = False
                    break
            
            if match:
                count += 1
        
        return count