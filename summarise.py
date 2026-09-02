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

    # --- YouTube: the hype curve
    row["yt_subscribers"] = as_number(
        dig(src, "youtube", "rockstar_channel", "subscribers"))
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
        for r in readings:
            if not isinstance(r, dict):
                continue
            cur = as_number(r.get("current_travel_time"))
            free = as_number(r.get("free_flow_travel_time"))
            if cur and free:
                cur_total += cur
                free_total += free
                ok += 1
            rc = road_class_number(r.get("road_class"))
            if rc is not None:
                road_classes.append(rc)

        row[f"{key}_delay_pct"] = round((cur_total / free_total - 1) * 100, 1) if free_total else None
        row[f"{key}_points_ok"] = ok or None
        row[f"{key}_seconds_measured"] = free_total or None
        # A rising road class means a point has drifted onto a smaller road.
        row[f"{key}_road_class"] = round(median(road_classes), 1) if road_classes else None

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


def add_hn_rate(points):
    """Convert the ever-rising Hacker News counter into items per hour.

    Two guards. Gaps over three hours are left blank rather than smeared
    into a misleading average. Gaps under thirty minutes are also blank:
    the counter lags by a few minutes, so a five-minute window measures
    that lag rather than the real posting rate, and it showed up in the
    data as a systematic underestimate.
    """
    prev = None
    for p in points:
        p["hn_items_per_hour"] = None
        now_id, now_t = p.get("hn_max_item_id"), parse_time(p.get("t"))
        if prev and now_id and now_t:
            prev_id, prev_t = prev
            gap_h = (now_t - prev_t).total_seconds() / 3600
            if prev_id and 0.5 <= gap_h <= 3 and now_id >= prev_id:
                p["hn_items_per_hour"] = round((now_id - prev_id) / gap_h)
        if now_id and now_t:
            prev = (now_id, now_t)
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
    add_hn_rate(points)

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

    with open(os.path.join(OUT_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at_utc": now.isoformat(timespec="seconds"),
                   "coverage": coverage,
                   "latest": points[-1],
                   "changes": build_changes(points)},
                  f, ensure_ascii=False, indent=1)

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
