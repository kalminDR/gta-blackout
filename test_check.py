#!/usr/bin/env python3
"""Tests for the health check, which is the only thing that tells us a source
has died.

It was changed on 7 September 2026 to judge over several snapshots rather than
only the newest, because ENTSO-E returns HTTP 503 for a few minutes at a time
and every one of those was failing the workflow. The obvious risk in that
change is muting the alarm, so these tests push from both sides: a source that
blinked must not fail the run, and a source that is genuinely dead must still
fail it.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, "/home/claude/repo")

ROOT = pathlib.Path(__file__).resolve().parent
passed = failed = 0


def check(name, got, want=True):
    global passed, failed
    if got == want:
        passed += 1
        print(f"  PASS  {name}   [{got}]")
    else:
        failed += 1
        print(f"  FAIL  {name}   got {got!r}, wanted {want!r}")


def snapshot(entsoe_ok, twitch_ok=True):
    """One snapshot, with entsoe and twitch either working or erroring."""
    return {
        "collected_at_utc": "2026-09-07T12:00:00+00:00",
        "sources": {
            "entsoe": ({"DE": {"load_mw": 40000.0, "t": "2026-09-07T11:00:00+00:00"}}
                       if entsoe_ok else {"DE": {"error": "HTTP 503: ..."}}),
            "twitch": ({"top100_total": 700000} if twitch_ok
                       else {"error": "HTTP 500"}),
        },
    }


def run_check(snapshots):
    """Run collect.py --check against a fabricated data/ directory."""
    tmp = tempfile.mkdtemp()
    try:
        day = pathlib.Path(tmp) / "data" / "2026-09-07"
        day.mkdir(parents=True)
        for i, snap in enumerate(snapshots):
            (day / f"{i:02d}00.json").write_text(json.dumps(snap), encoding="utf-8")
        for f in ("collect.py", "backfill.py"):
            shutil.copy(ROOT / f, tmp)
        r = subprocess.run([sys.executable, "collect.py", "--check"],
                           cwd=tmp, capture_output=True, text=True,
                           env=dict(os.environ, ENTSOE_TOKEN="", TWITCH_CLIENT_ID=""))
        return r.returncode, r.stderr + r.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


print("1. A source that blinked does not fail the run")
# Working for five readings, failing on the newest: upstream's problem.
code, out = run_check([snapshot(True)] * 5 + [snapshot(False)])
check("exit code is zero", code, 0)
check("and it says so rather than staying silent", "blinked" in out, True)
check("naming the source", "entsoe" in out, True)

print("\n2. A source that is genuinely dead still fails the run")
# Nothing usable in any recent snapshot.
code, out = run_check([snapshot(False)] * 6)
check("exit code is one", code, 1)
check("and it is called DEAD, not blinked", "DEAD" in out, True)
check("with no 'blinked' excuse", "blinked" in out, False)

print("\n3. The boundary: one success inside the window is enough to be alive")
code, _ = run_check([snapshot(True)] + [snapshot(False)] * 5)
check("worked six readings ago, dead since -- still only a blink", code, 0)
# One more failure and that success falls out of the window.
code, out = run_check([snapshot(True)] + [snapshot(False)] * 6)
check("one reading later it has left the window, and the alarm fires", code, 1)
check("and it is reported as dead", "DEAD" in out, True)

print("\n4. One dead source fails the run even while others are fine")
code, out = run_check([snapshot(True, twitch_ok=False)] * 6)
check("twitch dead, entsoe fine: still fails", code, 1)
check("and only twitch is named", "twitch" in out and "DEAD" in out, True)

print("\n5. Two blinking sources are still not a failure")
code, _ = run_check([snapshot(True)] * 5 + [snapshot(False, twitch_ok=False)])
check("both blinked, neither is dead", code, 0)

# ---------------------------------------------------------------------------
# Cadence. From 13 September 2026 GitHub's scheduler started the collector
# every four to six hours instead of hourly, for two weeks, and every check
# above stayed green because the runs that did happen worked. A missing run
# leaves no failure behind, so only the gaps between readings can show it.
# ---------------------------------------------------------------------------
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(ROOT))
import collect  # noqa: E402

T0 = datetime(2026, 9, 14, 0, 5, tzinfo=timezone.utc)


def hours(*hs):
    return [T0 + timedelta(hours=h) for h in hs]


print("\n6. Hourly readings are on schedule")
check("24 hourly readings: no complaint", collect.cadence_problem(hours(*range(24))), None)
check("one missed hour is not a fault",
      collect.cadence_problem(hours(*[h for h in range(24) if h != 20])), None)

print("\n7. The 13 September pattern raises the alarm")
late = collect.cadence_problem(hours(0, 5, 10, 14, 19, 24))
check("a reading every four to six hours is reported", late is not None, True)
check("and it blames the scheduler, not a source", "scheduler" in (late or ""), True)
check("three readings in six hours is still too few",
      collect.cadence_problem(hours(0, 1, 2, 3, 4, 5, 6, 8, 10, 12)) is not None, True)

print("\n8. Too little history is not a fault")
check("a fresh start with two readings", collect.cadence_problem(hours(0, 1)), None)
check("no readings at all", collect.cadence_problem([]), None)

print("\n9. The whole check fails on a sparse cadence, and says why")
sparse = []
for h in (0, 5, 10, 14, 19, 24):
    s = snapshot(True)
    s["collected_at_utc"] = (T0 + timedelta(hours=h)).isoformat()
    sparse.append(s)
code, out = run_check(sparse)
check("exit code is one", code, 1)
check("with a CADENCE line", "CADENCE" in out, True)
check("and no source is called dead", "DEAD" in out, False)
hourly = []
for h in range(8):
    s = snapshot(True)
    s["collected_at_utc"] = (T0 + timedelta(hours=h)).isoformat()
    hourly.append(s)
code, out = run_check(hourly)
check("the same sources hourly: exit code zero", code, 0)


def gate_at(newest, now):
    """Run collect.gate() against a data/ directory holding one snapshot."""
    tmp = tempfile.mkdtemp()
    here = os.getcwd()
    try:
        day = pathlib.Path(tmp) / "data" / newest.strftime("%Y-%m-%d")
        day.mkdir(parents=True)
        s = snapshot(True)
        s["collected_at_utc"] = newest.isoformat()
        (day / newest.strftime("%H%M.json")).write_text(json.dumps(s), encoding="utf-8")
        os.chdir(tmp)
        return collect.gate(now)[0]
    finally:
        os.chdir(here)
        shutil.rmtree(tmp, ignore_errors=True)


print("\n10. The gate: the fallback schedule stands down when the hour is done")
# The heartbeat collects at :05; GitHub's fallback fires at :37.
check("reading 32 minutes old: skip", gate_at(T0, T0 + timedelta(minutes=32)), False)
check("reading 90 minutes old: run", gate_at(T0, T0 + timedelta(minutes=90)), True)
check("the boundary, 45 minutes: run", gate_at(T0, T0 + timedelta(minutes=45)), True)
empty = tempfile.mkdtemp()
here = os.getcwd()
try:
    os.chdir(empty)
    check("no data at all: run", collect.gate(T0)[0], True)
finally:
    os.chdir(here)
    shutil.rmtree(empty, ignore_errors=True)

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
