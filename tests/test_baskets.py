"""Dynamic equal-weighted baskets (spec §2.3) and reaction status (spec §5.3)."""
import datetime as dt

import numpy as np
import pandas as pd

from pipeline.build_series import build_one
from pipeline.compute_reactions import SeriesView, reaction

SPEC = {"tickers": ["A", "B", "C"], "benchmark": "BM", "min_constituents": 2,
        "timezone": "America/New_York", "open": "09:30", "close": "16:00"}


def make_prices():
    idx = pd.bdate_range("2024-01-01", periods=30)
    p = pd.DataFrame(index=idx, dtype=float)
    p["A"] = 100 * np.cumprod(np.r_[1, np.full(29, 1.01)])     # +1%/day
    p["B"] = np.nan
    p.loc[idx[10]:, "B"] = 50 * np.cumprod(np.r_[1, np.full(19, 0.99)])  # -1%/day from day 10
    p["C"] = np.nan
    p["BM"] = 200.0
    return p


def view(df):
    df = df.copy()
    df.columns = [f"x|us|{c}" for c in df.columns]
    return SeriesView(df, "x|us", SPEC)


def test_basket_averages_only_listed_members():
    df = build_one(make_prices(), SPEC)
    # Before B lists, only one member → insufficient (NaN return)
    assert df["n"].iloc[5] == 1 and np.isnan(df["ret"].iloc[5])
    # After B's first return, the basket is the simple mean of +1% and -1%
    assert df["n"].iloc[12] == 2
    assert abs(df["ret"].iloc[12]) < 1e-12


def test_reaction_insufficient_then_ok():
    sv = view(build_one(make_prices(), SPEC))
    early = dt.datetime(2024, 1, 3, 15, tzinfo=dt.timezone.utc)
    out, _ = reaction(sv, early)
    assert out["status"]["1w"] == "insufficient" and out["absolute"]["1w"] is None
    later = dt.datetime(2024, 1, 17, 15, tzinfo=dt.timezone.utc)  # B listed on Jan 15
    out, path = reaction(sv, later)
    assert out["status"]["1w"] == "ok"
    assert out["constituents"] == 2
    assert out["vs_market"]["1w"] == out["absolute"]["1w"]  # flat benchmark
    assert path["offsets"][0] <= 0


def test_in_progress_when_horizon_not_reached():
    sv = view(build_one(make_prices(), SPEC))
    a = dt.datetime(2024, 2, 5, 15, tzinfo=dt.timezone.utc)  # ~4 sessions before the data ends
    out, _ = reaction(sv, a)
    assert out["status"]["1w"] == "in_progress"
    assert out["absolute"]["1w"] is not None
    assert out["status"]["3m"] == "in_progress"
