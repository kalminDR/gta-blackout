#!/usr/bin/env python3
"""
Checks on the index maths, run against data where the answer is known.

Run:  python test_indices.py

Six weeks of hourly points with a strong daily cycle and a weekend bulge -
the same shape the real data has, and the shape that would break a naive
baseline. Every test states what it proves.
"""

import math
import sys
from datetime import datetime, timedelta, timezone

import indices


def cycle(t, base):
    """Daily sine plus a weekend lift. Deliberately large, so a baseline
    that ignores the hour of the week cannot possibly pass."""
    daily = 1 + 0.6 * math.sin((t.hour - 4) / 24 * 2 * math.pi)
    weekend = 1.4 if t.weekday() >= 5 else 1.0
    return base * daily * weekend


def make_series(weeks=6, spike=None):
    """spike: (datetime, {metric_key: multiplier})"""
    points = []
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    for h in range(weeks * 7 * 24):
        t = start + timedelta(hours=h)
        p = {"t": t.isoformat(timespec="seconds")}
        levels = {
            "twitch_gta6_viewers": 40000,
            "twitch_gta6_channels": 900,
            "yt_trailer_views_per_hour": 12000,
            "yt_rockstar_views_per_hour": 30000,
            "steam_cs2": 900000,
            "steam_dota2": 600000,
            "steam_pubg": 190000,
            "steam_apex": 77000,
            "steam_bg3": 55000,
            "steam_rdr2": 37000,
            "steam_gta5": 58000,
            "steam_gta5_enhanced": 52000,
            "twitch_other_viewers": 800000,
            "psn_incidents": 4,
            "xbox_service_issues": 1,
        }
        for key, base in levels.items():
            p[key] = round(cycle(t, base), 2)
        for city in indices.CITY_TZ:
            p[f"{city}_travel_index"] = round(cycle(t, 120), 2)
        p["hn_items_per_hour"] = round(cycle(t, 900), 2)

        if spike and t == spike[0]:
            for key, mult in spike[1].items():
                if key in p:
                    p[key] = round(p[key] * mult, 2)
        points.append(p)
    return points


def panel_index(points, when, panel):
    for p in points:
        if p["t"] == when.isoformat(timespec="seconds"):
            entry = (p.get("indices") or {}).get(panel)
            return entry["index"] if entry else None
    return None


FAILS = []


def check(name, condition, detail=""):
    print(f"  {'PASS' if condition else 'FAIL'}  {name}"
          + (f"   [{detail}]" if detail else ""))
    if not condition:
        FAILS.append(name)


def main():
    print("\n1. A perfectly normal series should read exactly 100 everywhere")
    pts = indices.compute(make_series())
    vals = [(p.get("indices") or {}).get("attention") for p in pts]
    scored = [v["index"] for v in vals if v]
    check("every scored hour is 100",
          scored and all(v == 100 for v in scored),
          f"{len(scored)} scored hours, range {min(scored)}-{max(scored)}"
          if scored else "nothing scored")
    check("most hours got a baseline",
          len(scored) > 0.8 * len(pts), f"{len(scored)}/{len(pts)}")

    print("\n2. Tripling GTA attention should read exactly 300")
    when = datetime(2026, 10, 8, 14, tzinfo=timezone.utc)
    pts = indices.compute(make_series(spike=(when, {
        "twitch_gta6_viewers": 3, "twitch_gta6_channels": 3,
        "yt_trailer_views_per_hour": 3, "yt_rockstar_views_per_hour": 3})))
    got = panel_index(pts, when, "attention")
    check("attention = 300", got == 300, f"got {got}")

    print("\n3. THE STEAM SIGN. Other games falling must not cancel attention.")
    print("   Attention triples and every Steam game halves in the same hour.")
    spike = {"twitch_gta6_viewers": 3, "twitch_gta6_channels": 3,
             "yt_trailer_views_per_hour": 3, "yt_rockstar_views_per_hour": 3}
    for key, _ in indices.STEAM_GAMES:
        spike[key] = 0.5
    spike["twitch_other_viewers"] = 0.5
    pts = indices.compute(make_series(spike=(when, spike)))
    att = panel_index(pts, when, "attention")
    disp = panel_index(pts, when, "displacement")
    check("attention still 300, untouched by Steam", att == 300, f"got {att}")
    check("displacement = 200 (halving reads as double displacement)",
          disp == 200, f"got {disp}")
    check("the two did not cancel out", att > 100 and disp > 100,
          f"attention {att}, displacement {disp}")

    print("\n4. Small games must count as much as Counter-Strike")
    print("   Only CS2 and Dota halve; the six smaller games are unchanged.")
    pts = indices.compute(make_series(spike=(when, {
        "steam_cs2": 0.5, "steam_dota2": 0.5})))
    disp = panel_index(pts, when, "displacement")
    check("two of nine moving barely shifts the median",
          disp is not None and 95 <= disp <= 105,
          f"got {disp} - a player-weighted sum would have read about 130")

    print("\n5. Work falls when activity falls (not flipped upward)")
    spike = {f"{c}_travel_index": 0.7 for c in indices.CITY_TZ}
    pts = indices.compute(make_series(spike=(when, spike)))
    work = panel_index(pts, when, "work")
    check("work index below 100", work is not None and work < 100, f"got {work}")
    check("30% less road load reads as roughly 70",
          work is not None and 68 <= work <= 72, f"got {work}")

    print("\n6. Short history must stay blank, never guess 100")
    pts = indices.compute(make_series(weeks=1))
    scored = [p for p in pts if (p.get("indices") or {}).get("attention")]
    check("one week of data scores nothing",
          len(scored) == 0, f"{len(scored)} hours scored")

    print("\n7. Placebo Thursdays")
    pts = indices.compute(make_series(spike=(
        datetime(2026, 10, 8, 14, tzinfo=timezone.utc),
        {"twitch_gta6_viewers": 8, "twitch_gta6_channels": 8,
         "yt_trailer_views_per_hour": 8, "yt_rockstar_views_per_hour": 8})))
    days = indices.placebo(pts, "attention")
    check("every Thursday in range is listed", len(days) >= 4, f"{len(days)} days")
    spiked = [d for d in days if d["date"] == "2026-10-08"]
    others = [d["peak"] for d in days if d["date"] != "2026-10-08"]
    check("a one-hour spike is invisible in the day's median",
          spiked and spiked[0]["index"] == 100,
          f"median {spiked[0]['index'] if spiked else '?'} - which is why "
          f"the peak is published too")
    check("the spiked Thursday has the highest peak",
          spiked and others and spiked[0]["peak"] > max(others),
          f"peak {spiked[0]['peak'] if spiked else '?'} vs others max "
          f"{max(others) if others else '?'}")
    check("percentile puts it at the top",
          indices.percentile_of(spiked[0]["peak"], others, +1) == 100.0
          if spiked and others else False)

    print("\n8. A dead source must not drag a panel")
    pts_ok = indices.compute(make_series())
    pts_bad = make_series()
    for p in pts_bad:
        p["steam_cs2"] = 1          # API returns nonsense for one game
    pts_bad = indices.compute(pts_bad)
    disp_ok = panel_index(pts_ok, when, "displacement")
    disp_bad = panel_index(pts_bad, when, "displacement")
    check("one broken game leaves displacement at 100",
          disp_bad == disp_ok == 100, f"healthy {disp_ok}, with broken {disp_bad}")

    print("\n9. Local time: cities are matched on their own clock")
    check("timezone database available", indices.HAVE_TZ)
    ny = indices.hour_keys(datetime(2026, 11, 19, 14, tzinfo=timezone.utc),
                           "America/New_York")
    bp = indices.hour_keys(datetime(2026, 11, 19, 14, tzinfo=timezone.utc),
                           "Europe/Budapest")
    check("14:00 UTC is a different local hour in New York and Budapest",
          ny[1] != bp[1], f"New York {ny[1][1]}:00, Budapest {bp[1][1]}:00")

    print("\n" + ("-" * 60))
    if FAILS:
        print(f"{len(FAILS)} FAILED: {', '.join(FAILS)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
