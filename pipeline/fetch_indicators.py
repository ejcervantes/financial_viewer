"""Tone indicators (spec §7): EPU (US, daily), GPR (daily), VIX → data/derived/indicators.json.

EPU and GPR are noisy day to day, so the exported line is a 7-day moving average.
"""
from __future__ import annotations

import io
import os
import sys

import pandas as pd
import requests

from pipeline.common import DATA, RAW, write_json

START = "1998-01-01"
UA = {"User-Agent": "Mozilla/5.0 (compatible; event-reactions-dashboard)"}
GPR_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=USEPUINDXD"
FRED_API = "https://api.stlouisfed.org/fred/series/observations"
EPU_SITE = "https://www.policyuncertainty.com/media/All_Daily_Policy_Data.csv"


def fetch_epu() -> pd.Series:
    key = os.environ.get("FRED_API_KEY")
    if key:
        try:
            r = requests.get(FRED_API, params={"series_id": "USEPUINDXD", "api_key": key, "file_type": "json",
                                               "observation_start": START}, timeout=60)
            r.raise_for_status()
            obs = r.json()["observations"]
            s = pd.Series({pd.Timestamp(o["date"]): float(o["value"]) for o in obs if o["value"] != "."})
            return s.sort_index()
        except Exception as exc:
            print(f"FRED API failed ({exc}); trying CSV", file=sys.stderr)
    for url in (FRED_CSV, EPU_SITE):
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            if "daily_policy_index" in df:
                idx = pd.to_datetime(dict(year=df.year, month=df.month, day=df.day))
                return pd.Series(df["daily_policy_index"].to_numpy(), index=idx).sort_index()
            df.columns = ["date", "value"]
            df = df[pd.to_numeric(df["value"], errors="coerce").notna()]
            return pd.Series(df["value"].astype(float).to_numpy(), index=pd.to_datetime(df["date"])).sort_index()
        except Exception as exc:
            print(f"EPU source {url} failed: {exc}", file=sys.stderr)
    raise RuntimeError("No EPU source available")


def fetch_gpr() -> pd.Series:
    r = requests.get(GPR_URL, headers=UA, timeout=120)
    r.raise_for_status()
    df = pd.read_excel(io.BytesIO(r.content))
    df = df[pd.to_numeric(df["GPRD"], errors="coerce").notna()]
    idx = pd.to_datetime(df["DAY"].astype(int).astype(str), format="%Y%m%d")
    return pd.Series(df["GPRD"].astype(float).to_numpy(), index=idx).sort_index()


def fetch_vix() -> pd.Series:
    prices = pd.read_parquet(RAW / "prices.parquet")
    return prices["^VIX"].dropna()


def pack(s: pd.Series, smooth: int | None) -> dict:
    s = s[s.index >= START]
    if smooth:
        s = s.rolling(smooth, min_periods=1).mean()
    return {"dates": [d.date().isoformat() for d in s.index], "values": [round(float(v), 1) for v in s.to_numpy()]}


def main() -> None:
    out_path = DATA / "derived" / "indicators.json"
    out = {}
    meta = {
        "epu": {"label": "Economic Policy Uncertainty (US)", "short": "EPU", "note": "7-day average", "source": "Baker, Bloom & Davis via FRED (USEPUINDXD)"},
        "gpr": {"label": "Geopolitical Risk Index", "short": "GPR", "note": "7-day average", "source": "Caldara & Iacoviello"},
        "vix": {"label": "VIX", "short": "VIX", "note": "daily close", "source": "Cboe via Yahoo Finance"},
    }
    for key, fn, smooth in (("epu", fetch_epu, 7), ("gpr", fetch_gpr, 7), ("vix", fetch_vix, None)):
        try:
            out[key] = {**meta[key], **pack(fn(), smooth)}
            print(f"{key}: {out[key]['dates'][0]} → {out[key]['dates'][-1]} ({len(out[key]['dates'])} points)")
        except Exception as exc:
            # Keep yesterday's data rather than failing the whole daily build.
            print(f"{key} failed: {exc}", file=sys.stderr)
            from pipeline.common import read_json
            prev = read_json(out_path, {})
            if key in prev:
                out[key] = prev[key]
    write_json(out_path, out)


if __name__ == "__main__":
    main()
