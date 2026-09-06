#!/usr/bin/env python3
"""The evening ratio: electricity demand with the weather divided out.

Why this exists
---------------
Claim 02 is "we stayed in". A country that sits down in front of a screen
changes the shape of its own evening, and transmission operators record that
hour by hour with no interest whatsoever in this game. That makes electricity
the best story on the list -- and, so far, the weakest evidence.

Two earlier attempts failed for the same reason: raw demand is dominated by
the weather. Comparing 19 November to a baseline of other November evenings
measures how cold 19 November was. France came out +52% on one such test,
which is electric heating, not football.

The measure that survives is a ratio taken inside a single day:

    the evening peak, divided by the same day's late afternoon

A cold day lifts both hours, so the ratio cancels weather and season. What it
cannot cancel is people changing what they do between 16:00 and the evening --
which is exactly the thing claim 02 is about.

The hours below are not a guess. They are the definition that reproduces the
December 2022 World Cup results recorded in CLAUDE.md section 5: France -1.7
standard deviations on its own semi-final, Spain +4.4 on a group match, Italy
+3.6 the same evening. Change them and that check stops passing.

Where the baseline comes from, and why it matters
------------------------------------------------
Not from the live collection. The live series began on 6 September 2026 and
would need roughly six weeks to hold enough same-weekday evenings to compare
against -- and every one of those weeks is contaminated. Dutch demand at
midday in summer is dominated by rooftop solar feeding in behind the meter:
the ratio's coefficient of variation runs to 29.7% in August, against 3.7-8.0%
in October to December. A baseline built through September would bake that in
and call it normal.

The backfill already holds four October-to-December windows, 2022 through
2025. That is the correct comparison set for a November event, and it is the
same rule section 5 established for the subway: compare a day to its own
season, never to a different one.

The detection floor, measured
-----------------------------
Coefficient of variation of the ratio, non-holiday weekdays, per year, over
the October-December windows in the backfill:

    DE 2.2-2.6%   FR 1.8-3.0%   ES 2.2-2.9%   SE 2.2-3.6%
    IT 2.9-4.6%   PL 3.2-4.1%   NL 3.7-8.0%   HU 6.0-7.0%

Section 5 records 1.8-2.5% "across three years and seven countries". That
holds for the best four and is too optimistic for the rest. Hungary is the
least sensitive instrument of the eight by a wide margin -- worth saying
plainly, because it is the country a Hungarian reader will look at first.

Nothing here prints a number it cannot support: a day without both hours has
no ratio, and a country without enough baseline days gets no z-score.
"""

import datetime
import json
import pathlib
import statistics
from zoneinfo import ZoneInfo

# All eight countries the backfill returns keep Central European Time, so one
# zone covers them. 19 November 2026 falls in CET, an hour ahead of UTC.
TZ = ZoneInfo("Europe/Berlin")

# The evening peak is taken as the largest of these hours rather than a fixed
# one, because the peak moves by an hour or so with the season and between
# countries. Local time throughout.
PEAK_HOURS = (18, 19, 20, 21)
REFERENCE_HOUR = 16

# A baseline thinner than this is not a baseline. Four Oct-Dec windows of
# weekdays give roughly 250 days per country, so this only bites when a
# country or a window is missing.
MIN_BASELINE_DAYS = 30

ROOT = pathlib.Path(__file__).resolve().parent
BACKFILL = ROOT / "data" / "backfill" / "entsoe_load.json"


def evening_ratio(hours):
    """The ratio for one day, from {local_hour: megawatts}.

    None when the day lacks either end of the comparison. A partial day is
    not a small measurement, it is no measurement.
    """
    peak = [hours[h] for h in PEAK_HOURS if isinstance(hours.get(h), (int, float))]
    reference = hours.get(REFERENCE_HOUR)
    if not peak or not isinstance(reference, (int, float)) or reference <= 0:
        return None
    return max(peak) / reference


def days_by_local_date(points):
    """Group [timestamp, megawatts] pairs into {local date: {local hour: mw}}.

    Local, not UTC. An evening peak is a fact about when people are at home,
    and that follows the clock on their wall.
    """
    out = {}
    for item in points:
        if not (isinstance(item, (list, tuple)) and len(item) == 2):
            continue
        ts, value = item
        if not isinstance(value, (int, float)):
            continue
        try:
            t = datetime.datetime.fromisoformat(ts).astimezone(TZ)
        except (ValueError, TypeError):
            continue
        out.setdefault(t.date(), {})[t.hour] = value
    return out


def ratios_for(points, months=None, years=None, weekdays_only=True):
    """{date: ratio} for every day that has one."""
    out = {}
    for day, hours in days_by_local_date(points).items():
        if months and day.month not in months:
            continue
        if years and day.year not in years:
            continue
        if weekdays_only and day.weekday() >= 5:
            continue
        r = evening_ratio(hours)
        if r is not None:
            out[day] = r
    return out


def baseline(ratios):
    """Mean, spread and size of a set of ratios, or None if too thin.

    The coefficient of variation is returned alongside because it is the
    detection floor: a country whose ordinary evenings vary by 7% cannot
    testify to a 3% change, and the page has no business implying it can.
    """
    vals = list(ratios.values()) if isinstance(ratios, dict) else list(ratios)
    if len(vals) < MIN_BASELINE_DAYS:
        return None
    mean = statistics.mean(vals)
    sd = statistics.stdev(vals)
    return {"mean": mean, "sd": sd, "n": len(vals),
            "cv_pct": round(100 * sd / mean, 1) if mean else None}


def z_score(ratio, base):
    """How far one day sits from its own season, in standard deviations."""
    if ratio is None or not base or not base["sd"]:
        return None
    return (ratio - base["mean"]) / base["sd"]


def load_backfill(path=None):
    """The ENTSO-E history from disk: {country: [[timestamp, mw], ...]}."""
    p = pathlib.Path(path) if path else BACKFILL
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8")).get("data") or {}
    out = {}
    for code, entry in data.items():
        if isinstance(entry, dict) and isinstance(entry.get("points"), list):
            out[code] = entry["points"]
    return out


def autumn_baselines(backfill=None, months=(10, 11, 12)):
    """The October-December baseline for each country, from the backfill.

    This is what 19 November 2026 will be compared against. Countries the
    backfill does not carry -- Great Britain, which stopped publishing to
    ENTSO-E after Brexit -- are simply absent, not filled in.
    """
    data = backfill if backfill is not None else load_backfill()
    out = {}
    for code, points in data.items():
        base = baseline(ratios_for(points, months=months))
        if base:
            out[code] = base
    return out
