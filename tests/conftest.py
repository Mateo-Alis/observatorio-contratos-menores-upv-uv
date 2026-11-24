import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

FIXTURES = Path(__file__).resolve().parent / "fixtures"
