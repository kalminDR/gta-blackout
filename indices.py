#!/usr/bin/env python3
"""
Grand Theft Attention - index computation.

summarise.py turns raw snapshots into a flat row of numbers per hour.
This module turns those rows into indices.

Four separate panels, never merged into one number:

    attention       how much attention GTA VI itself pulls
    displacement    what people stop doing instead
    work            work-related and everyday activity
    infrastructure  technical side effects

Merging them would be a category error: a 40% rise in Twitch viewers and a
6% fall in traffic are not two observations of the same variable. Worse,
mixing them can cancel out a real effect - which is exactly what would have
happened with Steam sitting in the attention index with a positive sign.

How one metric becomes a number
-------------------------------
    d = log2( (value + eps) / (baseline + eps) ) * direction

Log ratio because it is symmetric: +1 means double, -1 means half, 0 means
normal. A raw difference is not symmetric and a raw ratio is not either.

direction is +1 where a rise means "GTA effect" and -1 where a fall does.
After this alignment every component means the same thing: positive is more
GTA. This is the fix for the Steam sign error.

    panel = median(d of its components)

Median rather than geometric mean, because one API returning nonsense should
not drag the whole panel. With two components a median is the mean, so this
only starts to matter as sources are added - which they are.

    displayed = 100 * 2 ** panel

So 100 is a normal hour, 200 is double, 50 is half.

Baselines
---------
Every value is compared to the same hour of the same weekday, because the
daily and weekly cycle is far larger than any launch effect will be. The
baseline is the median of those matching hours, excluding the point itself.

Traffic is matched in the city's own local time. 08:00 in Budapest and
08:00 in Los Angeles are both a rush hour; 08:00 UTC is a rush hour in one
of them and the middle of the night in the other.

If there are not enough matching weekday-hours, it falls back to the same
hour of day on any day. If that also fails, the metric is left empty. It
never invents a number.
"""

import math
from datetime import datetime, timezone
from statistics import median

try:
    from zoneinfo import ZoneInfo
    HAVE_TZ = True
except ImportError:                                   # pragma: no cover
    HAVE_TZ = False

# Minimum matching observations before a baseline is trusted.
#
# Two was enough for a technical preview but not for a published claim: the
# median of two points is just their mean, so one odd day moves it. By
# November each weekday-hour will have eight or more observations.
MIN_SAMPLES_HOUR_OF_WEEK = 6
# The fallback pools a whole day type, so it is a coarser match and asks for
# more observations before it is trusted. Weekends only supply two days a
# week, so this is five weeks of history before a weekend hour can be scored.
MIN_SAMPLES_HOUR_OF_DAY = 10

# Kept small relative to the smallest real value, so it only matters when a
# metric legitimately hits zero (no GTA VI streams before launch).
EPS = 1.0

# effect: which way a panel moves when GTA VI is having an effect.
#
# Inside a panel every component is aligned so they cannot cancel out. Across
# panels the display follows plain reading instead. An attention index of 200
# means twice the attention; a work index of 94 means activity six percent
# below normal. Flipping work to "higher = more effect" would be internally
# consistent and completely unreadable in a headline.
PANELS = {
    "attention": {"name": "Attention", "effect": +1},
    "displacement": {"name": "Displacement", "effect": +1},
    "work": {"name": "Work & Mobility", "effect": -1},
    "infrastructure": {"name": "Infrastructure", "effect": +1},
}

PANEL_NAMES = {k: v["name"] for k, v in PANELS.items()}


class Metric:
    """One measured quantity and how it enters a panel.

    direction: +1 if a rise means more GTA effect, -1 if a fall does.
    primary:   False keeps it computed and published but out of the panel
               median. Used for signals that are interesting but too noisy
               to carry a headline.
    tz:        which clock its daily cycle follows.
    """

    def __init__(self, key, panel, direction, label,
                 primary=True, tz="UTC", evidence="measured"):
        self.key = key
        self.panel = panel
        self.direction = direction
        self.label = label
        self.primary = primary
        self.tz = tz
        self.evidence = evidence


# The Steam basket, one entry per game. Each game is normalised against its
# own baseline before anything is aggregated - otherwise Counter-Strike 2 and
# Dota 2, with roughly a million players between them, decide the number on
# their own and the smaller titles never register.
STEAM_GAMES = [
    ("steam_cs2", "Counter-Strike 2"),
    ("steam_dota2", "Dota 2"),
    ("steam_pubg", "PUBG"),
    ("steam_apex", "Apex Legends"),
    ("steam_bg3", "Baldur's Gate 3"),
    ("steam_rdr2", "Red Dead Redemption 2"),
    ("steam_gta5", "Grand Theft Auto V"),
    ("steam_gta5_enhanced", "GTA V Enhanced"),
]

CITY_TZ = {
    "traffic_budapest": "Europe/Budapest",
    "traffic_london": "Europe/London",
    "traffic_berlin": "Europe/Berlin",
    "traffic_warsaw": "Europe/Warsaw",
    "traffic_newyork": "America/New_York",
    "traffic_losangeles": "America/Los_Angeles",
}


def build_metrics():
    m = []

    # --- Attention: GTA VI itself.
    m.append(Metric("twitch_gta6_viewers", "attention", +1,
                    "GTA VI viewers on Twitch"))
    m.append(Metric("twitch_gta6_channels", "attention", +1,
                    "GTA VI live channels"))
    m.append(Metric("yt_trailer_views_per_hour", "attention", +1,
                    "Trailer views per hour"))
    m.append(Metric("yt_rockstar_views_per_hour", "attention", +1,
                    "Rockstar channel views per hour", primary=False))

    # --- Displacement: what deflates. Sign flipped: a fall is the effect.
    for key, label in STEAM_GAMES:
        m.append(Metric(key, "displacement", -1, label))
    m.append(Metric("twitch_other_viewers", "displacement", -1,
                    "Twitch viewers outside GTA"))

    # --- Work & mobility, each city on its own clock.
    for key, tz in CITY_TZ.items():
        m.append(Metric(f"{key}_travel_index", "work", +1,
                        key.replace("traffic_", "").title() + " road load",
                        tz=tz))
    # Hacker News is demoted to secondary. A quiet hour on HN can mean people
    # are playing, or that no interesting story broke, or a US holiday, or
    # that everyone is busy arguing about GTA - which would push it up, not
    # down. Worth publishing, not worth carrying a headline.
    m.append(Metric("hn_items_per_hour", "work", +1,
                    "Hacker News items per hour", primary=False))

    # --- Infrastructure.
    m.append(Metric("psn_incidents", "infrastructure", +1,
                    "PlayStation Network incidents"))
    m.append(Metric("xbox_service_issues", "infrastructure", +1,
                    "Xbox service issues"))

    return m


METRICS = build_metrics()


# ------------------------------------------------------------- time keys

_TZ_CACHE = {}


def _zone(name):
    if name == "UTC" or not HAVE_TZ:
        return timezone.utc
    if name not in _TZ_CACHE:
        try:
            _TZ_CACHE[name] = ZoneInfo(name)
        except Exception:
            # No tzdata on this machine. Fall back to UTC rather than
            # crashing, and say so in the output.
            _TZ_CACHE[name] = timezone.utc
    return _TZ_CACHE[name]


def parse_time(text):
    if not text:
        return None
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None


def hour_keys(t, tz_name):
    """(weekday-hour, daytype-hour) in the metric's own timezone.

    The second key is the fallback used when a weekday-hour has too few
    observations. It deliberately keeps weekdays and weekends apart: a plain
    hour-of-day fallback pools Sunday 14:00 with Wednesday 14:00, and on a
    series with a normal weekend bulge that alone reported a 40% effect on
    quiet Sundays. A fallback that invents an effect is worse than none.
    """
    local = t.astimezone(_zone(tz_name))
    weekend = local.weekday() >= 5
    return (local.weekday() * 24 + local.hour, (int(weekend), local.hour))


# --------------------------------------------------------- baseline work

def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _local_day(t, tz):
    """The calendar date on the metric's own clock."""
    try:
        return t.astimezone(_zone(tz or "UTC")).date().isoformat()
    except Exception:
        return t.date().isoformat()


def collect_observations(points, metric):
    """Every usable (time, value) pair for one metric, with its hour keys."""
    obs = []
    for p in points:
        t = parse_time(p.get("t"))
        v = _num(p.get(metric.key))
        if t is None or v is None:
            continue
        how, hod = hour_keys(t, metric.tz)
        # The local date is part of the key so a baseline can require
        # distinct days rather than distinct readings.
        obs.append({"t": t, "v": v, "how": how, "hod": hod,
                    "day": _local_day(t, metric.tz)})
    return obs


def baseline_for(obs, target, exclude_self=True):
    """Median of comparable past-and-present hours.

    Returns (value, quality). Quality is 'hour_of_week', 'hour_of_day' or
    None, and is published so a reader can see which one was used rather
    than having to trust that a baseline existed at all.

    The point being scored is excluded from its own baseline. Without that,
    a single extreme hour partly normalises itself away and the effect looks
    smaller than it is.
    """
    def by_day(matching):
        """One value per calendar day, so a burst of readings in a single
        hour cannot masquerade as a baseline.

        This mattered in practice: on 2 September the collector was run
        seven times inside forty-four minutes while it was being set up,
        which cleared a six-sample threshold on its own and produced index
        values that were really comparing that morning with itself.
        """
        days = {}
        for o in matching:
            days.setdefault(o["day"], []).append(o["v"])
        return [median(v) for v in days.values()]

    same_week = by_day([o for o in obs
                        if o["how"] == target["how"]
                        and not (exclude_self and o["t"] == target["t"])])
    if len(same_week) >= MIN_SAMPLES_HOUR_OF_WEEK:
        return median(same_week), "hour_of_week"

    same_hour = by_day([o for o in obs
                        if o["hod"] == target["hod"]
                        and not (exclude_self and o["t"] == target["t"])])
    if len(same_hour) >= MIN_SAMPLES_HOUR_OF_DAY:
        return median(same_hour), "hour_of_day"

    return None, None


def log_deviation(value, baseline, direction):
    """Aligned log2 ratio. Positive always means 'more GTA effect'."""
    if baseline is None or baseline + EPS <= 0:
        return None
    return direction * math.log2((value + EPS) / (baseline + EPS))


# ------------------------------------------------------------ the panels

def compute(points):
    """Attach per-metric deviations and per-panel indices to every point.

    Every point is scored against the whole series, not only against what
    came before it. The baselines are recomputed from raw data on every run
    anyway, so a September hour gets the benefit of October's observations.
    """
    obs_by_metric = {m.key: collect_observations(points, m) for m in METRICS}

    # A metric that never moves is not evidence of calm, it is a broken or
    # cached feed. Left in, it would contribute a permanent zero deviation
    # and drag every panel towards 100. Excluded, and named in the output so
    # the omission is visible rather than silent.
    frozen = {key for key, obs in obs_by_metric.items()
              if len(obs) >= 6 and len({o["v"] for o in obs}) == 1}
    by_time = {}
    for m in METRICS:
        for o in obs_by_metric[m.key]:
            by_time.setdefault(o["t"], {})[m.key] = o

    compute.frozen_metrics = sorted(frozen)

    for p in points:
        t = parse_time(p.get("t"))
        if t is None:
            continue
        deviations, quality = {}, {}

        for m in METRICS:
            if m.key in frozen:
                continue
            target = by_time.get(t, {}).get(m.key)
            if target is None:
                continue
            base, qual = baseline_for(obs_by_metric[m.key], target)
            d = log_deviation(target["v"], base, m.direction)
            if d is None:
                continue
            deviations[m.key] = round(d, 4)
            quality[m.key] = qual

        p["deviations"] = deviations or None
        p["baseline_quality"] = quality or None

        indices = {}
        for panel in PANEL_NAMES:
            members = [deviations[m.key] for m in METRICS
                       if m.panel == panel and m.primary and m.key in deviations]
            if not members:
                indices[panel] = None
                continue
            indices[panel] = {
                "index": round(100 * (2 ** median(members))),
                "log2": round(median(members), 4),
                "components": len(members),
                "components_expected": sum(
                    1 for m in METRICS if m.panel == panel and m.primary),
            }
        p["indices"] = indices

    return points


# ---------------------------------------------------------- placebo test

def placebo(points, panel, weekday=3, window_hours=(0, 24)):
    """Run the same measurement on every earlier Thursday.

    This is the difference between "the index hit 180" and "the index was
    higher than on 99% of comparable Thursdays". Without it there is no way
    to tell an effect from a noisy day, and a single number invites exactly
    the criticism the project exists to avoid.

    Returns one entry per matching day with its own daily index, so the
    launch day can be given a percentile against its own history.
    """
    days = {}
    for p in points:
        t = parse_time(p.get("t"))
        if t is None or t.weekday() != weekday:
            continue
        if not (window_hours[0] <= t.hour < window_hours[1]):
            continue
        entry = (p.get("indices") or {}).get(panel)
        if not entry:
            continue
        days.setdefault(t.date().isoformat(), []).append(entry["log2"])

    out = []
    for day, values in sorted(days.items()):
        extreme = max(values) if PANELS[panel]["effect"] > 0 else min(values)
        out.append({
            "date": day,
            # Typical hour of that day: catches a sustained shift.
            "index": round(100 * (2 ** median(values))),
            # Most extreme hour of that day: catches a launch-night spike,
            # which a 24-hour median swallows completely.
            "peak": round(100 * (2 ** extreme)),
            "hours": len(values),
        })
    return out


def percentile_of(value, others, effect=+1):
    """How extreme this value is, in the direction that counts as an effect.

    For attention that is the top tail; for work it is the bottom one. A work
    index in the 99th percentile of *high* values would be the opposite of
    the finding. None when there is nothing to compare against yet, which is
    the honest answer in September.
    """
    if not others:
        return None
    beaten = sum(1 for o in others if (o < value if effect > 0 else o > value))
    return round(100 * beaten / len(others), 1)


def summary(points):
    """Headline block for the site: index, coverage and placebo context."""
    if not points:
        return {}
    latest = points[-1]
    out = {"panels": {}}

    for panel, cfg in PANELS.items():
        entry = (latest.get("indices") or {}).get(panel)
        history = placebo(points, panel)
        past = [h["peak"] for h in history[:-1]]
        today = history[-1]["peak"] if history else None

        out["panels"][panel] = {
            "name": cfg["name"],
            "effect_direction": ("higher = more effect" if cfg["effect"] > 0
                                 else "lower = more effect"),
            "index": entry["index"] if entry else None,
            "sources_available": entry["components"] if entry else 0,
            "sources_expected": (entry["components_expected"] if entry else
                                 sum(1 for m in METRICS
                                     if m.panel == panel and m.primary)),
            "placebo_thursdays": len(past),
            "placebo_peak_today": today,
            "placebo_percentile": (
                percentile_of(today, past, cfg["effect"])
                if today is not None and past else None),
            "evidence": "measured",
        }

    out["metrics"] = [{
        "key": m.key,
        "label": m.label,
        "panel": m.panel,
        "direction": "rise = GTA effect" if m.direction > 0 else "fall = GTA effect",
        "primary": m.primary,
        "timezone": m.tz,
        "evidence": m.evidence,
        "value": latest.get(m.key),
        "deviation_log2": (latest.get("deviations") or {}).get(m.key),
        "baseline_quality": (latest.get("baseline_quality") or {}).get(m.key),
    } for m in METRICS]

    out["frozen_metrics"] = getattr(compute, "frozen_metrics", [])
    out["baseline_rules"] = {
        "min_samples_hour_of_week": MIN_SAMPLES_HOUR_OF_WEEK,
        "min_samples_hour_of_day": MIN_SAMPLES_HOUR_OF_DAY,
        "timezone_support": HAVE_TZ,
    }
    return out
