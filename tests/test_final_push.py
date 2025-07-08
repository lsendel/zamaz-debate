"""
Final push to reach 80% coverage
"""
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.track_evolution import EvolutionTracker


class TestFinalPush:
    """Final tests to reach 80%"""
    
    def test_track_evolution_show_empty_history(self):
        """Test show_history with no history to cover lines 53-54"""
        tracker = EvolutionTracker()
        tracker.history = []  # Ensure empty history
        
        with patch('builtins.print') as mock_print:
            tracker.show_history()
            
            # Should print the "no history" message
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("No evolution history yet" in call for call in print_calls)
    
    def test_pr_review_service_error_paths(self):
        """Test error handling in PR review service"""
        from services.pr_review_service import PRReviewService
        
        service = PRReviewService()
        
        # Test merge_pr error handling
        with patch('subprocess.run', side_effect=Exception("Git error")):
            with patch('builtins.print') as mock_print:
                service.merge_pr("test-branch")
                
                # Should print error
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("Error" in call for call in print_calls)
    
    def test_pr_review_service_human_reviewer(self):
        """Test human reviewer path"""
        from services.pr_review_service import PRReviewService
        from domain.models import PullRequest, ImplementationAssignee
        
        service = PRReviewService()
        
        pr = PullRequest(
            id="pr_test",
            title="Test PR",
            body="Test body",
            branch_name="test-branch",
            base_branch="main",
            assignee="human",
            implementation_assignee=ImplementationAssignee.HUMAN
        )
        
        # Test human reviewer path
        with patch('builtins.print') as mock_print:
            result = service.determine_reviewer(pr)
            
            assert result == "human"
    
    def test_track_evolution_record_without_nucleus_file(self):
        """Test recording evolution when nucleus.py doesn't exist"""
        tracker = EvolutionTracker()
        tracker.history = []
        
        # Mock nucleus file not existing (covers lines 31-32)
        with patch('pathlib.Path.exists', return_value=False):
            with patch('builtins.open', create=True) as mock_open:
                # Mock the file write
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                with patch('json.dump'):
                    tracker.record_evolution("v2.0", "New feature", "Enhancement")
                    
                    # Should have code_hash as N/A
                    assert len(tracker.history) == 1
                    assert tracker.history[0]["code_hash"] == "N/A"
                    assert tracker.history[0]["code_size"] == 0