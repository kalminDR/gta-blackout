#!/usr/bin/env python3
"""Tests for which traffic points count, and from when.

On 27 September 2026 eighteen of the thirty-six candidate points were kept:
the ones that register any delay at all. The rest read "empty road" through
every rush hour, and a road that never looks busy cannot look quieter on
19 November. See the note above CITY_POINTS in collect.py.

Two things are checked here. That the city figure is built only from the kept
points, over the whole history, so the series is one instrument. And that the
kept set is the one fixed before 1 October -- the traffic prediction is a rank
test across Thursdays from that date, and a point swapped in mid-window would
make one Thursday incomparable with the others.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import summarise  # noqa: E402

passed = failed = 0


def check(name, got, want=True):
    global passed, failed
    if got == want:
        passed += 1
        print(f"  PASS  {name}   [{got}]")
    else:
        failed += 1
        print(f"  FAIL  {name}   got {got!r}, wanted {want!r}")


def reading(point, cur, free, metres=1500, frc="FRC1"):
    return {"point": point, "current_travel_time": cur,
            "free_flow_travel_time": free, "road_class": frc,
            "segment_metres": metres}


def snap(t, budapest_points):
    return {"collected_at_utc": t,
            "sources": {"traffic": {"Budapest": {"points": budapest_points}}}}


AFTER = "2026-09-20T16:05:00+00:00"
BEFORE = "2026-09-05T16:05:00+00:00"

print("1. Only kept points make up the city figure")
kept = [reading("hungaria_korut", 150, 100), reading("ulloi_ut", 120, 100)]
row = summarise.flatten(snap(AFTER, kept))
check("two kept points: (270 / 200 - 1) = 35% delay",
      row["traffic_budapest_delay_pct"], 35.0)
check("both counted", row["traffic_budapest_points_ok"], 2)

# A retired point on a long empty road would pull the city towards zero.
deaf = reading("m0_south", 300, 300, metres=4638, frc="FRC2")
row = summarise.flatten(snap(AFTER, kept + [deaf]))
check("a retired point's reading changes nothing",
      row["traffic_budapest_delay_pct"], 35.0)
check("and is not counted as a point", row["traffic_budapest_points_ok"], 2)
check("nor as a rejection -- it was never a candidate any more",
      row["traffic_budapest_points_rejected"], 0)

print("\n2. The existing quality gate still applies to kept points")
short = reading("vaci_ut", 500, 100, metres=400)
row = summarise.flatten(snap(AFTER, kept + [short]))
check("a kept point on a short segment is still rejected",
      row["traffic_budapest_delay_pct"], 35.0)
check("and counted as rejected", row["traffic_budapest_points_rejected"], 1)

print("\n3. Readings from before the rebuild are a different instrument")
row = summarise.flatten(snap(BEFORE, kept))
check("same point names, before 6 September 09:00 UTC: no figure",
      row["traffic_budapest_delay_pct"], None)
check("no points counted", row["traffic_budapest_points_ok"], None)
check("and no claim that the gate looked and found nothing",
      row["traffic_budapest_points_rejected"], None)
row = summarise.flatten(snap("2026-09-06T09:15:21+00:00", kept))
check("the first rebuilt snapshot counts", row["traffic_budapest_delay_pct"], 35.0)

print("\n4. The kept set is fixed for the prediction window")
# Changing this set after 1 October 2026 changes the instrument in the middle
# of a rank test. If a point dies during the window it is dropped (the city
# reads fewer points), never replaced: a replacement would measure a road the
# earlier Thursdays never saw.
FIXED = {
    "Budapest": {"hungaria_korut", "ulloi_ut", "vaci_ut"},
    "London": {"a3_wandsworth", "a13_east"},
    "Berlin": {"frankfurter_allee", "prenzlauer_allee", "tempelhofer_damm"},
    "Warsaw": {"wislostrada", "trasa_lazienkowska"},
    "New York": {"bqe_i278", "lie_i495_queens", "fdr_drive", "cross_bronx_i95"},
    "Los Angeles": {"i110_harbor", "i405_sepulveda", "i210_pasadena",
                    "i10_santa_monica"},
}
for city, names in FIXED.items():
    check(f"{city}: kept set unchanged", set(collect.CITY_POINTS[city]), names)
check("every city in the series has points",
      set(summarise.CITY_KEYS) <= set(collect.CITY_POINTS), True)
check("no point is both kept and retired",
      any(set(collect.CITY_POINTS[c]) & set(collect.RETIRED_POINTS.get(c, {}))
          for c in collect.CITY_POINTS), False)
check("every retired point says why",
      all(isinstance(v, tuple) and len(v) == 2 and v[1]
          for pts in collect.RETIRED_POINTS.values() for v in pts.values()), True)
check("18 calls an hour to TomTom, down from 36",
      sum(len(p) for p in collect.CITY_POINTS.values()), 18)

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
