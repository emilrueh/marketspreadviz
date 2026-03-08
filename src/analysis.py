import pandas as pd
from scipy.signal import find_peaks

from src.fetcher import fetch_pair_data
from src.models import SpreadPoint, SpreadResponse, SpikeAnnotation
from src.utils import SPREAD_PAIRS, DEFAULT_PERIOD, DEFAULT_SENSITIVITY, DEFAULT_ROLLING_WINDOW


def build_spread_response(
    pair_name: str,
    period: str = DEFAULT_PERIOD,
    sensitivity: int = DEFAULT_SENSITIVITY,
    window: int = DEFAULT_ROLLING_WINDOW,
) -> SpreadResponse:
    pair_config = SPREAD_PAIRS[pair_name]
    df = fetch_pair_data(pair_config["numerator"], pair_config["denominator"], period)

    df["growth_a"] = df["close_a"] / df["close_a"].shift(window) - 1
    df["growth_b"] = df["close_b"] / df["close_b"].shift(window) - 1
    df["growth_spread"] = df["growth_a"] - df["growth_b"]

    valid = df.dropna(subset=["growth_a", "growth_b", "growth_spread"])

    spread = valid["growth_spread"] * 100
    spread_values = spread.values
    spread_index = spread.index

    # Prominence threshold: sensitivity 1→strict (high), 10→sensitive (low)
    rolling_std_val = spread.rolling(window=window).std().median()
    min_prominence = rolling_std_val * (4.0 - (sensitivity - 1) * (3.5 / 9))

    # Detect peaks (local highs → red arrows, fall starts here)
    peak_indices, peak_props = find_peaks(
        spread_values,
        prominence=max(min_prominence, 0.1),
        distance=5,
    )

    # Detect troughs (local lows → green arrows, rise starts here)
    trough_indices, trough_props = find_peaks(
        -spread_values,
        prominence=max(min_prominence, 0.1),
        distance=5,
    )

    # Confirmation: only keep peaks where spread drops by at least
    # 30% of the peak's prominence within the next `window` days
    confirmed_peaks = []
    for i, idx in enumerate(peak_indices):
        prominence = peak_props["prominences"][i]
        lookahead = spread_values[idx : idx + window]
        if len(lookahead) > 1:
            max_drop = spread_values[idx] - lookahead[1:].min()
            if max_drop >= prominence * 0.3:
                confirmed_peaks.append(idx)

    confirmed_troughs = []
    for i, idx in enumerate(trough_indices):
        prominence = trough_props["prominences"][i]
        lookahead = spread_values[idx : idx + window]
        if len(lookahead) > 1:
            max_rise = lookahead[1:].max() - spread_values[idx]
            if max_rise >= prominence * 0.3:
                confirmed_troughs.append(idx)

    data = [
        SpreadPoint(
            date=date.strftime("%Y-%m-%d"),
            growth_a=round(row["growth_a"] * 100, 4),
            growth_b=round(row["growth_b"] * 100, 4),
            growth_spread=round(row["growth_spread"] * 100, 4),
        )
        for date, row in valid.iterrows()
    ]

    spikes = []
    for idx in confirmed_peaks:
        spikes.append(
            SpikeAnnotation(
                date=spread_index[idx].strftime("%Y-%m-%d"),
                value=round(float(spread_values[idx]), 3),
                direction="down",
            )
        )
    for idx in confirmed_troughs:
        spikes.append(
            SpikeAnnotation(
                date=spread_index[idx].strftime("%Y-%m-%d"),
                value=round(float(spread_values[idx]), 3),
                direction="up",
            )
        )
    spikes.sort(key=lambda s: s.date)

    return SpreadResponse(
        pair=pair_name,
        label=pair_config["label"],
        ticker_a=pair_config["numerator"],
        ticker_b=pair_config["denominator"],
        name_a=pair_config["name_a"],
        name_b=pair_config["name_b"],
        period=period,
        window=window,
        prominence=round(float(max(min_prominence, 0.1)), 4),
        data=data,
        spikes=spikes,
    )
