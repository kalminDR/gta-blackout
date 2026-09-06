#!/usr/bin/env python3
"""Tests for the six published predictions.

Most of these are structural: a prediction that reaches the page without a
threshold, a base rate, or the claim it serves is not a prediction, it is a
boast. The rest re-derive the two thresholds that were rewritten because their
first versions would have been satisfied with no game involved, and assert
that the rewritten versions are not.
"""

import datetime
import statistics
import sys

sys.path.insert(0, "/home/claude/repo")
import json  # noqa: E402
import power  # noqa: E402
import predictions  # noqa: E402

passed = failed = 0


def check(name, got, want=True):
    global passed, failed
    if got == want:
        passed += 1
        print(f"  PASS  {name}   [{got}]")
    else:
        failed += 1
        print(f"  FAIL  {name}   got {got!r}, wanted {want!r}")


print("1. Every prediction is complete")
REQUIRED = ("id", "claim", "says", "rule", "threshold_from", "base_rate", "caveat")
check("there are six", len(predictions.PREDICTIONS), 6)
check("the ids are unique",
      len({p["id"] for p in predictions.PREDICTIONS}), 6)
for p in predictions.PREDICTIONS:
    missing = [f for f in REQUIRED if not p.get(f)]
    check(f"{p['id']}: carries every field", missing, [])
    check(f"{p['id']}: the rule names a date or a window",
          any(w in p["rule"] for w in ("2026", "19 November")))

print("\n2. Every prediction serves one of the six claims")
# The site is organised around six sentences a reader could have said. A
# prediction that does not land under one of them is the apparatus talking
# about itself.
CLAIM_IDS = {"work", "home", "quiet", "consoles", "servers", "money"}
for p in predictions.PREDICTIONS:
    check(f"{p['id']}: claim '{p['claim']}' exists", p["claim"] in CLAIM_IDS)
check("claim 06 gets no prediction, by design",
      any(p["claim"] == "money" for p in predictions.PREDICTIONS), False)
check("claim 04 gets none either, for want of a defensible threshold",
      any(p["claim"] == "consoles" for p in predictions.PREDICTIONS), False)

print("\n3. The subway threshold, re-derived")
mta = json.load(open("data/backfill/mta_ridership.json"))["data"]
sub = {datetime.date.fromisoformat(r["date"]): r["count"]
       for r in mta if r["mode"] == "Subway" and r.get("count")}


def thanksgiving(y):
    d1 = datetime.date(y, 11, 1)
    first = d1 + datetime.timedelta(days=(3 - d1.weekday()) % 7)
    return first + datetime.timedelta(days=21)


def november_thursdays(y):
    tg = thanksgiving(y)
    return {d: v for d, v in sub.items()
            if d.year == y and d.month == 11 and d.weekday() == 3 and d != tg}


for y in (2023, 2024, 2025):
    thu = november_thursdays(y)
    mean = statistics.mean(thu.values())
    worst = min(100 * (v / mean - 1) for v in thu.values())
    check(f"{y}: no November Thursday falls 3% below its month", worst > -3.0)
    check(f"{y}: nor even 1.5% below", worst > -1.5)
    third = sorted(thu)[2]
    fires = (thu[third] == min(thu.values())
             and 100 * (thu[third] / mean - 1) <= -3.0)
    check(f"{y}: the published rule does not fire", fires, False)

print("\n4. And the version it replaced would have been broken by Christmas")
# The inherited rule compared 19 November to the whole October-December
# window. Christmas Eve and New Year's Eve are Thursdays in 2026.
xmas_thursdays = [d for d in (datetime.date(2026, 12, 24),
                              datetime.date(2026, 12, 31))]
check("both fall on a Thursday",
      all(d.weekday() == 3 for d in xmas_thursdays))
for y in (2023, 2024, 2025):
    window = {d: v for d, v in sub.items()
              if d.year == y and d.month in (10, 11, 12) and d.weekday() == 3
              and d != thanksgiving(y)}
    lowest = min(window, key=window.get)
    check(f"{y}: the lowest Thursday of the old window was in late December",
          lowest.month == 12 and lowest.day >= 21)

print("\n5. The electricity threshold, re-derived")
bf = power.load_backfill()
COUNTRIES = ["DE", "FR", "ES", "IT", "NL", "PL", "SE", "HU"]
ratios = {c: power.ratios_for(bf[c], months=(10, 11, 12), weekdays_only=True)
          for c in COUNTRIES}
bases = {c: power.baseline(ratios[c]) for c in COUNTRIES}
days = sorted(set.intersection(*[set(r) for r in ratios.values()]))
counts = [sum(1 for c in COUNTRIES
              if abs(power.z_score(ratios[c][d], bases[c])) >= 2.0) for d in days]
rate = {k: sum(1 for n in counts if n >= k) / len(days) for k in (1, 2, 3)}
check("a baseline of ordinary weekdays to measure against", len(days) > 200)
check("one grid clearing two sigma is common, so it is not the rule",
      rate[1] > 0.20)
check("three grids is rare, which is why it is the rule", rate[3] < 0.02)
check("the published rule asks for three",
      "three of the eight" in
      next(p for p in predictions.PREDICTIONS if p["id"] == "power")["rule"])

print("\n6. No prediction is already satisfied")
# The Russian PlayStation Store lesson: a prediction true before the event is
# worse than no prediction, because it looks like a result.
series = json.load(open("public/series.json"))["points"]
psn = [x["psn_incidents"] for x in series
       if isinstance(x.get("psn_incidents"), (int, float))]
check("PSN incidents outside Russia stand at zero, so the rule can still fail",
      max(psn) if psn else None, 0)
check("and there were readings to check", len(psn) > 50)

print("\n7. The commitment is published with them")
check("there is a commitment", bool(predictions.COMMITMENT))
check("it promises not to edit them",
      "not quietly edit" in predictions.COMMITMENT)
pub = predictions.as_published()
check("the published shape carries the release day",
      pub["release_day"], "2026-11-19")
# If this were generated from the clock, the page would re-earn "written in
# advance" every hour and the phrase would mean nothing.
check("the publication date is a fixed constant, not today",
      pub["published_at"], predictions.PUBLISHED_AT)
check("and it is before the launch", pub["published_at"] < pub["release_day"])
check("and all six", len(pub["predictions"]), 6)

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
