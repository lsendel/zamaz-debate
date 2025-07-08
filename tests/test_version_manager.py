#!/usr/bin/env python3
"""
Tests for Version Manager
"""
import pytest
import tempfile
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.version_manager import VersionManager, VersionBump


class TestVersionManager:
    """Test suite for version manager"""
    
    @pytest.fixture
    def version_manager(self):
        """Create version manager with temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            version_file = Path(temp_dir) / "version.json"
            yield VersionManager(version_file)
    
    def test_initialization(self, version_manager):
        """Test version manager initialization"""
        assert version_manager.get_current_version() == "0.1.0"
        history = version_manager.get_version_history()
        assert len(history) == 1
        assert history[0]["version"] == "0.1.0"
    
    def test_parse_version(self, version_manager):
        """Test version string parsing"""
        major, minor, patch = version_manager.parse_version("1.2.3")
        assert major == 1
        assert minor == 2
        assert patch == 3
        
        # Test invalid format
        with pytest.raises(ValueError):
            version_manager.parse_version("1.2")
        
        with pytest.raises(ValueError):
            version_manager.parse_version("invalid")
    
    def test_patch_bump(self, version_manager):
        """Test patch version bump"""
        new_version = version_manager.bump_version(
            VersionBump.PATCH,
            ["Fixed bug in evolution tracker"]
        )
        assert new_version == "0.1.1"
        assert version_manager.get_current_version() == "0.1.1"
    
    def test_minor_bump(self, version_manager):
        """Test minor version bump"""
        new_version = version_manager.bump_version(
            VersionBump.MINOR,
            ["Added new feature"]
        )
        assert new_version == "0.2.0"
        assert version_manager.get_current_version() == "0.2.0"
    
    def test_major_bump(self, version_manager):
        """Test major version bump"""
        new_version = version_manager.bump_version(
            VersionBump.MAJOR,
            ["Breaking change in API"]
        )
        assert new_version == "1.0.0"
        assert version_manager.get_current_version() == "1.0.0"
    
    def test_version_sequence(self, version_manager):
        """Test proper version sequence"""
        # Start at 0.1.0
        assert version_manager.get_current_version() == "0.1.0"
        
        # Patch bump to 0.1.1
        version_manager.bump_version(VersionBump.PATCH, ["Fix 1"])
        assert version_manager.get_current_version() == "0.1.1"
        
        # Another patch to 0.1.2
        version_manager.bump_version(VersionBump.PATCH, ["Fix 2"])
        assert version_manager.get_current_version() == "0.1.2"
        
        # Minor bump resets patch to 0.2.0
        version_manager.bump_version(VersionBump.MINOR, ["New feature"])
        assert version_manager.get_current_version() == "0.2.0"
        
        # Major bump resets minor and patch to 1.0.0
        version_manager.bump_version(VersionBump.MAJOR, ["Breaking change"])
        assert version_manager.get_current_version() == "1.0.0"
    
    def test_evolution_version_mapping(self, version_manager):
        """Test mapping evolutions to versions"""
        evolution_id = "evo_123_20250708_120000"
        
        new_version = version_manager.bump_version(
            VersionBump.MINOR,
            ["Added new feature"],
            evolution_id=evolution_id
        )
        
        # Check evolution is mapped to version
        assert version_manager.get_version_for_evolution(evolution_id) == new_version
    
    def test_version_history(self, version_manager):
        """Test version history tracking"""
        # Add several versions
        version_manager.bump_version(VersionBump.PATCH, ["Fix 1"])
        version_manager.bump_version(VersionBump.MINOR, ["Feature 1"])
        version_manager.bump_version(VersionBump.PATCH, ["Fix 2"])
        
        history = version_manager.get_version_history()
        assert len(history) == 4  # Initial + 3 bumps
        
        # Check versions in order
        versions = [h["version"] for h in history]
        assert versions == ["0.1.0", "0.1.1", "0.2.0", "0.2.1"]
        
        # Check changes are recorded
        assert history[1]["changes"] == ["Fix 1"]
        assert history[2]["changes"] == ["Feature 1"]
        assert history[3]["changes"] == ["Fix 2"]
    
    def test_should_bump_version(self, version_manager):
        """Test version bump determination based on evolution type"""
        # Feature should trigger minor bump
        assert version_manager.should_bump_version("feature") == VersionBump.MINOR
        
        # Enhancement should trigger patch bump
        assert version_manager.should_bump_version("enhancement") == VersionBump.PATCH
        
        # Fix should trigger patch bump
        assert version_manager.should_bump_version("fix") == VersionBump.PATCH
        assert version_manager.should_bump_version("bugfix") == VersionBump.PATCH
        
        # Breaking change should trigger major bump
        assert version_manager.should_bump_version("breaking") == VersionBump.MAJOR
        assert version_manager.should_bump_version("breaking-change") == VersionBump.MAJOR
        
        # Unknown type defaults to minor
        assert version_manager.should_bump_version("unknown") == VersionBump.MINOR
    
    def test_persistence(self):
        """Test version data persistence"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Create version manager and make changes
            vm1 = VersionManager(temp_path)
            vm1.bump_version(VersionBump.MINOR, ["Feature 1"], "evo_1")
            vm1.bump_version(VersionBump.PATCH, ["Fix 1"], "evo_2")
            
            # Create new instance with same file
            vm2 = VersionManager(temp_path)
            
            # Should have same version
            assert vm2.get_current_version() == "0.2.1"
            
            # Should have same history
            assert len(vm2.get_version_history()) == 3
            
            # Should have same evolution mappings
            assert vm2.get_version_for_evolution("evo_1") == "0.2.0"
            assert vm2.get_version_for_evolution("evo_2") == "0.2.1"
        
        finally:
            # Clean up
            if temp_path.exists():
                temp_path.unlink()