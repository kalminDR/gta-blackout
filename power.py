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


# How far from its own ordinary evening a reading must sit before it is
# allowed to say anything. Two standard deviations: about one ordinary
# evening in twenty clears it by chance, which is the right amount of
# scepticism for a second witness that is not carrying the claim on its own.
SPEAKS_AT_SIGMA = 2.0

# The windows the backfill actually holds, as month sets. A day is compared to
# the window its own month falls in -- an autumn evening against autumn
# evenings -- because the ratio drifts with the season even though it cancels
# the weather.
SEASON_WINDOWS = ((10, 11, 12), (8, 9))


def season_for(month):
    for window in SEASON_WINDOWS:
        if month in window:
            return window
    return None


def season_baseline(points, day, backfill_points=None):
    """The baseline one particular day should be judged against.

    Two things are matched, and both are load-bearing.

    Season, because the ratio drifts through the year even though it cancels
    weather. And weekday class, because the ratio is structurally higher at
    weekends everywhere -- in Italy by 3.6 weekday standard deviations. That
    second one is not a refinement. Scoring a Sunday against weekdays is what
    turned an ordinary Sunday in November 2022 into the +4.1 sigma this
    project recorded for two years as evidence that the method works. Enforced
    here rather than left to the caller, because the caller is the one who
    got it wrong.
    """
    months = season_for(day.month)
    if not months:
        return None
    src = backfill_points if backfill_points is not None else points
    ratios = ratios_for(src, months=months, weekdays_only=False)
    weekend = day.weekday() >= 5
    return baseline({d: v for d, v in ratios.items()
                     if d != day and (d.weekday() >= 5) == weekend})


def verdict(live_points, backfill_points, day=None):
    """What one country's grid has to say, or why it cannot say it.

    Returns None when there is no complete evening to judge. Otherwise a dict
    carrying the reading, how far it sits from an ordinary evening of the same
    kind, and -- always -- the smallest change this particular grid could have
    distinguished at all. That last number is why a quiet Germany is evidence
    and a quiet Hungary is not, and it travels with every reading so the page
    cannot show one without the other.
    """
    live = ratios_for(live_points, weekdays_only=False)
    if not live:
        return None
    day = day or max(live)
    ratio = live.get(day)
    if ratio is None:
        return None
    base = season_baseline(live_points, day, backfill_points)
    if not base:
        return {"day": day.isoformat(), "ratio": round(ratio, 4),
                "z": None, "detects_pct": None,
                "reason": "no season-matched baseline"}
    z = z_score(ratio, base)
    # The smallest deviation this grid could tell apart from an ordinary
    # evening. Expressed as a percentage of that evening, because "13%" is a
    # thing a reader can picture and "6.5% coefficient of variation" is not.
    detects = round(SPEAKS_AT_SIGMA * base["cv_pct"], 1) if base["cv_pct"] else None
    return {
        "day": day.isoformat(),
        "ratio": round(ratio, 4),
        "baseline": round(base["mean"], 4),
        "z": round(z, 2) if z is not None else None,
        "deviation_pct": round(100 * (ratio / base["mean"] - 1), 1),
        "detects_pct": detects,
        "speaks": bool(z is not None and abs(z) >= SPEAKS_AT_SIGMA),
        "baseline_days": base["n"],
        "weekend": day.weekday() >= 5,
    }


def merge_windows(snapshots):
    """Assemble each country's hourly curve from the collectors' windows.

    Every snapshot carries the last twelve hours the operator had published,
    so each clock hour arrives about a dozen times: first as a partial hour
    with only some quarters settled, then complete. The latest snapshot to
    mention an hour has the most settled version of it, so later readings
    replace earlier ones.

    `snapshots` is a list of raw snapshot dicts, newest last.
    """
    by_country = {}
    for snap in snapshots:
        entsoe = (snap.get("sources") or {}).get("entsoe") or {}
        if not isinstance(entsoe, dict):
            continue
        for code, entry in entsoe.items():
            if not isinstance(entry, dict) or len(code) != 2:
                continue
            hours = by_country.setdefault(code, {})
            window = entry.get("hourly")
            if isinstance(window, list):
                for item in window:
                    if isinstance(item, (list, tuple)) and len(item) == 2 \
                            and isinstance(item[1], (int, float)):
                        hours[item[0]] = item[1]
            elif isinstance(entry.get("load_mw"), (int, float)) and entry.get("t"):
                # Snapshots taken before the window was kept. One reading,
                # filed under the hour it was measured, not collected.
                hours[entry["t"]] = entry["load_mw"]
    return {c: sorted(h.items()) for c, h in by_country.items()}


def verdicts(live_by_country, backfill=None):
    """Every country's evening verdict.

    A country with no history to judge it against says nothing rather than
    being scored against someone else's past.
    """
    bf = backfill if backfill is not None else load_backfill()
    out = {}
    for code, pts in (live_by_country or {}).items():
        if code not in bf:
            continue
        v = verdict([list(p) for p in pts], bf[code])
        if v:
            out[code] = v
    return out


def verdicts_from_snapshots(snapshots, backfill=None):
    """The whole path, from raw snapshots to what claim 02 gets to say."""
    return verdicts(merge_windows(snapshots), backfill)
