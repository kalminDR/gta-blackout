# STATE — Grand Theft Attention

Generated **2026-09-05 20:24 UTC** by `state.py`, from the repository itself. Nothing here is written from memory. If it disagrees with any other document, this file is right and the other document is stale.

## Where we are

- **8 sources working**, 1 failing, 2 waiting on a key
- **2 planned sources have no code at all**: entsoe, chicago
- **93 snapshots** over 83.0 hours (3.5 days); last one 0.1 h ago

## Sources

Newest snapshot: `data/2026-09-05/2015.json`

| Source | State | What it says | Secrets |
|---|---|---|---|
| `twitch` | 🟢 OK | 5 fields | `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET` |
| `steam` | 🟢 OK | 8 fields | `STEAM_API_KEY` |
| `hackernews` | 🟢 OK | 2 fields | — |
| `youtube` | 🟢 OK | 3 fields | `YOUTUBE_API_KEY`, `YOUTUBE_VIDEO_IDS` |
| `traffic` | 🟢 OK | 6 fields | `TOMTOM_API_KEY` |
| `console_status` | 🟢 OK | 2 fields | — |
| `steam_charts` | 🟢 OK | 2 fields | — |
| `console_prices` | 🔴 FAILING | auth_error: HTTP 401: {"error":"invalid_client","error_description":"client authentication failed"} | `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` |
| `retail_stock` | 🟡 WAITING | skipped: no BESTBUY_API_KEY | `BESTBUY_API_KEY` |
| `polymarket` | 🟢 OK | 3 fields | — |
| `selfreport` | 🟡 WAITING | skipped: no SELFREPORT_URL | `SELFREPORT_URL` |

## Planned but not built

- **`entsoe`** — Did a country stay in: hourly electricity demand, EU — **no code anywhere in the repo**
- **`mta`** — Did people commute: New York transit (backfill, daily) — referenced in backfill.py but not registered as a source
- **`chicago`** — Did people commute: a second, independent transit system — **no code anywhere in the repo**
- **`wikipedia`** — Attention: edits and pageviews, six languages — referenced in backfill.py but not registered as a source

Deliberately abandoned: **reddit** (API closed, November 2025); **github** (Bot activity dominates; issue comments fell ~98%); **stackoverflow** (Volume collapsed to ~1% of 2023 by August 2026); **yahoo_finance** (Runner IPs blocked); **bestbuy** (Requires a US phone number); **gdelt** (Runner IPs rate-limited; manual browser fetch instead)

## Collection

- First: `2026-09-02 09:14 UTC` · Last: `2026-09-05 20:15 UTC`
- 93 of ~84 expected hourly readings
- **1 gaps over two hours:**
  - 3.1 h, 2026-09-03 02:19 → 05:27 UTC

## Metrics needing attention

A metric that never errors but never moves is the dangerous kind: it reads as data and is not.

| | Metric | Readings | Problem |
|---|---|---|---|
| 🔴 | `bestbuy_*` (6 metrics) | 0/93 | never returned a number — source not authenticating |
| 🔴 | `listings_*` (9 metrics) | 0/93 | never returned a number — source not authenticating |
| 🔴 | `price_*` (9 metrics) | 0/93 | never returned a number — source not authenticating |
| 🔴 | `baseline_quality` | 0/93 | never returned a number |
| 🔴 | `deviations` | 0/93 | never returned a number |
| 🔴 | `psn_incidents` | 86/93 | frozen at 1 for all 86 readings |
| 🔴 | `steam_rank_gta5` | 87/93 | frozen at 7 for all 87 readings |
| 🔴 | `steam_rank_gta5_enh` | 87/93 | frozen at 20 for all 87 readings |
| 🔴 | `traffic_budapest_delay_pct` | 88/93 | zero in 48 of 88 readings |
| 🔴 | `xbox_service_issues` | 86/93 | zero in 84 of 86 readings |
| 🔴 | `yt_rockstar_views_per_hour` | 77/93 | zero in 73 of 77 readings |
| 🔴 | `yt_subscribers` | 89/93 | frozen at 1.37e+07 for all 89 readings |
| 🔴 | `yt_subscribers_per_hour` | 77/93 | frozen at 0 for all 77 readings; zero in 77 of 77 readings |

## Indices

| Panel | Value |
|---|---|
| attention | **null** |
| displacement | **null** |
| work | **null** |
| infrastructure | **null** |

Baseline needs 6 samples per hour-of-week bucket. **1 of 168 buckets qualify** (82 seen at all). Nulls here are correct behaviour, not a bug: the page refuses to print a number it cannot support.

## Historical backfill

| File | Rows | From | To |
|---|---|---|---|
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
