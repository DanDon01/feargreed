import pytest
import psutil
import platform
from feargreeddisplay import API_CACHE, Config, load_gif_frames


# Skip test if not running on Raspberry Pi (These two lines are for GitHub Actions only and can be removed if not using it)
if not platform.machine().startswith("arm"):
    pytest.skip("Skipping test because it's not running on a Raspberry Pi", allow_module_level=True)


def test_memory_management():
    """Test memory optimization features"""
    initial_memory = psutil.virtual_memory().available
    
    # Test GIF frame limiting
    frames = load_gif_frames("gifs/animations/bitcoinspin1_opt.gif")
    assert len(frames) <= 20, "Frame limit exceeded"
    
    # Check memory usage
    final_memory = psutil.virtual_memory().available
    memory_diff = initial_memory - final_memory
    assert memory_diff < 50 * 1024 * 1024, "Memory usage too high"

def test_api_cache():
    """Test API caching system"""
    from feargreeddisplay import get_fear_greed_index
    
    # First call should populate cache
    result1, value1 = get_fear_greed_index()
    assert 'fear_greed' in API_CACHE
    assert API_CACHE['fear_greed']['data'] is not None
    
    # Second call should use cache
    result2, value2 = get_fear_greed_index()
    assert result1 == result2, "Cache not being used"

def test_config_persistence():
    """Test configuration save/load"""
    config = Config()
    config.led_brightness = 0.75
    config.save()
    
    loaded_config = Config.load()
    assert loaded_config.led_brightness == 0.75

def test_placeholder():
    """Basic test to verify CI pipeline is working"""
    assert True

def test_sample_calculation():
    """Sample test demonstrating pytest functionality"""
    expected = 4
    actual = 2 + 2
    assert actual == expected