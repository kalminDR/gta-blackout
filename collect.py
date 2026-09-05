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

Deliberately NOT collected here: share prices. Yahoo and Stooq both refuse
requests from GitHub Actions IP ranges, and minute-level history stays free
for about 30 days anyway - so grab TTWO/SONY/MSFT by hand in early December
instead of fighting a rate limiter every hour until then.

Missing API keys are fine - that source is simply skipped and marked as such.
"""

import base64
import glob
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

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
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        # Most APIs explain themselves in the response body. Throwing that
        # away leaves a bare "401 Unauthorized", which says nothing about
        # whether the key is wrong, the scope is wrong, or the account is
        # not approved yet.
        try:
            detail = e.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            detail = ""
        raise RuntimeError(f"HTTP {e.code}: {detail or e.reason}") from None


def get_text(url, headers=None):
    """Same client as get_json, but for APIs that answer in XML.

    ENTSO-E is one of them. It also answers errors in XML, with the reason
    inside the body, so the body is kept on failure for the same reason it is
    kept everywhere else here: "HTTP 401" alone never tells you whether the
    token is wrong, expired, or simply not yet activated.
    """
    h = {"User-Agent": UA, "Accept": "application/xml"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            detail = ""
        raise RuntimeError(f"HTTP {e.code}: {detail or e.reason}") from None


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


def as_float(value):
    """Numbers arrive as ints, floats and strings depending on the API."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def dig(obj, *path):
    """Nested lookup that never raises on a missing or odd-shaped field."""
    cur = obj
    for step in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(step)
        if cur is None:
            return None
    return cur


def env(name):
    v = os.environ.get(name, "").strip()
    return v or None


# ---------------------------------------------------------------- sources

# Twitch categories we follow directly, by exact name.
#
# GTA V is here as much for testing as for measurement: it is live right now,
# so it exercises the same code path as GTA VI every hour and proves the
# pagination works long before launch night, when there is no time to debug.
TWITCH_CATEGORIES = {
    "gta6": "Grand Theft Auto VI",
    "gta5": "Grand Theft Auto V",
}

# Pages of 100 streams. Twenty is 2,000 channels.
#
# Five would have been plenty on a normal day and useless on the one night
# that matters: the channel count would simply have flatlined at the page
# limit exactly when it was supposed to spike. The `truncated` flag says
# whether the ceiling was actually hit, so a capped reading is never
# mistaken for a real one.
TWITCH_MAX_PAGES = 20


def _twitch_category(headers, name):
    """Every visible live stream in one category, aggregated.

    The top-100 list answers "how busy is Twitch", not "how much attention
    is on GTA VI" - on a normal day GTA VI need not appear in it at all,
    and on launch night it would be capped by the size of the list. Asking
    for the category directly removes both problems.
    """
    games = get_json("https://api.twitch.tv/helix/games?name="
                     + urllib.parse.quote(name), headers=headers)
    items = games.get("data") or []
    if not items:
        # Expected for GTA VI until Twitch creates the category. Recorded as
        # a fact rather than an error, so it is visible when it flips.
        return {"category_exists": False, "queried_name": name}

    game_id = items[0].get("id")
    streams, cursor, pages = [], None, 0
    while pages < TWITCH_MAX_PAGES:
        url = f"https://api.twitch.tv/helix/streams?game_id={game_id}&first=100"
        if cursor:
            url += "&after=" + urllib.parse.quote(cursor)
        res = get_json(url, headers=headers)
        batch = res.get("data") or []
        streams.extend(batch)
        pages += 1
        cursor = dig(res, "pagination", "cursor")
        if not cursor or len(batch) < 100:
            break
        time.sleep(0.3)

    viewers = [int(s.get("viewer_count") or 0) for s in streams]
    per_lang = {}
    for s in streams:
        per_lang[s.get("language") or "(unknown)"] = (
            per_lang.get(s.get("language") or "(unknown)", 0)
            + int(s.get("viewer_count") or 0))

    total = sum(viewers)
    top5 = sum(sorted(viewers, reverse=True)[:5])
    return {
        "category_exists": True,
        "game_id": game_id,
        "channels": len(streams),
        "total_viewers": total,
        "median_viewers_per_channel": (
            round(statistics.median(viewers), 1) if viewers else 0),
        # If a handful of big channels hold nearly all the viewers, the
        # number says more about who went live than about public interest.
        "top5_share_pct": round(100 * top5 / total, 1) if total else None,
        "viewers_by_language": dict(sorted(per_lang.items(),
                                           key=lambda kv: -kv[1])[:25]),
        "pages_fetched": pages,
        "truncated": bool(cursor) and pages >= TWITCH_MAX_PAGES,
    }


def collect_twitch():
    """Two views of Twitch: the platform's top end, and GTA specifically.

    The top-100 total is the displacement signal - when GTA VI launches,
    everything else should visibly deflate. The per-category figures are the
    direct attention signal. They answer different questions and must not be
    added together.
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

    categories = {}
    for key, name in TWITCH_CATEGORIES.items():
        try:
            categories[key] = _twitch_category(headers, name)
        except Exception as e:
            categories[key] = {"error": str(e)[:120]}
        time.sleep(0.3)

    return {
        "stream_count": len(streams),
        "total_viewers_top100": sum(per_game.values()),
        "viewers_by_game": dict(sorted(per_game.items(),
                                       key=lambda kv: -kv[1])),
        "viewers_by_language": dict(sorted(per_lang.items(),
                                           key=lambda kv: -kv[1])),
        "categories": categories,
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
    # However the list was typed - spaces after commas, a trailing comma,
    # a stray newline - normalise it rather than making the person retype it.
    raw_ids = env("YOUTUBE_VIDEO_IDS") or "QdBZY2fkU-0"
    ids = [v.strip() for v in raw_ids.replace("\n", ",").split(",") if v.strip()]
    odd = [v for v in ids if len(v) != 11]
    vids = ",".join(ids)
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
        out["videos"] = {"error": str(e)[:200]}

    # A YouTube id is always eleven characters. Flagging the odd ones here
    # saves hunting for a silently missing video later.
    if odd:
        out["video_ids_wrong_length"] = odd
    out["video_ids_tracked"] = len(ids)
    return out


# Traffic measurement points.
#
# The first version used city-centre coordinates, which was wrong: TomTom
# returns the road segment nearest the point, and in a dense centre that is
# a random side street. New York landed on a 90-metre stretch that never
# congests, and London kept snapping to different segments between calls.
#
# So: three points per city, placed on major commuter arteries, and the
# city's figure is the median of the three. One dud point can no longer
# ruin a city, and a segment that shifts is outvoted by the other two.
CITY_POINTS = {
    "Budapest": {
        "hungaria_korut": (47.5300, 19.0800),
        "ulloi_ut":       (47.4650, 19.1200),
        "budaorsi_ut":    (47.4650, 18.9900),
    },
    "London": {
        "a40_westway":       (51.5200, -0.2100),
        "a406_north_circ":   (51.5750, -0.2300),
        "a2_old_kent_road":  (51.4850, -0.0650),
    },
    "Berlin": {
        "a100_stadtring":   (52.4900, 13.3300),
        "frankfurter_allee": (52.5150, 13.4700),
        "kaiserdamm":       (52.5100, 13.2950),
    },
    "Warsaw": {
        "wislostrada":        (52.2450, 21.0300),
        "s8_trasa_torunska":  (52.2900, 20.9900),
        "aleje_jerozolimskie": (52.2280, 20.9800),
    },
    "New York": {
        "fdr_drive":       (40.7500, -73.9700),
        "cross_bronx_i95": (40.8430, -73.9200),
        "lie_i495_queens": (40.7350, -73.8700),
    },
    "Los Angeles": {
        "i405_sepulveda": (34.0900, -118.4500),
        "i10_santa_monica": (34.0300, -118.3400),
        "us101_hollywood": (34.0950, -118.3300),
    },
}


def collect_traffic():
    """Live congestion on major roads. If people stay home, the commute
    lightens - but only if we are measuring roads that carry commuters."""
    key = env("TOMTOM_API_KEY")
    if not key:
        return {"skipped": "no TOMTOM_API_KEY"}

    out = {}
    for city, points in CITY_POINTS.items():
        readings = []
        for name, (lat, lon) in points.items():
            url = ("https://api.tomtom.com/traffic/services/4/flowSegmentData/"
                   f"absolute/10/json?point={lat},{lon}&key={key}")
            try:
                d = get_json(url)["flowSegmentData"]
                readings.append({
                    "point": name,
                    "current_speed": d.get("currentSpeed"),
                    "free_flow_speed": d.get("freeFlowSpeed"),
                    "current_travel_time": d.get("currentTravelTime"),
                    "free_flow_travel_time": d.get("freeFlowTravelTime"),
                    # Road class: 0 is a motorway, higher is more local.
                    # Lets us spot a point that has drifted onto a side street.
                    "road_class": d.get("frc"),
                })
            except Exception as e:
                readings.append({"point": name, "error": str(e)[:100]})
            time.sleep(0.4)
        out[city] = {"points": readings}
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


# ------------------------------------------------------- console hardware

# What we search for, on each marketplace. Prices are in the marketplace's
# own currency, so each entry carries its own sanity range: anything outside
# it is an accessory, a controller, a faceplate or a scam, not a console.
EBAY_MARKETS = {
    "EBAY_US": {"currency": "USD", "min": 300, "max": 1600},
    "EBAY_GB": {"currency": "GBP", "min": 250, "max": 1400},
    "EBAY_DE": {"currency": "EUR", "min": 300, "max": 1600},
}

EBAY_PRODUCTS = {
    "ps5_pro": "PlayStation 5 Pro console",
    "ps5": "PlayStation 5 Slim console disc",
    "xbox_series_x": "Xbox Series X console",
}


def _price_stats(prices):
    """Median and spread. Median, not mean, because one absurd listing
    should not move the number."""
    if not prices:
        return None
    prices = sorted(prices)
    return {
        "count": len(prices),
        "min": round(prices[0], 2),
        "median": round(statistics.median(prices), 2),
        "max": round(prices[-1], 2),
    }


def collect_console_prices():
    """Second-hand console prices per market.

    Retail price barely moves, because it is set by Sony and Microsoft. What
    moves when stock runs out is the resale price, and that is a continuous
    number rather than a yes/no, so it is the more sensitive measure of
    scarcity.
    """
    cid, secret = env("EBAY_CLIENT_ID"), env("EBAY_CLIENT_SECRET")
    if not (cid and secret):
        return {"skipped": "no EBAY_CLIENT_ID / EBAY_CLIENT_SECRET"}

    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    try:
        tok = get_json(
            "https://api.ebay.com/identity/v1/oauth2/token",
            headers={"Authorization": f"Basic {basic}",
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials",
                  "scope": "https://api.ebay.com/oauth/api_scope"},
            method="POST",
        )["access_token"]
    except Exception as e:
        # Fingerprints of the credentials, never the credentials. Enough to
        # spot a truncated paste or a stray space without leaking anything.
        return {"auth_error": str(e)[:400],
                "client_id_length": len(cid),
                "client_id_prefix": cid[:12],
                "client_secret_length": len(secret),
                # eBay's Dev ID is a UUID and is ALSO exactly 36 characters,
                # so length alone cannot tell it apart from the Cert ID.
                # A production Cert ID always starts with "PRD-". Four
                # characters of a public constant prefix leak nothing.
                "client_secret_prefix": secret[:4],
                "secret_looks_like_cert_id": secret.upper().startswith("PRD-"),
                "looks_like_sandbox": "SBX" in cid.upper()}

    out = {}
    for market, cfg in EBAY_MARKETS.items():
        out[market] = {"currency": cfg["currency"]}
        for key, query in EBAY_PRODUCTS.items():
            try:
                url = ("https://api.ebay.com/buy/browse/v1/item_summary/search"
                       "?q=" + urllib.parse.quote(query) +
                       "&limit=100&filter=" + urllib.parse.quote(
                           f"price:[{cfg['min']}..{cfg['max']}],"
                           f"priceCurrency:{cfg['currency']},"
                           "buyingOptions:{FIXED_PRICE}"))
                res = get_json(url, headers={
                    "Authorization": f"Bearer {tok}",
                    "X-EBAY-C-MARKETPLACE-ID": market,
                })
                items = res.get("itemSummaries") or []
                prices, titles = [], []
                for it in items:
                    p = as_float(dig(it, "price", "value"))
                    if p is not None:
                        prices.append(p)
                        titles.append((it.get("title") or "")[:70])
                stats = _price_stats(prices)
                out[market][key] = stats or {"count": 0}
                # Keep a few titles so we can see whether the search is
                # returning consoles or junk, and tighten it if needed.
                out[market][key]["sample_titles"] = titles[:3]
            except Exception as e:
                out[market][key] = {"error": str(e)[:120]}
            time.sleep(0.6)
    return out


# Best Buy is the largest US electronics retailer with a public API, so it
# is our one real window into actual retail stock rather than resale prices.
BESTBUY_SEARCHES = {
    "ps5_pro": "PlayStation 5 Pro",
    "ps5": "PlayStation 5 Console",
    "xbox_series_x": "Xbox Series X Console",
}


def collect_retail_stock():
    """Is it actually on the shelves? US only, but the biggest single market."""
    key = env("BESTBUY_API_KEY")
    if not key:
        return {"skipped": "no BESTBUY_API_KEY"}

    out = {}
    for slug, term in BESTBUY_SEARCHES.items():
        try:
            search = urllib.parse.quote(f'search={term}')
            url = (f"https://api.bestbuy.com/v1/products(({search}))"
                   f"?apiKey={key}&format=json&pageSize=10"
                   "&show=sku,name,salePrice,regularPrice,onlineAvailability,"
                   "inStoreAvailability,orderable")
            res = get_json(url)
            products = res.get("products") or []
            out[slug] = {
                "matches": res.get("total"),
                "products": [{
                    "sku": p.get("sku"),
                    "name": (p.get("name") or "")[:70],
                    "sale_price": p.get("salePrice"),
                    "regular_price": p.get("regularPrice"),
                    "online": p.get("onlineAvailability"),
                    "in_store": p.get("inStoreAvailability"),
                    "orderable": p.get("orderable"),
                } for p in products[:5]],
            }
        except Exception as e:
            out[slug] = {"error": str(e)[:120]}
        time.sleep(1)
    return out


# ------------------------------------------------------- press attention

# GDELT indexes news from over a hundred countries and needs no key at all.
# We ask three ways: how much coverage, in which languages, from which
# countries. The country split is the geographic layer most of our other
# sources cannot give us.
GDELT_QUERY = '("grand theft auto vi" OR "grand theft auto 6" OR "gta vi" OR "gta 6")'


def _gdelt(mode, timespan="24h"):
    url = ("https://api.gdeltproject.org/api/v2/doc/doc?query="
           + urllib.parse.quote(GDELT_QUERY)
           + f"&mode={mode}&timespan={timespan}&format=json")
    return get_json(url)


def collect_gdelt():
    """How much of the world's press is talking about this game.

    NOT IN THE HOURLY RUN. GDELT returned 429 to every attempt from GitHub
    Actions, including single requests with sixteen-second backoffs, so it
    is blocking the shared runner addresses rather than rate-limiting us.
    Kept here because the function works fine from an ordinary connection,
    and because GDELT timelines are retroactive - see the browser URL in
    README.md for fetching it by hand.

    Volume is returned as a raw article count alongside "norm", the total
    number of articles GDELT saw in the same interval. The ratio matters
    more than the count, because global news output itself swings by day
    and by weekend.
    """
    out = {}

    try:
        raw = _gdelt("timelinevolraw")
        series = (raw.get("timeline") or [{}])[0].get("data") or []
        recent = series[-6:]
        out["volume"] = {
            "points": [{"t": p.get("date"), "articles": p.get("value"),
                        "all_articles": p.get("norm")} for p in recent],
            "series_length": len(series),
        }
    except Exception as e:
        out["volume"] = {"error": str(e)[:150]}

    # GDELT throttles aggressively; three rapid calls earned a 429. Two
    # calls, five seconds apart, is inside what it tolerates. Language is
    # dropped because source country already carries the geography.
    time.sleep(5)
    for mode, key in (("timelinesourcecountry", "by_country"),):
        try:
            raw = _gdelt(mode, timespan="24h")
            # Each series is one country or language; we want the latest
            # value from each, not the whole curve.
            latest = {}
            for s in raw.get("timeline") or []:
                pts = s.get("data") or []
                if pts:
                    latest[s.get("series")] = pts[-1].get("value")
            out[key] = dict(sorted(latest.items(), key=lambda kv: -(kv[1] or 0))[:25])
        except Exception as e:
            out[key] = {"error": str(e)[:150]}
        time.sleep(5)

    return out


# ------------------------------------------------------- money on the line

# People are betting real money on when this game arrives and whether it
# slips again. That is attention priced in dollars, and the delay market is
# a live read on the single biggest risk to this project.
POLYMARKET_TERMS = ["gta", "grand theft auto"]


# Electricity demand, from the transmission operators themselves.
#
# This is the closest thing to a national attendance register that exists.
# Nobody files a report saying they stayed in; the grid simply notices. When a
# country sits down in front of a screen at the same time, demand shifts, and
# the shift is recorded hourly by state operators with no interest whatsoever
# in this game.
#
# There is a documented precedent for the size of the effect. The British grid
# has measured demand surges around televised football for decades -- the 1990
# World Cup semi-final against West Germany produced roughly 2,800 MW, a group
# match in 2018 around 600 MW. That gives us a ruler the reader already
# understands, which is worth more than any index.
#
# The honest caveat, stated here rather than discovered in November: a launch
# effect is likely to be far smaller than a penalty shootout, plausibly inside
# the operators' own forecast error. It may not show up at all. The shape of
# the evening peak may move even when its height does not, and if neither
# moves we will publish that too.
ENTSOE_ZONES = {
    # The eight largest European console markets, plus home.
    "GB": "10YGB----------A",
    "DE": "10Y1001A1001A83F",
    "FR": "10YFR-RTE------C",
    "ES": "10YES-REE------0",
    "IT": "10YIT-GRTN-----B",
    "NL": "10YNL----------L",
    "PL": "10YPL-AREA-----S",
    "SE": "10YSE-1--------K",
    "HU": "10YHU-MAVIR----U",
}

# Minutes per period, by the resolution code ENTSO-E reports.
ENTSOE_RESOLUTION = {"PT15M": 15, "PT30M": 30, "PT60M": 60, "P1D": 1440}


def _entsoe_points(xml):
    """Pull (timestamp, megawatts) out of a GL_MarketDocument.

    Namespaces on these documents change between schema versions, so tags are
    matched on their local name. A document that carries a Reason instead of a
    TimeSeries is an error dressed as a success -- ENTSO-E returns HTTP 200
    with "No matching data found" inside -- so that case is detected and
    reported rather than silently becoming an empty reading.
    """
    import xml.etree.ElementTree as ET

    def local(el):
        return el.tag.rsplit("}", 1)[-1]

    root = ET.fromstring(xml)
    if local(root).startswith("Acknowledgement"):
        bits = []
        for el in root.iter():
            if local(el) in ("code", "text") and el.text:
                bits.append(el.text.strip())
        return [], "; ".join(bits)[:200] or "acknowledgement, no data"

    out = []
    for period in root.iter():
        if local(period) != "Period":
            continue
        start, minutes = None, 60
        for child in period:
            name = local(child)
            if name == "timeInterval":
                for sub in child:
                    if local(sub) == "start" and sub.text:
                        start = datetime.fromisoformat(
                            sub.text.strip().replace("Z", "+00:00"))
            elif name == "resolution" and child.text:
                minutes = ENTSOE_RESOLUTION.get(child.text.strip(), 60)
        if start is None:
            continue
        for point in period:
            if local(point) != "Point":
                continue
            pos, qty = None, None
            for f in point:
                if local(f) == "position" and f.text:
                    pos = int(f.text)
                elif local(f) in ("quantity", "price.amount") and f.text:
                    qty = as_float(f.text)
            if pos is not None and qty is not None:
                out.append((start + timedelta(minutes=minutes * (pos - 1)), qty))
    out.sort()
    return out, None


def collect_entsoe():
    """Actual total load per country, most recent settled hour.

    Publication lags real time, and by a different amount in each country, so
    the lag is recorded alongside the reading. A number without its age is not
    usable for an hourly comparison.
    """
    token = env("ENTSOE_TOKEN")
    if not token:
        return {"skipped": "no ENTSOE_TOKEN"}

    now = datetime.now(timezone.utc)
    # A twelve-hour window: wide enough to survive the slowest publisher,
    # narrow enough that one country's outage cannot dominate the response.
    start = (now - timedelta(hours=12)).strftime("%Y%m%d%H00")
    end = (now + timedelta(hours=1)).strftime("%Y%m%d%H00")

    out = {}
    for code, eic in ENTSOE_ZONES.items():
        url = ("https://web-api.tp.entsoe.eu/api"
               "?documentType=A65&processType=A16"
               "&outBiddingZone_Domain=" + urllib.parse.quote(eic) +
               "&periodStart=" + start + "&periodEnd=" + end +
               "&securityToken=" + urllib.parse.quote(token))
        try:
            points, reason = _entsoe_points(get_text(url))
            if reason:
                out[code] = {"no_data": reason}
                continue
            if not points:
                out[code] = {"no_data": "document parsed, no points"}
                continue
            t, mw = points[-1]
            out[code] = {
                "load_mw": round(mw, 1),
                "t": t.isoformat(),
                "lag_hours": round((now - t).total_seconds() / 3600, 2),
                "points_in_window": len(points),
            }
        except Exception as e:
            # The token is in the URL, so it would appear in any message that
            # echoes it back. Strip it before the error is ever written down.
            msg = str(e)[:300].replace(token, "<token>")
            out[code] = {"error": msg}
    return out


def collect_polymarket():
    """Open prediction markets about Grand Theft Auto VI.

    The endpoint shape is undocumented and has moved before, so we try a
    few forms and record which one answered.
    """
    found, errors, seen = {}, {}, {}
    candidates = [
        # A direct search is the cheapest route if this endpoint exists.
        "https://gamma-api.polymarket.com/public-search?q=grand%20theft%20auto&limit_per_type=20",
        "https://gamma-api.polymarket.com/events?closed=false&limit=500&order=volume&ascending=false",
        "https://gamma-api.polymarket.com/markets?closed=false&limit=500&order=volume&ascending=false",
    ]

    for url in candidates:
        try:
            data = get_json(url)
        except Exception as e:
            errors[url] = str(e)[:100]
            continue

        # The three endpoints wrap their results differently, so unwrap
        # whichever shape came back rather than assuming one.
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = (data.get("data") or data.get("events")
                    or data.get("markets") or [])
            if not rows:
                for v in data.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        rows = v
                        break
        else:
            rows = []

        seen[url] = {
            "rows": len(rows),
            "keys": sorted(rows[0].keys())[:14] if rows and isinstance(rows[0], dict) else [],
            "sample_titles": [
                str(r.get("title") or r.get("question") or r.get("slug") or "")[:60]
                for r in rows[:3] if isinstance(r, dict)
            ],
        }

        for row in rows:
            if not isinstance(row, dict):
                continue
            text = " ".join(str(row.get(k) or "") for k in
                            ("title", "question", "slug", "description")).lower()
            if not any(term in text for term in POLYMARKET_TERMS):
                continue
            key = row.get("slug") or row.get("id")
            if not key or key in found:
                continue
            found[key] = {
                "title": (row.get("title") or row.get("question") or "")[:120],
                "volume": as_float(row.get("volume") or row.get("volumeNum")),
                "liquidity": as_float(row.get("liquidity") or row.get("liquidityNum")),
                "end_date": row.get("endDate"),
                # Outcome prices are the actual probabilities the crowd is
                # paying for; they arrive as a JSON string more often than not.
                "outcomes": row.get("outcomes"),
                "outcome_prices": row.get("outcomePrices"),
                "source_url": url,
            }
        if found:
            break
        time.sleep(0.5)

    if not found:
        return {"markets": {}, "market_count": 0, "errors": errors,
                "endpoints_tried": seen,
                "note": "no matching markets - see endpoints_tried for what came back"}

    return {
        "market_count": len(found),
        "total_volume": round(sum(m["volume"] or 0 for m in found.values()), 2),
        "markets": found,
    }


# ------------------------------------------------------- the community count

def collect_selfreport():
    """The running total of what readers say they will do on 19 November.

    This is the one dataset we gather ourselves rather than read from
    somebody else's API, so it is worth stating what it is: a self-selected
    count of people who chose to answer, not a representative survey.

    Fetching it here, once an hour, is deliberate. The Workers free plan
    allows 100,000 requests a day, and a single press mention could spend
    that on page views alone if the site called the endpoint directly. This
    way the figure travels with the rest of the snapshot and the site reads
    it from a static file; only the person who has just answered gets a
    live reply from the endpoint itself.
    """
    base = env("SELFREPORT_URL")
    if not base:
        return {"skipped": "no SELFREPORT_URL"}
    try:
        return get_json(base.rstrip("/") + "/counts")
    except Exception as e:
        return {"error": str(e)[:200]}


# ---------------------------------------------------------------- runner

SOURCES = {
    "twitch": collect_twitch,
    "steam": collect_steam,
    "hackernews": collect_hackernews,
    "youtube": collect_youtube,
    "traffic": collect_traffic,
    "console_status": collect_console_status,
    "steam_charts": collect_steam_charts,
    "console_prices": collect_console_prices,
    "retail_stock": collect_retail_stock,
    "entsoe": collect_entsoe,
    "polymarket": collect_polymarket,
    "selfreport": collect_selfreport,
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
    # Only date-named folders. data/backfill/ also lives here and holds a
    # completely different shape of file; sorted() puts "backfill" after
    # "2026-..." alphabetically, so without this filter the check reads a
    # backfill file, finds no "sources" key and crashes every hour.
    days = sorted(d for d in glob.glob(os.path.join("data", "*"))
                  if re.fullmatch(r"\d{4}-\d{2}-\d{2}", os.path.basename(d)))
    if not days:
        print("no snapshot folders yet", file=sys.stderr)
        return 0
    files = sorted(glob.glob(os.path.join(days[-1], "*.json")))
    if not files:
        print("no snapshots yet", file=sys.stderr)
        return 0

    with open(files[-1], encoding="utf-8") as f:
        snap = json.load(f)

    # A source that says "skipped" has no key configured yet. That is a
    # decision, not a fault, so it must not raise an alarm every hour -
    # otherwise the real alarms get ignored.
    waiting = [name for name, val in snap["sources"].items()
               if isinstance(val, dict) and "skipped" in val]
    dead = [name for name, val in snap["sources"].items()
            if name not in waiting and not has_real_data(val)]

    for name in snap["sources"]:
        state = "DEAD" if name in dead else ("waiting for key" if name in waiting else "ok")
        print(f"  {name:16s} {state}", file=sys.stderr)

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
