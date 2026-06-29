"""Package init. Put the PROJECT ROOT on sys.path here (once, before any
submodule runs) so anything under web/backend can `from part_2 import ...`."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
