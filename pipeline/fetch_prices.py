"""Download adjusted daily closes for every ticker (period=max) → data/raw/prices.parquet.

Also writes data/raw/ticker_coverage.json with the first/last date per ticker,
which doubles as the ticker verification report.
"""
from __future__ import annotations

import sys
import time

import pandas as pd
import yfinance as yf

from pipeline.common import RAW, all_tickers, load_sectors, write_json


def download(ticker: str, retries: int = 3) -> pd.Series | None:
    for attempt in range(retries):
        try:
            df = yf.download(ticker, period="max", auto_adjust=True, progress=False, threads=False)
            if df is None or df.empty:
                return None
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            close = close.dropna()
            close = close[close > 0]
            close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
            return close.rename(ticker)
        except Exception as exc:  # network hiccups
            print(f"  {ticker}: attempt {attempt + 1} failed: {exc}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    return None


def main() -> int:
    cfg = load_sectors()
    tickers = all_tickers(cfg) + ["^VIX"]
    series, coverage, missing = [], {}, []
    for t in tickers:
        s = download(t)
        if s is None or s.empty:
            missing.append(t)
            print(f"MISSING  {t}")
            continue
        series.append(s)
        coverage[t] = {"first": s.index[0].date().isoformat(), "last": s.index[-1].date().isoformat(), "rows": len(s)}
        print(f"ok       {t:<12} {coverage[t]['first']} → {coverage[t]['last']}  ({len(s)} rows)")
    prices = pd.concat(series, axis=1, sort=True)
    RAW.mkdir(parents=True, exist_ok=True)
    prices.to_parquet(RAW / "prices.parquet")
    write_json(RAW / "ticker_coverage.json", {"coverage": coverage, "missing": missing})
    print(f"\n{len(coverage)} tickers saved, {len(missing)} missing: {missing}")
    # Fail the daily job only if a benchmark is missing; a missing basket member just shrinks the basket.
    benchmarks = {m["benchmark"] for m in cfg["markets"].values()}
    benchmarks |= {spec["benchmark"] for sec in cfg["sectors"] for spec in sec["markets"].values() if "benchmark" in spec}
    return 1 if benchmarks & set(missing) else 0


if __name__ == "__main__":
    sys.exit(main())
