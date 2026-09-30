"""Take-Two's share price, once a day. A witness under claim 06.

Claim 06 -- "It cost somebody money" -- is otherwise arithmetic on
assumptions. This is the one measured number beside it: what the market made
of the day. It carries no prediction and never gets a verdict, for two
reasons. A share price says what investors expect the game to earn, not
whether anybody stayed home. And launch days often fall even when sales are
huge, because the good news was priced in months earlier. Printed as a fact,
it is useful; scored as evidence, it would mislead.

Why Take-Two alone. Sony and Microsoft are far too large for one game to move
their shares, so their price on 19 November would be about everything else
they do. The Nasdaq-100 travels beside Take-Two -- through the QQQ fund,
because the provider does not serve indices -- so that a day the whole market
fell is not read as a day GTA fell.

Why once a day, and why here rather than in collect.py. The hourly collector
cannot use Yahoo or Stooq: both refuse GitHub's runners. Alpha Vantage takes
a free key instead of blocking by address, but its free tier allows only a
couple of dozen calls a day, and a closing price is a daily number anyway.
Each call returns the last hundred trading days, so a missed day is filled by
the next one, the way an ENTSO-E call carries twelve hours.

The history is merged, never overwritten. Every other backfill file is
rewritten whole on each run, which is safe for sources that can re-send years
of history. This one can re-send only a hundred days, so a failed call must
leave what we already have untouched.
"""

import json
import os
import statistics

FILE = os.path.join("data", "backfill", "shares.json")
SOURCE = "Alpha Vantage TIME_SERIES_DAILY"

# What each symbol is, in words a reader would use.
SYMBOLS = {
    "TTWO": "Take-Two Interactive",
    "QQQ": "the Nasdaq-100",
}
COMPANY, MARKET = "TTWO", "QQQ"

# Days of history before the page may say how unusual a day's move was. With
# fewer, "a typical day" would be a guess dressed as a measurement.
MIN_DAYS_FOR_TYPICAL = 40


def url(symbol, key):
    return ("https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
            f"&symbol={symbol}&outputsize=compact&apikey={key}")


def parse(payload):
    """Daily rows from one Alpha Vantage response, oldest first.

    Raises ValueError naming the reason when the response carries no prices.
    The provider answers HTTP 200 for its own errors, with a message where the
    prices should be -- a bad key, a bad symbol, or the daily limit -- so the
    status code alone would file an error as an empty day.
    """
    if not isinstance(payload, dict):
        raise ValueError("response is not a JSON object")
    for k in ("Error Message", "Note", "Information"):
        if payload.get(k):
            raise ValueError(f"{k}: {str(payload[k])[:200]}")
    series = next((v for k, v in payload.items()
                   if k.startswith("Time Series") and isinstance(v, dict)), None)
    if not series:
        raise ValueError("no time series in response: keys "
                         + ", ".join(sorted(payload)[:5]))

    def field(values, name):
        # Keys arrive as "4. close"; match on the word, not the number.
        for k, v in values.items():
            if k.split(". ", 1)[-1] == name:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None
        return None

    rows = []
    for day, values in series.items():
        if not isinstance(values, dict):
            continue
        close = field(values, "close")
        if close is None or close <= 0:
            continue          # a day without a usable close is left out
        vol = field(values, "volume")
        rows.append({"date": day[:10], "close": close,
                     "volume": int(vol) if vol is not None else None})
    if not rows:
        raise ValueError("time series present but no usable closing prices")
    return sorted(rows, key=lambda r: r["date"])


def merge(old_rows, new_rows):
    """Union by date. A day the provider sends again replaces ours."""
    by_date = {r["date"]: r for r in (old_rows or []) if r.get("date")}
    for r in new_rows or []:
        by_date[r["date"]] = r
    return [by_date[d] for d in sorted(by_date)]


def load(path=FILE):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def summary(data):
    """What the page may say about the latest trading day, or None.

    Needs the same date for both symbols and the trading day before it for
    both. Anything short of that returns what can honestly be said -- the
    close alone -- or nothing.
    """
    symbols = (data or {}).get("symbols") or {}
    company = {r["date"]: r["close"] for r in
               (symbols.get(COMPANY) or {}).get("rows") or []}
    market = {r["date"]: r["close"] for r in
              (symbols.get(MARKET) or {}).get("rows") or []}
    if not company:
        return None

    days = sorted(company)
    last = days[-1]
    out = {"date": last, "close": round(company[last], 2),
           "company": SYMBOLS[COMPANY], "days": len(days)}

    # Daily moves on days where both closed, against their own previous day.
    both = [d for d in days if d in market]
    moves = {}
    for prev, day in zip(both, both[1:]):
        c = company[day] / company[prev] - 1
        m = market[day] / market[prev] - 1
        moves[day] = (c * 100, m * 100, (c - m) * 100)

    if last in moves:
        c, m, x = moves[last]
        out.update(change_pct=round(c, 2), market_change_pct=round(m, 2),
                   excess_pct=round(x, 2))
        earlier = [abs(v[2]) for d, v in moves.items() if d != last]
        if len(earlier) >= MIN_DAYS_FOR_TYPICAL:
            out["typical_excess_pct"] = round(statistics.median(earlier), 2)
    return out
