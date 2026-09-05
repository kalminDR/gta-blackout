#!/usr/bin/env python3
"""Derive the project's current state from the repository itself.

Why this exists
---------------
PROJECT.md was written by hand and drifted away from reality. It claimed the
eBay keys were not set while the collector was already failing authentication
with them, and it listed ENTSO-E as "done" when no line of ENTSO-E code had
ever been written. A document that has to be remembered will always lose to a
system that keeps running.

So this file does not describe the project. It interrogates it: it reads the
collector's own source, the snapshots on disk and the published JSON, and
writes down what it finds. Run it, and STATE.md is true as of that moment.

Only one block below is maintained by hand -- PLANNED -- because intent cannot
be measured. Everything else is derived, and the script's job is to report
where intent and reality have come apart.

    python3 state.py            # writes STATE.md
    python3 state.py --print    # writes it and prints it
"""

import ast
import json
import pathlib
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# THE ONLY HAND-MAINTAINED BLOCK.
# What we intend to collect. The script checks each against the real code and
# reports anything with no implementation. Add a line when a source is decided
# on, not when it is finished -- the gap is the point.
# ---------------------------------------------------------------------------
PLANNED = {
    "twitch":          "Live attention: concurrent viewers, by language",
    "steam":           "Displacement: are other games emptying out",
    "steam_charts":    "Displacement: broader player-count basket",
    "youtube":         "Attention: view velocity on Rockstar's videos",
    "traffic":         "Did people commute: six cities, three arterial points each",
    "console_status":  "Did the servers buckle: PSN and Xbox status",
    "console_prices":  "Did consoles run out: eBay resale, US/GB/DE",
    "retail_stock":    "Did consoles run out: retail availability",
    "polymarket":      "Crowd expectation of the launch",
    "hackernews":      "Background chatter volume",
    "selfreport":      "What people say they will do, from our own form",
    "entsoe":          "Did a country stay in: hourly electricity demand, EU",
    "mta":             "Did people commute: New York transit (backfill, daily)",
    "chicago":         "Did people commute: a second, independent transit system",
    "wikipedia":       "Attention: edits and pageviews, six languages",
}

# Sources deliberately abandoned, so the script stops flagging them as gaps.
REJECTED = {
    "reddit":         "API closed, November 2025",
    "github":         "Bot activity dominates; issue comments fell ~98%",
    "stackoverflow":  "Volume collapsed to ~1% of 2023 by August 2026",
    "yahoo_finance":  "Runner IPs blocked",
    "bestbuy":        "Requires a US phone number",
    "gdelt":          "Runner IPs rate-limited; manual browser fetch instead",
}


def rel(p):
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------
# 1. What the collector actually implements
# ---------------------------------------------------------------------------
def read_collector():
    """Parse collect.py rather than trusting any list of what it does."""
    path = ROOT / "collect.py"
    if not path.exists():
        return {"error": "collect.py not found"}
    tree = ast.parse(path.read_text(encoding="utf-8"))

    registered, secrets_by_func = [], defaultdict(set)

    for node in ast.walk(tree):
        # SOURCES = {"twitch": collect_twitch, ...}
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "SOURCES":
                    if isinstance(node.value, ast.Dict):
                        for k in node.value.keys:
                            if isinstance(k, ast.Constant):
                                registered.append(k.value)

    # env("SOMETHING") calls, attributed to the enclosing function
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "env"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)):
                secrets_by_func[fn.name].add(node.args[0].value)

    return {"registered": registered, "secrets_by_func": dict(secrets_by_func)}


def find_source_code(name):
    """Is there any implementation of this source anywhere in the repo?"""
    hits = []
    for f in sorted(ROOT.glob("*.py")):
        if f.name == "state.py":
            continue
        text = f.read_text(encoding="utf-8", errors="replace").lower()
        if name.lower() in text:
            hits.append(f.name)
    return hits


# ---------------------------------------------------------------------------
# 2. What the newest snapshot says about each source
# ---------------------------------------------------------------------------
FAIL_KEYS = ("error", "auth_error", "http_error", "exception")


def newest_snapshot():
    days = sorted([d for d in (ROOT / "data").glob("2*") if d.is_dir()])
    if not days:
        return None, None
    for day in reversed(days):
        files = sorted(day.glob("*.json"))
        if files:
            f = files[-1]
            try:
                return f, json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
    return None, None


def classify(block):
    """Working, failing or waiting -- and why, in the source's own words."""
    if not isinstance(block, dict):
        return "OK", ""
    for k in FAIL_KEYS:
        if k in block:
            return "FAILING", f"{k}: {str(block[k])[:150]}"
    if "skipped" in block:
        return "WAITING", f"skipped: {str(block['skipped'])[:150]}"
    payload = {k: v for k, v in block.items() if v is not None}
    if not payload:
        return "EMPTY", "returned nothing"
    return "OK", f"{len(payload)} fields"


# ---------------------------------------------------------------------------
# 3. Coverage and gaps
# ---------------------------------------------------------------------------
def coverage():
    stamps = []
    for day in sorted((ROOT / "data").glob("2*")):
        if not day.is_dir():
            continue
        for f in sorted(day.glob("*.json")):
            try:
                t = json.loads(f.read_text(encoding="utf-8")).get("collected_at_utc")
                if t:
                    stamps.append(datetime.fromisoformat(t.replace("Z", "+00:00")))
            except Exception:
                pass
    stamps.sort()
    if not stamps:
        return {"count": 0}
    gaps = [(a, b, (b - a).total_seconds() / 3600)
            for a, b in zip(stamps, stamps[1:]) if (b - a) > timedelta(hours=2)]
    span = (stamps[-1] - stamps[0]).total_seconds() / 3600
    age = (datetime.now(timezone.utc) - stamps[-1]).total_seconds() / 3600
    return {"count": len(stamps), "first": stamps[0], "last": stamps[-1],
            "span_hours": span, "age_hours": age, "gaps": gaps,
            "expected": int(span) + 1}


# ---------------------------------------------------------------------------
# 4. Metric health -- the silent failures
# ---------------------------------------------------------------------------
def metric_health():
    path = ROOT / "public" / "series.json"
    if not path.exists():
        return []
    points = json.loads(path.read_text(encoding="utf-8")).get("points", [])
    if not points:
        return []
    keys = sorted({k for p in points for k in p if k != "t"})
    n_points = len(points)
    out = []
    for k in keys:
        vals = [p.get(k) for p in points]
        # Structural keys hold objects, not readings. Judging them as numbers
        # produced a page of false alarms in the first version of this script.
        if any(isinstance(v, (dict, list, str)) for v in vals):
            continue
        # Descriptors that are meant to be constant: the road class of a fixed
        # measurement point does not change, and flagging it as "frozen" buries
        # the metrics that genuinely stopped moving.
        if k.endswith(("_road_class", "_points_ok")):
            continue
        nums = [v for v in vals if isinstance(v, (int, float))]
        present, nulls = len(nums), len(vals) - len([v for v in vals if isinstance(v, (int, float))])
        sev, flags = 0, []

        if present == 0:
            sev, flags = 3, ["never returned a number"]
        else:
            if len(set(nums)) == 1 and present >= 20:
                sev = max(sev, 3)
                flags.append(f"frozen at {nums[0]:g} for all {present} readings")
            zeros = sum(1 for v in nums if v == 0)
            if present >= 20 and zeros / present > 0.4:
                sev = max(sev, 3)
                flags.append(f"zero in {zeros} of {present} readings")
            # A late start is not a fault; intermittent failure is.
            if nulls and present:
                first = next(i for i, v in enumerate(vals) if isinstance(v, (int, float)))
                after = sum(1 for v in vals[first:] if not isinstance(v, (int, float)))
                if after / max(1, n_points - first) > 0.25:
                    sev = max(sev, 2)
                    flags.append(f"missing {after} of {n_points - first} since it started")
        if flags:
            out.append((k, present, n_points, sev, flags))

    # Collapse whole families that are dark for one shared reason.
    dead = [r for r in out if r[3] == 3 and r[4] == ["never returned a number"]]
    groups = defaultdict(list)
    for r in dead:
        groups[r[0].split("_")[0]].append(r[0])
    collapsed = [r for r in out if r not in dead]
    for prefix, names in sorted(groups.items()):
        if len(names) >= 3:
            collapsed.append((f"`{prefix}_*` ({len(names)} metrics)", 0, n_points, 3,
                              ["never returned a number — source not authenticating"]))
        else:
            collapsed += [r for r in dead if r[0] in names]
    return sorted(collapsed, key=lambda r: (-r[3], r[0]))


# ---------------------------------------------------------------------------
# 5. Are the indices computable yet# 5. Are the indices computable yet
# ---------------------------------------------------------------------------
def index_readiness():
    path = ROOT / "public" / "latest.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    indices = (data.get("latest") or {}).get("indices") or {}

    min_hw = 6
    try:
        src = (ROOT / "indices.py").read_text(encoding="utf-8")
        for line in src.splitlines():
            if line.startswith("MIN_SAMPLES_HOUR_OF_WEEK"):
                min_hw = int(line.split("=")[1].strip())
    except Exception:
        pass

    series = ROOT / "public" / "series.json"
    buckets = Counter()
    if series.exists():
        for p in json.loads(series.read_text(encoding="utf-8")).get("points", []):
            t = p.get("t")
            if t:
                d = datetime.fromisoformat(t.replace("Z", "+00:00"))
                buckets[(d.weekday(), d.hour)] += 1
    ready = sum(1 for v in buckets.values() if v >= min_hw)
    return {"indices": indices, "min_hour_of_week": min_hw,
            "buckets_seen": len(buckets), "buckets_ready": ready,
            "buckets_total": 168}


# ---------------------------------------------------------------------------
# 6. Historical backfill on disk
# ---------------------------------------------------------------------------
def backfill():
    out = []
    d = ROOT / "data" / "backfill"
    if not d.exists():
        return out
    for f in sorted(d.glob("*.json")):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            out.append((f.name, "unreadable", "", ""))
            continue
        rows = j.get("rows") or (len(j.get("data", [])) if isinstance(j.get("data"), list) else "")
        out.append((f.name, rows, j.get("first", ""), j.get("last", "")))
    return out


# ---------------------------------------------------------------------------
# 7. Front end: are the placeholders actually wired
# ---------------------------------------------------------------------------
def frontend():
    path = ROOT / "index.html"
    if not path.exists():
        return {"error": "index.html not found"}
    s = path.read_text(encoding="utf-8")
    import re
    in_html = set(re.findall(r'id="([A-Za-z0-9_\-]+)"', s))
    wanted = set(re.findall(r'getElementById\("([A-Za-z0-9_\-]+)"\)', s))
    wanted |= set(re.findall(r'\$\("([A-Za-z0-9_\-]+)"\)', s))
    return {"ids": len(in_html), "referenced": len(wanted),
            "orphan_js": sorted(wanted - in_html),
            "reads_new_shape": "indices||{}" in s.replace(" ", "")
                               or "L.indices" in s.replace(" ", "")}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def main():
    L = []
    w = L.append
    now = datetime.now(timezone.utc)

    w("# STATE — Grand Theft Attention")
    w("")
    w(f"Generated **{now:%Y-%m-%d %H:%M UTC}** by `state.py`, from the repository "
      "itself. Nothing here is written from memory. If it disagrees with any "
      "other document, this file is right and the other document is stale.")
    w("")

    coll = read_collector()
    registered = coll.get("registered", [])
    snap_path, snap = newest_snapshot()
    live = (snap or {}).get("sources", {})

    # --- headline -----------------------------------------------------------
    states = {name: classify(live[name])[0] for name in live}
    ok = [n for n, s in states.items() if s == "OK"]
    bad = [n for n, s in states.items() if s in ("FAILING", "EMPTY")]
    wait = [n for n, s in states.items() if s == "WAITING"]
    missing = [n for n in PLANNED if n not in registered and not any(
        n in h for h in [""]) and not find_source_code(n)]

    cov = coverage()
    w("## Where we are")
    w("")
    w(f"- **{len(ok)} sources working**, {len(bad)} failing, {len(wait)} waiting on a key")
    w(f"- **{len(missing)} planned sources have no code at all**"
      + (f": {', '.join(missing)}" if missing else ""))
    if cov.get("count"):
        w(f"- **{cov['count']} snapshots** over {cov['span_hours']:.1f} hours "
          f"({cov['span_hours']/24:.1f} days); last one {cov['age_hours']:.1f} h ago")
    w("")

    # --- sources ------------------------------------------------------------
    w("## Sources")
    w("")
    w(f"Newest snapshot: `{rel(snap_path) if snap_path else 'none'}`")
    w("")
    w("| Source | State | What it says | Secrets |")
    w("|---|---|---|---|")
    secs = coll.get("secrets_by_func", {})
    for name in registered:
        state, why = classify(live.get(name, {})) if name in live else ("ABSENT", "not in snapshot")
        mark = {"OK": "🟢", "FAILING": "🔴", "WAITING": "🟡",
                "EMPTY": "🟠", "ABSENT": "⚪"}.get(state, "⚪")
        used = sorted(secs.get(f"collect_{name}", []))
        w(f"| `{name}` | {mark} {state} | {why} | {', '.join(f'`{s}`' for s in used) or '—'} |")
    w("")

    # --- gaps between intent and code --------------------------------------
    w("## Planned but not built")
    w("")
    rows = 0
    for name, why in PLANNED.items():
        if name in registered:
            continue
        files = find_source_code(name)
        w(f"- **`{name}`** — {why} — "
          + (f"referenced in {', '.join(files)} but not registered as a source"
             if files else "**no code anywhere in the repo**"))
        rows += 1
    if not rows:
        w("Nothing. Every planned source is registered.")
    w("")
    w("Deliberately abandoned: "
      + "; ".join(f"**{k}** ({v})" for k, v in REJECTED.items()))
    w("")

    # --- collection health --------------------------------------------------
    w("## Collection")
    w("")
    if cov.get("count"):
        w(f"- First: `{cov['first']:%Y-%m-%d %H:%M UTC}` · Last: `{cov['last']:%Y-%m-%d %H:%M UTC}`")
        w(f"- {cov['count']} of ~{cov['expected']} expected hourly readings")
        if cov["gaps"]:
            w(f"- **{len(cov['gaps'])} gaps over two hours:**")
            for a, b, h in cov["gaps"][:6]:
                w(f"  - {h:.1f} h, {a:%Y-%m-%d %H:%M} → {b:%H:%M UTC}")
        else:
            w("- No gaps over two hours")
    else:
        w("No snapshots on disk.")
    w("")

    # --- metrics that lie quietly ------------------------------------------
    w("## Metrics needing attention")
    w("")
    mh = metric_health()
    if mh:
        w("A metric that never errors but never moves is the dangerous kind: it "
          "reads as data and is not.")
        w("")
        w("| | Metric | Readings | Problem |")
        w("|---|---|---|---|")
        for k, present, total, sev, flags in mh:
            mark = "🔴" if sev == 3 else "🟠"
            name = k if k.startswith("`") else f"`{k}`"
            w(f"| {mark} | {name} | {present}/{total} | {'; '.join(flags)} |")
    else:
        w("Every metric varies and returns numbers.")
    w("")

    # --- indices ------------------------------------------------------------
    w("## Indices")
    w("")
    ir = index_readiness()
    if ir:
        vals = ir["indices"]
        w("| Panel | Value |")
        w("|---|---|")
        for k, v in vals.items():
            w(f"| {k} | {'**null**' if v is None else f'{v:.1f}'} |")
        w("")
        w(f"Baseline needs {ir['min_hour_of_week']} samples per hour-of-week bucket. "
          f"**{ir['buckets_ready']} of {ir['buckets_total']} buckets qualify** "
          f"({ir['buckets_seen']} seen at all). Nulls here are correct behaviour, "
          "not a bug: the page refuses to print a number it cannot support.")
    w("")

    # --- history ------------------------------------------------------------
    w("## Historical backfill")
    w("")
    bf = backfill()
    if bf:
        w("| File | Rows | From | To |")
        w("|---|---|---|---|")
        for n, r, a, b in bf:
            w(f"| `{n}` | {r} | {a} | {b} |")
    else:
        w("No backfill on disk.")
    w("")

    # --- front end ----------------------------------------------------------
    w("## Front end")
    w("")
    fe = frontend()
    if "error" in fe:
        w(fe["error"])
    else:
        w(f"- {fe['ids']} element ids in the HTML, {fe['referenced']} referenced by script")
        w("- Reads the current `indices` shape: "
          + ("yes" if fe["reads_new_shape"] else "**no — still on the old shape**"))
        if fe["orphan_js"]:
            w(f"- **Script writes to ids that do not exist:** "
              + ", ".join(f"`{i}`" for i in fe["orphan_js"][:12]))
        else:
            w("- No orphaned ids")
    w("")

    w("---")
    w("")
    w("Regenerate with `python3 state.py`. Edit `PLANNED` when a source is "
      "decided on, not when it is finished — the gap between intent and code is "
      "the most useful thing this file reports.")

    text = "\n".join(L) + "\n"
    (ROOT / "STATE.md").write_text(text, encoding="utf-8")
    if "--print" in sys.argv:
        print(text)
    else:
        print(f"wrote {rel(ROOT / 'STATE.md')} ({len(text)} chars)")


if __name__ == "__main__":
    main()
