"""Day-0 rule (spec §3.4).

For one market, given the announcement instant (UTC) and the market's actual trading
calendar (the dates that have prices):

* base (t-1): the last session whose close is strictly before the announcement.
* day 0:      the session in progress at the announcement (open <= A < close);
              otherwise the first session that opens after the announcement.

Using the data's own calendar means holidays and unscheduled closures (e.g. the US
after 9/11) are handled automatically.
"""
from __future__ import annotations

import datetime as dt
from bisect import bisect_left
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import pandas as pd


@dataclass(frozen=True)
class Session:
    timezone: str
    open: str   # "HH:MM" local
    close: str  # "HH:MM" local

    def bounds_utc(self, day: dt.date) -> tuple[dt.datetime, dt.datetime]:
        tz = ZoneInfo(self.timezone)
        oh, om = map(int, self.open.split(":"))
        ch, cm = map(int, self.close.split(":"))
        o = dt.datetime(day.year, day.month, day.day, oh, om, tzinfo=tz).astimezone(dt.timezone.utc)
        c = dt.datetime(day.year, day.month, day.day, ch, cm, tzinfo=tz).astimezone(dt.timezone.utc)
        return o, c


@dataclass(frozen=True)
class Anchor:
    base_idx: int | None  # index in calendar of t-1 (None if no prior session)
    day0_idx: int | None  # index in calendar of day 0 (None if not reached yet)


def parse_utc(value) -> dt.datetime:
    if isinstance(value, dt.datetime):
        ts = value
    else:
        ts = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc)


def anchor(announced_at: dt.datetime, calendar: pd.DatetimeIndex | list[dt.date], session: Session) -> Anchor:
    """Locate base (t-1) and day 0 in `calendar` (sorted trading dates)."""
    days = list(pd.DatetimeIndex(calendar).date)
    if not days:
        return Anchor(None, None)
    a = parse_utc(announced_at)
    # Candidate sessions are around the announcement's local date; search from the
    # first session on/after (local date - 1) to avoid scanning the whole calendar.
    local_day = a.astimezone(ZoneInfo(session.timezone)).date()
    start = max(bisect_left(days, local_day - dt.timedelta(days=1)) - 1, 0)

    day0_idx = None
    for i in range(start, len(days)):
        o, c = session.bounds_utc(days[i])
        if o <= a < c or o > a:
            day0_idx = i
            break

    # Base = last session with close < A. If day 0 is in progress, it's the one before it;
    # if day 0 opens after A, the previous session closed before A as well.
    if day0_idx is None:
        # Announcement is after the last available session's close → base is the last session.
        base_idx = len(days) - 1
        _, c = session.bounds_utc(days[base_idx])
        if c > a:  # still in progress at A and no later session yet (shouldn't happen: caught above)
            base_idx -= 1
    else:
        base_idx = day0_idx - 1 if day0_idx > 0 else None
    return Anchor(base_idx, day0_idx)
