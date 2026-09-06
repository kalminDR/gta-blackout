#!/usr/bin/env python3
"""Verdicts on the six predictions, computed from the readings.

The one rule this file exists to enforce
----------------------------------------
**Failed means we measured and it did not happen. It never means we could not
measure.** Those are different findings and collapsing them would be the worst
thing this project could do: a collector outage on 19 November would print as
evidence that nothing happened, which is a false result dressed as a real one.

So every scorer here establishes that the readings it needs are actually
present before it forms any opinion at all. Missing data yields a verdict of
None and a reason naming what is missing. There is no path from absent data to
"failed".

Provisional verdicts
--------------------
Two of the six -- traffic and steam -- are rank tests over Thursdays between
1 October and 17 December. Those cannot be settled on 19 November, because a
December Thursday could still come in lower. On the day they report
`provisional: True` and say where they stand; they settle when the window
closes. Saying so is better than pretending the day is the end of it, and it
is a detail a sceptical reader will check.

Every verdict carries the numbers it was computed from, so it can be argued
with rather than believed.
"""

import datetime
from statistics import median

import indices
import power
import predictions

RELEASE = datetime.date(2026, 11, 19)
# The rank window both Thursday tests run over.
WINDOW_START = datetime.date(2026, 10, 1)
WINDOW_END = datetime.date(2026, 12, 17)
# The launch evening, local time, for the hours the displacement tests read.
EVENING_HOURS = (18, 19, 20, 21, 22, 23)


def _result(verdict=None, reason=None, provisional=False, **evidence):
    return {"verdict": verdict, "reason": reason,
            "provisional": provisional, "evidence": evidence}


def _cannot(reason, **evidence):
    """No verdict, and why. Never 'failed'."""
    return _result(None, reason, **evidence)


def _thursdays_in_window():
    d, out = WINDOW_START, []
    while d <= WINDOW_END:
        if d.weekday() == 3:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def _local_day(iso, tz):
    t = indices.parse_time(iso)
    if t is None:
        return None
    try:
        return t.astimezone(indices._zone(tz)).date()
    except Exception:
        return t.date()


def _local_hour(iso, tz):
    t = indices.parse_time(iso)
    if t is None:
        return None
    try:
        return t.astimezone(indices._zone(tz)).hour
    except Exception:
        return t.hour


# ------------------------------------------------------------------ 01 subway

def score_subway(mta_rows):
    """Lower than 5 and 12 November, and 3% below the mean of the three.

    Reads the MTA backfill rather than the hourly series: ridership is
    published daily, well after the day it describes, so this one cannot be
    scored on the evening itself.
    """
    wanted = [datetime.date(2026, 11, 5), datetime.date(2026, 11, 12), RELEASE]
    daily = {}
    for row in mta_rows or []:
        if row.get("mode") != "Subway" or not row.get("count"):
            continue
        try:
            daily[datetime.date.fromisoformat(row["date"])] = float(row["count"])
        except (ValueError, TypeError):
            continue

    missing = [d.isoformat() for d in wanted if d not in daily]
    if missing:
        return _cannot(f"the MTA series does not yet carry {', '.join(missing)}",
                       have=sorted(d.isoformat() for d in daily)[-1:] or None)

    vals = {d: daily[d] for d in wanted}
    mean = sum(vals.values()) / len(vals)
    launch = vals[RELEASE]
    others = [vals[d] for d in wanted if d != RELEASE]
    lowest = launch < min(others)
    margin = 100 * (launch / mean - 1)
    return _result(
        "passed" if (lowest and margin <= -3.0) else "failed",
        ridership={d.isoformat(): round(v) for d, v in vals.items()},
        lowest_of_the_three=lowest,
        deviation_from_mean_pct=round(margin, 2),
        needed="lowest of the three and at most -3.00%")


# ----------------------------------------------------------------- 01 traffic

def score_traffic(points, today=None):
    """Four of six cities at their lowest Thursday evening delay of the window."""
    today = today or datetime.date.today()
    cities = sorted({k[len("traffic_"):-len("_delay_pct")]
                     for p in points for k in p
                     if k.startswith("traffic_") and k.endswith("_delay_pct")})
    if not cities:
        return _cannot("no traffic readings in the series")

    per_city, unscorable = {}, []
    for city in cities:
        tz = indices.CITY_TZ.get(f"traffic_{city}", "UTC")
        by_day = {}
        for p in points:
            v = p.get(f"traffic_{city}_delay_pct")
            if not isinstance(v, (int, float)):
                continue
            day, hour = _local_day(p.get("t"), tz), _local_hour(p.get("t"), tz)
            if day is None or day.weekday() != 3 or hour not in EVENING_HOURS:
                continue
            if WINDOW_START <= day <= WINDOW_END:
                by_day.setdefault(day, []).append(v)
        peaks = {d: max(v) for d, v in by_day.items()}
        if RELEASE not in peaks:
            unscorable.append(city)
            continue
        per_city[city] = {
            "launch_peak_delay_pct": round(peaks[RELEASE], 1),
            "lowest_so_far": peaks[RELEASE] == min(peaks.values()),
            "thursdays_measured": len(peaks),
        }

    if unscorable:
        return _cannot(
            "no launch-evening reading for " + ", ".join(sorted(unscorable)),
            cities_scored=sorted(per_city))

    lowest = [c for c, d in per_city.items() if d["lowest_so_far"]]
    open_window = today <= WINDOW_END
    return _result(
        None if open_window else ("passed" if len(lowest) >= 4 else "failed"),
        reason=(f"the window runs to {WINDOW_END.isoformat()}; a December "
                "Thursday can still come in lower") if open_window else None,
        provisional=open_window,
        cities=per_city,
        cities_lowest_so_far=sorted(lowest),
        needed="at least 4 of 6")


# ------------------------------------------------------------------- 02 power

def score_power(snapshots, backfill=None):
    """Three of eight grids at two standard deviations from their own autumn."""
    verdicts = power.verdicts_from_snapshots(snapshots, backfill)
    on_the_day = {c: v for c, v in verdicts.items() if v.get("day") == RELEASE.isoformat()}
    if not on_the_day:
        return _cannot("no country has a complete launch-day evening yet",
                       days_available=sorted({v.get("day") for v in verdicts.values()}))

    scored = {c: v for c, v in on_the_day.items() if v.get("z") is not None}
    unscored = sorted(set(on_the_day) - set(scored))
    if not scored:
        return _cannot("no grid could be scored against its own autumn baseline",
                       without_baseline=unscored)

    speaking = sorted(c for c, v in scored.items() if v.get("speaks"))
    return _result(
        "passed" if len(speaking) >= 3 else "failed",
        grids={c: {"deviation_pct": v.get("deviation_pct"), "z": v.get("z"),
                   "could_detect_pct": v.get("detects_pct")}
               for c, v in sorted(scored.items())},
        grids_speaking=speaking,
        grids_without_baseline=unscored,
        needed="at least 3 of 8")


# ------------------------------------------------------------------- 03 steam

def score_steam(points, today=None):
    """The six displaced games at their lowest same-hour Thursday total."""
    today = today or datetime.date.today()
    basket = predictions.STEAM_DISPLACED

    by_day_hour = {}
    for p in points:
        parts = [p.get(k) for k in basket]
        if any(not isinstance(v, (int, float)) for v in parts):
            continue          # a partial basket is not a smaller basket
        day, hour = _local_day(p.get("t"), "UTC"), _local_hour(p.get("t"), "UTC")
        if day is None or day.weekday() != 3 or hour not in EVENING_HOURS:
            continue
        if WINDOW_START <= day <= WINDOW_END:
            by_day_hour.setdefault(hour, {}).setdefault(day, []).append(sum(parts))

    hours_won, hours_measured = [], []
    for hour, days in sorted(by_day_hour.items()):
        if RELEASE not in days:
            continue
        totals = {d: median(v) for d, v in days.items()}
        hours_measured.append(hour)
        if totals[RELEASE] == min(totals.values()):
            hours_won.append(hour)

    if not hours_measured:
        return _cannot("no complete launch-evening basket reading",
                       games_required=basket)

    open_window = today <= WINDOW_END
    won = len(hours_won) > 0
    return _result(
        None if open_window else ("passed" if won else "failed"),
        reason=(f"the window runs to {WINDOW_END.isoformat()}") if open_window else None,
        provisional=open_window,
        hours_measured=hours_measured,
        hours_lowest_so_far=hours_won,
        games=basket,
        needed="lowest for at least one launch-evening hour")


# ------------------------------------------------------------------ 03 twitch

def score_twitch(points):
    """Twice the same-hour, same-weekday median, four hours running."""
    metric = indices.Metric("twitch_top100_total", "attention", 1, "Twitch top 100")
    obs = indices.collect_observations(points, metric)
    if not obs:
        return _cannot("no Twitch readings in the series")

    window = [o for o in obs
              if RELEASE <= o["t"].date() <= RELEASE + datetime.timedelta(days=1)]
    if not window:
        return _cannot("no Twitch readings on 19 or 20 November")

    run = best = 0
    detail, without_baseline = [], 0
    for o in sorted(window, key=lambda o: o["t"]):
        base, quality = indices.baseline_for(obs, o)
        if base is None or quality != "hour_of_week":
            without_baseline += 1
            run = 0                        # a gap is not a continuation
            continue
        ratio = o["v"] / base
        detail.append({"t": o["t"].isoformat(), "ratio": round(ratio, 2)})
        run = run + 1 if ratio >= 2.0 else 0
        best = max(best, run)

    if without_baseline and best < 4:
        return _cannot(
            f"{without_baseline} of {len(window)} launch-window readings have no "
            "same-hour, same-weekday baseline, so a run of four cannot be ruled out",
            longest_run_measured=best)

    return _result("passed" if best >= 4 else "failed",
                   longest_run_at_or_above_2x=best,
                   readings=detail,
                   needed="4 consecutive hourly readings")


# ---------------------------------------------------------------- 05 servers

def score_servers(points):
    """One PlayStation incident outside Russia, on the day or the day after."""
    window = []
    for p in points:
        day = _local_day(p.get("t"), "UTC")
        if day is None or not (RELEASE <= day <= RELEASE + datetime.timedelta(days=1)):
            continue
        v = p.get("psn_incidents")
        if isinstance(v, (int, float)):
            window.append((p.get("t"), v))

    if not window:
        return _cannot("no PlayStation status readings on 19 or 20 November")

    incidents = [(t, v) for t, v in window if v > 0]
    return _result("passed" if incidents else "failed",
                   readings=len(window),
                   readings_with_an_incident=len(incidents),
                   first_incident=incidents[0][0] if incidents else None,
                   needed="at least one")


# --------------------------------------------------------------------- all

SCORERS = {
    "subway": lambda ctx: score_subway(ctx.get("mta")),
    "traffic": lambda ctx: score_traffic(ctx["points"], ctx.get("today")),
    "power": lambda ctx: score_power(ctx.get("snapshots") or [], ctx.get("backfill")),
    "steam": lambda ctx: score_steam(ctx["points"], ctx.get("today")),
    "twitch": lambda ctx: score_twitch(ctx["points"]),
    "servers": lambda ctx: score_servers(ctx["points"]),
}


def score_all(points, snapshots=None, mta=None, backfill=None, today=None):
    """Every verdict, keyed by prediction id.

    A scorer that raises is reported as unscored with the error, never as a
    failure: an exception in this file is our bug, not the world's answer.
    """
    ctx = {"points": points, "snapshots": snapshots, "mta": mta,
           "backfill": backfill, "today": today}
    out = {}
    for pid, fn in SCORERS.items():
        try:
            out[pid] = fn(ctx)
        except Exception as e:
            out[pid] = _cannot(f"scorer error: {str(e)[:160]}")
    return out
