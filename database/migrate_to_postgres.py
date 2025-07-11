#!/usr/bin/env python3
"""
Migration script to move data from JSON files to PostgreSQL
Supports hybrid operation during transition
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import asyncio
import asyncpg
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()


class DataMigrator:
    """Migrates JSON file data to PostgreSQL"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None
        self.stats = {
            "debates": {"total": 0, "migrated": 0, "errors": 0},
            "decisions": {"total": 0, "migrated": 0, "errors": 0},
            "evolutions": {"total": 0, "migrated": 0, "errors": 0}
        }
    
    async def connect(self):
        """Establish database connection"""
        self.conn = await asyncpg.connect(self.db_url)
        print("Connected to PostgreSQL")
    
    async def disconnect(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            print("Disconnected from PostgreSQL")
    
    async def migrate_debates(self):
        """Migrate debates from JSON files"""
        debates_dir = Path("data/debates")
        if not debates_dir.exists():
            print("No debates directory found")
            return
        
        debate_files = list(debates_dir.glob("*.json"))
        self.stats["debates"]["total"] = len(debate_files)
        
        for debate_file in debate_files:
            try:
                # Check if already migrated
                check = await self.conn.fetchval(
                    "SELECT 1 FROM migration_tracking WHERE file_path = $1",
                    str(debate_file)
                )
                if check:
                    print(f"Skipping {debate_file.name} - already migrated")
                    continue
                
                with open(debate_file) as f:
                    data = json.load(f)
                
                # Insert debate
                debate_id = await self.conn.fetchval("""
                    INSERT INTO debates (
                        external_id, question, context, complexity, method,
                        start_time, end_time, final_decision, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                """,
                    data["id"],
                    data.get("question", ""),
                    data.get("context", ""),
                    data.get("complexity", "moderate"),
                    data.get("method", "debate"),
                    datetime.fromisoformat(data["start_time"]),
                    datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
                    data.get("final_decision", ""),
                    json.dumps({"file_source": str(debate_file)})
                )
                
                # Insert rounds
                for i, round_data in enumerate(data.get("rounds", [])):
                    await self.conn.execute("""
                        INSERT INTO debate_rounds (
                            debate_id, round_number, claude_response, gemini_response
                        ) VALUES ($1, $2, $3, $4)
                    """,
                        debate_id,
                        round_data.get("round", i + 1),
                        round_data.get("claude", ""),
                        round_data.get("gemini", "")
                    )
                
                # Insert consensus analysis if present
                if "consensus" in data and isinstance(data["consensus"], dict):
                    consensus = data["consensus"]
                    await self.conn.execute("""
                        INSERT INTO consensus_analyses (
                            debate_id, has_consensus, consensus_level, consensus_type,
                            areas_of_agreement, areas_of_disagreement, combined_recommendation
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        debate_id,
                        consensus.get("has_consensus", False),
                        consensus.get("level", 0.0),
                        consensus.get("type", "none"),
                        consensus.get("areas_of_agreement", []),
                        consensus.get("areas_of_disagreement", []),
                        consensus.get("combined_recommendation", "")
                    )
                
                # Track migration
                await self.conn.execute("""
                    INSERT INTO migration_tracking (file_path, file_type, success)
                    VALUES ($1, $2, $3)
                """, str(debate_file), "debate", True)
                
                self.stats["debates"]["migrated"] += 1
                print(f"Migrated debate: {data['id']}")
                
            except Exception as e:
                print(f"Error migrating {debate_file}: {e}")
                self.stats["debates"]["errors"] += 1
                
                # Track failed migration
                await self.conn.execute("""
                    INSERT INTO migration_tracking (file_path, file_type, success, error_message)
                    VALUES ($1, $2, $3, $4)
                """, str(debate_file), "debate", False, str(e))
    
    async def migrate_decisions(self):
        """Migrate decisions from JSON files"""
        decisions_dir = Path("data/decisions")
        if not decisions_dir.exists():
            print("No decisions directory found")
            return
        
        decision_files = list(decisions_dir.glob("*.json"))
        self.stats["decisions"]["total"] = len(decision_files)
        
        for decision_file in decision_files:
            try:
                # Check if already migrated
                check = await self.conn.fetchval(
                    "SELECT 1 FROM migration_tracking WHERE file_path = $1",
                    str(decision_file)
                )
                if check:
                    print(f"Skipping {decision_file.name} - already migrated")
                    continue
                
                with open(decision_file) as f:
                    data = json.load(f)
                
                # Get debate_id if linked
                debate_id = None
                if data.get("debate_id"):
                    debate_id = await self.conn.fetchval(
                        "SELECT id FROM debates WHERE external_id = $1",
                        data["debate_id"]
                    )
                
                # Insert decision
                await self.conn.execute("""
                    INSERT INTO decisions (
                        external_id, question, context, decision_text,
                        decision_type, method, rounds, implementation_assignee,
                        debate_id, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                    data["id"],
                    data.get("question", ""),
                    data.get("context", ""),
                    data.get("decision_text", ""),
                    data.get("decision_type", "MODERATE"),
                    data.get("method", "debate"),
                    data.get("rounds", 0),
                    data.get("implementation_assignee"),
                    debate_id,
                    datetime.fromisoformat(data["timestamp"])
                )
                
                # Track migration
                await self.conn.execute("""
                    INSERT INTO migration_tracking (file_path, file_type, success)
                    VALUES ($1, $2, $3)
                """, str(decision_file), "decision", True)
                
                self.stats["decisions"]["migrated"] += 1
                print(f"Migrated decision: {data['id']}")
                
            except Exception as e:
                print(f"Error migrating {decision_file}: {e}")
                self.stats["decisions"]["errors"] += 1
                
                await self.conn.execute("""
                    INSERT INTO migration_tracking (file_path, file_type, success, error_message)
                    VALUES ($1, $2, $3, $4)
                """, str(decision_file), "decision", False, str(e))
    
    async def migrate_evolutions(self):
        """Migrate evolution history"""
        evo_file = Path("data/evolutions/evolution_history.json")
        if not evo_file.exists():
            print("No evolution history found")
            return
        
        try:
            with open(evo_file) as f:
                data = json.load(f)
            
            evolutions = data.get("evolutions", [])
            self.stats["evolutions"]["total"] = len(evolutions)
            
            for i, evo in enumerate(evolutions):
                try:
                    # Get debate_id if linked
                    debate_id = None
                    if evo.get("debate_id"):
                        debate_id = await self.conn.fetchval(
                            "SELECT id FROM debates WHERE external_id = $1",
                            evo["debate_id"]
                        )
                    
                    # Insert evolution
                    await self.conn.execute("""
                        INSERT INTO evolutions (
                            evolution_number, evolution_type, feature,
                            description, debate_id, timestamp
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                        i + 1,
                        evo.get("type", "enhancement"),
                        evo.get("feature", "unknown"),
                        evo.get("description", "")[:1000],  # Truncate long descriptions
                        debate_id,
                        datetime.fromisoformat(evo.get("timestamp", datetime.now().isoformat()))
                    )
                    
                    self.stats["evolutions"]["migrated"] += 1
                    
                except Exception as e:
                    print(f"Error migrating evolution {i}: {e}")
                    self.stats["evolutions"]["errors"] += 1
            
        except Exception as e:
            print(f"Error reading evolution history: {e}")
    
    async def print_summary(self):
        """Print migration summary"""
        print("\n" + "="*50)
        print("Migration Summary")
        print("="*50)
        
        for entity, stats in self.stats.items():
            print(f"\n{entity.capitalize()}:")
            print(f"  Total: {stats['total']}")
            print(f"  Migrated: {stats['migrated']}")
            print(f"  Errors: {stats['errors']}")
            
            if stats['total'] > 0:
                success_rate = (stats['migrated'] / stats['total']) * 100
                print(f"  Success Rate: {success_rate:.1f}%")
    
    async def run(self):
        """Run the complete migration"""
        try:
            await self.connect()
            
            print("\nStarting migration...")
            print("="*50)
            
            print("\nMigrating debates...")
            await self.migrate_debates()
            
            print("\nMigrating decisions...")
            await self.migrate_decisions()
            
            print("\nMigrating evolutions...")
            await self.migrate_evolutions()
            
            await self.print_summary()
            
        finally:
            await self.disconnect()


async def main():
    """Main entry point"""
    # Get database URL from environment or use default
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/zamaz_debate"
    )
    
    print(f"Database URL: {db_url}")
    print("\nThis script will migrate JSON files to PostgreSQL.")
    print("Existing data in the database will not be overwritten.")
    
    response = input("\nProceed with migration? (y/n): ")
    if response.lower() != 'y':
        print("Migration cancelled")
        return
    
    migrator = DataMigrator(db_url)
    await migrator.run()


if __name__ == "__main__":
    asyncio.run(main())