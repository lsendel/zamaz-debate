"""
Tests for utility modules
"""
import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock, mock_open
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))


class TestLocalhostChecker:
    """Test suite for localhost checker functions"""
    
    @pytest.mark.asyncio
    async def test_check_localhost(self):
        """Test check_localhost function"""
        from src.utils import localhost_checker
        
        # Mock pyppeteer launch
        with patch('src.utils.localhost_checker.launch') as mock_launch:
            # Mock browser and page
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_page.title = AsyncMock(return_value="Test Title")
            mock_page.content = AsyncMock(return_value="<html><body>Test Content</body></html>")
            mock_page.screenshot = AsyncMock()
            mock_page.close = AsyncMock()
            
            mock_browser = AsyncMock()
            mock_browser.newPage = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()
            
            mock_launch.return_value = mock_browser
            
            # Mock file operations
            with patch('builtins.open', mock_open()):
                with patch('os.makedirs'):
                    await localhost_checker.check_localhost("http://localhost:8000", "test_output")
            
            # Verify browser was launched
            mock_launch.assert_called_once()
            # Check that goto was called with the URL (ignore the exact options format)
            assert mock_page.goto.called
            assert mock_page.goto.call_args[0][0] == "http://localhost:8000"
    
    @pytest.mark.asyncio
    async def test_check_localhost_error_handling(self):
        """Test error handling in check_localhost"""
        from src.utils import localhost_checker
        
        # Mock a browser that will raise error during navigation
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Navigation error"))
        mock_page.screenshot = AsyncMock()
        
        mock_browser = AsyncMock()
        mock_browser.newPage = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()
        
        with patch('src.utils.localhost_checker.launch', return_value=mock_browser):
            with patch('builtins.print') as mock_print:
                with patch('os.makedirs'):
                    await localhost_checker.check_localhost("http://localhost:8000")
                
                # Verify error was printed
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("Error accessing" in call for call in print_calls)
    
    def test_main_function(self):
        """Test main function"""
        from src.utils import localhost_checker
        
        with patch('asyncio.run') as mock_run:
            with patch('sys.argv', ['localhost_checker.py', 'http://localhost:3000']):
                # Import and run the main block
                with patch.object(localhost_checker, '__name__', '__main__'):
                    exec(open('src/utils/localhost_checker.py').read(), {'__name__': '__main__'})
                    
                    # asyncio.run should have been called
                    assert mock_run.called


class TestSelfImprove:
    """Test suite for self improve functions"""
    
    @pytest.mark.asyncio
    async def test_apply_improvement(self):
        """Test apply_improvement function"""
        # Mock DebateNucleus at the correct import path
        with patch('src.core.nucleus.DebateNucleus') as mock_nucleus_class:
            # Configure mock nucleus
            mock_nucleus = Mock()
            mock_nucleus.evolve_self = AsyncMock(return_value={
                'decision': 'Add more unit tests',
                'complexity': 'moderate'
            })
            mock_nucleus_class.return_value = mock_nucleus
            
            # Mock the sys.path insertion and import
            with patch('sys.path', sys.path + []):
                with patch.dict('sys.modules', {'nucleus': MagicMock(DebateNucleus=mock_nucleus_class)}):
                    from src.utils.self_improve import apply_improvement
                    
                    # Mock user input
                    with patch('builtins.input', return_value='n'):
                        with patch('builtins.print') as mock_print:
                            await apply_improvement()
                            
                            # Verify improvement was suggested
                            assert mock_nucleus.evolve_self.called
                            assert any("Add more unit tests" in str(call) for call in mock_print.call_args_list)
                            assert any("Improvement skipped" in str(call) for call in mock_print.call_args_list)
    
    @pytest.mark.asyncio
    async def test_apply_improvement_accepted(self):
        """Test accepting improvement"""
        with patch('src.core.nucleus.DebateNucleus') as mock_nucleus_class:
            # Configure mock nucleus
            mock_nucleus = Mock()
            mock_nucleus.evolve_self = AsyncMock(return_value={
                'decision': 'Refactor code',
                'complexity': 'complex'
            })
            mock_nucleus_class.return_value = mock_nucleus
            
            # Mock the sys.path insertion and import
            with patch('sys.path', sys.path + []):
                with patch.dict('sys.modules', {'nucleus': MagicMock(DebateNucleus=mock_nucleus_class)}):
                    from src.utils.self_improve import apply_improvement
                    
                    # Mock user accepting
                    with patch('builtins.input', return_value='y'):
                        with patch('builtins.print') as mock_print:
                            await apply_improvement()
                            
                            # Verify manual implementation message
                            assert any("implement the improvement manually" in str(call) for call in mock_print.call_args_list)
    
    @pytest.mark.asyncio
    async def test_continuous_improvement(self):
        """Test continuous improvement loop"""
        with patch('src.core.nucleus.DebateNucleus'):
            with patch('sys.path', sys.path + []):
                with patch.dict('sys.modules', {'nucleus': MagicMock()}):
                    from src.utils.self_improve import continuous_improvement, apply_improvement
                    
                    # Mock apply_improvement to break the loop after first iteration
                    call_count = 0
                    async def mock_apply():
                        nonlocal call_count
                        call_count += 1
                        if call_count > 1:
                            raise KeyboardInterrupt()
                    
                    with patch('src.utils.self_improve.apply_improvement', side_effect=mock_apply):
                        with patch('asyncio.sleep', new_callable=AsyncMock):
                            with pytest.raises(KeyboardInterrupt):
                                await continuous_improvement()
                            
                            assert call_count == 2  # Called twice before breaking


class TestEvolutionTracker:
    """Test suite for evolution tracker"""
    
    def test_init(self):
        """Test EvolutionTracker initialization"""
        from src.utils.track_evolution import EvolutionTracker
        
        # Mock the file existence check and loading
        with patch('pathlib.Path.exists', return_value=False):
            tracker = EvolutionTracker()
            
            # Verify attributes
            assert tracker.evolution_file == "evolution_history.json"
            assert tracker.history == []  # Empty when file doesn't exist
    
    def test_record_evolution(self):
        """Test recording evolution"""
        from src.utils.track_evolution import EvolutionTracker
        
        # Initialize tracker with empty history
        with patch('pathlib.Path.exists', return_value=False):
            tracker = EvolutionTracker()
        
        # Mock file operations for record_evolution
        with patch('pathlib.Path.exists', return_value=True):
            # Mock json.dump to capture what was written
            with patch('json.dump') as mock_dump:
                with patch('builtins.open', mock_open(read_data="# Nucleus code")):
                    tracker.record_evolution("v1.0", "Added feature X", "Performance improvement")
                    
                    # Check that json.dump was called with the right data
                    assert mock_dump.called
                    history = mock_dump.call_args[0][0]
                    
                    assert len(history) == 1
                    assert history[0]["version"] == "v1.0"
                    assert history[0]["changes"] == "Added feature X"
                    assert history[0]["reason"] == "Performance improvement"
    
    def test_show_history(self):
        """Test showing evolution history"""
        from src.utils.track_evolution import EvolutionTracker
        
        mock_history = [
            {
                "version": "v1.0",
                "changes": "Initial release",
                "reason": "Bootstrap",
                "timestamp": "2024-01-01T00:00:00",
                "code_size": 1024,
                "code_hash": "abcd1234"
            },
            {
                "version": "v1.1", 
                "changes": "Added caching",
                "reason": "Performance",
                "timestamp": "2024-01-02T00:00:00",
                "code_size": 1536,
                "code_hash": "efgh5678"
            }
        ]
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_history))):
                tracker = EvolutionTracker()
                
                with patch('builtins.print') as mock_print:
                    tracker.show_history()
                    
                    # Verify history was printed
                    print_output = ' '.join(str(call) for call in mock_print.call_args_list)
                    assert "v1.0" in print_output
                    assert "v1.1" in print_output
                    assert "Initial release" in print_output
                    assert "Added caching" in print_output
    
    def test_load_history_with_existing_file(self):
        """Test loading history from existing file"""
        from src.utils.track_evolution import EvolutionTracker
        
        mock_history = [{"version": "v1.0", "changes": "Test"}]
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_history))):
                tracker = EvolutionTracker()
                
                assert tracker.history == mock_history
    
    def test_main_function_track_evolution(self):
        """Test main function of track_evolution module"""
        # Test that main block exists by checking the source
        with open('src/utils/track_evolution.py', 'r') as f:
            source = f.read()
            assert 'if __name__ == "__main__":' in source
            assert 'tracker.show_history()' in source
            assert 'class EvolutionTracker:' in source