import pytest
from feargreeddisplay import FearGreedDisplay

def test_fear_greed_ranges():
    """Test fear/greed index categorization"""
    display = FearGreedDisplay()
    
    test_cases = [
        (0, "extreme_fear"),
        (25, "extreme_fear"),
        (26, "fear"),
        (45, "fear"),
        (50, "neutral"),
        (76, "extreme_greed")
    ]
    
    for value, expected in test_cases:
        assert display.get_sentiment(value) == expected, f"Failed for value: {value}"

def test_display_initialization():
    """Test basic display setup"""
    try:
        display = FearGreedDisplay()
        assert display is not None
    except Exception as e:
        pytest.fail(f"Display initialization failed: {str(e)}")

def test_gif_folder_structure():
    """Test required folders exist"""
    import os
    
    required_paths = [
        "gifs/fear_greed",
        "gifs/money_flow",
        "gifs/animations",
        "gifs/incoming"
    ]
    
    for path in required_paths:
        assert os.path.exists(path), f"Missing required folder: {path}"