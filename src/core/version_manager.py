#!/usr/bin/env python3
"""
Version Manager for Zamaz Debate System
Handles semantic versioning and tracks feature releases
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
from enum import Enum


class VersionBump(Enum):
    """Types of version bumps following semantic versioning"""
    PATCH = "patch"  # Bug fixes, minor changes
    MINOR = "minor"  # New features, backward compatible
    MAJOR = "major"  # Breaking changes


class VersionManager:
    """Manages system versioning with semantic versioning rules"""
    
    def __init__(self, version_file: Optional[Path] = None):
        """Initialize version manager with optional custom version file path"""
        if version_file is None:
            # Default to data directory
            self.version_file = Path(__file__).parent.parent.parent / "data" / "version.json"
        else:
            self.version_file = Path(version_file)
        
        # Ensure directory exists
        self.version_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize version data
        self.version_data = self._load_version_data()
    
    def _load_version_data(self) -> Dict:
        """Load version data from file or create initial version"""
        if self.version_file.exists():
            with open(self.version_file, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                # File exists but is empty, treat as new
        
        # Initialize with default version
        initial_data = {
            "current_version": "0.1.0",
            "version_history": [
                {
                    "version": "0.1.0",
                    "timestamp": datetime.now().isoformat(),
                    "changes": ["Initial release"],
                    "evolution_count": 0
                }
            ],
            "evolution_version_map": {}  # Maps evolution IDs to versions
        }
        self._save_version_data(initial_data)
        return initial_data
    
    def _save_version_data(self, data: Optional[Dict] = None):
        """Save version data to file"""
        if data is None:
            data = self.version_data
        
        with open(self.version_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_current_version(self) -> str:
        """Get the current system version"""
        return self.version_data["current_version"]
    
    def parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse version string into major, minor, patch components"""
        parts = version.split('.')
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {version}")
        
        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
            return major, minor, patch
        except ValueError:
            raise ValueError(f"Invalid version format: {version}")
    
    def bump_version(self, bump_type: VersionBump, changes: list, evolution_id: Optional[str] = None) -> str:
        """
        Bump the version according to semantic versioning rules
        
        Args:
            bump_type: Type of version bump (PATCH, MINOR, MAJOR)
            changes: List of changes in this version
            evolution_id: Optional evolution ID to associate with this version
            
        Returns:
            New version string
        """
        current = self.get_current_version()
        major, minor, patch = self.parse_version(current)
        
        # Apply version bump
        if bump_type == VersionBump.PATCH:
            patch += 1
        elif bump_type == VersionBump.MINOR:
            minor += 1
            patch = 0  # Reset patch version
        elif bump_type == VersionBump.MAJOR:
            major += 1
            minor = 0  # Reset minor version
            patch = 0  # Reset patch version
        
        new_version = f"{major}.{minor}.{patch}"
        
        # Update version data
        self.version_data["current_version"] = new_version
        
        # Add to version history
        version_entry = {
            "version": new_version,
            "timestamp": datetime.now().isoformat(),
            "changes": changes,
            "evolution_count": len(self.version_data.get("evolution_version_map", {}))
        }
        
        if evolution_id:
            version_entry["evolution_id"] = evolution_id
            # Map evolution to version
            self.version_data["evolution_version_map"][evolution_id] = new_version
        
        self.version_data["version_history"].append(version_entry)
        
        # Save updated data
        self._save_version_data()
        
        return new_version
    
    def get_version_for_evolution(self, evolution_id: str) -> Optional[str]:
        """Get the version associated with a specific evolution"""
        return self.version_data.get("evolution_version_map", {}).get(evolution_id)
    
    def get_version_history(self) -> list:
        """Get the complete version history"""
        return self.version_data.get("version_history", [])
    
    def should_bump_version(self, evolution_type: str) -> Optional[VersionBump]:
        """
        Determine if version should be bumped based on evolution type
        
        Args:
            evolution_type: Type of evolution (feature, enhancement, fix, etc.)
            
        Returns:
            VersionBump type or None if no bump needed
        """
        # Map evolution types to version bumps
        bump_map = {
            "feature": VersionBump.MINOR,
            "enhancement": VersionBump.PATCH,
            "fix": VersionBump.PATCH,
            "bugfix": VersionBump.PATCH,
            "refactor": VersionBump.PATCH,
            "breaking": VersionBump.MAJOR,
            "major": VersionBump.MAJOR,
        }
        
        evolution_type_lower = evolution_type.lower()
        
        # Check for breaking changes
        if "breaking" in evolution_type_lower:
            return VersionBump.MAJOR
        
        return bump_map.get(evolution_type_lower, VersionBump.MINOR)