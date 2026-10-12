# STATE — Grand Theft Attention

Generated **2026-10-12 21:08 UTC** by `state.py`, from the repository itself. Nothing here is written from memory. If it disagrees with any other document, this file is right and the other document is stale.

## Where we are

- **10 sources working**, 0 failing, 2 waiting on a key
- **0 planned sources have no code at all**
- **721 snapshots** over 971.9 hours (40.5 days); last one 0.0 h ago

## Sources

Newest snapshot: `data/2026-10-12/2106.json`

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

- **`mta`** — Did people commute: New York transit (backfill, daily) — referenced in backfill.py, score.py, summarise.py, test_backfill.py, test_chicago.py, test_predictions.py, test_score.py but not registered as a source
- **`chicago`** — Did people commute: a second, independent transit system — referenced in backfill.py, test_chicago.py but not registered as a source
- **`wikipedia`** — Attention: edits and pageviews, six languages — referenced in backfill.py but not registered as a source

Deliberately abandoned: **reddit** (API closed, November 2025); **github** (Bot activity dominates; issue comments fell ~98%); **stackoverflow** (Volume collapsed to ~1% of 2023 by August 2026); **yahoo_finance** (Runner IPs blocked); **bestbuy** (Requires a US phone number); **gdelt** (Runner IPs rate-limited; manual browser fetch instead)

## Collection

- First: `2026-09-02 09:14 UTC` · Last: `2026-10-12 21:06 UTC`
- 721 of ~972 expected hourly readings
- **77 gaps over two hours:**
  - 3.1 h, 2026-09-03 02:19 → 05:27 UTC
  - 4.1 h, 2026-09-13 13:14 → 17:21 UTC
  - 3.2 h, 2026-09-13 17:21 → 20:36 UTC
  - 2.4 h, 2026-09-13 20:36 → 23:03 UTC
  - 5.4 h, 2026-09-13 23:03 → 04:29 UTC
  - 6.0 h, 2026-09-14 04:29 → 10:29 UTC

## Metrics needing attention

A metric that never errors but never moves is the dangerous kind: it reads as data and is not. Judged on the last 24 readings — one full daily cycle — not on the whole history, so a fault that has since been repaired does not keep raising its hand.

| | Metric | Readings | Problem |
|---|---|---|---|
| 🔴 | `bestbuy_*` (6 metrics) | 0/721 | never returned a number — source not authenticating |
| 🔴 | `power_*` (3 metrics) | 0/721 | never returned a number — source not authenticating |
| 🔴 | `polymarket_total_volume` | 680/721 | frozen at 4.1224e+06 for all 24 readings |
| 🔴 | `price_de_ps5_pro` | 617/721 | frozen at 1034.82 for all 24 readings |
| 🔴 | `steam_rank_gta5` | 710/721 | frozen at 10 for all 24 readings |
| 🔴 | `steam_rank_gta5_enh` | 710/721 | frozen at 29 for all 24 readings |
| 🔴 | `yt_rockstar_views_per_hour` | 637/721 | zero in 23 of 24 readings |

## Indices

| Panel | Value |
|---|---|
| attention | **null** |
| displacement | 97.0 (from 9 of 9 components) |
| work | 100.0 (from 6 of 6 components) |
| infrastructure | 100.0 (from 2 of 2 components) |

Baseline needs 6 samples per hour-of-week bucket. **8 of 168 buckets qualify** (168 seen at all). Nulls here are correct behaviour, not a bug: the page refuses to print a number it cannot support.

## Historical backfill

| File | Readings | From | To | Size |
|---|---|---|---|---|
| `chicago_ridership.json` | 1,308 | 2023-01-01 | 2026-07-31 | 130 KB |
| `entsoe_load.json` | 71,209 in 8 series | 2022-10-01 | 2026-10-10 | 2636 KB |
| `gdelt_geography.json` | 76 | 2026-07-15 | 2026-10-10 | 3 KB |
| `mta_ridership.json` | 10,917 | 2023-01-01 | 2026-10-08 | 567 KB |
| `shares.json` | 218 in 2 series | 2026-05-06 | 2026-10-09 | 12 KB |
| `stackexchange.json` | 212 in 2 series | 2023-01-01 | 2026-10-11 | 10 KB |
| `wikipedia.json` | 8,214 in 6 series | 2023-01-01 | 2026-09-30 | 290 KB |
| `wikipedia_pageviews.json` | 8,816 in 7 series | 2023-01-01 | 2026-10-11 | 276 KB |

## Front end

- 44 element ids in the HTML, 30 referenced by script
- Reads the current `indices` shape: yes
- No orphaned ids

---

Regenerate with `python3 state.py`. Edit `PLANNED` when a source is decided on, not when it is finished — the gap between intent and code is the most useful thing this file reports.
