#!/usr/bin/env python3
"""
Migration script to upgrade evolution tracking to v2
Safely migrates existing evolution data with deduplication
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.evolution_tracker import EvolutionTracker
from src.core.evolution_tracker_v2 import EvolutionTrackerV2


def backup_existing_data():
    """Create backup of existing evolution data"""
    data_dir = Path(__file__).parent.parent / "data" / "evolutions"
    history_file = data_dir / "evolution_history.json"
    
    if history_file.exists():
        backup_file = data_dir / "evolution_history_backup.json"
        print(f"📦 Creating backup at {backup_file}")
        
        with open(history_file, 'r') as f:
            data = json.load(f)
        
        with open(backup_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print("✅ Backup created successfully")
        return True
    
    return False


def migrate_evolution_data():
    """Migrate evolution data from v1 to v2"""
    print("🚀 Starting evolution data migration to v2...")
    
    # Create backup first
    if not backup_existing_data():
        print("⚠️ No existing data to migrate")
        return
    
    # Load old tracker
    print("📖 Loading existing evolution data...")
    old_tracker = EvolutionTracker()
    old_summary = old_tracker.get_evolution_summary()
    
    print(f"Found {old_summary['total_evolutions']} evolutions to migrate")
    print(f"Evolution types: {json.dumps(old_summary['evolution_types'], indent=2)}")
    
    # Create new tracker (will use different file initially)
    print("\n🔄 Migrating to new tracker with enhanced duplicate detection...")
    
    # Temporarily rename the history file
    data_dir = Path(__file__).parent.parent / "data" / "evolutions"
    history_file = data_dir / "evolution_history.json"
    temp_file = data_dir / "evolution_history_temp.json"
    
    if history_file.exists():
        history_file.rename(temp_file)
    
    # Create new tracker
    new_tracker = EvolutionTrackerV2()
    
    # Migrate evolutions
    migrated = 0
    skipped = 0
    
    for evo in old_tracker.history.get("evolutions", []):
        # Clean up evolution data
        clean_evo = {
            "type": evo.get("type", "feature"),
            "feature": evo.get("feature", "unknown"),
            "description": evo.get("description", ""),
            "priority": evo.get("priority", "medium"),
        }
        
        # Add optional fields if present
        if evo.get("debate_id"):
            clean_evo["debate_id"] = evo["debate_id"]
        
        if evo.get("decision_text"):
            clean_evo["decision_text"] = evo["decision_text"]
        
        # Try to add to new tracker
        if new_tracker.add_evolution(clean_evo):
            migrated += 1
            print(f"✅ Migrated: {clean_evo['type']} - {clean_evo['feature']}")
        else:
            skipped += 1
            print(f"⏭️ Skipped duplicate: {clean_evo['type']} - {clean_evo['feature']}")
    
    # Get new summary
    new_summary = new_tracker.get_evolution_summary()
    
    print(f"\n📊 Migration Summary:")
    print(f"  - Total evolutions processed: {old_summary['total_evolutions']}")
    print(f"  - Successfully migrated: {migrated}")
    print(f"  - Duplicates removed: {skipped}")
    print(f"  - New total evolutions: {new_summary['total_evolutions']}")
    print(f"  - Current version: {new_summary['current_version']}")
    print(f"  - Unique features: {new_summary.get('unique_features', 'N/A')}")
    
    # Clean up temp file
    if temp_file.exists():
        temp_file.unlink()
    
    print("\n✅ Migration completed successfully!")
    print("📝 The system now has:")
    print("  - Enhanced duplicate detection")
    print("  - Automatic version management")
    print("  - Data integrity validation")
    print("  - Thread-safe operations")


if __name__ == "__main__":
    migrate_evolution_data()