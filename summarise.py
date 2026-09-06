#!/usr/bin/env python3
"""
Attention Heist - snapshot aggregator.

collect.py writes one raw JSON file per hour. By November there will be
roughly 1,900 of them, and no web page can open 1,900 files. This script
reads them all and writes two small ones into public/ :

    public/series.json   the full hourly time series
    public/latest.json   the current state, plus how it changed

It rebuilds both from scratch on every run rather than appending. That is
slightly more work each hour, but it means the entire history is recomputed
whenever we change a formula - which is exactly why collect.py stores raw
numbers and never derived ones.

Run:  python summarise.py
"""

import glob
import indices
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from statistics import median

DATA_DIR = "data"
OUT_DIR = "public"

# Steam app IDs we care about, and the short key each becomes.
STEAM_KEYS = {
    "Grand Theft Auto V": "steam_gta5",
    "Grand Theft Auto V Enhanced": "steam_gta5_enhanced",
    "Counter-Strike 2": "steam_cs2",
    "Dota 2": "steam_dota2",
    "PUBG": "steam_pubg",
    "Apex Legends": "steam_apex",
    "Baldur's Gate 3": "steam_bg3",
    "Red Dead Redemption 2": "steam_rdr2",
}

# The two GTA V app IDs, so we can track their position in Steam's live
# ranking. The ranking is ordered by current players even though the API
# only hands us the daily peak, so the rank itself is the live signal.
STEAM_RANK_APPIDS = {271590: "steam_rank_gta5", 3240220: "steam_rank_gta5_enh"}

# A segment shorter than this cannot hold a queue; a road class this local
# is not a commuter route. Both mirror the collector's own thresholds.
MIN_SEGMENT_METRES = 700
MIN_ROAD_CLASS = 4

CITY_KEYS = {
    "Budapest": "traffic_budapest",
    "London": "traffic_london",
    "Berlin": "traffic_berlin",
    "Warsaw": "traffic_warsaw",
    "New York": "traffic_newyork",
    "Los Angeles": "traffic_losangeles",
}


# ---------------------------------------------------------------- helpers

def dig(obj, *path, default=None):
    """Walk a nested structure without ever raising.

    Snapshots contain error blocks where numbers normally sit, so every
    lookup has to survive hitting a string, a missing key or None.
    """
    cur = obj
    for step in path:
        if isinstance(cur, dict):
            cur = cur.get(step)
        elif isinstance(cur, list) and isinstance(step, int) and -len(cur) <= step < len(cur):
            cur = cur[step]
        else:
            return default
        if cur is None:
            return default
    return cur


def road_class_number(value):
    """TomTom returns the road class as "FRC0".."FRC7", not a number.
    0 is a motorway, 7 is a local street."""
    if isinstance(value, str) and value.upper().startswith("FRC"):
        try:
            return int(value[3:])
        except ValueError:
            return None
    return as_number(value)


def as_number(value):
    """Return a number, or None. Counts arrive as ints and as strings."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return None
    return None


def parse_time(text):
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


# ------------------------------------------------------------ extraction

def flatten(snap):
    """Turn one raw snapshot into a flat row of numbers."""
    src = snap.get("sources") or {}
    row = {"t": snap.get("collected_at_utc")}

    # --- Twitch: attention, and where it is
    tw = src.get("twitch") or {}
    by_game = tw.get("viewers_by_game")
    row["twitch_top100_total"] = as_number(tw.get("total_viewers_top100"))
    if isinstance(by_game, dict) and by_game:
        row["twitch_gta5"] = as_number(by_game.get("Grand Theft Auto V")) or 0
        top_game, top_viewers = max(by_game.items(), key=lambda kv: kv[1])
        row["twitch_top_game"] = top_game
        row["twitch_top_game_viewers"] = as_number(top_viewers)
    lang = tw.get("viewers_by_language")
    row["twitch_by_language"] = lang if isinstance(lang, dict) else None

    # Direct category figures. Absent from older snapshots, which is fine:
    # the metric is simply blank for those hours rather than zero.
    cats = tw.get("categories")
    if isinstance(cats, dict):
        for slug in ("gta6", "gta5"):
            c = cats.get(slug)
            if not isinstance(c, dict) or not c.get("category_exists"):
                continue
            row[f"twitch_{slug}_viewers"] = as_number(c.get("total_viewers"))
            row[f"twitch_{slug}_channels"] = as_number(c.get("channels"))
            row[f"twitch_{slug}_top5_share"] = as_number(c.get("top5_share_pct"))

    # Everything on the platform's top end that is not GTA. This is the
    # displacement side of Twitch and has to be separated from the GTA
    # figures above - added together they would partly cancel out.
    if isinstance(by_game, dict) and by_game:
        row["twitch_other_viewers"] = sum(
            v for g, v in by_game.items()
            if isinstance(v, (int, float)) and "grand theft auto" not in g.lower())

    # --- Steam: what people stop playing
    st = src.get("steam") or {}
    basket = []
    for name, key in STEAM_KEYS.items():
        n = as_number(st.get(name))
        row[key] = n
        if n is not None:
            basket.append(n)
    row["steam_basket_total"] = sum(basket) if basket else None

    for entry in dig(src, "steam_charts", "data", default=[]) or []:
        key = STEAM_RANK_APPIDS.get(entry.get("appid")) if isinstance(entry, dict) else None
        if key:
            row[key] = as_number(entry.get("rank"))

    # --- Hacker News: raw counter now, rate computed later
    row["hn_max_item_id"] = as_number(dig(src, "hackernews", "max_item_id"))

    # Money staked on this game. Always a lower bound: it is the volume across
    # the markets our search finds, not the size of the whole market, and the
    # page must say so.
    row["polymarket_total_volume"] = as_number(dig(src, "polymarket", "total_volume"))
    row["polymarket_market_count"] = as_number(dig(src, "polymarket", "market_count"))

    # --- YouTube: the hype curve
    row["yt_subscribers"] = as_number(
        dig(src, "youtube", "rockstar_channel", "subscribers"))
    row["yt_rockstar_total_views"] = as_number(
        dig(src, "youtube", "rockstar_channel", "total_views"))
    videos = dig(src, "youtube", "videos", default={})
    if isinstance(videos, dict):
        for vid, stats in videos.items():
            if not isinstance(stats, dict):
                continue
            row[f"yt_{vid}_views"] = as_number(stats.get("views"))
            row[f"yt_{vid}_likes"] = as_number(stats.get("likes"))

    # --- Traffic: how much slower than a free-flowing road.
    # Median across several points per city, so one dud measurement point
    # or a segment that shifts cannot drag the city's number around.
    traffic = src.get("traffic") or {}
    for city, key in CITY_KEYS.items():
        entry = traffic.get(city) or {}
        readings = entry.get("points")
        if not isinstance(readings, list):
            # Snapshots from before the multi-point change had one flat
            # reading per city. Keep reading them so the history survives.
            readings = [entry] if entry else []

        # Sum the seconds, then take the ratio - which is how traffic
        # indices are normally built. It weights each point by how long its
        # segment is, so a jammed 60-metre stub cannot outvote a clear 2 km
        # of main road, and a median cannot hide a real jam behind two
        # free-flowing stretches.
        cur_total, free_total, ok, road_classes = 0, 0, 0, []
        rejected = 0
        for r in readings:
            if not isinstance(r, dict):
                continue
            cur = as_number(r.get("current_travel_time"))
            free = as_number(r.get("free_flow_travel_time"))
            rc = road_class_number(r.get("road_class"))

            # How much road this point watches. Older snapshots predate the
            # field, so it is derived when absent rather than treated as a
            # failure -- the history stays usable.
            metres = as_number(r.get("segment_metres"))
            if metres is None:
                speed = as_number(r.get("free_flow_speed"))
                if speed and free:
                    metres = speed * 1000 / 3600 * free

            # A point is dropped, not averaged in, when it cannot carry the
            # signal. Two ways to fail: too short to hold a queue, or sitting
            # on a local road that no commuter uses. Averaging a dead point
            # into the city figure is worse than having one point fewer,
            # because it pulls every reading towards zero delay and then
            # spikes when a single vehicle stops on eighty metres of tarmac.
            too_short = metres is not None and metres < MIN_SEGMENT_METRES
            too_local = rc is not None and rc >= MIN_ROAD_CLASS
            if too_short or too_local:
                rejected += 1
                continue

            if cur and free:
                cur_total += cur
                free_total += free
                ok += 1
            if rc is not None:
                road_classes.append(rc)

        row[f"{key}_delay_pct"] = round((cur_total / free_total - 1) * 100, 1) if free_total else None
        # Travel time as a percentage of free flow: 100 is an empty road,
        # 130 is a third slower. A delay percentage cannot be used for a
        # ratio because it sits near zero at night and the log of a ratio
        # of near-zero numbers is meaningless.
        row[f"{key}_travel_index"] = round(cur_total / free_total * 100, 1) if free_total else None
        row[f"{key}_points_ok"] = ok or None
        row[f"{key}_points_rejected"] = rejected or None
        row[f"{key}_seconds_measured"] = free_total or None
        # A rising road class means a point has drifted onto a smaller road.
        row[f"{key}_road_class"] = round(median(road_classes), 1) if road_classes else None

    # --- Electricity demand: did a country stay in
    #
    # Absolute megawatts are not comparable between countries -- Germany's
    # ordinary evening dwarfs Hungary's -- so the level is stored raw and the
    # index layer does the comparing, each country against its own past. The
    # lag is stored beside it because a reading whose age is unknown cannot be
    # placed on an hourly timeline at all.
    power = src.get("entsoe") or {}
    if isinstance(power, dict):
        for code, entry in power.items():
            if not isinstance(entry, dict) or len(code) != 2:
                continue
            short = code.lower()
            row[f"power_{short}_load_mw"] = as_number(entry.get("load_mw"))
            row[f"power_{short}_lag_hours"] = as_number(entry.get("lag_hours"))

    # --- Hardware scarcity: resale price, then actual retail stock
    for market, short in (("EBAY_US", "us"), ("EBAY_GB", "uk"), ("EBAY_DE", "de")):
        for prod in ("ps5_pro", "ps5", "xbox_series_x"):
            row[f"price_{short}_{prod}"] = as_number(
                dig(src, "console_prices", market, prod, "median"))
            row[f"listings_{short}_{prod}"] = as_number(
                dig(src, "console_prices", market, prod, "count"))

    for prod in ("ps5_pro", "ps5", "xbox_series_x"):
        products = dig(src, "retail_stock", prod, "products", default=[])
        if isinstance(products, list) and products:
            # "in stock somewhere" is the honest reading: any matching SKU
            # that Best Buy will actually sell you right now.
            row[f"bestbuy_{prod}_online"] = any(
                p.get("online") is True for p in products if isinstance(p, dict))
            row[f"bestbuy_{prod}_price"] = as_number(
                dig(products, 0, "sale_price"))
        else:
            row[f"bestbuy_{prod}_online"] = None
            row[f"bestbuy_{prod}_price"] = None

    # --- Console health
    row["psn_incidents"] = as_number(
        dig(src, "console_status", "playstation", "data", "incident_count"))
    xbox_issues = dig(src, "console_status", "xbox", "data", "service_issues")
    row["xbox_service_issues"] = len(xbox_issues) if isinstance(xbox_issues, list) else None

    return row


# Counters that only ever go up, and the per-hour metric each becomes.
#
# A cumulative total must never be compared to a baseline directly. Rockstar's
# lifetime view count rises every hour whether anything is happening or not,
# so against a four-week-old baseline it would show a permanent, meaningless
# "effect" that grows with time. The rate of change is the real signal.
CUMULATIVE = {
    "hn_max_item_id": "hn_items_per_hour",
    "yt_rockstar_total_views": "yt_rockstar_views_per_hour",
    "yt_subscribers": "yt_subscribers_per_hour",
}

# Trailer view and like counters are discovered per video ID, so they are
# matched by suffix rather than listed.
CUMULATIVE_SUFFIXES = {"_views": "_views_per_hour", "_likes": "_likes_per_hour"}


def rate_targets(points):
    """Which keys to differentiate, fixed list plus discovered trailers."""
    targets = dict(CUMULATIVE)
    for p in points:
        for key in p:
            if not key.startswith("yt_"):
                continue
            for suffix, replacement in CUMULATIVE_SUFFIXES.items():
                if key.endswith(suffix) and key not in targets:
                    targets[key] = key[: -len(suffix)] + replacement
    return targets


def add_rates(points):
    """Turn every cumulative counter into a per-hour rate.

    Two guards, both learned from the Hacker News data. Gaps over three
    hours are left blank rather than smeared into a misleading average.
    Gaps under thirty minutes are also blank: these counters lag by a few
    minutes, so a five-minute window measures the lag rather than the real
    rate, and it showed up as a systematic underestimate - 280 to 587 items
    where the true figure was 865 to 991.
    """
    targets = rate_targets(points)
    prev = {}
    for p in points:
        now_t = parse_time(p.get("t"))
        for source, out_key in targets.items():
            p[out_key] = None
            now_v = p.get(source)
            if not isinstance(now_v, (int, float)) or isinstance(now_v, bool):
                continue
            if now_t and source in prev:
                prev_v, prev_t = prev[source]
                gap_h = (now_t - prev_t).total_seconds() / 3600
                # A counter that goes backwards means the API restated
                # something. Skip rather than publish a negative rate.
                if 0.5 <= gap_h <= 3 and now_v >= prev_v:
                    p[out_key] = round((now_v - prev_v) / gap_h, 2)
            if now_t:
                prev[source] = (now_v, now_t)
    return points


# --------------------------------------------------------------- outputs

def build_changes(points):
    """Compare the newest reading to roughly a day and a week earlier."""
    if not points:
        return {}
    latest = points[-1]
    now = parse_time(latest.get("t"))
    if not now:
        return {}

    def closest_to(target):
        best, best_gap = None, None
        for p in points[:-1]:
            t = parse_time(p.get("t"))
            if not t:
                continue
            gap = abs((t - target).total_seconds())
            if best_gap is None or gap < best_gap:
                best, best_gap = p, gap
        # only usable if we actually landed within 3 hours of the target
        return best if best_gap is not None and best_gap <= 3 * 3600 else None

    changes = {}
    for label, delta in (("vs_24h", timedelta(days=1)),
                         ("vs_7d", timedelta(days=7))):
        ref = closest_to(now - delta)
        if not ref:
            continue
        for key, new in latest.items():
            if key == "t" or not isinstance(new, (int, float)) or isinstance(new, bool):
                continue
            old = ref.get(key)
            if not isinstance(old, (int, float)) or isinstance(old, bool) or not old:
                continue
            changes.setdefault(key, {})[label] = {
                "then": old,
                "absolute": round(new - old, 2),
                "percent": round((new / old - 1) * 100, 1),
            }
    return changes


def day_shape(points):
    """What an ordinary day looks like in our own data, hour by hour.

    Two curves: how busy the roads are, and how many people are playing or
    watching games. On a normal day they run against each other - roads peak
    when people travel to work, games peak in the evening. That contrast is
    the whole question in one picture, and on 19 November we find out whether
    the shape holds.

    Each curve is scaled to its own maximum, because the point is the shape
    and not the units.
    """
    roads, games = {}, {}
    for p in points:
        t = parse_time(p.get("t"))
        if not t:
            continue
        # Average the cities that reported, so one quiet city cannot flatten
        # the curve and one accident cannot spike it.
        city = [p.get(k + "_travel_index") for k in CITY_KEYS.values()]
        city = [v for v in city if isinstance(v, (int, float)) and v > 0]
        if city:
            roads.setdefault(t.hour, []).append(sum(city) / len(city))
        g = [p.get(k) for k in ("steam_basket_total", "twitch_top100_total")]
        if all(isinstance(v, (int, float)) and v > 0 for v in g):
            games.setdefault(t.hour, []).append(sum(g))

    def curve(buckets):
        if len(buckets) < 6:      # too few hours covered to draw a day
            return None
        med = {h: median(v) for h, v in buckets.items()}
        top = max(med.values()) or 1
        return [round(med[h] / top, 3) if h in med else None for h in range(24)]

    return {
        "roads": curve(roads),
        "games": curve(games),
        "hours_covered": sorted(set(list(roads) + list(games))),
    }


def observed_ranges(points):
    """Ranges the page can quote instead of hard-coding a number.

    A sentence like "still draws 70,000 to 150,000 players" must be tied to
    a stated observation window, otherwise it reads as a permanent property
    of the game and quietly goes stale. The page injects these and says how
    long we have been watching.
    """
    def span(*keys):
        vals = []
        for p in points:
            parts = [p.get(k) for k in keys]
            if all(isinstance(v, (int, float)) and v > 0 for v in parts):
                vals.append(sum(parts))
        if not vals:
            return None
        return {"min": int(min(vals)), "max": int(max(vals)),
                "median": int(median(vals)), "readings": len(vals)}

    first = parse_time(points[0].get("t")) if points else None
    last = parse_time(points[-1].get("t")) if points else None
    return {
        "from": points[0].get("t") if points else None,
        "to": points[-1].get("t") if points else None,
        "days": (round((last - first).total_seconds() / 86400, 1)
                 if first and last else None),
        "gta5_steam_players": span("steam_gta5", "steam_gta5_enhanced"),
        "trailer_views": span("yt_QdBZY2fkU-0_views"),
    }


def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*", "*.json")))
    if not files:
        print("No snapshots found - has collect.py run yet?", file=sys.stderr)
        return 1

    points, unreadable = [], []
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                snap = json.load(f)
            if snap.get("collected_at_utc"):
                points.append(flatten(snap))
        except Exception as e:
            unreadable.append({"file": path, "error": str(e)[:120]})

    if not points:
        print("Snapshots exist but none could be read.", file=sys.stderr)
        return 1

    points.sort(key=lambda p: p.get("t") or "")
    add_rates(points)
    indices.compute(points)

    first_t, last_t = parse_time(points[0]["t"]), parse_time(points[-1]["t"])
    span_days = round((last_t - first_t).total_seconds() / 86400, 1) if first_t and last_t else 0
    now = datetime.now(timezone.utc)

    coverage = {
        "first_snapshot": points[0]["t"],
        "last_snapshot": points[-1]["t"],
        "snapshot_count": len(points),
        "days_of_history": span_days,
        "unreadable_files": unreadable,
        "hours_since_last_snapshot": max(0.0, round(
            (now - last_t).total_seconds() / 3600, 1)) if last_t else None,
    }

    os.makedirs(OUT_DIR, exist_ok=True)

    with open(os.path.join(OUT_DIR, "series.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at_utc": now.isoformat(timespec="seconds"),
                   "coverage": coverage,
                   "points": points}, f, ensure_ascii=False, separators=(",", ":"))

    panels = indices.summary(points)

    with open(os.path.join(OUT_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at_utc": now.isoformat(timespec="seconds"),
                   "coverage": coverage,
                   "latest": points[-1],
                   "observed": observed_ranges(points),
                   "panels": panels,
                   "changes": build_changes(points)},
                  f, ensure_ascii=False, indent=1)

    # A small file with nothing but the four index lines, so the chart on
    # the page does not have to download the whole series.
    chart = [{"t": p["t"],
              **{name: (p.get("indices") or {}).get(name, {}).get("index")
                 if isinstance((p.get("indices") or {}).get(name), dict) else None
                 for name in indices.PANEL_NAMES}}
             for p in points]
    with open(os.path.join(OUT_DIR, "chart.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at_utc": now.isoformat(timespec="seconds"),
                   "day_shape": day_shape(points),
                   "panels": {k: v for k, v in indices.PANEL_NAMES.items()},
                   "placebo": {name: indices.placebo(points, name)
                               for name in indices.PANEL_NAMES},
                   "points": chart}, f, ensure_ascii=False, separators=(",", ":"))

    series_kb = os.path.getsize(os.path.join(OUT_DIR, "series.json")) / 1024
    print(f"{len(points)} snapshots over {span_days} days "
          f"-> public/series.json ({series_kb:.0f} KB) + public/latest.json",
          file=sys.stderr)
    if unreadable:
        print(f"warning: {len(unreadable)} file(s) could not be read",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
