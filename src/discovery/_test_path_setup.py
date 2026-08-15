import sys, os
from pathlib import Path
# Ensure src is in module search path when tests run
sys.path.append(str(Path(__file__).resolve().parent.parent))
