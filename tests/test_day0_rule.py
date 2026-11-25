"""Tests for the day-0 rule (spec §3.4), using the spec's own examples."""
import datetime as dt

import pandas as pd
import pytest

from pipeline.calendar_rules import Session, anchor

US = Session("America/New_York", "09:30", "16:00")
EU = Session("Europe/Berlin", "09:00", "17:30")
HK = Session("Asia/Hong_Kong", "09:30", "16:00")


def bdays(start, end, skip=()):
    days = pd.bdate_range(start, end)
    return pd.DatetimeIndex([d for d in days if d.date().isoformat() not in skip])


def dates(cal, a):
    return (cal[a.base_idx].date().isoformat() if a.base_idx is not None else None,
            cal[a.day0_idx].date().isoformat() if a.day0_idx is not None else None)


# US markets were closed 11–14 Sep 2001.
US_2001 = bdays("2001-09-03", "2001-09-28", skip={"2001-09-03", "2001-09-11", "2001-09-12", "2001-09-13", "2001-09-14"})
EU_2001 = bdays("2001-09-03", "2001-09-28")
NINE_ELEVEN = dt.datetime(2001, 9, 11, 12, 46, tzinfo=dt.timezone.utc)


def test_9_11_europe_open_day0_same_day():
    assert dates(EU_2001, anchor(NINE_ELEVEN, EU_2001, EU)) == ("2001-09-10", "2001-09-11")


def test_9_11_us_reopens_on_17th():
    assert dates(US_2001, anchor(NINE_ELEVEN, US_2001, US)) == ("2001-09-10", "2001-09-17")


def test_9_11_hk_closed_so_next_day():
    assert dates(EU_2001, anchor(NINE_ELEVEN, EU_2001, HK)) == ("2001-09-11", "2001-09-12")


CAL = bdays("2024-03-25", "2024-04-30")


def test_after_us_close_is_next_day_everywhere():
    a = dt.datetime(2024, 4, 3, 20, 30, tzinfo=dt.timezone.utc)  # 16:30 EDT Wed
    assert dates(CAL, anchor(a, CAL, US)) == ("2024-04-03", "2024-04-04")
    assert dates(CAL, anchor(a, CAL, EU)) == ("2024-04-03", "2024-04-04")
    assert dates(CAL, anchor(a, CAL, HK)) == ("2024-04-03", "2024-04-04")


def test_weekend_is_monday():
    a = dt.datetime(2024, 4, 6, 15, 0, tzinfo=dt.timezone.utc)  # Saturday
    for s in (US, EU, HK):
        assert dates(CAL, anchor(a, CAL, s)) == ("2024-04-05", "2024-04-08")


def test_intraday_us_announcement():
    a = dt.datetime(2024, 4, 10, 18, 0, tzinfo=dt.timezone.utc)  # 14:00 EDT, Europe closed
    assert dates(CAL, anchor(a, CAL, US)) == ("2024-04-09", "2024-04-10")
    assert dates(CAL, anchor(a, CAL, EU)) == ("2024-04-10", "2024-04-11")
    assert dates(CAL, anchor(a, CAL, HK)) == ("2024-04-10", "2024-04-11")


def test_exactly_at_open_counts_as_in_progress():
    a = dt.datetime(2024, 4, 10, 13, 30, tzinfo=dt.timezone.utc)  # 09:30 EDT
    assert dates(CAL, anchor(a, CAL, US)) == ("2024-04-09", "2024-04-10")


def test_exactly_at_close_is_next_session():
    a = dt.datetime(2024, 4, 10, 20, 0, tzinfo=dt.timezone.utc)  # 16:00 EDT
    assert dates(CAL, anchor(a, CAL, US)) == ("2024-04-10", "2024-04-11")


def test_dst_transition_winter_vs_summer():
    # 14:00 UTC: US closed in winter (opens 14:30 UTC), open in summer (opens 13:30 UTC).
    winter = bdays("2024-01-08", "2024-01-31")
    a = dt.datetime(2024, 1, 10, 14, 0, tzinfo=dt.timezone.utc)
    assert dates(winter, anchor(a, winter, US)) == ("2024-01-09", "2024-01-10")  # opens later the same day
    a = dt.datetime(2024, 4, 10, 14, 0, tzinfo=dt.timezone.utc)
    assert dates(CAL, anchor(a, CAL, US)) == ("2024-04-09", "2024-04-10")


def test_announcement_beyond_data_has_no_day0():
    a = dt.datetime(2024, 5, 3, 12, 0, tzinfo=dt.timezone.utc)
    base, day0 = dates(CAL, anchor(a, CAL, US))
    assert base == "2024-04-30" and day0 is None


@pytest.mark.parametrize("hour", [0, 5, 23])
def test_base_is_strictly_before_announcement(hour):
    a = dt.datetime(2024, 4, 10, hour, 0, tzinfo=dt.timezone.utc)
    for s in (US, EU, HK):
        an = anchor(a, CAL, s)
        _, close = s.bounds_utc(CAL[an.base_idx].date())
        assert close <= a
