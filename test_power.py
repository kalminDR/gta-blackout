#!/usr/bin/env python3
"""Tests for the evening ratio.

Two kinds of check. The first kind is arithmetic on fixtures: does the ratio
do what it says, and does it refuse to answer when it should. The second kind
is a regression lock on the real backfill: the hours were chosen because they
reproduce the December 2022 World Cup results recorded in CLAUDE.md section 5,
so those results are asserted here. If somebody adjusts PEAK_HOURS or
REFERENCE_HOUR to make a number look better, this file fails.
"""

import datetime
import sys

sys.path.insert(0, "/home/claude/repo")
import power  # noqa: E402

passed = failed = 0


def check(name, got, want=True):
    global passed, failed
    if got == want:
        passed += 1
        print(f"  PASS  {name}   [{got}]")
    else:
        failed += 1
        print(f"  FAIL  {name}   got {got!r}, wanted {want!r}")


def hours(**kw):
    return {int(k[1:]): v for k, v in kw.items()}


print("1. The ratio itself")
check("peak over reference",
      power.evening_ratio(hours(h16=100.0, h18=110.0, h19=120.0)), 1.2)
check("the largest evening hour wins, not the last",
      power.evening_ratio(hours(h16=100.0, h18=130.0, h19=110.0)), 1.3)
check("hours outside the window are ignored",
      power.evening_ratio(hours(h16=100.0, h19=110.0, h23=900.0)), 1.1)

print("\n2. A day that cannot be measured returns nothing, never a guess")
check("no reference hour", power.evening_ratio(hours(h18=110.0)), None)
check("no evening hour", power.evening_ratio(hours(h16=100.0)), None)
check("empty day", power.evening_ratio({}), None)
check("a zero reference is not a divisor",
      power.evening_ratio(hours(h16=0.0, h19=110.0)), None)
check("a missing value is not a number",
      power.evening_ratio(hours(h16=None, h19=110.0)), None)

print("\n3. Local time, not UTC")
# 17:00 UTC in November is 18:00 CET: inside the evening window. The same
# clock time in August is 19:00 CEST. Reading these as UTC would put the
# evening peak in the wrong bucket half the year.
pts = [["2026-11-19T15:00:00+00:00", 100.0], ["2026-11-19T17:00:00+00:00", 130.0]]
days = power.days_by_local_date(pts)
day = datetime.date(2026, 11, 19)
check("timestamps land on the local date", list(days), [day])
check("15:00 UTC is the 16:00 reference hour in CET", sorted(days[day]), [16, 18])
check("and the ratio follows", power.evening_ratio(days[day]), 1.3)

print("\n4. A thin baseline is refused")
check("under the minimum, no baseline",
      power.baseline([1.0] * (power.MIN_BASELINE_DAYS - 1)), None)
check("at the minimum, a baseline exists",
      power.baseline([1.0, 1.1] * power.MIN_BASELINE_DAYS) is not None)
check("no ratio means no z-score", power.z_score(None, {"mean": 1.0, "sd": 0.1}), None)
check("no baseline means no z-score", power.z_score(1.2, None), None)
check("a baseline that never varies cannot score anything",
      power.z_score(1.2, {"mean": 1.0, "sd": 0.0}), None)

print("\n5. The backfill baselines")
bases = power.autumn_baselines()
check("eight countries have an autumn baseline", len(bases), 8)
check("Great Britain is absent, not invented", "GB" in bases, False)
check("every baseline is built from real days",
      all(b["n"] >= power.MIN_BASELINE_DAYS for b in bases.values()))
# The floor each country can actually detect. Locked so that a country
# quietly getting noisier is noticed rather than published.
check("Germany is the most sensitive instrument", bases["DE"]["cv_pct"] <= 2.5)
check("Hungary is the least sensitive, and knows it",
      bases["HU"]["cv_pct"] >= 6.0)

print("\n6. Regression lock: December 2022, from CLAUDE.md section 5")
# The hours are not adjustable to taste. France on its own semi-final is the
# one like-for-like comparison section 5 offers -- a Wednesday against other
# weekdays -- and this implementation reproduces it. Change PEAK_HOURS or
# REFERENCE_HOUR and this fails.
bf = power.load_backfill()
semi = datetime.date(2022, 12, 14)      # France-Morocco semi-final, Wed, 20:00 CET

def z_on(code, day, weekend):
    r = power.ratios_for(bf[code], months=(10, 11, 12), weekdays_only=False)
    r = {d: v for d, v in r.items() if (d.weekday() >= 5) == weekend}
    return power.z_score(r.get(day), power.baseline({d: v for d, v in r.items()
                                                     if d != day}))

fr = z_on("FR", semi, weekend=False)
check("France sags on its own semi-final, weekday against weekdays",
      -2.5 < fr < -1.0)

print("\n7. The weekend is not an event")
# Section 5 records Spain +4.1 and Italy +4.1 on 27 November 2022 as evidence
# that the ratio detects a big television audience. That match was a Sunday,
# and those figures come from scoring a Sunday against a weekday baseline.
# The ratio is structurally higher at weekends in every country -- Italy by
# 3.6 weekday standard deviations, which is the whole of its supposed World
# Cup signal. Compared Sunday to Sunday, both readings vanish.
#
# This is asserted rather than corrected because it is the reason the method
# must always compare like with like, and because the same mistake would make
# 19 November 2026 look like a result no matter what happened.
group = datetime.date(2022, 11, 27)     # Spain-Germany, Sunday, 20:00 CET
for code in ("ES", "IT"):
    same = z_on(code, group, weekend=True)
    check(f"{code} on the group match, Sunday against Sundays, is nothing",
          abs(same) < 1.5)

for code, gap in (("IT", 3.0), ("ES", 1.5)):
    allr = power.ratios_for(bf[code], months=(10, 11, 12), weekdays_only=False)
    wd = power.baseline({d: v for d, v in allr.items() if d.weekday() < 5})
    we = power.baseline({d: v for d, v in allr.items() if d.weekday() >= 5})
    check(f"{code}: the weekend alone is worth more than {gap} weekday sd",
          (we["mean"] - wd["mean"]) / wd["sd"] > gap)

print("\n8. The verdict a country hands the page")
# The invariant the front end depends on: a reading never arrives without the
# size of what its grid could have detected. Without that number the page
# cannot tell an informative silence from an ignorant one, and would show
# Hungary's blindness and Germany's evidence as the same "no change".
day = datetime.date(2022, 12, 14)
for code in ("DE", "FR", "HU"):
    v = power.verdict(bf[code], bf[code], day=day)
    check(f"{code}: a verdict exists for a real day", v is not None)
    check(f"{code}: it carries the floor it could have detected",
          isinstance(v["detects_pct"], float))
    check(f"{code}: and the day it is about", v["day"], day.isoformat())

de = power.verdict(bf["DE"], bf["DE"], day=day)
hu = power.verdict(bf["HU"], bf["HU"], day=day)
check("Germany's floor is lower than Hungary's, which is the whole point",
      de["detects_pct"] < hu["detects_pct"])
check("neither of them speaks on an ordinary evening",
      de["speaks"] is False and hu["speaks"] is False)

print("\n9. Weekday class is matched, not assumed")
# The guard against repeating the Sunday-versus-weekday error, this time
# enforced by the code rather than by whoever calls it.
sunday = datetime.date(2022, 11, 27)
v_sun = power.verdict(bf["IT"], bf["IT"], day=sunday)
check("a Sunday is judged as a weekend", v_sun["weekend"])
check("a Wednesday is judged as a weekday",
      power.verdict(bf["IT"], bf["IT"], day=day)["weekend"], False)
check("Italy on that Sunday stays silent, as it should",
      v_sun["speaks"], False)
# Scored the wrong way round it would have been a headline.
wrong = power.baseline({d: r for d, r in
                        power.ratios_for(bf["IT"], months=(10, 11, 12)).items()})
check("and scored against weekdays it would have cleared two sigma",
      abs(power.z_score(v_sun["ratio"], wrong)) > 2.0)

print("\n10. Nothing to judge yields nothing")
check("a series with no complete evening has no verdict",
      power.verdict([["2026-09-06T09:15:00+00:00", 40000.0]], bf["DE"]), None)
check("an empty series has no verdict", power.verdict([], bf["DE"]), None)
check("a country absent from the backfill is skipped, not invented",
      power.verdicts_from_series(
          [{"t": "2026-11-19T15:00:00+00:00", "power_gb_load_mw": 30000.0},
           {"t": "2026-11-19T19:00:00+00:00", "power_gb_load_mw": 33000.0}]),
      {})

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
