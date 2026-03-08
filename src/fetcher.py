import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from src.utils import DATA_DIR, CACHE_MAX_AGE_HOURS


def get_cache_path(ticker: str, period: str) -> Path:
    sanitized = ticker.replace("=", "_")
    return DATA_DIR / f"{sanitized}_{period}.csv"


def is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    return age_hours < CACHE_MAX_AGE_HOURS


def fetch_ticker_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    cache_path = get_cache_path(ticker, period)

    if is_cache_fresh(cache_path):
        df = pd.read_csv(cache_path, index_col="Date", parse_dates=True)
        return df

    raw = yf.download(ticker, period=period, auto_adjust=True, progress=False)

    if raw.empty:
        raise ValueError(f"No data returned for ticker {ticker}")

    df = raw[["Close"]].copy()
    df.columns = ["Close"]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path)

    return df


def fetch_pair_data(ticker_a: str, ticker_b: str, period: str = "1y") -> pd.DataFrame:
    df_a = fetch_ticker_data(ticker_a, period)
    df_b = fetch_ticker_data(ticker_b, period)

    joined = df_a.join(df_b, lsuffix="_a", rsuffix="_b", how="inner")
    joined.columns = ["close_a", "close_b"]

    return joined
