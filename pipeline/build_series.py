"""Build one daily index per sector × market (dynamic equal-weighted baskets) plus its benchmark.

Output: data/raw/series.parquet with columns "<sector>|<market>|<field>":
  cal   1.0 on the series' trading days (union of constituent + benchmark sessions)
  ret   basket daily return (mean of constituents that traded that day)
  n     number of constituents with a return that day
  level cumulative index (starts at 1.0, insufficient days count as 0% return)
  bench benchmark adjusted close (ffilled within the series calendar, max 5 sessions)

Reaction windows check `n >= min_constituents` on every day, so a chained level across
an insufficient gap is never used for a published number.
"""
from __future__ import annotations

import pandas as pd

from pipeline.common import RAW, load_sectors, market_spec

FFILL_LIMIT = 5  # sessions a stale price may be carried (holidays on one exchange of a mixed basket)


def constituent_returns(prices: pd.DataFrame, tickers: list[str], cal: pd.DatetimeIndex) -> pd.DataFrame:
    cols = {}
    for t in tickers:
        if t not in prices:
            continue
        p = prices[t].dropna()
        if p.empty:
            continue
        p = p.reindex(cal).ffill(limit=FFILL_LIMIT)
        p[p.index < prices[t].first_valid_index()] = float("nan")
        cols[t] = p.pct_change(fill_method=None)
    return pd.DataFrame(cols, index=cal)


def build_one(prices: pd.DataFrame, spec: dict) -> pd.DataFrame:
    tickers = [t for t in spec["tickers"] if t in prices]
    bench = spec["benchmark"]
    # The series' calendar: the benchmark's sessions; before the benchmark exists, the
    # union of the constituents' sessions.
    own = prices[tickers].dropna(how="all").index if tickers else pd.DatetimeIndex([])
    if bench in prices and prices[bench].notna().any():
        b_dates = prices[bench].dropna().index
        cal = own[own < b_dates[0]].union(b_dates)
    else:
        cal = own
    rets = constituent_returns(prices, tickers, cal)
    n = rets.notna().sum(axis=1)
    ret = rets.mean(axis=1, skipna=True)
    ret[n < spec["min_constituents"]] = float("nan")
    level = (1 + ret.fillna(0)).cumprod()
    b = prices[bench].reindex(cal).ffill(limit=FFILL_LIMIT) if bench in prices else pd.Series(float("nan"), index=cal)
    b[b.index < (prices[bench].first_valid_index() if bench in prices else cal[-1])] = float("nan")
    return pd.DataFrame({"cal": 1.0, "ret": ret, "n": n.astype(float), "level": level, "bench": b}, index=cal)


def main() -> None:
    cfg = load_sectors()
    prices = pd.read_parquet(RAW / "prices.parquet")
    frames = []
    for sector in cfg["sectors"]:
        for market in sector["markets"]:
            spec = market_spec(cfg, sector, market)
            df = build_one(prices, spec)
            df.columns = [f"{sector['id']}|{market}|{c}" for c in df.columns]
            frames.append(df)
            ok = df[f"{sector['id']}|{market}|n"] >= spec["min_constituents"]
            first = ok.idxmax().date() if ok.any() else None
            print(f"{sector['id']:<12} {market}  first usable day: {first}")
    out = pd.concat(frames, axis=1, sort=True)
    out.to_parquet(RAW / "series.parquet")
    print(f"saved {out.shape[1] // 5} series, {len(out)} rows")


if __name__ == "__main__":
    main()
