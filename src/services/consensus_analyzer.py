"""
Advanced Consensus Analyzer for Debate System

This module provides intelligent consensus detection using semantic analysis
and structured argument extraction.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import difflib


class Position(Enum):
    """Possible positions in a debate"""
    STRONGLY_SUPPORT = "strongly_support"
    SUPPORT = "support"
    NEUTRAL = "neutral"
    OPPOSE = "oppose"
    STRONGLY_OPPOSE = "strongly_oppose"


@dataclass
class ArgumentAnalysis:
    """Analysis of a single argument"""
    position: Position
    key_points: List[str]
    concerns: List[str]
    recommendations: List[str]
    confidence: float


@dataclass
class ConsensusResult:
    """Result of consensus analysis"""
    has_consensus: bool
    consensus_level: float  # 0.0 to 1.0
    consensus_type: str  # "full", "partial", "none"
    areas_of_agreement: List[str]
    areas_of_disagreement: List[str]
    combined_recommendation: str
    confidence: float


class ConsensusAnalyzer:
    """Advanced consensus analyzer using semantic analysis"""
    
    def __init__(self):
        # Position indicators with weights
        self.position_indicators = {
            Position.STRONGLY_SUPPORT: {
                "patterns": ["strongly recommend", "absolutely", "definitely should", "critical to", "essential"],
                "weight": 1.0
            },
            Position.SUPPORT: {
                "patterns": ["recommend", "should", "beneficial", "good idea", "proceed", "yes"],
                "weight": 0.7
            },
            Position.NEUTRAL: {
                "patterns": ["could", "might", "consider", "depends", "trade-offs"],
                "weight": 0.5
            },
            Position.OPPOSE: {
                "patterns": ["should not", "avoid", "unnecessary", "not recommended", "no"],
                "weight": 0.3
            },
            Position.STRONGLY_OPPOSE: {
                "patterns": ["strongly against", "definitely not", "dangerous", "critical flaw", "must avoid"],
                "weight": 0.0
            }
        }
        
        # Key phrase extractors
        self.extractors = {
            "recommendations": [
                r"recommend(?:ation)?s?:?\s*([^.]+)",
                r"(?:should|must|need to)\s+([^.]+)",
                r"(?:propose|suggest)\s+([^.]+)"
            ],
            "concerns": [
                r"concern(?:s|ed)?\s*(?:about|with|:)?\s*([^.]+)",
                r"risk(?:s)?\s*(?:of|:)?\s*([^.]+)",
                r"problem(?:s)?\s*(?:with|:)?\s*([^.]+)",
                r"challenge(?:s)?\s*(?:of|:)?\s*([^.]+)"
            ],
            "benefits": [
                r"benefit(?:s)?\s*(?:of|:)?\s*([^.]+)",
                r"advantage(?:s)?\s*(?:of|:)?\s*([^.]+)",
                r"improve(?:ment)?s?\s*(?:in|:)?\s*([^.]+)"
            ]
        }
    
    def analyze_debate(self, claude_response: str, gemini_response: str) -> ConsensusResult:
        """Analyze debate responses and determine consensus"""
        # Analyze individual arguments
        claude_analysis = self._analyze_argument(claude_response)
        gemini_analysis = self._analyze_argument(gemini_response)
        
        # Compare positions
        position_alignment = self._calculate_position_alignment(
            claude_analysis.position, 
            gemini_analysis.position
        )
        
        # Find areas of agreement and disagreement
        agreements = self._find_agreements(claude_analysis, gemini_analysis)
        disagreements = self._find_disagreements(claude_analysis, gemini_analysis)
        
        # Determine consensus level
        consensus_level = self._calculate_consensus_level(
            position_alignment,
            len(agreements),
            len(disagreements),
            claude_analysis.confidence,
            gemini_analysis.confidence
        )
        
        # Determine consensus type
        if consensus_level >= 0.8:
            consensus_type = "full"
            has_consensus = True
        elif consensus_level >= 0.5:
            consensus_type = "partial"
            has_consensus = True
        else:
            consensus_type = "none"
            has_consensus = False
        
        # Create combined recommendation
        combined_recommendation = self._create_combined_recommendation(
            claude_analysis, 
            gemini_analysis,
            agreements,
            disagreements,
            has_consensus
        )
        
        return ConsensusResult(
            has_consensus=has_consensus,
            consensus_level=consensus_level,
            consensus_type=consensus_type,
            areas_of_agreement=agreements,
            areas_of_disagreement=disagreements,
            combined_recommendation=combined_recommendation,
            confidence=(claude_analysis.confidence + gemini_analysis.confidence) / 2
        )
    
    def _analyze_argument(self, response: str) -> ArgumentAnalysis:
        """Analyze a single argument"""
        response_lower = response.lower()
        
        # Determine position
        position, position_confidence = self._determine_position(response_lower)
        
        # Extract key points
        key_points = self._extract_key_points(response)
        concerns = self._extract_concerns(response)
        recommendations = self._extract_recommendations(response)
        
        # Calculate overall confidence
        confidence = self._calculate_argument_confidence(
            position_confidence,
            len(key_points),
            len(recommendations)
        )
        
        return ArgumentAnalysis(
            position=position,
            key_points=key_points,
            concerns=concerns,
            recommendations=recommendations,
            confidence=confidence
        )
    
    def _determine_position(self, text: str) -> Tuple[Position, float]:
        """Determine the position expressed in the text"""
        scores = {}
        
        for position, indicators in self.position_indicators.items():
            score = 0
            matches = 0
            
            for pattern in indicators["patterns"]:
                if pattern in text:
                    score += indicators["weight"]
                    matches += 1
            
            if matches > 0:
                scores[position] = score / matches
        
        if not scores:
            return Position.NEUTRAL, 0.5
        
        # Get position with highest score
        best_position = max(scores, key=scores.get)
        confidence = scores[best_position]
        
        return best_position, confidence
    
    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from the text"""
        points = []
        
        # Look for numbered or bulleted lists
        list_patterns = [
            r'\d+\.\s*([^.\n]+)',
            r'[-•]\s*([^.\n]+)',
            r'(?:First|Second|Third|Finally),?\s*([^.\n]+)'
        ]
        
        for pattern in list_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            points.extend([m.strip() for m in matches if len(m.strip()) > 10])
        
        return list(set(points))[:5]  # Limit to top 5 unique points
    
    def _extract_concerns(self, text: str) -> List[str]:
        """Extract concerns from the text"""
        concerns = []
        
        for pattern in self.extractors["concerns"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            concerns.extend([m.strip() for m in matches if len(m.strip()) > 10])
        
        return list(set(concerns))[:3]
    
    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract recommendations from the text"""
        recommendations = []
        
        for pattern in self.extractors["recommendations"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            recommendations.extend([m.strip() for m in matches if len(m.strip()) > 10])
        
        return list(set(recommendations))[:3]
    
    def _calculate_position_alignment(self, pos1: Position, pos2: Position) -> float:
        """Calculate alignment between two positions"""
        position_values = {
            Position.STRONGLY_SUPPORT: 1.0,
            Position.SUPPORT: 0.75,
            Position.NEUTRAL: 0.5,
            Position.OPPOSE: 0.25,
            Position.STRONGLY_OPPOSE: 0.0
        }
        
        val1 = position_values[pos1]
        val2 = position_values[pos2]
        
        # Calculate alignment (1.0 = perfect alignment, 0.0 = opposite)
        return 1.0 - abs(val1 - val2)
    
    def _find_agreements(self, analysis1: ArgumentAnalysis, analysis2: ArgumentAnalysis) -> List[str]:
        """Find areas of agreement between two analyses"""
        agreements = []
        
        # Compare recommendations
        for rec1 in analysis1.recommendations:
            for rec2 in analysis2.recommendations:
                similarity = difflib.SequenceMatcher(None, rec1.lower(), rec2.lower()).ratio()
                if similarity > 0.6:
                    agreements.append(f"Both recommend: {rec1}")
                    break
        
        # Compare concerns
        for concern1 in analysis1.concerns:
            for concern2 in analysis2.concerns:
                similarity = difflib.SequenceMatcher(None, concern1.lower(), concern2.lower()).ratio()
                if similarity > 0.6:
                    agreements.append(f"Both concerned about: {concern1}")
                    break
        
        return agreements
    
    def _find_disagreements(self, analysis1: ArgumentAnalysis, analysis2: ArgumentAnalysis) -> List[str]:
        """Find areas of disagreement between two analyses"""
        disagreements = []
        
        # Check position disagreement
        if abs(self.position_indicators[analysis1.position]["weight"] - 
               self.position_indicators[analysis2.position]["weight"]) > 0.4:
            disagreements.append(
                f"Position difference: Claude is {analysis1.position.value}, "
                f"Gemini is {analysis2.position.value}"
            )
        
        # Find unique concerns
        unique_concerns1 = set(analysis1.concerns) - set(analysis2.concerns)
        unique_concerns2 = set(analysis2.concerns) - set(analysis1.concerns)
        
        if unique_concerns1:
            disagreements.append(f"Claude uniquely concerned about: {', '.join(unique_concerns1)}")
        if unique_concerns2:
            disagreements.append(f"Gemini uniquely concerned about: {', '.join(unique_concerns2)}")
        
        return disagreements
    
    def _calculate_consensus_level(self, position_alignment: float, agreements: int, 
                                  disagreements: int, conf1: float, conf2: float) -> float:
        """Calculate overall consensus level"""
        # Weighted components
        position_weight = 0.4
        agreement_weight = 0.3
        confidence_weight = 0.3
        
        # Calculate agreement ratio
        total_points = agreements + disagreements
        agreement_ratio = agreements / total_points if total_points > 0 else 0.5
        
        # Average confidence
        avg_confidence = (conf1 + conf2) / 2
        
        # Calculate weighted consensus
        consensus = (
            position_alignment * position_weight +
            agreement_ratio * agreement_weight +
            avg_confidence * confidence_weight
        )
        
        return min(1.0, max(0.0, consensus))
    
    def _calculate_argument_confidence(self, position_conf: float, 
                                     num_points: int, num_recs: int) -> float:
        """Calculate confidence in an argument analysis"""
        # Base confidence from position detection
        confidence = position_conf
        
        # Boost for having clear points and recommendations
        if num_points > 0:
            confidence += 0.1
        if num_recs > 0:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _create_combined_recommendation(self, analysis1: ArgumentAnalysis, 
                                      analysis2: ArgumentAnalysis,
                                      agreements: List[str],
                                      disagreements: List[str],
                                      has_consensus: bool) -> str:
        """Create a combined recommendation based on both analyses"""
        if has_consensus:
            if analysis1.position in [Position.SUPPORT, Position.STRONGLY_SUPPORT]:
                action = "proceed with the proposed approach"
            else:
                action = "reconsider or modify the approach"
            
            recommendation = f"Both AIs recommend to {action}. "
            
            if agreements:
                recommendation += f"Key agreements: {'; '.join(agreements[:2])}. "
            
            if disagreements:
                recommendation += f"Points requiring attention: {'; '.join(disagreements[:1])}"
        else:
            recommendation = "The AIs have divergent views on this proposal. "
            recommendation += f"Claude's position: {analysis1.position.value}. "
            recommendation += f"Gemini's position: {analysis2.position.value}. "
            recommendation += "Further discussion or a tie-breaker may be needed."
        
        return recommendation