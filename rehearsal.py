#!/usr/bin/env python3
"""A made-up autumn, for rehearsing 19 November before it happens.

Builds hourly readings from 1 October to 18 December 2026 in the same shape
the collector produces, with a launch effect switched on or off, and feeds
them to the real scorers at the moments that matter: launch night, the day
after, a week after, and once the rank window has closed.

Nothing here is evidence and nothing here is published. It exists because the
only other way to find out what the site says on launch day is to wait for
launch day. test_rehearsal.py turns what it found into assertions.

Usage:  python rehearsal.py            prints the verdicts for each scenario
"""

import datetime as dt
import math
import random
from zoneinfo import ZoneInfo

import indices
import power
import predictions
import score

UTC = dt.timezone.utc
START = dt.datetime(2026, 10, 1, tzinfo=UTC)
END = dt.datetime(2026, 12, 18, 23, tzinfo=UTC)
RELEASE = score.RELEASE
CITIES = ("budapest", "london", "berlin", "warsaw", "newyork", "losangeles")


def _hours(until):
    t = START
    while t <= until:
        yield t
        t += dt.timedelta(hours=1)


def _launch_evening(t, tz):
    """True on the evening of 19 November, local time."""
    lt = t.astimezone(ZoneInfo(tz))
    return lt.date() == RELEASE and 17 <= lt.hour <= 23


def _lost(t, outage):
    """With `outage`, the collector is dead for all of 19 and 20 November."""
    return outage and RELEASE <= t.date() <= RELEASE + dt.timedelta(days=1)


def build_points(effect, until, after=False, seed=1, outage=False):
    """The flattened hourly series, as summarise.flatten would produce it.

    `effect` switches the launch on. `after` keeps it on for the weeks that
    follow -- GTA still being streamed and played -- which is what a real
    launch does, and what a baseline that reaches past the launch would see.
    """
    rnd = random.Random(seed)
    pts = []
    for t in _hours(until):
        if _lost(t, outage):
            continue
        p = {"t": t.isoformat()}
        post = after and t.date() > RELEASE

        # Twitch: a daily cycle peaking around 20:00 UTC.
        cyc = 0.5 + 0.5 * math.cos((t.hour - 20) / 24 * 2 * math.pi)
        tw = 400_000 + 900_000 * cyc
        tw *= 1 + rnd.uniform(-0.05, 0.05)
        if effect and RELEASE <= t.date() <= RELEASE + dt.timedelta(days=1) \
                and (t.date() == RELEASE and t.hour >= 17 or t.hour <= 2):
            tw *= 2.6
        if post:
            tw *= 1.5
        p["twitch_top100_total"] = round(tw)

        # Steam: the six displaced games, each with its own cycle.
        for i, key in enumerate(predictions.STEAM_DISPLACED):
            v = (80_000 + 20_000 * i) * (0.7 + 0.3 * cyc)
            v *= 1 + rnd.uniform(-0.03, 0.03)
            if effect and t.date() == RELEASE and t.hour >= 17:
                v *= 0.7
            if post:
                v *= 0.85
            p[key] = round(v)

        # Roads: evening delay in each city's own time zone.
        for c in CITIES:
            tz = indices.CITY_TZ.get(f"traffic_{c}", "UTC")
            lt = t.astimezone(ZoneInfo(tz))
            base = 35 if 16 <= lt.hour <= 19 else (15 if 7 <= lt.hour <= 22 else 0)
            v = base * (1 + rnd.uniform(-0.08, 0.08)) if base else 0
            if effect and _launch_evening(t, tz):
                v *= 0.55
            p[f"traffic_{c}_delay_pct"] = round(v, 1)

        # Sony's status page.
        p["psn_incidents"] = 1 if (effect and t.date() == RELEASE and t.hour == 21) else 0
        pts.append(p)
    return pts


def build_snapshots(effect, until, backfill, outage=False):
    """ENTSO-E snapshots: one carrying every hour, per country.

    Each ordinary evening is set to its own country's autumn mean, so ordinary
    days score near zero. With the effect on, four grids rise three standard
    deviations on 19 November, enough to clear "three of eight at two".
    """
    tz = power.TZ
    speaking = {"DE", "FR", "ES", "IT"}
    hourly = {}
    cache = {}
    day = START.date()
    while day <= until.date():
        for code, pts in backfill.items():
            # The baseline depends on the season window and weekday class
            # only (made-up 2026 days are never in the backfill), so it is
            # computed once per kind rather than for every day.
            key = (code, power.season_for(day.month), day.weekday() >= 5)
            if key not in cache:
                cache[key] = power.season_baseline(pts, day, pts)
            base = cache[key]
            if not base:
                continue
            # With `outage`, only two grids publish the launch evening: not
            # enough to reach three, whatever they show.
            if outage and day == RELEASE and code not in ("DE", "FR"):
                continue
            ratio = base["mean"]
            if effect and day == RELEASE and code in speaking:
                ratio = base["mean"] + 3 * base["sd"]
            for h in range(24):
                lt = dt.datetime(day.year, day.month, day.day, h, tzinfo=tz)
                if lt.astimezone(UTC) > until:
                    continue
                mw = 40_000 * (ratio if 18 <= h <= 21 else 1.0)
                hourly.setdefault(code, []).append(
                    [lt.astimezone(UTC).isoformat(), mw])
        day += dt.timedelta(days=1)
    return [{"collected_at_utc": until.isoformat(),
             "sources": {"entsoe": {c: {"hourly": v} for c, v in hourly.items()}}}]


def build_mta(effect, until, outage=False):
    """Daily New York subway counts: weekdays near 4.6 million."""
    rows, rnd = [], random.Random(7)
    day = dt.date(2026, 9, 1)
    while day < until.date():                      # published the next morning
        v = 4_600_000 if day.weekday() < 5 else 2_400_000
        v *= 1 + rnd.uniform(-0.006, 0.006)
        if effect and day == RELEASE:
            v *= 0.93
        if outage and day == RELEASE:
            day += dt.timedelta(days=1)
            continue
        rows.append({"date": day.isoformat(), "mode": "Subway", "count": round(v)})
        day += dt.timedelta(days=1)
    return rows


MOMENTS = {
    "launch night, 23:30 UTC": dt.datetime(2026, 11, 19, 23, 30, tzinfo=UTC),
    "next day, 22:00 UTC": dt.datetime(2026, 11, 20, 22, 0, tzinfo=UTC),
    "a week later": dt.datetime(2026, 11, 26, 22, 0, tzinfo=UTC),
    "window closed, 18 Dec": END,
}


def run(effect, after=False, outage=False, moments=MOMENTS):
    bf = power.load_backfill()
    out = {}
    for name, now in moments.items():
        pts = build_points(effect, now, after=after, outage=outage)
        snaps = build_snapshots(effect, now, bf, outage=outage)
        mta = build_mta(effect, now, outage=outage)
        out[name] = score.score_all(pts, snapshots=snaps, mta=mta,
                                    backfill=bf, today=now.date())
    return out


def _line(v):
    if v["verdict"]:
        return v["verdict"].upper()
    if v.get("provisional"):
        return "so far"
    return "no verdict: " + (v.get("reason") or "")[:70]


if __name__ == "__main__":
    for title, kw in [("A STRONG LAUNCH", dict(effect=True)),
                      ("A STRONG LAUNCH, STILL PLAYED AFTERWARDS",
                       dict(effect=True, after=True)),
                      ("NOTHING HAPPENS", dict(effect=False)),
                      ("NOTHING HAPPENS, AND THE COLLECTOR IS DOWN FOR IT",
                       dict(effect=False, outage=True))]:
        print(f"\n=== {title}")
        for moment, verdicts in run(**kw).items():
            print(f"  {moment}")
            for pid, v in verdicts.items():
                print(f"    {pid:8s} {_line(v)}")
