#!/usr/bin/env python3
"""Tests for Take-Two's daily share price (shares.py, backfill.fetch_shares).

The provider cannot be reached from the build environment, so responses are
fixtures in its documented shape. The first live run of the backfill is the
real check of that shape, and this file should be corrected against it.

Three things matter most. An error that arrives as HTTP 200 must read as an
error, not as a day without prices. A failed call must never shrink the
history on disk -- each call carries only a hundred trading days, so the file
is the only copy of anything older. And the page may only say what the rows
support: no daily move without both symbols on both days, no "typical day"
without enough days to know one.
"""

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backfill  # noqa: E402
import shares  # noqa: E402

passed = failed = 0


def check(name, got, want=True):
    global passed, failed
    if got == want:
        passed += 1
        print(f"  PASS  {name}   [{got}]")
    else:
        failed += 1
        print(f"  FAIL  {name}   got {got!r}, wanted {want!r}")


def response(closes, symbol="TTWO"):
    """An Alpha Vantage TIME_SERIES_DAILY body for {date: close}."""
    return {
        "Meta Data": {"1. Information": "Daily Prices (open, high, low, close) and Volumes",
                      "2. Symbol": symbol, "3. Last Refreshed": max(closes),
                      "4. Output Size": "Compact", "5. Time Zone": "US/Eastern"},
        "Time Series (Daily)": {
            d: {"1. open": f"{c:.4f}", "2. high": f"{c:.4f}", "3. low": f"{c:.4f}",
                "4. close": f"{c:.4f}", "5. volume": "1200000"}
            for d, c in closes.items()},
    }


def raises(fn):
    try:
        fn()
    except ValueError as e:
        return str(e)
    return None


print("1. Parsing a response")
rows = shares.parse(response({"2026-09-25": 210.5, "2026-09-24": 208.0}))
check("two days, oldest first", [r["date"] for r in rows], ["2026-09-24", "2026-09-25"])
check("close read from '4. close'", rows[-1]["close"], 210.5)
check("volume kept as a whole number", rows[-1]["volume"], 1200000)

print("\n2. The provider's errors arrive as HTTP 200 and must read as errors")
for body, word in [({"Error Message": "Invalid API call."}, "Error Message"),
                   ({"Information": "Our standard API rate limit is 25 requests per day."}, "Information"),
                   ({"Note": "Thank you for using Alpha Vantage!"}, "Note"),
                   ({"Meta Data": {}}, "no time series"),
                   ([], "not a JSON object")]:
    msg = raises(lambda: shares.parse(body))
    check(f"{word}: raised, naming the reason", word in (msg or ""), True)
msg = raises(lambda: shares.parse({"Time Series (Daily)": {"2026-09-25": {"4. close": "0"}}}))
check("a zero close is not a price", "no usable closing prices" in (msg or ""), True)

print("\n3. Merging keeps history and lets a re-sent day win")
old = [{"date": "2026-05-01", "close": 180.0}, {"date": "2026-09-24", "close": 207.0}]
new = [{"date": "2026-09-24", "close": 208.0}, {"date": "2026-09-25", "close": 210.5}]
m = shares.merge(old, new)
check("the old day outside the new window survives", m[0]["date"], "2026-05-01")
check("the re-sent day takes the provider's latest figure", m[1]["close"], 208.0)
check("three days in all", len(m), 3)

print("\n4. A failed call never shrinks what is on disk")
existing = {"symbols": {"TTWO": {"rows": old}, "QQQ": {"rows": old}}}
real_get, real_sleep = backfill.get_json, backfill.time.sleep
backfill.time.sleep = lambda s: None
try:
    backfill.get_json = lambda url: {"Information": "rate limit reached"}
    out = backfill.fetch_shares("SECRETKEY", existing)
    check("TTWO keeps both stored days", len(out["symbols"]["TTWO"]["rows"]), 2)
    check("and says why nothing was added",
          "rate limit" in out["symbols"]["TTWO"].get("last_error", ""), True)

    def boom(url):
        raise OSError(f"connection refused for {url}")
    backfill.get_json = boom
    out = backfill.fetch_shares("SECRETKEY", existing)
    check("a network error keeps the history too", len(out["symbols"]["QQQ"]["rows"]), 2)
    check("and the API key never reaches the committed file",
          "SECRETKEY" in json.dumps(out), False)

    out = backfill.fetch_shares("", existing)
    check("no key: history kept", len(out["symbols"]["TTWO"]["rows"]), 2)
    check("and the file says it was skipped",
          out["symbols"]["TTWO"]["last_error"].startswith("skipped"), True)

    backfill.get_json = lambda url: response({"2026-09-25": 210.5})
    out = backfill.fetch_shares("SECRETKEY", existing)
    check("a good call adds its day to the stored ones",
          [r["date"] for r in out["symbols"]["TTWO"]["rows"]],
          ["2026-05-01", "2026-09-24", "2026-09-25"])
    check("and carries no stale error", "last_error" in out["symbols"]["TTWO"], False)
finally:
    backfill.get_json, backfill.time.sleep = real_get, real_sleep

print("\n5. The page says only what the rows support")


def series(n, start=100.0, step=1.0, first=datetime.date(2026, 5, 1)):
    return [{"date": (first + datetime.timedelta(days=i)).isoformat(),
             "close": start + step * i} for i in range(n)]


check("no rows: nothing to print", shares.summary({}), None)

only_company = {"symbols": {"TTWO": {"rows": series(3)}}}
s = shares.summary(only_company)
check("company without market: the close alone", s["close"], 102.0)
check("and no daily move, which would need the market beside it",
      "change_pct" in s, False)

ttwo = [{"date": "2026-09-24", "close": 200.0}, {"date": "2026-09-25", "close": 190.0}]
qqq = [{"date": "2026-09-24", "close": 500.0}, {"date": "2026-09-25", "close": 505.0}]
s = shares.summary({"symbols": {"TTWO": {"rows": ttwo}, "QQQ": {"rows": qqq}}})
check("Take-Two down 5% on the day", s["change_pct"], -5.0)
check("the market up 1%", s["market_change_pct"], 1.0)
check("six points worse than the market", s["excess_pct"], -6.0)
check("two days are not enough to say what a typical day is",
      "typical_excess_pct" in s, False)

qqq_gap = [{"date": "2026-09-24", "close": 500.0}]
s = shares.summary({"symbols": {"TTWO": {"rows": ttwo}, "QQQ": {"rows": qqq_gap}}})
check("market missing on the latest day: no move is claimed", "change_pct" in s, False)

long_ttwo = series(shares.MIN_DAYS_FOR_TYPICAL + 2)
long_qqq = series(shares.MIN_DAYS_FOR_TYPICAL + 2, start=400.0, step=0.0)
s = shares.summary({"symbols": {"TTWO": {"rows": long_ttwo}, "QQQ": {"rows": long_qqq}}})
check("with enough days, a typical day is given", "typical_excess_pct" in s, True)
check("measured from the earlier days, not including the latest",
      s["typical_excess_pct"] > 0, True)

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
