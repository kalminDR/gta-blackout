# STATE — Grand Theft Attention

Generated **2026-09-06 11:24 UTC** by `state.py`, from the repository itself. Nothing here is written from memory. If it disagrees with any other document, this file is right and the other document is stale.

## Where we are

- **10 sources working**, 0 failing, 2 waiting on a key
- **1 planned sources have no code at all**: chicago
- **108 snapshots** over 98.0 hours (4.1 days); last one 0.2 h ago

## Sources

Newest snapshot: `data/2026-09-06/1114.json`

| Source | State | What it says | Secrets |
|---|---|---|---|
| `twitch` | 🟢 OK | 5 fields | `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET` |
| `steam` | 🟢 OK | 8 fields | `STEAM_API_KEY` |
| `hackernews` | 🟢 OK | 2 fields | — |
| `youtube` | 🟢 OK | 3 fields | `YOUTUBE_API_KEY`, `YOUTUBE_VIDEO_IDS` |
| `traffic` | 🟢 OK | 6 fields | `TOMTOM_API_KEY` |
| `console_status` | 🟢 OK | 2 fields | — |
| `steam_charts` | 🟢 OK | 2 fields | — |
| `console_prices` | 🟢 OK | 3 fields | `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` |
| `retail_stock` | 🟡 WAITING | skipped: no BESTBUY_API_KEY | `BESTBUY_API_KEY` |
| `entsoe` | 🟢 OK | 9 fields | `ENTSOE_TOKEN` |
| `polymarket` | 🟢 OK | 3 fields | — |
| `selfreport` | 🟡 WAITING | skipped: no SELFREPORT_URL | `SELFREPORT_URL` |

## Planned but not built

- **`mta`** — Did people commute: New York transit (backfill, daily) — referenced in backfill.py but not registered as a source
- **`chicago`** — Did people commute: a second, independent transit system — **no code anywhere in the repo**
- **`wikipedia`** — Attention: edits and pageviews, six languages — referenced in backfill.py but not registered as a source

Deliberately abandoned: **reddit** (API closed, November 2025); **github** (Bot activity dominates; issue comments fell ~98%); **stackoverflow** (Volume collapsed to ~1% of 2023 by August 2026); **yahoo_finance** (Runner IPs blocked); **bestbuy** (Requires a US phone number); **gdelt** (Runner IPs rate-limited; manual browser fetch instead)

## Collection

- First: `2026-09-02 09:14 UTC` · Last: `2026-09-06 11:14 UTC`
- 108 of ~98 expected hourly readings
- **1 gaps over two hours:**
  - 3.1 h, 2026-09-03 02:19 → 05:27 UTC

## Metrics needing attention

A metric that never errors but never moves is the dangerous kind: it reads as data and is not.

| | Metric | Readings | Problem |
|---|---|---|---|
| 🔴 | `bestbuy_*` (6 metrics) | 0/108 | never returned a number — source not authenticating |
| 🔴 | `baseline_quality` | 0/108 | never returned a number |
| 🔴 | `deviations` | 0/108 | never returned a number |
| 🔴 | `power_gb_lag_hours` | 0/108 | never returned a number |
| 🔴 | `power_gb_load_mw` | 0/108 | never returned a number |
| 🔴 | `psn_incidents` | 101/108 | frozen at 1 for all 101 readings |
| 🔴 | `steam_rank_gta5_enh` | 102/108 | frozen at 20 for all 102 readings |
| 🔴 | `traffic_budapest_delay_pct` | 103/108 | zero in 60 of 103 readings |
| 🔴 | `traffic_london_delay_pct` | 96/108 | zero in 79 of 96 readings |
| 🔴 | `traffic_losangeles_points_rejected` | 93/108 | frozen at 3 for all 93 readings |
| 🔴 | `traffic_newyork_delay_pct` | 96/108 | zero in 39 of 96 readings |
| 🔴 | `traffic_newyork_points_rejected` | 99/108 | frozen at 1 for all 99 readings |
| 🔴 | `traffic_warsaw_delay_pct` | 96/108 | zero in 47 of 96 readings |
| 🔴 | `xbox_service_issues` | 101/108 | zero in 99 of 101 readings |
| 🔴 | `yt_rockstar_views_per_hour` | 92/108 | zero in 87 of 92 readings |
| 🔴 | `yt_subscribers` | 104/108 | frozen at 1.37e+07 for all 104 readings |
| 🔴 | `yt_subscribers_per_hour` | 92/108 | frozen at 0 for all 92 readings; zero in 92 of 92 readings |
| 🟠 | `traffic_berlin_points_rejected` | 6/108 | missing 97 of 103 since it started |
| 🟠 | `traffic_losangeles_delay_pct` | 9/108 | missing 94 of 103 since it started |
| 🟠 | `traffic_losangeles_seconds_measured` | 9/108 | missing 94 of 103 since it started |
| 🟠 | `traffic_losangeles_travel_index` | 9/108 | missing 94 of 103 since it started |
| 🟠 | `yt_QdBZY2fkU-0_likes_per_hour` | 73/108 | missing 26 of 99 since it started |
| 🟠 | `yt_VQRLujxTm3c_likes_per_hour` | 47/108 | missing 16 of 63 since it started |

## Indices

| Panel | Value |
|---|---|
| attention | **null** |
| displacement | **null** |
| work | **null** |
| infrastructure | **null** |

Baseline needs 6 samples per hour-of-week bucket. **1 of 168 buckets qualify** (97 seen at all). Nulls here are correct behaviour, not a bug: the page refuses to print a number it cannot support.

## Historical backfill

| File | Rows | From | To |
|---|---|---|---|
| `entsoe_load.json` |  |  |  |
| `gdelt_geography.json` |  |  |  |
| `mta_ridership.json` | 10600 | 2023-01-01 | 2026-09-03 |
| `stackexchange.json` |  |  |  |
| `wikipedia.json` |  |  |  |
| `wikipedia_pageviews.json` |  |  |  |

## Front end

- 40 element ids in the HTML, 27 referenced by script
- Reads the current `indices` shape: yes
- No orphaned ids

---

Regenerate with `python3 state.py`. Edit `PLANNED` when a source is decided on, not when it is finished — the gap between intent and code is the most useful thing this file reports.
