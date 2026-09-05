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

    The dataset returns one row per date PER MODE, so the text column that
    names the mode matters as much as the number. An earlier version kept
    only numeric fields and threw the labels away, leaving seven anonymous
    figures per day.
    """
    url = ("https://data.ny.gov/resource/sayj-mze2.json"
           f"?$where=date>='{start.isoformat()}T00:00:00'"
           "&$order=date&$limit=100000")
    rows = get_json(url)
    if not rows:
        return {"error": "no rows returned"}

    all_fields = sorted(rows[0].keys())

    out = []
    for r in rows:
        rec = {}
        for k, v in r.items():
            if k == "date":
                rec["date"] = (v or "")[:10]
            elif _is_number(v):
                rec[k] = _num(v)
            else:
                rec[k] = v          # the mode label lives here
        out.append(rec)

    modes = sorted({r.get(k) for r in out for k in r
                    if isinstance(r.get(k), str) and k != "date"})

    return {
        "source": "data.ny.gov dataset sayj-mze2",
        "all_fields": all_fields,
        "modes_found": modes,
        "rows": len(out),
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

    KEPT FOR THE RECORD, NOT FOR THE INDEX. The backfill showed Stack
    Overflow falling from ~2,990 questions a day in January 2023 to a
    median of 43 in August 2026 - about 1.4% of what it was. At that
    volume the random variation alone is around plus or minus six, so a
    one-day effect could never be separated from noise. The decline itself
    is worth publishing; the series is not usable as a work signal.

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
                {"date": (r.get("timestamp") or "")[:10], "edits": r.get("edits")}
                for r in results
            ]
        except Exception as e:
            out[project] = {"error": str(e)[:120]}
        time.sleep(0.6)
    return {"source": "wikimedia.org analytics API", "projects": out}


# ------------------------------------------------- Wikipedia pageviews

def fetch_wikipedia_pageviews(start, end):
    """Daily views of the Grand Theft Auto VI article, per language.

    Curiosity, measured directly and going back years, which makes it one
    of the few hype signals with a real baseline rather than eleven weeks
    of it. The language split doubles as a rough geography.

    Article titles differ by language, so rather than guessing them we ask
    the English Wikipedia for its own language links and use whatever it
    returns.
    """
    titles = {"en.wikipedia": "Grand Theft Auto VI"}
    try:
        res = get_json(
            "https://en.wikipedia.org/w/api.php?action=query&format=json"
            "&prop=langlinks&lllimit=500&titles="
            + urllib.parse.quote("Grand Theft Auto VI"))
        pages = (res.get("query") or {}).get("pages") or {}
        for page in pages.values():
            for link in page.get("langlinks") or []:
                code, title = link.get("lang"), link.get("*")
                if code and title:
                    titles[f"{code}.wikipedia"] = title
    except Exception as e:
        return {"error": f"could not resolve article titles: {str(e)[:120]}"}

    # Six languages is enough for a geographic read without 300 calls.
    wanted = ["en.wikipedia", "de.wikipedia", "ja.wikipedia",
              "es.wikipedia", "fr.wikipedia", "ru.wikipedia", "pt.wikipedia"]

    out, resolved = {}, {}
    for project in wanted:
        title = titles.get(project)
        if not title:
            out[project] = {"error": "no article in this language"}
            continue
        resolved[project] = title
        url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
               f"{project}/all-access/user/"
               + urllib.parse.quote(title.replace(" ", "_"), safe="")
               + f"/daily/{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}")
        try:
            res = get_json(url)
            out[project] = [
                {"date": (i.get("timestamp") or "")[:8], "views": i.get("views")}
                for i in res.get("items") or []
            ]
        except Exception as e:
            out[project] = {"error": str(e)[:120]}
        time.sleep(0.6)

    return {
        "source": "wikimedia.org pageviews API, per article",
        "article_titles": resolved,
        "languages_available": len(titles),
        "projects": out,
    }


# ------------------------------------------------------- press geography

GDELT_QUERY = ('("grand theft auto vi" OR "grand theft auto 6" '
               'OR "gta vi" OR "gta 6")')


def fetch_gdelt_geography():
    """Which countries' press is covering this, over the past three months.

    This lives here rather than in the hourly collector because GDELT
    enforces one request every five seconds per address and its timelines
    are retroactive anyway - there is nothing to lose by fetching geography
    occasionally instead of every hour.
    """
    out = {}
    for mode, key, span in (("timelinesourcecountry", "by_country", "3m"),
                            ("timelinelang", "by_language", "3m")):
        url = ("https://api.gdeltproject.org/api/v2/doc/doc?query="
               + urllib.parse.quote(GDELT_QUERY)
               + f"&mode={mode}&timespan={span}&format=json")
        for attempt in range(3):
            try:
                res = get_json(url)
                out[key] = {
                    (s.get("series") or "?"): [
                        {"t": p.get("date"), "value": p.get("value")}
                        for p in (s.get("data") or [])
                    ]
                    for s in (res.get("timeline") or [])
                }
                break
            except Exception as e:
                out[key] = {"error": str(e)[:150]}
                if "429" not in str(e):
                    break
                time.sleep(8 * (attempt + 1))
        time.sleep(6)
    return {"source": "api.gdeltproject.org DOC 2.0", "query": GDELT_QUERY, **out}


# -------------------------------------------------------------- main

# Electricity demand, going back far enough to have something to compare to.
#
# The hourly collector only knows the present. Without years of the same weeks
# behind it, a reading on 19 November is a number with nothing beside it. What
# makes the claim testable is that the same Thursday in the same season has
# been recorded four times already.
#
# Only the autumn window is fetched, not whole years. A launch on 19 November
# is compared against the Thursdays around it, not against July, and pulling
# four full years for nine countries would produce a file too large to keep in
# a repository for no analytical gain.
ENTSOE_WINDOWS = [
    (date(2022, 10, 1), date(2022, 12, 15)),
    (date(2023, 10, 1), date(2023, 12, 15)),
    (date(2024, 10, 1), date(2024, 12, 15)),
    (date(2025, 10, 1), date(2025, 12, 15)),
]

# Days per request. ENTSO-E accepts a year for load data, but shorter chunks
# fail smaller: one bad month leaves a hole instead of losing the country.
ENTSOE_CHUNK_DAYS = 30


def _hourly_means(points):
    """Collapse whatever resolution a country reports down to hourly means.

    Some operators publish every fifteen minutes and some every hour. Storing
    both raw would mean every later comparison had to re-learn which is which,
    and would quadruple the file for four times no information. The hour is
    the unit every comparison in this project uses, so the conversion happens
    once, here.
    """
    buckets = {}
    for t, mw in points:
        hour = t.replace(minute=0, second=0, microsecond=0)
        buckets.setdefault(hour, []).append(mw)
    return {h: round(sum(v) / len(v), 1) for h, v in buckets.items()}


def fetch_entsoe(token):
    """Hourly load per country across the autumn windows, several years deep."""
    from collect import ENTSOE_ZONES, _entsoe_points, get_text

    series, notes, calls = {}, {}, 0
    today = datetime.now(timezone.utc).date()

    # The current year runs from before the live collector started up to
    # yesterday, so the two meet without a gap.
    windows = list(ENTSOE_WINDOWS) + [(date(today.year, 8, 1),
                                       today - timedelta(days=1))]

    for code, eic in ENTSOE_ZONES.items():
        hours, problems = {}, []
        for win_start, win_end in windows:
            if win_start >= win_end:
                continue
            cursor = win_start
            while cursor < win_end:
                stop = min(cursor + timedelta(days=ENTSOE_CHUNK_DAYS), win_end)
                url = ("https://web-api.tp.entsoe.eu/api"
                       "?documentType=A65&processType=A16"
                       "&outBiddingZone_Domain=" + urllib.parse.quote(eic) +
                       "&periodStart=" + cursor.strftime("%Y%m%d") + "0000" +
                       "&periodEnd=" + stop.strftime("%Y%m%d") + "0000" +
                       "&securityToken=" + urllib.parse.quote(token))
                try:
                    pts, reason = _entsoe_points(get_text(url))
                    calls += 1
                    if reason:
                        problems.append(f"{cursor}..{stop}: {reason[:80]}")
                    else:
                        hours.update(_hourly_means(pts))
                except Exception as e:
                    problems.append(f"{cursor}..{stop}: "
                                    + str(e)[:80].replace(token, "<token>"))
                # Well inside the published rate limit, and gentler on a
                # service that is publishing this for free.
                time.sleep(0.4)
                cursor = stop

        if hours:
            ordered = sorted(hours)
            series[code] = {
                "first": ordered[0].isoformat(),
                "last": ordered[-1].isoformat(),
                "hours": len(ordered),
                # Timestamp and value together, so a gap stays a gap rather
                # than silently shifting every later reading by an hour.
                "points": [[h.isoformat(), hours[h]] for h in ordered],
            }
        if problems:
            notes[code] = problems[:12]

    return {
        "source": "ENTSO-E Transparency Platform, A65 actual total load",
        "resolution": "hourly mean",
        "unit": "MW",
        "windows": [[a.isoformat(), b.isoformat()] for a, b in windows],
        "countries_ok": sorted(series),
        "countries_missing": sorted(set(ENTSOE_ZONES) - set(series)),
        "requests": calls,
        "problems": notes,
        "data": series,
    }


def main():
    start = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2023, 1, 1)
    end = datetime.now(timezone.utc).date() - timedelta(days=1)
    os.makedirs(OUT, exist_ok=True)

    jobs = {
        "mta_ridership": lambda: fetch_mta(start),
        "stackexchange": lambda: fetch_stackexchange(start, end),
        "wikipedia": lambda: fetch_wikipedia(start, end),
        "wikipedia_pageviews": lambda: fetch_wikipedia_pageviews(start, end),
        "gdelt_geography": lambda: fetch_gdelt_geography(),
        "entsoe_load": lambda: (
            fetch_entsoe(os.environ.get("ENTSOE_TOKEN", "").strip())
            if os.environ.get("ENTSOE_TOKEN", "").strip()
            else {"skipped": "no ENTSOE_TOKEN in environment"}),
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
