from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TICKER_MAP = dict(CL="CL=F", BZ="BZ=F", NG="NG=F", TTF="TTF=F", GC="GC=F", SI="SI=F")

SPREAD_PAIRS = dict(
    oil=dict(numerator="BZ=F", denominator="CL=F", label="Brent / WTI",
             name_a="Brent (BZ1!)", name_b="WTI (CL1!)", category="oil markets", tab="Oil"),
    gas=dict(numerator="TTF=F", denominator="NG=F", label="TTF / Henry Hub",
             name_a="TTF (TTF1!)", name_b="Henry Hub (NG1!)", category="natural gas markets", tab="Gas"),
    metals=dict(numerator="GC=F", denominator="SI=F", label="Gold / Silver",
                name_a="Gold (GC1!)", name_b="Silver (SI1!)", category="precious metals markets", tab="Metals"),
    crypto=dict(numerator="BTC-USD", denominator="ETH-USD", label="Bitcoin / Ethereum",
                name_a="Bitcoin (BTC)", name_b="Ethereum (ETH)", category="cryptocurrency markets", tab="Crypto"),
    indices=dict(numerator="^GSPC", denominator="^IXIC", label="S&P 500 / Nasdaq",
                 name_a="S&P 500", name_b="Nasdaq", category="US equity index markets", tab="US"),
    europe=dict(numerator="^DJI", denominator="^STOXX50E", label="Dow / Euro Stoxx 50",
                name_a="Dow Jones", name_b="Euro Stoxx 50", category="transatlantic equity markets", tab="Europe"),
    china=dict(numerator="ACWI", denominator="FXI", label="ACWI / China",
               name_a="ACWI (Global)", name_b="FXI (China)", category="global equity markets", tab="China"),
)

DATA_DIR = PROJECT_ROOT / "data"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DEFAULT_PERIOD = "1y"
DEFAULT_SENSITIVITY = 5
DEFAULT_ROLLING_WINDOW = 30
CACHE_MAX_AGE_HOURS = 24
