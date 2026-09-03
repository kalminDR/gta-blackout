#!/usr/bin/env python3
"""
Attention Heist - historical backfill.

collect.py records the present. This fetches the past, from the three
sources that publish it and need no credentials at all:

    New York transit ridership   daily,  back to 2020, from the State of NY
    Stack Exchange questions     daily,  back years, from the public API
    Wikipedia edits              daily,  back years, from Wikimedia

These matter because they turn the Work Index from something with one day
of history into something with several years. By November we will not be
comparing launch day against eleven weeks - we will be comparing it against
every November Thursday since 2020.

Everything lands in data/backfill/ as one file per source. Safe to re-run:
each run overwrites its own file and nothing else.

Run:  python backfill.py            (default window: from 2023-01-01)
      python backfill.py 2020-01-01
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

UA = "attention-heist/1.0 (research project; contact: hello@eureka.works)"
OUT = os.path.join("data", "backfill")
TIMEOUT = 40


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def days_between(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


# ------------------------------------------------- New York transit

def fetch_mta(start):
    """Systemwide ridership: subway, bus, commuter rail, tolls.

    Published by the State of New York the following day, going back to
    2020. The strongest 'did people actually travel to work' number we can
    get, because it needs no interpretation at all - it is a count.
    """
    url = ("https://data.ny.gov/resource/sayj-mze2.json"
           f"?$where=date>='{start.isoformat()}T00:00:00'"
           "&$order=date&$limit=50000")
    rows = get_json(url)
    if not rows:
        return {"error": "no rows returned"}

    # Field names on this dataset have changed before, so discover them
    # rather than hard-coding and silently reading nothing.
    numeric_fields = sorted(
        k for k, v in rows[0].items()
        if k != "date" and _is_number(v)
    )

    out = []
    for r in rows:
        rec = {"date": (r.get("date") or "")[:10]}
        for f in numeric_fields:
            rec[f] = _num(r.get(f))
        out.append(rec)

    return {
        "source": "data.ny.gov dataset sayj-mze2",
        "fields_found": numeric_fields,
        "days": len(out),
        "first": out[0]["date"] if out else None,
        "last": out[-1]["date"] if out else None,
        "data": out,
    }


def _is_number(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------- Stack Exchange

def fetch_stackexchange(start, end):
    """How many questions people asked, per day.

    The free API allows 300 calls a day from one address, so older history
    is fetched a week at a time and only the recent months day by day. That
    is the right trade anyway: we need fine detail around the launch, and
    only a seasonal shape further back.
    """
    fine_from = max(start, date(2026, 8, 1))
    calls, daily, weekly = 0, [], []

    def count(a, b):
        nonlocal calls
        url = ("https://api.stackexchange.com/2.3/questions"
               f"?site=stackoverflow&filter=total"
               f"&fromdate={int(datetime.combine(a, datetime.min.time(), timezone.utc).timestamp())}"
               f"&todate={int(datetime.combine(b, datetime.min.time(), timezone.utc).timestamp())}")
        calls += 1
        return get_json(url).get("total")

    # Weekly buckets for the deep history.
    d = start
    while d < fine_from and calls < 140:
        nxt = min(d + timedelta(days=7), fine_from)
        try:
            weekly.append({"week_start": d.isoformat(), "days": (nxt - d).days,
                           "questions": count(d, nxt)})
        except Exception as e:
            weekly.append({"week_start": d.isoformat(), "error": str(e)[:90]})
        d = nxt
        time.sleep(0.4)

    # Daily buckets from August 2026 onwards.
    d = fine_from
    while d <= end and calls < 280:
        try:
            daily.append({"date": d.isoformat(), "questions": count(d, d + timedelta(days=1))})
        except Exception as e:
            daily.append({"date": d.isoformat(), "error": str(e)[:90]})
        d += timedelta(days=1)
        time.sleep(0.4)

    return {
        "source": "api.stackexchange.com, stackoverflow",
        "api_calls_used": calls,
        "complete": d > end,
        "note": None if d > end else
                f"Stopped at {d.isoformat()} to stay inside the free daily "
                f"quota. Run this again tomorrow to continue.",
        "weekly": weekly,
        "daily": daily,
    }


# --------------------------------------------------------- Wikipedia

WIKI_PROJECTS = ["en.wikipedia.org", "de.wikipedia.org", "ja.wikipedia.org",
                 "es.wikipedia.org", "fr.wikipedia.org", "ru.wikipedia.org"]


def fetch_wikipedia(start, end):
    """Edits per day, per language.

    Unpaid, voluntary, cognitive work - which makes it a useful counterpart
    to paid work: nobody edits Wikipedia because a manager asked them to.
    The language split also gives us a rough geography.
    """
    out = {}
    for project in WIKI_PROJECTS:
        url = ("https://wikimedia.org/api/rest_v1/metrics/edits/aggregate/"
               f"{project}/all-editor-types/all-page-types/daily/"
               f"{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}")
        try:
            res = get_json(url)
            results = (res.get("items") or [{}])[0].get("results") or []
            out[project] = [
                {"date": (r.get("timestamp") or "")[:8], "edits": r.get("edits")}
                for r in results
            ]
        except Exception as e:
            out[project] = {"error": str(e)[:120]}
        time.sleep(0.6)
    return {"source": "wikimedia.org analytics API", "projects": out}


# -------------------------------------------------------------- main

def main():
    start = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2023, 1, 1)
    end = datetime.now(timezone.utc).date() - timedelta(days=1)
    os.makedirs(OUT, exist_ok=True)

    jobs = {
        "mta_ridership": lambda: fetch_mta(start),
        "stackexchange": lambda: fetch_stackexchange(start, end),
        "wikipedia": lambda: fetch_wikipedia(start, end),
    }

    print(f"Backfilling {start} to {end}\n", file=sys.stderr)
    failures = 0
    for name, fn in jobs.items():
        began = time.time()
        try:
            payload = fn()
            status = "ok"
        except Exception as e:
            payload, status = {"error": str(e)[:300]}, "FAILED"
            failures += 1
        payload["fetched_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        size = os.path.getsize(os.path.join(OUT, name + ".json")) / 1024
        print(f"  {name:16s} {status:6s} {time.time()-began:5.1f}s  {size:7.0f} KB",
              file=sys.stderr)

    print(f"\nWritten to {OUT}/", file=sys.stderr)
    return 1 if failures == len(jobs) else 0


if __name__ == "__main__":
    sys.exit(main())
