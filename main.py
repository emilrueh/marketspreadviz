import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log"),
    ],
)
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.utils import TICKER_MAP, SPREAD_PAIRS, FRONTEND_DIR, DEFAULT_PERIOD, DEFAULT_SENSITIVITY, DEFAULT_ROLLING_WINDOW
from src.models import PricePoint, PriceResponse
from src.analysis import build_spread_response
from src.fetcher import fetch_ticker_data
from src.news import fetch_spike_news

load_dotenv()

app = FastAPI(title="MarketSpreadViz")


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/spread/{pair}")
def get_spread(
    pair: str,
    period: str = Query(default=DEFAULT_PERIOD),
    sensitivity: int = Query(default=DEFAULT_SENSITIVITY, ge=1, le=10),
    window: int = Query(default=DEFAULT_ROLLING_WINDOW),
):
    if pair not in SPREAD_PAIRS:
        raise HTTPException(status_code=404, detail=f"Unknown pair: {pair}. Use: {list(SPREAD_PAIRS.keys())}")

    return build_spread_response(pair, period, sensitivity, window)


@app.get("/api/price/{ticker}")
def get_price(
    ticker: str,
    period: str = Query(default=DEFAULT_PERIOD),
):
    if ticker not in TICKER_MAP:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}. Use: {list(TICKER_MAP.keys())}")

    yahoo_ticker = TICKER_MAP[ticker]
    df = fetch_ticker_data(yahoo_ticker, period)

    data = [
        PricePoint(date=date.strftime("%Y-%m-%d"), close=round(row["Close"], 4))
        for date, row in df.iterrows()
    ]

    return PriceResponse(ticker=ticker, period=period, data=data)


@app.get("/api/news/{pair}/{date}")
async def get_spike_news(
    pair: str,
    date: str,
    direction: str = Query(default="up"),
):
    if pair not in SPREAD_PAIRS:
        raise HTTPException(status_code=404, detail=f"Unknown pair: {pair}. Use: {list(SPREAD_PAIRS.keys())}")

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    pair_config = SPREAD_PAIRS[pair]
    return await fetch_spike_news(pair, date, direction, pair_config)


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
