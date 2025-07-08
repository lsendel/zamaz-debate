"""
Performance tests for Zamaz Debate System
"""
import pytest
import asyncio
import time
import os
import tempfile
import shutil
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.nucleus import DebateNucleus
from src.core.evolution_tracker import EvolutionTracker
from services.ai_client_factory import AIClientFactory
from domain.models import Decision, DecisionType


class TestPerformance:
    """Performance test suite"""
    
    @pytest.fixture
    def nucleus(self):
        """Create nucleus with mock AI clients"""
        # Enable mock mode
        os.environ["USE_MOCK_AI"] = "true"
        nucleus = DebateNucleus()
        yield nucleus
        # Cleanup
        os.environ["USE_MOCK_AI"] = "false"
    
    @pytest.fixture
    def temp_evolution_dir(self):
        """Create temporary directory for evolution data"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_simple_decision_performance(self, nucleus):
        """Test performance of simple decisions"""
        start_time = time.time()
        
        # Run 100 simple decisions
        tasks = []
        for i in range(100):
            question = f"Should we rename variable_{i}?"
            tasks.append(nucleus.decide(question))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # All should be simple decisions
        assert all(r["method"] == "direct" for r in results)
        assert all(r["rounds"] == 0 for r in results)
        
        # Should complete 100 simple decisions in under 2 seconds
        assert duration < 2.0, f"Simple decisions took {duration:.2f}s, expected < 2s"
        
        # Calculate throughput
        throughput = len(results) / duration
        print(f"\nSimple decision throughput: {throughput:.1f} decisions/second")
    
    @pytest.mark.asyncio
    async def test_complex_decision_performance(self, nucleus):
        """Test performance of complex decisions with debates"""
        start_time = time.time()
        
        # Run 10 complex decisions
        tasks = []
        for i in range(10):
            question = f"What architecture pattern should we use for feature_{i}?"
            tasks.append(nucleus.decide(question))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # All should be debate decisions
        assert all(r["method"] == "debate" for r in results)
        assert all(r["rounds"] > 0 for r in results)
        
        # Should complete 10 debates in under 10 seconds with mocks
        assert duration < 10.0, f"Complex decisions took {duration:.2f}s, expected < 10s"
        
        # Calculate throughput
        throughput = len(results) / duration
        print(f"\nComplex decision throughput: {throughput:.1f} decisions/second")
    
    def test_evolution_tracker_performance(self, temp_evolution_dir):
        """Test evolution tracker performance with many evolutions"""
        # Use temporary directory to avoid conflicts
        tracker = EvolutionTracker(evolutions_dir=temp_evolution_dir)
        
        start_time = time.time()
        
        # Add 1000 evolutions
        successful_adds = 0
        for i in range(1000):
            evolution = {
                "type": "feature",
                "feature": f"feature_{i}",
                "description": f"Add feature number {i}",
                "debate_id": f"debate_{i}"
            }
            if tracker.add_evolution(evolution):
                successful_adds += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in under 40 seconds (file I/O is slow)
        assert duration < 40.0, f"Adding evolutions took {duration:.2f}s, expected < 40s"
        
        # Check duplicate detection is working
        assert successful_adds == 1000  # All should be unique
        
        # Test duplicate detection performance
        dup_start = time.time()
        duplicate_evolution = {
            "type": "feature",
            "feature": "feature_500",
            "description": "Add feature number 500",
            "debate_id": "debate_500"
        }
        result = tracker.add_evolution(duplicate_evolution)
        dup_end = time.time()
        
        assert result is False  # Should be detected as duplicate
        assert dup_end - dup_start < 0.1  # Duplicate check should be fast
        
        print(f"\nEvolution tracker throughput: {successful_adds / duration:.1f} evolutions/second")
    
    @pytest.mark.asyncio
    async def test_concurrent_decision_performance(self, nucleus):
        """Test performance with concurrent decision requests"""
        start_time = time.time()
        
        # Mix of simple and complex questions
        questions = []
        for i in range(50):
            if i % 5 == 0:
                questions.append(f"What architecture should we use for system_{i}?")
            else:
                questions.append(f"Should we rename var_{i}?")
        
        # Run all concurrently
        tasks = [nucleus.decide(q) for q in questions]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Count decision types
        simple_count = sum(1 for r in results if r["method"] == "direct")
        complex_count = sum(1 for r in results if r["method"] == "debate")
        
        assert simple_count == 40
        assert complex_count == 10
        
        # Should handle mixed load efficiently
        assert duration < 6.0, f"Mixed decisions took {duration:.2f}s, expected < 6s"
        
        throughput = len(results) / duration
        print(f"\nMixed decision throughput: {throughput:.1f} decisions/second")
        print(f"  Simple: {simple_count}, Complex: {complex_count}")
    
    def test_memory_efficiency(self, nucleus):
        """Test memory efficiency with many decisions"""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not installed")
        
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run many decisions synchronously
        for i in range(100):
            question = f"Test question {i}"
            asyncio.run(nucleus.decide(question))
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB for 100 decisions)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.1f}MB"
        
        print(f"\nMemory usage: Initial={initial_memory:.1f}MB, Final={final_memory:.1f}MB, Increase={memory_increase:.1f}MB")
    
    @pytest.mark.asyncio
    async def test_decision_latency(self, nucleus):
        """Test individual decision latency"""
        latencies = []
        
        # Measure latency for 20 simple decisions
        for i in range(20):
            start = time.time()
            await nucleus.decide(f"Should we rename x_{i}?")
            end = time.time()
            latencies.append((end - start) * 1000)  # Convert to ms
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        # Simple decisions should have low latency
        assert avg_latency < 20, f"Average latency {avg_latency:.1f}ms, expected < 20ms"
        assert max_latency < 100, f"Max latency {max_latency:.1f}ms, expected < 100ms"
        
        print(f"\nSimple decision latency: avg={avg_latency:.1f}ms, min={min_latency:.1f}ms, max={max_latency:.1f}ms")
    
    def test_evolution_summary_performance(self, temp_evolution_dir):
        """Test performance of evolution summary generation"""
        tracker = EvolutionTracker(evolutions_dir=temp_evolution_dir)
        
        # Add many evolutions
        for i in range(500):
            evolution = {
                "type": "feature" if i % 3 == 0 else "enhancement",
                "feature": f"feature_{i}",
                "description": f"Description {i}"
            }
            tracker.add_evolution(evolution)
        
        # Test summary generation performance
        start_time = time.time()
        summary = tracker.get_evolution_summary()
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000  # ms
        
        # Summary generation should be fast even with many evolutions
        assert duration < 100, f"Summary generation took {duration:.1f}ms, expected < 100ms"
        assert summary["total_evolutions"] == 500
        
        print(f"\nEvolution summary generation: {duration:.1f}ms for {summary['total_evolutions']} evolutions")
    
    @pytest.mark.asyncio
    async def test_pr_creation_performance(self):
        """Test PR creation performance"""
        from services.pr_service import PRService
        from domain.models import Decision, DecisionType
        from datetime import datetime
        
        # Enable PR creation but not auto-push
        os.environ["CREATE_PR_FOR_DECISIONS"] = "true"
        os.environ["AUTO_PUSH_PR"] = "false"
        
        pr_service = PRService()
        
        # Create sample decision
        decision = Decision(
            id="perf_test_123",
            question="Should we optimize performance?",
            context="Performance is critical",
            decision_text="Yes, optimize performance",
            decision_type=DecisionType.COMPLEX,
            method="debate",
            rounds=2,
            timestamp=datetime.now()
        )
        
        # Measure PR creation time
        start_time = time.time()
        pr = await pr_service.create_pr_for_decision(decision)
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000  # ms
        
        # PR creation should be fast
        assert duration < 500, f"PR creation took {duration:.1f}ms, expected < 500ms"
        assert pr is not False  # Should create PR
        
        print(f"\nPR creation time: {duration:.1f}ms")
        
        # Cleanup
        os.environ["CREATE_PR_FOR_DECISIONS"] = "false"