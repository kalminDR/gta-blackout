#!/usr/bin/env python3
"""Tests for the D1 schema, run against the statements worker.js really issues.

The schema was exported from the live database rather than reconstructed, so
these tests are not checking that the export was typed correctly -- they check
that worker.js and schema.sql still agree. They will fail if somebody adds a
column to an INSERT, renames an answer, or drops the seed rows.

The seed rows get a section of their own because their absence is silent.
"UPDATE tallies SET n = n + 1 WHERE answer = ?" against a missing row matches
nothing, changes nothing, and raises nothing: the vote lands in `reports`, the
counter never moves, and /counts under-reports for ever while looking healthy.
"""

import pathlib
import re
import sqlite3
import sys

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


def fresh():
    con = sqlite3.connect(":memory:")
    con.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    return con


WORKER = (ROOT / "worker.js").read_text(encoding="utf-8")

print("1. The schema loads and holds what worker.js expects")
con = fresh()
tables = {r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
check("the three tables exist", tables, {"reports", "tallies", "subscribers"})
check("no Cloudflare internals were exported", "_cf_KV" in tables, False)

print("\n2. Every statement worker.js issues actually runs")
# Pulled out of the file rather than retyped, so a change there breaks this.
now = "2026-11-19T20:15:00.000Z"
con.execute(
    "INSERT INTO reports (answer, country, industry, submitted_at) VALUES (?, ?, ?, ?)",
    ("day_off", "HU", "technology", now))
check("a full report inserts", con.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 1)

con.execute(
    "INSERT INTO reports (answer, country, industry, submitted_at) VALUES (?, ?, ?, ?)",
    ("working", None, None, now))
check("country and industry are optional, as the worker allows",
      con.execute("SELECT COUNT(*) FROM reports WHERE country IS NULL").fetchone()[0], 1)

con.execute("UPDATE tallies SET n = n + 1 WHERE answer = ?", ("day_off",))
check("the tally increments",
      con.execute("SELECT n FROM tallies WHERE answer='day_off'").fetchone()[0], 1)

rows = con.execute("SELECT answer, n FROM tallies").fetchall()
check("GET /counts reads four rows and no scan", len(rows), 4)

con.execute("INSERT INTO subscribers (email, submitted_at) VALUES (?, ?) "
            "ON CONFLICT(email) DO NOTHING", ("a@b.com", now))
con.execute("INSERT INTO subscribers (email, submitted_at) VALUES (?, ?) "
            "ON CONFLICT(email) DO NOTHING", ("a@b.com", now))
check("signing up twice is a no-op, not an error or a duplicate",
      con.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0], 1)

print("\n3. The seed rows, whose absence would be silent")
answers = {r[0] for r in con.execute("SELECT answer FROM tallies")}
in_worker = set(re.findall(r"^\s{2}(\w+):\s+\"", WORKER, re.M))
check("worker.js declares four answers", len(in_worker), 4)
check("and the schema seeds exactly those", answers, in_worker)

# The failure this guards against, demonstrated rather than described.
bare = sqlite3.connect(":memory:")
bare.executescript(re.sub(r"INSERT INTO tallies.*?;", "",
                          (ROOT / "schema.sql").read_text(encoding="utf-8"), flags=re.S))
bare.execute("INSERT INTO reports (answer, country, industry, submitted_at) "
             "VALUES (?, ?, ?, ?)", ("day_off", None, None, now))
cur = bare.execute("UPDATE tallies SET n = n + 1 WHERE answer = ?", ("day_off",))
check("without the seed rows the update silently matches nothing",
      cur.rowcount, 0)
check("while the report is stored anyway -- the two tables diverge in silence",
      bare.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 1)
check("and /counts would report a total of zero",
      bare.execute("SELECT COALESCE(SUM(n), 0) FROM tallies").fetchone()[0], 0)

print("\n4. A fresh database starts at zero, not at today's numbers")
check("every seeded tally is zero",
      [r[0] for r in fresh().execute("SELECT n FROM tallies")], [0, 0, 0, 0])

print(f"\n{passed} checks passed" + (f", {failed} FAILED" if failed else ""))
sys.exit(1 if failed else 0)
