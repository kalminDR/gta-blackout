#!/usr/bin/env python3
"""
Attention Heist - snapshot collector.

Runs once per hour. Takes a snapshot of five "perishable" data sources
(ones that cannot be recovered retroactively) and writes everything into
a single timestamped JSON file.

Design rules:
  1. Never crash. One broken source must not kill the whole run.
  2. Store raw numbers, never derived/calculated ones. Formulas change later,
     data cannot be re-collected.
  3. Everything in UTC.
  4. Append-only. Never overwrite an existing snapshot.

Missing API keys are fine - that source is simply skipped and marked as such.
"""

import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA = "attention-heist/1.0 (research project; contact: hello@eureka.works)"
TIMEOUT = 25


# ---------------------------------------------------------------- helpers

def get_json(url, headers=None, data=None, method="GET"):
    """Minimal HTTP client. Returns parsed JSON or raises."""
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def get_text(url, headers=None):
    """Same as get_json, but returns the raw body (for CSV endpoints)."""
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def try_urls(candidates, parser=None):
    """Try several URLs in order, return the first that works.

    These third-party endpoints are undocumented and move around, so instead
    of betting on one, we try each and record what happened. The snapshot
    then tells us which ones are alive.
    """
    errors = {}
    for url in candidates:
        try:
            raw = get_json(url)
            return {"source_url": url,
                    "data": parser(raw) if parser else raw}
        except Exception as e:
            errors[url] = str(e)[:100]
    return {"errors": errors}


def env(name):
    v = os.environ.get(name, "").strip()
    return v or None


# ---------------------------------------------------------------- sources

def collect_twitch():
    """Top 100 live streams worldwide, aggregated per game.

    This is the substitution signal: when GTA VI launches, everything else
    on Twitch should visibly deflate. We store the per-game totals plus the
    language breakdown (our only geographic hint on Twitch).
    """
    cid, secret = env("TWITCH_CLIENT_ID"), env("TWITCH_CLIENT_SECRET")
    if not (cid and secret):
        return {"skipped": "no TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET"}

    tok = get_json(
        "https://id.twitch.tv/oauth2/token",
        data={"client_id": cid, "client_secret": secret,
              "grant_type": "client_credentials"},
        method="POST",
    )["access_token"]

    headers = {"Client-Id": cid, "Authorization": f"Bearer {tok}"}
    res = get_json("https://api.twitch.tv/helix/streams?first=100", headers=headers)
    streams = res.get("data", [])

    per_game, per_lang = {}, {}
    for s in streams:
        g = s.get("game_name") or "(unknown)"
        lang = s.get("language") or "(unknown)"
        v = int(s.get("viewer_count") or 0)
        per_game[g] = per_game.get(g, 0) + v
        per_lang[lang] = per_lang.get(lang, 0) + v

    return {
        "stream_count": len(streams),
        "total_viewers_top100": sum(per_game.values()),
        "viewers_by_game": dict(sorted(per_game.items(),
                                       key=lambda kv: -kv[1])),
        "viewers_by_language": dict(sorted(per_lang.items(),
                                           key=lambda kv: -kv[1])),
    }


# Steam app IDs. GTA VI will not be here (console-only at launch), which is
# exactly the point: we are measuring what people stop playing.
STEAM_APPS = {
    "271590": "Grand Theft Auto V",
    "3240220": "Grand Theft Auto V Enhanced",
    "1174180": "Red Dead Redemption 2",
    "730": "Counter-Strike 2",
    "570": "Dota 2",
    "578080": "PUBG",
    "1172470": "Apex Legends",
    "1086940": "Baldur's Gate 3",
}


def collect_steam():
    """Concurrent player counts for a fixed basket of games."""
    key = env("STEAM_API_KEY")
    out = {}
    for appid, name in STEAM_APPS.items():
        url = ("https://api.steampowered.com/ISteamUserStats/"
               f"GetNumberOfCurrentPlayers/v1/?appid={appid}")
        if key:
            url += f"&key={key}"
        try:
            n = get_json(url)["response"].get("player_count")
            out[name] = n
        except Exception as e:
            out[name] = {"error": str(e)[:120]}
        time.sleep(0.4)   # be polite
    return out


def collect_hackernews():
    """Global developer activity, in one unauthenticated request.

    Hacker News hands out sequential item IDs to every post and comment ever
    made. The current maximum ID therefore only ever goes up, and the gap
    between two hourly snapshots is exactly how many items were created in
    that hour. That is a live activity rate for the people who are, in
    theory, supposed to be working.

    This replaces the Reddit collector: Reddit closed self-service API
    access in November 2025 and killed the public .json endpoints in
    May 2026, so there is no free path to their data any more.
    """
    out = {}
    try:
        out["max_item_id"] = get_json(
            "https://hacker-news.firebaseio.com/v0/maxitem.json")
    except Exception as e:
        out["max_item_id"] = {"error": str(e)[:120]}

    try:
        out["top_stories_count"] = len(get_json(
            "https://hacker-news.firebaseio.com/v0/topstories.json") or [])
    except Exception as e:
        out["top_stories_count"] = {"error": str(e)[:120]}

    return out


def collect_youtube():
    """Rockstar's channel and trailer counters.

    Slow-moving numbers, but the run-up curve makes good content in October,
    and view counts cannot be reconstructed after the fact.
    """
    key = env("YOUTUBE_API_KEY")
    if not key:
        return {"skipped": "no YOUTUBE_API_KEY"}

    out = {}
    try:
        ch = get_json("https://www.googleapis.com/youtube/v3/channels"
                      f"?part=statistics&forHandle=RockstarGames&key={key}")
        st = ch["items"][0]["statistics"]
        out["rockstar_channel"] = {
            "subscribers": st.get("subscriberCount"),
            "total_views": st.get("viewCount"),
        }
    except Exception as e:
        out["rockstar_channel"] = {"error": str(e)[:120]}

    # Comma-separated video IDs. Add each new trailer here as it drops.
    vids = env("YOUTUBE_VIDEO_IDS") or "QdBZY2fkU-0"
    try:
        vr = get_json("https://www.googleapis.com/youtube/v3/videos"
                      f"?part=statistics,snippet&id={vids}&key={key}")
        out["videos"] = {
            i["id"]: {
                "title": i["snippet"]["title"],
                "views": i["statistics"].get("viewCount"),
                "likes": i["statistics"].get("likeCount"),
                "comments": i["statistics"].get("commentCount"),
            }
            for i in vr.get("items", [])
        }
    except Exception as e:
        out["videos"] = {"error": str(e)[:120]}
    return out


# City centre coordinates. TomTom tells us current speed vs free-flow speed
# on the road segment nearest to each point.
CITIES = {
    "Budapest":   (47.4979, 19.0402),
    "London":     (51.5074, -0.1278),
    "Berlin":     (52.5200, 13.4050),
    "Warsaw":     (52.2297, 21.0122),
    "New York":   (40.7128, -74.0060),
    "Los Angeles": (34.0522, -118.2437),
}


def collect_traffic():
    """Live congestion per city. If people stay home, the commute lightens."""
    key = env("TOMTOM_API_KEY")
    if not key:
        return {"skipped": "no TOMTOM_API_KEY"}

    out = {}
    for city, (lat, lon) in CITIES.items():
        url = ("https://api.tomtom.com/traffic/services/4/flowSegmentData/"
               f"absolute/10/json?point={lat},{lon}&key={key}")
        try:
            d = get_json(url)["flowSegmentData"]
            out[city] = {
                "current_speed": d.get("currentSpeed"),
                "free_flow_speed": d.get("freeFlowSpeed"),
                "current_travel_time": d.get("currentTravelTime"),
                "free_flow_travel_time": d.get("freeFlowTravelTime"),
            }
        except Exception as e:
            out[city] = {"error": str(e)[:120]}
        time.sleep(0.4)
    return out


# ------------------------------------------------- console service status

def _condense_psn(raw):
    """Keep only what changed, not the whole localized service catalogue.

    The raw response lists every service in every country in every language,
    which is ~340 KB per call. All we actually need is: how many services we
    looked at, and which ones are currently reporting a problem.
    """
    countries = raw.get("countries") or []
    checked, incidents = 0, []
    for c in countries:
        for s in c.get("services") or []:
            checked += 1
            st = s.get("status") or []
            if st:
                incidents.append({
                    "country": c.get("countryCode"),
                    "service": s.get("serviceName"),
                    "since": (st[0] or {}).get("createdDate"),
                })
    return {
        "countries_checked": len(countries),
        "services_checked": checked,
        "incident_count": len(incidents),
        "incidents": incidents[:50],
    }


def _condense_xbox(raw):
    """Same idea for Xbox. A Status name of 'None' means healthy."""
    def bad(item):
        name = (item.get("Status") or {}).get("Name")
        return name and name != "None"

    services = raw.get("CoreServices") or []
    titles = raw.get("Titles") or []
    return {
        "overall": (raw.get("Status") or {}).get("Name"),
        "services_checked": len(services),
        "service_issues": [{"service": s.get("Name"),
                            "status": (s.get("Status") or {}).get("Name")}
                           for s in services if bad(s)],
        "titles_checked": len(titles),
        "title_issues": [{"title": x.get("Name"),
                          "status": (x.get("Status") or {}).get("Name")}
                         for x in titles if bad(x)][:50],
    }


def collect_console_status():
    """Are PlayStation Network and Xbox Live healthy right now?

    Nobody archives this publicly, so if PSN buckles four minutes after the
    midnight unlock, the only way to have proof is to have been watching.
    """
    return {
        "playstation": try_urls([
            "https://status.playstation.com/data/statuses/region/SCEE.json",
            "https://status.playstation.com/data/statuses/region/SCEA.json",
        ], parser=_condense_psn),
        "xbox": try_urls([
            "https://xnotify.xboxlive.com/servicestatusv6/US/en-US",
            "https://xnotify.xboxlive.com/servicestatusv6/GB/en-GB",
        ], parser=_condense_xbox),
    }


# ------------------------------------------------------ steam top charts

def collect_steam_charts():
    """The whole Steam most-played list, not just our hand-picked basket.

    Our fixed basket is a guess about which games GTA VI will pull people
    away from. This captures the full ranking so that in November we are not
    limited to the guesses we made in September.
    """
    def parse(raw):
        ranks = (raw.get("response") or {}).get("ranks") or []
        return [
            {"rank": r.get("rank"),
             "appid": r.get("appid"),
             "concurrent_in_game": r.get("concurrent_in_game"),
             "peak_in_game": r.get("peak_in_game")}
            for r in ranks[:100]
        ]

    return try_urls([
        "https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/",
        "https://api.steampowered.com/ISteamChartsService/GetGamesByConcurrentPlayers/v1/",
    ], parser=parse)


# ------------------------------------------------------------- the money

TICKERS = {
    "TTWO": "Take-Two Interactive (Rockstar's parent)",
    "SONY": "Sony (PlayStation)",
    "MSFT": "Microsoft (Xbox)",
}


def collect_stocks():
    """Share prices around the launch.

    Daily history stays free forever, but minute-level history only stays
    available from the free sources for about a month, so it is cheaper to
    just record it as we go than to rely on remembering in November.
    """
    out = {}
    for sym, desc in TICKERS.items():
        # Yahoo's chart endpoint wants to look like a browser.
        ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36")
        try:
            # Yahoo throttles the first calls from a shared IP and then
            # lets later ones through, so back off and try again rather
            # than giving up on the first refusal.
            raw = None
            for attempt in range(3):
                for host in ("query2", "query1"):
                    try:
                        raw = get_json(
                            f"https://{host}.finance.yahoo.com/v8/finance/"
                            f"chart/{sym}?interval=1m&range=1d",
                            headers={"User-Agent": ua},
                        )
                        break
                    except Exception:
                        continue
                if raw is not None:
                    break
                time.sleep(2 + 3 * attempt)
            if raw is None:
                raise RuntimeError("all yahoo hosts refused after 3 tries")
            meta = raw["chart"]["result"][0]["meta"]
            out[sym] = {
                "description": desc,
                "price": meta.get("regularMarketPrice"),
                "previous_close": meta.get("chartPreviousClose"),
                "day_high": meta.get("regularMarketDayHigh"),
                "day_low": meta.get("regularMarketDayLow"),
                "volume": meta.get("regularMarketVolume"),
                "currency": meta.get("currency"),
                "market_state": meta.get("marketState"),
                "source": "yahoo",
            }
        except Exception as e:
            # Fall back to Stooq, which serves a plain CSV with no key.
            try:
                csv = None
                for host in ("stooq.pl", "stooq.com"):
                    try:
                        csv = get_text(f"https://{host}/q/l/?s={sym.lower()}"
                                       ".us&f=sd2t2ohlcv&h&e=csv")
                        break
                    except Exception:
                        continue
                if csv is None:
                    raise RuntimeError("all stooq hosts refused")
                header, row = csv.strip().splitlines()[:2]
                out[sym] = {
                    "description": desc,
                    "csv": dict(zip(header.split(","), row.split(","))),
                    "source": "stooq",
                    "yahoo_error": str(e)[:100],
                }
            except Exception as e2:
                out[sym] = {"description": desc,
                            "error": f"yahoo: {str(e)[:80]} | stooq: {str(e2)[:80]}"}
        time.sleep(2)
    return out


# ---------------------------------------------------------------- runner

SOURCES = {
    "twitch": collect_twitch,
    "steam": collect_steam,
    "hackernews": collect_hackernews,
    "youtube": collect_youtube,
    "traffic": collect_traffic,
    "console_status": collect_console_status,
    "steam_charts": collect_steam_charts,
    "stocks": collect_stocks,
}


def main():
    now = datetime.now(timezone.utc)
    snapshot = {
        "collected_at_utc": now.isoformat(timespec="seconds"),
        "collector_version": "1.0",
        "sources": {},
    }

    for name, fn in SOURCES.items():
        started = time.time()
        try:
            snapshot["sources"][name] = fn()
            status = "ok"
        except Exception as e:
            snapshot["sources"][name] = {"error": str(e)[:300]}
            status = "FAILED"
        print(f"  {name:9s} {status:6s} ({time.time() - started:.1f}s)",
              file=sys.stderr)

    outdir = os.path.join("data", now.strftime("%Y-%m-%d"))
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, now.strftime("%H%M") + ".json")

    # Never overwrite an existing snapshot.
    if os.path.exists(path):
        path = path.replace(".json", f"-{int(time.time())}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"wrote {path}", file=sys.stderr)


def has_real_data(value):
    """Did this source return anything usable, or only errors/skips?"""
    if isinstance(value, dict):
        if "skipped" in value:
            return False
        return any(k not in ("error", "errors", "description", "source_url")
                   and has_real_data(v) for k, v in value.items())
    if isinstance(value, list):
        return any(has_real_data(v) for v in value)
    return value is not None


def check():
    """Read the newest snapshot and fail loudly if a source has gone dark.

    The collector deliberately swallows errors so one bad source cannot kill
    a run. The downside is that a broken source stays broken in silence, so
    this runs afterwards and makes the workflow fail, which makes GitHub
    send an email.
    """
    days = sorted(glob.glob(os.path.join("data", "*")))
    if not days:
        print("no data directory yet", file=sys.stderr)
        return 0
    files = sorted(glob.glob(os.path.join(days[-1], "*.json")))
    if not files:
        print("no snapshots yet", file=sys.stderr)
        return 0

    with open(files[-1], encoding="utf-8") as f:
        snap = json.load(f)

    dead = [name for name, val in snap["sources"].items()
            if not has_real_data(val)]

    for name in snap["sources"]:
        print(f"  {name:16s} {'DEAD' if name in dead else 'ok'}", file=sys.stderr)

    if dead:
        print(f"\nThese sources returned no usable data: {', '.join(dead)}",
              file=sys.stderr)
        print(f"Check {files[-1]} for the exact errors.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    main()
