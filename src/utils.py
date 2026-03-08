from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TICKER_MAP = dict(CL="CL=F", BZ="BZ=F", NG="NG=F", TTF="TTF=F")

SPREAD_PAIRS = dict(
    oil=dict(numerator="BZ=F", denominator="CL=F", label="Brent / WTI", name_a="Brent (BZ1!)", name_b="WTI (CL1!)"),
    gas=dict(numerator="TTF=F", denominator="NG=F", label="TTF / Henry Hub", name_a="TTF (TTF1!)", name_b="Henry Hub (NG1!)"),
)

DATA_DIR = PROJECT_ROOT / "data"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DEFAULT_PERIOD = "1y"
DEFAULT_SENSITIVITY = 5
DEFAULT_ROLLING_WINDOW = 30
CACHE_MAX_AGE_HOURS = 24
