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

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
