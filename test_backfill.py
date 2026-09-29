#!/usr/bin/env python3
"""The daily backfill must never write a file with less history than it had.

When the backfill ran by hand, rewriting each file from scratch was safe:
someone watched the run. Once it ran daily it was not. On 29 September 2026
three ENTSO-E monthly chunks timed out and the rewrite dropped them -- October
2025 for Germany, November 2025 for Spain, November 2022 for Italy -- which is
the autumn baseline the electricity prediction is scored against.
test_power.py caught it, but only because it happened to read those months.

These tests push on the rule directly, for both ways a run can lose data: a
whole source failing, and one source partly failing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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


def entsoe(points_by_code):
    return {"source": "ENTSO-E", "problems": {},
            "data": {c: {"points": [[t, mw] for t, mw in pts]}
                     for c, pts in points_by_code.items()}}


OCT = [("2025-10-01T18:00:00+00:00", 60000.0), ("2025-10-01T19:00:00+00:00", 61000.0)]
NOV = [("2025-11-01T18:00:00+00:00", 62000.0)]

print("1. ENTSO-E: a run that misses a chunk keeps the chunk it missed")
old = entsoe({"DE": OCT + NOV, "FR": NOV})
new = entsoe({"DE": NOV})                      # October timed out; FR entirely
out = backfill._keep_history("entsoe_load", old, new)
de = [t for t, _ in out["data"]["DE"]["points"]]
check("Germany still has its October evening", OCT[0][0] in de, True)
check("and every hour it had", len(de), 3)
check("France, absent from this run, is kept", "FR" in out["data"], True)
check("countries_ok describes the merged file", out["countries_ok"], ["DE", "FR"])

revised = entsoe({"DE": [("2025-11-01T18:00:00+00:00", 62500.0)]})
out = backfill._keep_history("entsoe_load", old, revised)
check("an hour fetched again takes the newer figure",
      dict(map(tuple, out["data"]["DE"]["points"]))["2025-11-01T18:00:00+00:00"], 62500.0)
check("the result is in time order",
      [t for t, _ in out["data"]["DE"]["points"]]
      == sorted(t for t, _ in out["data"]["DE"]["points"]), True)

print("\n2. Any source: a failed run keeps the old file and says what failed")
mta_old = {"source": "MTA", "rows": 3, "data": [1, 2, 3], "fetched_at_utc": "2026-09-28T06:31:00+00:00"}
err = {"error": "The read operation timed out", "fetched_at_utc": "2026-09-29T06:31:00+00:00"}
out = backfill._keep_history("mta_ridership", mta_old, err)
check("the ridership rows survive", out["data"], [1, 2, 3])
check("the error is recorded beside them", out["last_error"], "The read operation timed out")
check("with when it happened", out["last_error_at_utc"], "2026-09-29T06:31:00+00:00")
check("and fetched_at still says when the data was fetched",
      out["fetched_at_utc"], "2026-09-28T06:31:00+00:00")

out = backfill._keep_history("mta_ridership", mta_old, {"source": "MTA", "data": [1, 2, 3, 4]})
check("a successful run replaces the file", out["data"], [1, 2, 3, 4])
check("and carries no stale error", "last_error" in out, False)

print("\n3. Nothing to keep: the failure is written as it is")
out = backfill._keep_history("mta_ridership", {}, err)
check("no old file: the error is the file", out.get("error"), "The read operation timed out")
out = backfill._keep_history("mta_ridership", {"error": "earlier failure"}, err)
check("an old error is not 'history' worth keeping", out.get("error"),
      "The read operation timed out")

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
