import sys
import platform
from unittest.mock import MagicMock
import pytest

# If not running on a Raspberry Pi, skip all tests (prevents test collection errors)
if not platform.machine().startswith("arm"):
    pytest.skip("Skipping tests because they require Raspberry Pi hardware", allow_module_level=True)

# Mock RPi.GPIO globally to prevent import errors
sys.modules["RPi"] = MagicMock()
sys.modules["RPi.GPIO"] = MagicMock()
