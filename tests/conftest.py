"""Configure pytest to find the dashboard_weather package."""

import sys
from pathlib import Path

# Add project root to sys.path so `dashboard_weather` is importable
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
