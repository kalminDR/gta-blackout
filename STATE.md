# STATE — Grand Theft Attention

Generated **2026-09-06 21:17 UTC** by `state.py`, from the repository itself. Nothing here is written from memory. If it disagrees with any other document, this file is right and the other document is stale.

## Where we are

- **10 sources working**, 0 failing, 2 waiting on a key
- **1 planned sources have no code at all**: chicago
- **118 snapshots** over 108.0 hours (4.5 days); last one 0.1 h ago

## Sources

Newest snapshot: `data/2026-09-06/2114.json`

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

- **`mta`** — Did people commute: New York transit (backfill, daily) — referenced in backfill.py, score.py, summarise.py, test_predictions.py, test_score.py but not registered as a source
- **`chicago`** — Did people commute: a second, independent transit system — **no code anywhere in the repo**
- **`wikipedia`** — Attention: edits and pageviews, six languages — referenced in backfill.py but not registered as a source

Deliberately abandoned: **reddit** (API closed, November 2025); **github** (Bot activity dominates; issue comments fell ~98%); **stackoverflow** (Volume collapsed to ~1% of 2023 by August 2026); **yahoo_finance** (Runner IPs blocked); **bestbuy** (Requires a US phone number); **gdelt** (Runner IPs rate-limited; manual browser fetch instead)

## Collection

- First: `2026-09-02 09:14 UTC` · Last: `2026-09-06 21:14 UTC`
- 118 of ~108 expected hourly readings
- **1 gaps over two hours:**
  - 3.1 h, 2026-09-03 02:19 → 05:27 UTC

## Metrics needing attention

A metric that never errors but never moves is the dangerous kind: it reads as data and is not. Judged on the last 24 readings — one full daily cycle — not on the whole history, so a fault that has since been repaired does not keep raising its hand.

| | Metric | Readings | Problem |
|---|---|---|---|
| 🔴 | `bestbuy_*` (6 metrics) | 0/118 | never returned a number — source not authenticating |
| 🔴 | `power_*` (3 metrics) | 0/118 | never returned a number — source not authenticating |
| 🔴 | `baseline_quality` | 0/118 | never returned a number |
| 🔴 | `deviations` | 0/118 | never returned a number |
| 🔴 | `polymarket_market_count` | 78/118 | frozen at 6 for all 24 readings |
| 🔴 | `steam_rank_gta5_enh` | 112/118 | frozen at 20 for all 24 readings |
| 🔴 | `traffic_budapest_delay_pct` | 113/118 | zero in 13 of 24 readings |
| 🔴 | `traffic_london_delay_pct` | 106/118 | zero in 14 of 24 readings |
| 🔴 | `traffic_newyork_delay_pct` | 106/118 | zero in 11 of 24 readings |
| 🔴 | `traffic_warsaw_delay_pct` | 106/118 | zero in 14 of 24 readings |
| 🔴 | `twitch_gta5` | 115/118 | zero in 17 of 24 readings |
| 🔴 | `yt_QdBZY2fkU-0_likes_per_hour` | 73/118 | never returned a number |
| 🔴 | `yt_rockstar_views_per_hour` | 102/118 | zero in 22 of 24 readings |
| 🔴 | `yt_subscribers` | 114/118 | frozen at 1.37e+07 for all 24 readings |
| 🔴 | `yt_subscribers_per_hour` | 102/118 | frozen at 0 for all 24 readings; zero in 24 of 24 readings |
| 🟠 | `yt_EiQEBYDox_k_likes_per_hour` | 60/118 | missing 11 of 23 since it started |
| 🟠 | `yt_VQRLujxTm3c_likes_per_hour` | 50/118 | missing 3 of 6 since it started |

**Repaired.** These were failing earlier in the record and are clean across the last 24 readings. Listed so the fix is visible, and so nobody fixes it twice: `traffic_losangeles_delay_pct`, `traffic_losangeles_seconds_measured`, `traffic_losangeles_travel_index`.

## Indices

| Panel | Value |
|---|---|
| attention | **null** |
| displacement | **null** |
| work | **null** |
| infrastructure | **null** |

Baseline needs 6 samples per hour-of-week bucket. **1 of 168 buckets qualify** (107 seen at all). Nulls here are correct behaviour, not a bug: the page refuses to print a number it cannot support.

## Historical backfill

| File | Readings | From | To | Size |
|---|---|---|---|---|
| `entsoe_load.json` | 64,297 in 8 series | 2022-10-01 | 2026-09-04 | 2380 KB |
| `gdelt_geography.json` | 86 | 2026-06-09 | 2026-09-06 | 4 KB |
| `mta_ridership.json` | 10,600 | 2023-01-01 | 2026-09-03 | 550 KB |
| `stackexchange.json` | 176 in 2 series | 2023-01-01 | 2026-09-05 | 9 KB |
| `wikipedia.json` | 8,034 in 6 series | 2023-01-01 | 2026-08-31 | 284 KB |
| `wikipedia_pageviews.json` | 8,564 in 7 series | 2023-01-01 | 2026-09-05 | 268 KB |

## Front end

- 44 element ids in the HTML, 30 referenced by script
- Reads the current `indices` shape: yes
- No orphaned ids

---

Regenerate with `python3 state.py`. Edit `PLANNED` when a source is decided on, not when it is finished — the gap between intent and code is the most useful thing this file reports.
