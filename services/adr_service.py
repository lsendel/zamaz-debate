"""
Architectural Decision Records (ADR) Service
Manages creation and tracking of ADRs for the system
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum


class ADRStatus(Enum):
    """Status of an ADR"""
    PROPOSED = "Proposed"
    ACCEPTED = "Accepted"
    DEPRECATED = "Deprecated"
    SUPERSEDED = "Superseded"


class ADRService:
    """Service for managing Architectural Decision Records"""
    
    def __init__(self, adr_dir: Optional[Path] = None):
        self.adr_dir = adr_dir or Path(__file__).parent.parent / "docs" / "adr"
        self.adr_dir.mkdir(parents=True, exist_ok=True)
        self.adr_index_file = self.adr_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        """Load the ADR index"""
        if self.adr_index_file.exists():
            with open(self.adr_index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {"adrs": [], "next_number": 2}  # Starting at 2 since we have 000 and 001
            self._save_index()
    
    def _save_index(self):
        """Save the ADR index"""
        with open(self.adr_index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def create_adr(self, title: str, context: str, decision: str, 
                   consequences: Dict[str, List[str]], 
                   implementation_details: Optional[str] = None) -> str:
        """Create a new ADR"""
        adr_number = str(self.index["next_number"]).zfill(3)
        filename = f"{adr_number}-{self._slugify(title)}.md"
        filepath = self.adr_dir / filename
        
        # Generate ADR content
        content = self._generate_adr_content(
            adr_number, title, context, decision, 
            consequences, implementation_details
        )
        
        # Write ADR file
        with open(filepath, 'w') as f:
            f.write(content)
        
        # Update index
        self.index["adrs"].append({
            "number": adr_number,
            "title": title,
            "filename": filename,
            "status": ADRStatus.PROPOSED.value,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat()
        })
        self.index["next_number"] += 1
        self._save_index()
        
        return filename
    
    def _generate_adr_content(self, number: str, title: str, context: str, 
                             decision: str, consequences: Dict[str, List[str]], 
                             implementation_details: Optional[str] = None) -> str:
        """Generate the content of an ADR"""
        content = f"""# ADR-{number}: {title}

## Status
{ADRStatus.PROPOSED.value}

## Context
{context}

## Decision
{decision}

## Consequences

### Positive
"""
        for item in consequences.get("positive", []):
            content += f"- {item}\n"
        
        content += "\n### Negative\n"
        for item in consequences.get("negative", []):
            content += f"- {item}\n"
        
        content += "\n### Neutral\n"
        for item in consequences.get("neutral", []):
            content += f"- {item}\n"
        
        if implementation_details:
            content += f"\n## Implementation Details\n{implementation_details}\n"
        
        return content
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        return text.lower().replace(" ", "-").replace("_", "-")[:50]
    
    def get_all_adrs(self) -> List[Dict]:
        """Get all ADRs from the index"""
        return self.index["adrs"]
    
    def get_adr(self, number: str) -> Optional[Dict]:
        """Get a specific ADR by number"""
        for adr in self.index["adrs"]:
            if adr["number"] == number:
                return adr
        return None
    
    def update_adr_status(self, number: str, status: ADRStatus):
        """Update the status of an ADR"""
        for adr in self.index["adrs"]:
            if adr["number"] == number:
                adr["status"] = status.value
                adr["updated"] = datetime.now().isoformat()
                self._save_index()
                return True
        return False
    
    def create_adr_from_decision(self, decision_data: Dict) -> Optional[str]:
        """Create an ADR from a decision debate"""
        # Extract relevant information from the decision
        decision_text = decision_data.get("decision_text", "")
        
        # Parse the decision text to extract ADR components
        if "architectural decision" in decision_text.lower() or "adr" in decision_text.lower():
            # This is a decision about architecture
            title = self._extract_title_from_decision(decision_text)
            context = self._extract_context_from_decision(decision_data)
            decision = self._extract_decision_from_text(decision_text)
            consequences = self._extract_consequences_from_text(decision_text)
            
            if title and decision:
                return self.create_adr(
                    title=title,
                    context=context,
                    decision=decision,
                    consequences=consequences
                )
        
        return None
    
    def _extract_title_from_decision(self, decision_text: str) -> str:
        """Extract a title from decision text"""
        # Simple heuristic - look for the main topic
        lines = decision_text.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('#'):
                # Use first non-empty, non-header line
                return line.strip()[:100]
        return "Architectural Decision"
    
    def _extract_context_from_decision(self, decision_data: Dict) -> str:
        """Extract context from decision data"""
        question = decision_data.get("question", "")
        context = decision_data.get("context", "")
        return f"{question}\n\n{context}".strip()
    
    def _extract_decision_from_text(self, decision_text: str) -> str:
        """Extract the decision from the text"""
        # Look for decision markers
        if "Decision:" in decision_text:
            parts = decision_text.split("Decision:")
            if len(parts) > 1:
                return parts[1].split("\n\n")[0].strip()
        
        # Fallback - use consensus section
        if "Consensus:" in decision_text:
            return "Based on the debate consensus, the decision has been made as discussed above."
        
        return "See debate details for the decision."
    
    def _extract_consequences_from_text(self, decision_text: str) -> Dict[str, List[str]]:
        """Extract consequences from decision text"""
        consequences = {
            "positive": [],
            "negative": [],
            "neutral": []
        }
        
        # Look for pros/cons patterns
        text_lower = decision_text.lower()
        lines = decision_text.split('\n')
        
        current_section = None
        for line in lines:
            line_lower = line.lower().strip()
            
            # Detect section headers
            if any(word in line_lower for word in ['pros:', 'positive:', 'benefits:']):
                current_section = 'positive'
            elif any(word in line_lower for word in ['cons:', 'negative:', 'downsides:', 'risks:']):
                current_section = 'negative'
            elif any(word in line_lower for word in ['neutral:', 'trade-offs:']):
                current_section = 'neutral'
            elif line.strip().startswith('- ') and current_section:
                # Add bullet points to current section
                consequences[current_section].append(line.strip()[2:])
        
        # Ensure at least one item in each category
        if not consequences['positive']:
            consequences['positive'].append("To be documented after implementation")
        if not consequences['negative']:
            consequences['negative'].append("To be assessed during implementation")
        if not consequences['neutral']:
            consequences['neutral'].append("Architecture documentation established")
        
        return consequences