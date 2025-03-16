import sys
import pytest
import platform
from unittest.mock import MagicMock

# Check if we're running in CI (GitHub Actions) and not on a Raspberry Pi
ON_CI = "GITHUB_ACTIONS" in sys.environ
ON_PI = platform.machine().startswith("arm")

if ON_CI and not ON_PI:
    print("Mocking Raspberry Pi hardware for CI environment.")

    # Mock RPi.GPIO
    sys.modules["RPi"] = MagicMock()
    sys.modules["RPi.GPIO"] = MagicMock()

    # Mock other Raspberry Pi-related libraries
    sys.modules["spidev"] = MagicMock()
    sys.modules["smbus2"] = MagicMock()
    sys.modules["numpy"] = MagicMock()
    sys.modules["PIL"] = MagicMock()
    sys.modules["PIL.Image"] = MagicMock()
    sys.modules["PIL.ImageFont"] = MagicMock()
    sys.modules["PIL.ImageDraw"] = MagicMock()
    
    # Mock Display Library (ST7789, etc.)
    sys.modules["ST7789"] = MagicMock()

    # Mock FearGreedDisplay class if needed
    from feargreeddisplay import FearGreedDisplay
    FearGreedDisplay = MagicMock()

    print("Mocking complete.")

@pytest.fixture
def mock_display():
    """Fixture to provide a mocked display instance."""
    return MagicMock()

@pytest.fixture
def mock_api_response():
    """Fixture to provide a mocked API response."""
    return {"fear_greed_index": 50, "status": "neutral"}
