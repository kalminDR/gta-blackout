# STATE — Grand Theft Attention

Generated **2026-09-06 12:51 UTC** by `state.py`, from the repository itself. Nothing here is written from memory. If it disagrees with any other document, this file is right and the other document is stale.

## Where we are

- **10 sources working**, 0 failing, 2 waiting on a key
- **1 planned sources have no code at all**: chicago
- **109 snapshots** over 99.1 hours (4.1 days); last one 0.5 h ago

## Sources

Newest snapshot: `data/2026-09-06/1219.json`

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

- **`mta`** — Did people commute: New York transit (backfill, daily) — referenced in backfill.py, test_predictions.py but not registered as a source
- **`chicago`** — Did people commute: a second, independent transit system — **no code anywhere in the repo**
- **`wikipedia`** — Attention: edits and pageviews, six languages — referenced in backfill.py but not registered as a source

Deliberately abandoned: **reddit** (API closed, November 2025); **github** (Bot activity dominates; issue comments fell ~98%); **stackoverflow** (Volume collapsed to ~1% of 2023 by August 2026); **yahoo_finance** (Runner IPs blocked); **bestbuy** (Requires a US phone number); **gdelt** (Runner IPs rate-limited; manual browser fetch instead)

## Collection

- First: `2026-09-02 09:14 UTC` · Last: `2026-09-06 12:19 UTC`
- 109 of ~100 expected hourly readings
- **1 gaps over two hours:**
  - 3.1 h, 2026-09-03 02:19 → 05:27 UTC

## Metrics needing attention

A metric that never errors but never moves is the dangerous kind: it reads as data and is not. Judged on the last 24 readings — one full daily cycle — not on the whole history, so a fault that has since been repaired does not keep raising its hand.

| | Metric | Readings | Problem |
|---|---|---|---|
| 🔴 | `bestbuy_*` (6 metrics) | 0/109 | never returned a number — source not authenticating |
| 🔴 | `baseline_quality` | 0/109 | never returned a number |
| 🔴 | `deviations` | 0/109 | never returned a number |
| 🔴 | `polymarket_market_count` | 69/109 | frozen at 6 for all 24 readings |
| 🔴 | `power_gb_lag_hours` | 0/109 | never returned a number |
| 🔴 | `power_gb_load_mw` | 0/109 | never returned a number |
| 🔴 | `steam_rank_gta5_enh` | 103/109 | frozen at 20 for all 24 readings |
| 🔴 | `traffic_budapest_delay_pct` | 104/109 | zero in 16 of 24 readings |
| 🔴 | `traffic_london_delay_pct` | 97/109 | zero in 17 of 24 readings |
| 🔴 | `traffic_newyork_delay_pct` | 97/109 | zero in 10 of 24 readings |
| 🔴 | `traffic_warsaw_delay_pct` | 97/109 | zero in 10 of 24 readings |
| 🔴 | `twitch_gta5` | 106/109 | zero in 16 of 24 readings |
| 🔴 | `yt_rockstar_views_per_hour` | 93/109 | zero in 22 of 24 readings |
| 🔴 | `yt_subscribers` | 105/109 | frozen at 1.37e+07 for all 24 readings |
| 🔴 | `yt_subscribers_per_hour` | 93/109 | frozen at 0 for all 24 readings; zero in 24 of 24 readings |
| 🟠 | `yt_EiQEBYDox_k_likes_per_hour` | 54/109 | missing 10 of 24 since it started |
| 🟠 | `yt_QdBZY2fkU-0_likes_per_hour` | 73/109 | missing 18 of 23 since it started |
| 🟠 | `yt_VQRLujxTm3c_likes_per_hour` | 47/109 | missing 16 of 24 since it started |

**Repaired.** These were failing earlier in the record and are clean across the last 24 readings. Listed so the fix is visible, and so nobody fixes it twice: `traffic_losangeles_delay_pct`, `traffic_losangeles_seconds_measured`, `traffic_losangeles_travel_index`.

## Indices

| Panel | Value |
|---|---|
| attention | **null** |
| displacement | **null** |
| work | **null** |
| infrastructure | **null** |

Baseline needs 6 samples per hour-of-week bucket. **1 of 168 buckets qualify** (98 seen at all). Nulls here are correct behaviour, not a bug: the page refuses to print a number it cannot support.

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
