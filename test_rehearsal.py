#!/usr/bin/env python3
"""The launch, rehearsed: what the six verdicts say over time.

test_score.py checks each scorer on hand-built moments. This checks the whole
set across the days that matter -- launch night, the next evening, a week
later, and after the rank window closes -- on a made-up autumn from
rehearsal.py, in four versions of 19 November.

The first run of this found three faults that no single-moment test could:

  * the electricity verdict existed for one night, then reverted for good to
    "no complete launch-day evening yet" once the 20th was recorded;
  * Twitch and PlayStation printed FAILED on launch night with a day of their
    two-day window still to run;
  * with only two grids reporting, electricity printed FAILED although three
    were needed -- an outage reading as evidence.

Each assertion below is one of those, or the property they broke.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rehearsal  # noqa: E402

passed = failed = 0


def check(name, got, want=True):
    global passed, failed
    if got == want:
        passed += 1
        print(f"  PASS  {name}   [{got}]")
    else:
        failed += 1
        print(f"  FAIL  {name}   got {got!r}, wanted {want!r}")


NIGHT, NEXT, WEEK, CLOSED = rehearsal.MOMENTS


def verdicts(run, pid):
    return [run[m][pid]["verdict"] for m in rehearsal.MOMENTS]


print("1. A strong launch")
strong = rehearsal.run(effect=True)
check("electricity passes on launch night and stays passed",
      verdicts(strong, "power"), ["passed"] * 4)
check("PlayStation passes as soon as the incident is recorded",
      verdicts(strong, "servers"), ["passed"] * 4)
check("Twitch passes on launch night and stays passed",
      verdicts(strong, "twitch"), ["passed"] * 4)
check("the subway waits for the MTA, then passes",
      verdicts(strong, "subway"), [None, "passed", "passed", "passed"])
for pid in ("traffic", "steam"):
    check(f"{pid}: SO FAR until the window closes",
          [strong[m][pid]["provisional"] for m in (NEXT, WEEK)], [True, True])
    check(f"{pid}: then passed", strong[CLOSED][pid]["verdict"], "passed")

print("\n2. A strong launch, and GTA still played for weeks afterwards")
after = rehearsal.run(effect=True, after=True)
check("Twitch's verdict in December is the one given in November",
      after[CLOSED]["twitch"]["verdict"], after[WEEK]["twitch"]["verdict"])
check("and it is a pass", after[CLOSED]["twitch"]["verdict"], "passed")

print("\n3. Nothing happens")
null = rehearsal.run(effect=False)
check("nothing passes, at any moment",
      any(v["verdict"] == "passed" for m in null.values() for v in m.values()), False)
for pid in ("twitch", "servers"):
    check(f"{pid}: not FAILED while 20 November is still running",
          [null[m][pid]["verdict"] for m in (NIGHT, NEXT)], [None, None])
    check(f"{pid}: SO FAR meanwhile",
          [null[m][pid]["provisional"] for m in (NIGHT, NEXT)], [True, True])
check("once every window has closed, all six have failed",
      [null[CLOSED][pid]["verdict"] for pid in sorted(null[CLOSED])], ["failed"] * 6)

print("\n4. Nothing happens, and the collector is down for it")
down = rehearsal.run(effect=False, outage=True)
check("no prediction ever reads FAILED",
      [(m, pid) for m, vs in down.items() for pid, v in vs.items()
       if v["verdict"] == "failed"], [])
check("and every one says why it has no verdict",
      all(v["reason"] for vs in down.values() for v in vs.values()), True)
check("electricity names the grids that did not report",
      "did not report" in down[CLOSED]["power"]["reason"], True)

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
