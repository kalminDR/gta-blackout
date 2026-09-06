#!/usr/bin/env python3
"""Tests for the six verdicts.

The invariant this file exists for is in section 8: no scorer may return
"failed" from data it did not have. A collector outage on 19 November must
read as "could not measure", never as "nothing happened" -- the second is a
false result wearing the clothes of a real one, and it is the single most
damaging thing this project could publish.

Everything else here is the ordinary work: each rule passes when it should,
fails when it should, and the two window rules stay provisional until the
window closes.
"""

import datetime
import sys

sys.path.insert(0, "/home/claude/repo")
import predictions  # noqa: E402
import score  # noqa: E402

passed = failed = 0


def check(name, got, want=True):
    global passed, failed
    if got == want:
        passed += 1
        print(f"  PASS  {name}   [{got}]")
    else:
        failed += 1
        print(f"  FAIL  {name}   got {got!r}, wanted {want!r}")


LAUNCH = score.RELEASE
AFTER = datetime.date(2026, 12, 18)      # the day the window has closed


def mta(*pairs):
    return [{"date": d, "mode": "Subway", "count": c} for d, c in pairs]


def hourly(day, hour, **fields):
    return dict({"t": f"{day.isoformat()}T{hour:02d}:30:00+00:00"}, **fields)


print("1. Subway: lower than both, and 3% below the mean of the three")
low = mta(("2026-11-05", 4_500_000), ("2026-11-12", 4_500_000),
          ("2026-11-19", 4_200_000))
check("a clear drop passes", score.score_subway(low)["verdict"], "passed")
check("and reports the margin it used",
      score.score_subway(low)["evidence"]["deviation_from_mean_pct"] < -3, True)

flat = mta(("2026-11-05", 4_500_000), ("2026-11-12", 4_500_000),
           ("2026-11-19", 4_480_000))
check("lowest but not by enough fails", score.score_subway(flat)["verdict"], "failed")

high = mta(("2026-11-05", 4_200_000), ("2026-11-12", 4_500_000),
           ("2026-11-19", 4_300_000))
check("not the lowest fails", score.score_subway(high)["verdict"], "failed")

print("\n2. Traffic: four of six cities at their lowest Thursday evening")
def traffic_points(launch_delays, other_delays):
    pts = []
    for d in (datetime.date(2026, 10, 1), datetime.date(2026, 10, 8), LAUNCH):
        vals = launch_delays if d == LAUNCH else other_delays
        for utc_hour in range(24):
            pts.append(hourly(d, utc_hour, **{f"traffic_{c}_delay_pct": v
                                              for c, v in vals.items()}))
        # A day rolls into the next in UTC for the American cities.
        nxt = d + datetime.timedelta(days=1)
        for utc_hour in range(0, 8):
            pts.append(hourly(nxt, utc_hour, **{f"traffic_{c}_delay_pct": v
                                                for c, v in vals.items()}))
    return pts

six = ["budapest", "london", "berlin", "warsaw", "newyork", "losangeles"]
all_low = traffic_points({c: 5.0 for c in six}, {c: 30.0 for c in six})
r = score.score_traffic(all_low, today=AFTER)
check("six cities lowest passes once the window has closed", r["verdict"], "passed")
check("and it is not provisional after 17 December", r["provisional"], False)

r_open = score.score_traffic(all_low, today=LAUNCH)
check("but on the day itself it stays provisional", r_open["provisional"], True)
check("with no verdict yet", r_open["verdict"], None)
check("while still reporting where it stands",
      len(r_open["evidence"]["cities_lowest_so_far"]), 6)

three = dict({c: 5.0 for c in six[:3]}, **{c: 40.0 for c in six[3:]})
r3 = score.score_traffic(traffic_points(three, {c: 30.0 for c in six}), today=AFTER)
check("three of six is not four, and fails", r3["verdict"], "failed")

print("\n3. Steam: the six displaced games, lowest for the hour")
BASKET = predictions.STEAM_DISPLACED
check("the basket excludes both GTA titles",
      any("gta" in g for g in BASKET), False)
check("and holds six games", len(BASKET), 6)

def steam_points(launch_each, other_each):
    pts = []
    for d in (datetime.date(2026, 10, 1), datetime.date(2026, 10, 8), LAUNCH):
        n = launch_each if d == LAUNCH else other_each
        pts.append(hourly(d, 20, **{g: n for g in BASKET}))
    return pts

check("a launch-evening low passes after the window closes",
      score.score_steam(steam_points(1000, 5000), today=AFTER)["verdict"], "passed")
check("a launch-evening high fails",
      score.score_steam(steam_points(9000, 5000), today=AFTER)["verdict"], "failed")
check("and on the day it is provisional",
      score.score_steam(steam_points(1000, 5000), today=LAUNCH)["provisional"], True)

print("\n4. Servers: one PlayStation incident outside Russia")
check("an incident passes",
      score.score_servers([hourly(LAUNCH, 20, psn_incidents=2)])["verdict"], "passed")
check("a clean day fails",
      score.score_servers([hourly(LAUNCH, 20, psn_incidents=0)])["verdict"], "failed")
check("the day after counts too",
      score.score_servers([hourly(LAUNCH + datetime.timedelta(days=1), 3,
                                  psn_incidents=1)])["verdict"], "passed")
check("a reading from another day does not",
      score.score_servers([hourly(datetime.date(2026, 11, 12), 20,
                                  psn_incidents=5)])["verdict"], None)

print("\n5. THE INVARIANT: absent data never reads as 'it did not happen'")
# Each scorer, given nothing and given a launch day with holes in it. None of
# these may come back "failed": we did not measure, so we do not get to say.
empty_cases = [
    ("subway, no MTA rows", score.score_subway([])),
    ("subway, launch day missing", score.score_subway(
        mta(("2026-11-05", 4_500_000), ("2026-11-12", 4_500_000)))),
    ("traffic, no readings", score.score_traffic([], today=AFTER)),
    ("traffic, one city dark on the night", score.score_traffic(
        traffic_points({c: 5.0 for c in six[:5]}, {c: 30.0 for c in six}),
        today=AFTER)),
    ("power, no snapshots", score.score_power([])),
    ("steam, no readings", score.score_steam([], today=AFTER)),
    ("steam, a game missing from the basket", score.score_steam(
        [hourly(LAUNCH, 20, **{g: 100 for g in BASKET[:-1]})], today=AFTER)),
    ("twitch, no readings", score.score_twitch([])),
    ("twitch, nothing in the launch window", score.score_twitch(
        [hourly(datetime.date(2026, 10, 1), 20, twitch_top100_total=500_000)])),
    ("servers, no readings", score.score_servers([])),
]
for name, r in empty_cases:
    check(f"{name}: not 'failed'", r["verdict"] != "failed", True)
    check(f"{name}: says why", bool(r["reason"]), True)

print("\n6. A partial basket is not a smaller basket")
# Five of six games summed is a smaller number than six, and would look like
# displacement. It must be discarded, not summed.
partial = [hourly(LAUNCH, 20, **{g: 100 for g in BASKET[:-1]})]
full_other = [hourly(datetime.date(2026, 10, 1), 20, **{g: 100 for g in BASKET})]
r = score.score_steam(partial + full_other, today=AFTER)
check("an incomplete launch reading yields no verdict", r["verdict"], None)
check("rather than a spuriously low total", "basket" in (r["reason"] or ""), True)

print("\n7. score_all never raises, and never invents")
r = score.score_all([], snapshots=[], mta=[])
check("all six report", len(r), 6)
check("none of them failed on no data",
      [v["verdict"] for v in r.values()], [None] * 6)
check("and each says why", all(v["reason"] for v in r.values()), True)

# A scorer that throws is our bug, not the world's answer.
broken = dict(score.SCORERS)
try:
    score.SCORERS["subway"] = lambda ctx: 1 / 0
    r = score.score_all([], snapshots=[], mta=[])
    check("a crashing scorer reports unscored, not failed",
          r["subway"]["verdict"], None)
    check("and carries the error", "scorer error" in r["subway"]["reason"], True)
finally:
    score.SCORERS.clear()
    score.SCORERS.update(broken)

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
