#!/usr/bin/env python3
"""
Evolution History Tracker for Zamaz Debate System
Prevents repetition of previous evolutions and tracks system changes
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class EvolutionTracker:
    def __init__(self, evolutions_dir: str = None):
        if evolutions_dir is None:
            # Default to data/evolutions relative to project root
            evolutions_dir = Path(__file__).parent.parent.parent / "data" / "evolutions"
        self.evolutions_dir = Path(evolutions_dir)
        self.evolutions_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.evolutions_dir / "evolution_history.json"
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load evolution history from file"""
        if self.history_file.exists():
            with open(self.history_file, "r") as f:
                data = json.load(f)
                # Convert fingerprints list back to set
                if "fingerprints" in data and isinstance(data["fingerprints"], list):
                    data["fingerprints"] = set(data["fingerprints"])
                return data
        return {
            "evolutions": [],
            "fingerprints": set(),
            "created_at": datetime.now().isoformat(),
        }

    def _save_history(self):
        """Save evolution history to file"""
        # Convert set to list for JSON serialization
        history_copy = self.history.copy()
        history_copy["fingerprints"] = list(self.history["fingerprints"])

        with open(self.history_file, "w") as f:
            json.dump(history_copy, f, indent=2)

    def _generate_fingerprint(self, evolution: Dict) -> str:
        """Generate unique fingerprint for an evolution with enhanced deduplication"""
        # Create fingerprint from key aspects of the evolution
        key_parts = [
            evolution.get("type", "").lower().strip(),
            evolution.get("feature", "").lower().strip(),
        ]

        # Include significantly more content for better uniqueness (5x increase)
        description = evolution.get("description", "").lower()
        decision_text = evolution.get("decision_text", "").lower()

        # Include first 1000 chars of description and decision text (vs 200 previously)
        if description:
            key_parts.append(description[:1000])
        if decision_text:
            key_parts.append(decision_text[:1000])

        # Add time-window grouping for hour-based clustering
        if evolution.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(evolution["timestamp"])
                # Group by hour to prevent rapid duplicates
                hour_group = timestamp.strftime("%Y%m%d_%H")
                key_parts.append(f"time_window:{hour_group}")
            except:
                pass

        # Include debate_id if available for extra uniqueness
        if evolution.get("debate_id"):
            key_parts.append(evolution["debate_id"])

        # Enhanced technology recognition - 60+ technical terms
        technology_terms = [
            # Performance & Infrastructure
            "performance", "optimization", "caching", "redis", "memcached", "cdn",
            "load balancing", "scaling", "horizontal scaling", "vertical scaling",
            "profiling", "benchmarking", "metrics", "telemetry", "observability",
            
            # Security & Authentication
            "security", "authentication", "authorization", "oauth", "jwt", "ssl", "tls",
            "encryption", "hashing", "vulnerability", "audit", "compliance", "gdpr",
            
            # Development & Testing
            "testing", "unit test", "integration test", "e2e test", "test coverage",
            "testing framework", "jest", "pytest", "selenium", "cypress", "junit",
            "debugging", "profiler", "diagnostic", "logging", "monitoring",
            
            # Architecture & Design
            "architecture", "microservices", "monolith", "api", "rest", "graphql",
            "websocket", "grpc", "message queue", "kafka", "rabbitmq", "pubsub",
            "database", "sql", "nosql", "mongodb", "postgresql", "mysql",
            
            # DevOps & Deployment  
            "docker", "kubernetes", "k8s", "container", "deployment", "ci/cd",
            "jenkins", "github actions", "terraform", "ansible", "helm",
            
            # Frontend & UI
            "ui", "ux", "frontend", "react", "vue", "angular", "javascript",
            "typescript", "css", "html", "responsive", "mobile", "accessibility",
            
            # Backend & Services
            "backend", "server", "nodejs", "python", "java", "golang", "rust",
            "api gateway", "service mesh", "istio", "nginx", "apache",
            
            # Data & Analytics
            "analytics", "data", "etl", "pipeline", "spark", "hadoop", "elasticsearch",
            "search", "indexing", "machine learning", "ai", "ml", "data science",
            
            # Quality & Maintenance
            "refactor", "refactoring", "code quality", "technical debt", "linting",
            "static analysis", "code review", "documentation", "readme", "api doc",
            
            # Business Logic
            "validation", "business logic", "workflow", "automation", "integration",
            "plugin", "extension", "webhook", "notification", "event", "async"
        ]

        # Extract specific technical content for generic features
        combined_text = (description + " " + decision_text).lower()
        
        # Add found technology terms to fingerprint for specificity
        for tech_term in technology_terms:
            if tech_term in combined_text:
                key_parts.append(f"tech:{tech_term}")

        # Extract specific content patterns for common generic features
        if evolution.get("feature") == "performance_optimization":
            # Look for specific performance areas mentioned
            perf_specifics = self._extract_performance_specifics(combined_text)
            key_parts.extend(perf_specifics)
            
        elif evolution.get("feature") in ["improvement_enhancement", "enhancement_improvement"]:
            # Look for what specifically is being improved
            improvement_specifics = self._extract_improvement_specifics(combined_text)
            key_parts.extend(improvement_specifics)

        content = "|".join(sorted(set(filter(None, key_parts))))  # Sort and dedupe for consistency
        # Use longer hash (64 chars) for better uniqueness vs previous 32
        return hashlib.sha256(content.encode()).hexdigest()[:64]

    def _extract_performance_specifics(self, text: str) -> List[str]:
        """Extract specific performance optimization areas from text"""
        specifics = []
        perf_patterns = {
            "database": ["database", "query", "sql", "index", "connection pool"],
            "memory": ["memory", "heap", "garbage collection", "leak", "allocation"],
            "cpu": ["cpu", "processor", "thread", "concurrency", "parallel"],
            "network": ["network", "latency", "bandwidth", "http", "tcp"],
            "cache": ["cache", "caching", "redis", "memcached", "browser cache"],
            "frontend": ["frontend", "rendering", "dom", "javascript", "css"],
            "algorithm": ["algorithm", "complexity", "optimization", "efficiency"],
            "io": ["disk", "file", "storage", "read", "write", "streaming"]
        }
        
        for category, patterns in perf_patterns.items():
            if any(pattern in text for pattern in patterns):
                specifics.append(f"perf_area:{category}")
        
        return specifics

    def _extract_improvement_specifics(self, text: str) -> List[str]:
        """Extract specific improvement areas from generic improvement features"""
        specifics = []
        improvement_patterns = {
            "architecture": ["architecture", "design", "pattern", "structure"],
            "code_quality": ["code quality", "refactor", "clean", "maintainable"],
            "testing": ["test", "coverage", "quality assurance", "validation"],
            "documentation": ["documentation", "readme", "guide", "manual"],
            "usability": ["usability", "user experience", "interface", "workflow"],
            "reliability": ["reliability", "stability", "error handling", "resilience"],
            "security": ["security", "authentication", "encryption", "vulnerability"],
            "performance": ["performance", "speed", "optimization", "efficiency"]
        }
        
        for category, patterns in improvement_patterns.items():
            if any(pattern in text for pattern in patterns):
                specifics.append(f"improvement_area:{category}")
        
        return specifics

    def is_duplicate(self, evolution: Dict) -> bool:
        """Check if evolution is similar to previous ones using enhanced multi-layer detection"""
        # Layer 1: Primary fingerprint-based detection
        fingerprint = self._generate_fingerprint(evolution)
        if fingerprint in self.history["fingerprints"]:
            return True
        
        # Layer 2: Time-based duplicate checking (60-minute window)
        if self._check_time_based_duplicates(evolution):
            return True
        
        # Layer 3: Semantic similarity analysis (70% threshold)
        if self._check_semantic_similarity(evolution):
            return True
        
        # Layer 4: Text similarity using Jaccard coefficient
        if self._check_text_similarity(evolution):
            return True
        
        return False
    
    def _check_time_based_duplicates(self, evolution: Dict) -> bool:
        """Check for duplicates within 60-minute time window"""
        current_feature = evolution.get("feature", "")
        current_type = evolution.get("type", "")
        
        # Get current time or use provided timestamp
        current_time = datetime.now()
        if evolution.get("timestamp"):
            try:
                current_time = datetime.fromisoformat(evolution["timestamp"])
            except:
                pass
        
        # Check last 20 evolutions for time-based duplicates
        recent_evolutions = self.get_recent_evolutions(20)
        
        for recent_evo in recent_evolutions:
            try:
                recent_time = datetime.fromisoformat(recent_evo["timestamp"])
                time_diff = abs((current_time - recent_time).total_seconds())
                
                # Within 60-minute window (3600 seconds)
                if time_diff <= 3600:
                    # Same feature and type within time window = duplicate
                    if (current_feature == recent_evo.get("feature", "") and 
                        current_type == recent_evo.get("type", "")):
                        return True
                        
                    # Performance optimization within time window = likely duplicate
                    if (current_feature == "performance_optimization" and 
                        recent_evo.get("feature") == "performance_optimization"):
                        return True
                        
            except:
                continue
        
        return False
    
    def _check_text_similarity(self, evolution: Dict) -> bool:
        """Check for text similarity using Jaccard coefficient"""
        current_desc = evolution.get("description", "").lower()
        if not current_desc or len(current_desc) < 50:
            return False
            
        # Get words from current description
        current_words = set(current_desc.split())
        
        # Remove common stop words for better comparison
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
                     "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
                     "have", "has", "had", "do", "does", "did", "will", "would", "should",
                     "could", "may", "might", "must", "shall", "can", "this", "that", "these", 
                     "those", "i", "you", "he", "she", "it", "we", "they"}
        current_words = current_words - stop_words
        
        if len(current_words) < 5:
            return False
        
        # Check recent evolutions for text similarity
        recent_evolutions = self.get_recent_evolutions(15)
        
        for recent_evo in recent_evolutions:
            recent_desc = recent_evo.get("description", "").lower()
            if not recent_desc:
                continue
                
            recent_words = set(recent_desc.split()) - stop_words
            if len(recent_words) < 5:
                continue
            
            # Calculate Jaccard similarity coefficient
            intersection = len(current_words & recent_words)
            union = len(current_words | recent_words)
            
            if union > 0:
                jaccard_similarity = intersection / union
                # 60% text similarity threshold
                if jaccard_similarity > 0.6:
                    return True
        
        return False
    
    def _check_semantic_similarity(self, evolution: Dict) -> bool:
        """Check for semantic similarity with recent evolutions"""
        current_feature = evolution.get("feature", "")
        current_type = evolution.get("type", "")
        current_description = evolution.get("description", "").lower()
        
        # Get recent evolutions (last 10) for comparison
        recent_evolutions = self.get_recent_evolutions(10)
        
        for recent_evo in recent_evolutions:
            # Check for exact feature match
            if current_feature == recent_evo.get("feature", ""):
                return True
            
            # Check for similar features (e.g., performance_optimization variants)
            if self._are_features_similar(current_feature, recent_evo.get("feature", "")):
                return True
            
            # Check for similar content in descriptions
            if self._are_descriptions_similar(current_description, recent_evo.get("description", "").lower()):
                return True
        
        return False
    
    def _are_features_similar(self, feature1: str, feature2: str) -> bool:
        """Check if two features are semantically similar"""
        if not feature1 or not feature2:
            return False
        
        # Define feature similarity groups
        similar_groups = [
            {"performance_optimization", "performance_profiling", "performance_enhancement", "optimization_enhancement"},
            {"testing_framework", "automated_testing", "test_suite", "testing_enhancement"},
            {"security_enhancement", "security_hardening", "security_audit"},
            {"error_handling", "resilience", "error_recovery"},
            {"monitoring_system", "observability_system", "metrics_system"},
            {"logging_system", "audit_trail", "logging_enhancement"},
            {"user_interface", "ui_enhancement", "frontend_enhancement"},
            {"api_enhancement", "rest_api", "api_design"},
            {"caching_system", "cache_enhancement", "memory_cache"},
            {"database_system", "persistence", "storage_system"},
            {"webhook_system", "notification_system", "event_system"},
            {"documentation", "api_doc", "readme_enhancement"},
        ]
        
        # Check if both features belong to the same similarity group
        for group in similar_groups:
            if feature1 in group and feature2 in group:
                return True
        
        return False
    
    def _are_descriptions_similar(self, desc1: str, desc2: str) -> bool:
        """Check if two descriptions are semantically similar"""
        if not desc1 or not desc2:
            return False
        
        # Simple similarity check based on common words
        words1 = set(desc1.split())
        words2 = set(desc2.split())
        
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "may", "might", "must", "shall", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "her", "its", "our", "their"}
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        if union == 0:
            return False
        
        similarity = intersection / union
        
        # Consider similar if >70% word overlap
        return similarity > 0.7

    def add_evolution(self, evolution: Dict) -> bool:
        """Add new evolution if it's not a duplicate and is valid"""
        # Validate evolution before adding
        if not self._validate_evolution(evolution):
            return False
        
        if self.is_duplicate(evolution):
            return False

        fingerprint = self._generate_fingerprint(evolution)

        # Add metadata and impact scoring
        evolution["id"] = f"evo_{len(self.history['evolutions']) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        evolution["timestamp"] = datetime.now().isoformat()
        evolution["fingerprint"] = fingerprint
        evolution["impact_score"] = self._calculate_impact_score(evolution)
        evolution["validation_status"] = "validated"

        # Add to history
        self.history["evolutions"].append(evolution)
        self.history["fingerprints"].add(fingerprint)

        # Save to file
        self._save_history()
        self._save_evolution_detail(evolution)

        return True
    
    def _validate_evolution(self, evolution: Dict) -> bool:
        """Validate evolution structure and content"""
        required_fields = ["type", "feature", "description"]
        
        # Check required fields
        for field in required_fields:
            if field not in evolution or not evolution[field]:
                print(f"Evolution validation failed: missing {field}")
                return False
        
        # Validate evolution type
        valid_types = ["feature", "enhancement", "fix", "refactor", "documentation", "security", "performance", "testing"]
        if evolution["type"] not in valid_types:
            print(f"Evolution validation failed: invalid type '{evolution['type']}'. Must be one of: {valid_types}")
            return False
        
        # Validate feature name format
        feature = evolution["feature"]
        if len(feature) < 3 or len(feature) > 50:
            print(f"Evolution validation failed: feature name must be 3-50 characters")
            return False
        
        # Validate description length
        description = evolution["description"]
        if len(description) < 10 or len(description) > 5000:
            print(f"Evolution validation failed: description must be 10-5000 characters")
            return False
        
        return True
    
    def _calculate_impact_score(self, evolution: Dict) -> float:
        """Calculate the potential impact score of an evolution"""
        score = 0.0
        
        # Base score by type
        type_scores = {
            "security": 10.0,
            "fix": 8.0,
            "performance": 7.0,
            "testing": 6.0,
            "feature": 5.0,
            "enhancement": 4.0,
            "refactor": 3.0,
            "documentation": 2.0,
        }
        
        score += type_scores.get(evolution.get("type", ""), 1.0)
        
        # Feature-specific scoring
        feature = evolution.get("feature", "").lower()
        high_impact_features = [
            "evolution_system_enhancement", "security_enhancement", "testing_framework",
            "error_handling", "performance_profiling", "observability_system"
        ]
        
        if any(hif in feature for hif in high_impact_features):
            score += 3.0
        
        # Priority-based scoring
        priority = evolution.get("priority", "medium")
        priority_multipliers = {"high": 1.5, "medium": 1.0, "low": 0.7}
        score *= priority_multipliers.get(priority, 1.0)
        
        # Freshness bonus (encourage diversity)
        recent_features = [evo.get("feature", "") for evo in self.get_recent_evolutions(5)]
        if evolution.get("feature", "") not in recent_features:
            score += 2.0
        
        # Complexity bonus based on description length and technical terms
        description = evolution.get("description", "").lower()
        technical_terms = ["architecture", "algorithm", "optimization", "integration", "framework", "system", "infrastructure"]
        tech_count = sum(1 for term in technical_terms if term in description)
        score += min(tech_count * 0.5, 2.0)
        
        return round(score, 2)

    def _save_evolution_detail(self, evolution: Dict):
        """Save detailed evolution record"""
        filename = self.evolutions_dir / f"{evolution['id']}.json"
        with open(filename, "w") as f:
            json.dump(evolution, f, indent=2)

    def get_recent_evolutions(self, limit: int = 10) -> List[Dict]:
        """Get most recent evolutions"""
        return self.history["evolutions"][-limit:]

    def should_evolve(self) -> bool:
        """Check if evolution should proceed based on throttling rules"""
        recent_evolutions = self.get_recent_evolutions(10)

        # Check time since last evolution (5 minute cooldown)
        if recent_evolutions:
            last_evolution = recent_evolutions[-1]
            last_time = datetime.fromisoformat(last_evolution["timestamp"])
            time_since_last = (datetime.now() - last_time).seconds
            if time_since_last < 300:  # 5 minutes
                print(f"⏳ Evolution throttled: Only {time_since_last}s since last evolution (need 300s)")
                return False

        # Check for too many recent evolutions (max 5 in last hour)
        one_hour_ago = datetime.now().timestamp() - 3600
        recent_count = sum(
            1 for evo in recent_evolutions if datetime.fromisoformat(evo["timestamp"]).timestamp() > one_hour_ago
        )
        if recent_count >= 5:
            print(f"⏳ Evolution throttled: {recent_count} evolutions in last hour (max 5)")
            return False

        return True

    def get_evolution_summary(self) -> Dict:
        """Get comprehensive summary of evolution history"""
        evolutions = self.history["evolutions"]

        if not evolutions:
            return {
                "total_evolutions": 0,
                "evolution_types": {},
                "last_evolution": None,
                "diversity_score": 0.0,
                "avg_impact_score": 0.0,
            }

        # Count evolution types
        type_counts = {}
        feature_counts = {}
        impact_scores = []
        
        for evo in evolutions:
            evo_type = evo.get("type", "unknown")
            type_counts[evo_type] = type_counts.get(evo_type, 0) + 1
            
            feature = evo.get("feature", "unknown")
            feature_counts[feature] = feature_counts.get(feature, 0) + 1
            
            impact_score = evo.get("impact_score", 0.0)
            if isinstance(impact_score, (int, float)):
                impact_scores.append(impact_score)

        # Calculate diversity score (0-1, higher is more diverse)
        diversity_score = self._calculate_diversity_score(type_counts, feature_counts, len(evolutions))
        
        # Calculate average impact score
        avg_impact_score = sum(impact_scores) / len(impact_scores) if impact_scores else 0.0

        return {
            "total_evolutions": len(evolutions),
            "evolution_types": type_counts,
            "feature_distribution": feature_counts,
            "last_evolution": evolutions[-1],
            "first_evolution": evolutions[0] if evolutions else None,
            "diversity_score": round(diversity_score, 2),
            "avg_impact_score": round(avg_impact_score, 2),
            "high_impact_evolutions": len([s for s in impact_scores if s >= 8.0]),
            "duplicate_prevention_active": len(self.history["fingerprints"]) > 0,
        }
    
    def _calculate_diversity_score(self, type_counts: Dict, feature_counts: Dict, total: int) -> float:
        """Calculate diversity score for evolution history"""
        if total == 0:
            return 0.0
        
        # Calculate entropy for types
        type_entropy = 0.0
        for count in type_counts.values():
            p = count / total
            if p > 0:
                type_entropy -= p * (p ** 0.5)  # Modified entropy formula
        
        # Calculate feature diversity (penalize repeated features)
        feature_penalty = 0.0
        for count in feature_counts.values():
            if count > 1:
                feature_penalty += (count - 1) * 0.1
        
        # Combine scores
        diversity_score = max(0.0, type_entropy - feature_penalty)
        return min(1.0, diversity_score)  # Cap at 1.0
    
    def get_evolution_recommendations(self) -> List[Dict]:
        """Get recommendations for improving evolution diversity"""
        summary = self.get_evolution_summary()
        recommendations = []
        
        # Analyze type distribution
        type_counts = summary.get("evolution_types", {})
        total_evolutions = summary.get("total_evolutions", 0)
        
        if total_evolutions > 0:
            # Check for missing important types
            important_types = ["security", "testing", "fix", "refactor"]
            for itype in important_types:
                if type_counts.get(itype, 0) == 0:
                    recommendations.append({
                        "type": "missing_evolution_type",
                        "recommendation": f"Consider adding {itype} evolutions",
                        "priority": "high" if itype in ["security", "testing"] else "medium"
                    })
            
            # Check for imbalanced distribution
            max_count = max(type_counts.values()) if type_counts else 0
            if max_count > total_evolutions * 0.7:  # One type dominates >70%
                dominant_type = max(type_counts, key=type_counts.get)
                recommendations.append({
                    "type": "imbalanced_evolution_types",
                    "recommendation": f"Reduce focus on {dominant_type} evolutions, diversify",
                    "priority": "medium"
                })
        
        # Check diversity score
        diversity_score = summary.get("diversity_score", 0.0)
        if diversity_score < 0.3:
            recommendations.append({
                "type": "low_diversity",
                "recommendation": "Evolution history shows low diversity. Focus on different types and features.",
                "priority": "high"
            })
        
        return recommendations
    
    def rollback_evolution(self, evolution_id: str) -> bool:
        """Rollback a specific evolution (mark as inactive)"""
        for evo in self.history["evolutions"]:
            if evo.get("id") == evolution_id:
                evo["status"] = "rolled_back"
                evo["rollback_timestamp"] = datetime.now().isoformat()
                self._save_history()
                return True
        return False
    
    def get_active_evolutions(self) -> List[Dict]:
        """Get only active (non-rolled-back) evolutions"""
        return [evo for evo in self.history["evolutions"] if evo.get("status") != "rolled_back"]

    def suggest_next_evolution(self, debate_results: Dict) -> Optional[Dict]:
        """Analyze debate results and suggest next evolution"""
        # Extract key suggestions from debate
        claude_suggestion = debate_results.get("claude", "")
        gemini_suggestion = debate_results.get("gemini", "")

        # Parse suggestions to extract evolution type and feature
        evolution = {
            "type": self._extract_evolution_type(claude_suggestion, gemini_suggestion),
            "feature": self._extract_feature(claude_suggestion, gemini_suggestion),
            "description": f"Based on debate consensus: {debate_results.get('final_decision', '')}",
            "debate_id": debate_results.get("id", ""),
            "priority": self._determine_priority(claude_suggestion, gemini_suggestion),
        }

        # Check if it's a duplicate
        if not self.is_duplicate(evolution):
            return evolution

        return None

    def _extract_evolution_type(self, claude: str, gemini: str) -> str:
        """Extract evolution type from AI suggestions"""
        types = [
            "feature",
            "enhancement",
            "refactor",
            "fix",
            "optimization",
            "architecture",
        ]

        combined_text = (claude + " " + gemini).lower()

        for evo_type in types:
            if evo_type in combined_text:
                return evo_type

        return "feature"  # default

    def _extract_feature(self, claude: str, gemini: str) -> str:
        """Extract main feature from suggestions using advanced pattern matching"""
        combined_text = (claude + " " + gemini).lower()
        
        # Comprehensive feature patterns with priority ordering
        feature_patterns = [
            # High-priority specific features
            (["evolution system", "evolution tracking", "evolution audit", "meta-system"], "evolution_system_enhancement"),
            (["testing framework", "unit test", "integration test", "test suite", "test coverage"], "testing_framework"),
            (["security hardening", "security audit", "vulnerability", "authentication"], "security_enhancement"),
            (["performance profiling", "performance monitor", "performance metric"], "performance_profiling"),
            (["observability", "monitoring", "telemetry", "observability stack"], "observability_system"),
            (["error handling", "exception handling", "error recovery", "resilience"], "error_handling"),
            (["caching system", "cache", "redis", "memory cache"], "caching_system"),
            (["rate limiting", "throttling", "rate limit"], "rate_limiting"),
            (["configuration management", "config", "environment"], "configuration_management"),
            (["documentation", "readme", "docs", "api doc"], "documentation"),
            (["user interface", "ui", "frontend", "user experience"], "user_interface"),
            (["api enhancement", "rest api", "graphql", "api design"], "api_enhancement"),
            (["database", "persistence", "storage", "sql"], "database_system"),
            (["logging", "log", "audit trail"], "logging_system"),
            (["plugin", "extension", "addon", "module"], "plugin_architecture"),
            (["refactoring", "code quality", "clean code", "technical debt"], "code_refactoring"),
            (["validation", "input validation", "data validation"], "validation_system"),
            (["metrics", "analytics", "tracking", "telemetry"], "metrics_system"),
            (["webhook", "notification", "event", "callback"], "webhook_system"),
            (["deployment", "devops", "ci/cd", "docker"], "deployment_system"),
            (["backup", "recovery", "disaster recovery"], "backup_system"),
            (["search", "indexing", "elasticsearch", "full-text"], "search_system"),
            (["queue", "message queue", "async processing"], "queue_system"),
            (["scaling", "load balancing", "horizontal scaling"], "scaling_system"),
            (["debugging", "debug", "profiler", "diagnostic"], "debugging_tools"),
            # Generic performance patterns
            (["performance optimization", "optimize", "performance"], "performance_optimization"),
        ]
        
        # Find the most specific matching pattern
        for patterns, feature_name in feature_patterns:
            if any(pattern in combined_text for pattern in patterns):
                return feature_name
        
        # Advanced extraction for complex suggestions
        # Look for domain-specific terms
        domain_terms = {
            "ai": "ai_enhancement",
            "machine learning": "ml_enhancement",
            "debate": "debate_enhancement",
            "decision": "decision_enhancement",
            "workflow": "workflow_enhancement",
            "automation": "automation_enhancement",
            "integration": "integration_enhancement",
            "architecture": "architecture_enhancement",
        }
        
        for term, feature in domain_terms.items():
            if term in combined_text:
                return feature
        
        # Fallback: try to extract from key action words
        action_features = {
            "implement": "implementation_enhancement",
            "improve": "improvement_enhancement",
            "enhance": "enhancement_improvement",
            "optimize": "optimization_enhancement",
            "refactor": "refactoring_enhancement",
            "integrate": "integration_enhancement",
            "monitor": "monitoring_enhancement",
        }
        
        for action, feature in action_features.items():
            if action in combined_text:
                return feature
        
        # Last resort: use hash of content for uniqueness
        import hashlib
        content_hash = hashlib.md5(combined_text.encode()).hexdigest()[:8]
        return f"custom_improvement_{content_hash}"

    def _determine_priority(self, claude: str, gemini: str) -> str:
        """Determine priority based on AI emphasis"""
        high_priority_words = ["critical", "essential", "must", "immediately", "urgent"]
        medium_priority_words = ["should", "important", "beneficial", "recommended"]

        combined = (claude + " " + gemini).lower()

        if any(word in combined for word in high_priority_words):
            return "high"
        elif any(word in combined for word in medium_priority_words):
            return "medium"

        return "low"


if __name__ == "__main__":
    # Test the tracker
    tracker = EvolutionTracker()

    # Example evolution
    test_evolution = {
        "type": "feature",
        "feature": "performance_tracking",
        "description": "Add performance tracking with outcome measurement",
    }

    if tracker.add_evolution(test_evolution):
        print("Evolution added successfully!")
    else:
        print("Duplicate evolution detected!")

    print(f"\nEvolution Summary: {json.dumps(tracker.get_evolution_summary(), indent=2)}")
