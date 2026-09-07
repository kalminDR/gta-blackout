#!/usr/bin/env python3
"""Tests for the Chicago transit backfill.

Chicago exists for redundancy: New York is otherwise a single point of failure
under claim 01, and if the MTA feed is late or broken on 19 November the
strongest evidence for "fewer of us went to work" is simply absent.

The network is unreachable from the build environment, so the parser is
exercised against fixtures. The first three rows are real -- copied from the
live endpoint -- so that a change in the field names shows up here.

Most of this file is about `day_type`. The CTA labels every day weekday,
Saturday, or Sunday-and-holiday, which is the thing New York made us infer by
hunting for dips. But the CTA ships no code book, and a code book remembered
rather than read is exactly how a wrong assumption survives. So the meaning is
derived from the calendar, and these tests check the derivation rather than
the assumption.
"""

import datetime
import sys

sys.path.insert(0, "/home/claude/repo")
import backfill  # noqa: E402

passed = failed = 0


def check(name, got, want=True):
    global passed, failed
    if got == want:
        passed += 1
        print(f"  PASS  {name}   [{got}]")
    else:
        failed += 1
        print(f"  FAIL  {name}   got {got!r}, wanted {want!r}")


# Real rows from data.cityofchicago.org/resource/6iiy-9s97.json
REAL = [
    {"service_date": "2001-01-01T00:00:00.000", "day_type": "U",
     "bus": "297192", "rail_boardings": "126455", "total_rides": "423647"},
    {"service_date": "2001-01-02T00:00:00.000", "day_type": "W",
     "bus": "780827", "rail_boardings": "501952", "total_rides": "1282779"},
    {"service_date": "2001-01-03T00:00:00.000", "day_type": "W",
     "bus": "824923", "rail_boardings": "536432", "total_rides": "1361355"},
]

print("1. The real rows parse into the shape the rest of the project expects")
parsed = []
for r in REAL:
    rec = {}
    for k, v in r.items():
        if k == "service_date":
            rec["date"] = v[:10]
        elif backfill._is_number(v):
            rec[k] = backfill._num(v)
        else:
            rec[k] = v
    parsed.append(rec)

check("the date is a plain calendar date", parsed[0]["date"], "2001-01-01")
check("counts become numbers", parsed[1]["total_rides"], 1282779.0)
check("day_type stays a label, not a number", parsed[1]["day_type"], "W")
check("bus and rail are both carried",
      all(k in parsed[0] for k in ("bus", "rail_boardings")), True)

print("\n2. day_type is derived from the calendar, not from memory")
# A synthetic year using the coding the real data implies: weekdays W,
# Saturdays A, Sundays U -- and holidays U even when they fall midweek.
HOLIDAYS = {datetime.date(2025, 1, 1), datetime.date(2025, 7, 4),
            datetime.date(2025, 11, 27), datetime.date(2025, 12, 25),
            datetime.date(2025, 5, 26), datetime.date(2025, 9, 1)}
rows = []
d = datetime.date(2025, 1, 1)
while d <= datetime.date(2025, 12, 31):
    if d in HOLIDAYS:
        code = "U"
    elif d.weekday() == 5:
        code = "A"
    elif d.weekday() == 6:
        code = "U"
    else:
        code = "W"
    rows.append({"date": d.isoformat(), "day_type": code})
    d += datetime.timedelta(days=1)

meaning = backfill._day_type_meaning(rows)
check("all three codes are described", sorted(meaning), ["A", "U", "W"])
check("A is read as Saturday", meaning["A"]["mostly"], "Saturday")
check("and unambiguously so", meaning["A"]["share_pct"], 100.0)
check("U is read as Sunday", meaning["U"]["mostly"], "Sunday")
check("W is read as a weekday",
      meaning["W"]["mostly"] in ("Monday", "Tuesday", "Wednesday",
                                 "Thursday", "Friday"), True)

print("\n3. The holidays fall out of it, which is the point")
# Weekdays carrying a weekend code are holidays. New York made us find these
# by looking for dips beyond 5%; Chicago just says so.
midweek_holidays = sum(1 for h in HOLIDAYS if h.weekday() < 5)
check("every midweek holiday shows as an exception under U",
      meaning["U"]["weekday_exceptions"], midweek_holidays)
check("Saturday has no such exceptions", meaning["A"]["weekday_exceptions"], 0)
check("and a weekday code is not treated as a weekend one",
      meaning["W"]["weekday_exceptions"], 0)

print("\n4. Bad input is dropped, not guessed at")
check("a row with no date is ignored",
      backfill._day_type_meaning([{"day_type": "W"}]), {})
check("an unparseable date is ignored",
      backfill._day_type_meaning([{"date": "not-a-date", "day_type": "W"}]), {})
check("a missing day_type is ignored",
      backfill._day_type_meaning([{"date": "2025-01-02"}]), {})
check("no rows at all is empty, not an error",
      backfill._day_type_meaning([]), {})

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
