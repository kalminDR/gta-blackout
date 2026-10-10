# STATE — Grand Theft Attention

Generated **2026-10-10 16:07 UTC** by `state.py`, from the repository itself. Nothing here is written from memory. If it disagrees with any other document, this file is right and the other document is stale.

## Where we are

- **10 sources working**, 0 failing, 2 waiting on a key
- **0 planned sources have no code at all**
- **668 snapshots** over 918.9 hours (38.3 days); last one 0.0 h ago

## Sources

Newest snapshot: `data/2026-10-10/1606.json`

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

- First: `2026-09-02 09:14 UTC` · Last: `2026-10-10 16:06 UTC`
- 668 of ~919 expected hourly readings
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
| 🔴 | `bestbuy_*` (6 metrics) | 0/668 | never returned a number — source not authenticating |
| 🔴 | `power_*` (3 metrics) | 0/668 | never returned a number — source not authenticating |
| 🔴 | `power_pl_load_mw` | 493/668 | zero in 10 of 24 readings |
| 🔴 | `steam_rank_gta5` | 657/668 | frozen at 10 for all 24 readings |
| 🔴 | `yt_rockstar_views_per_hour` | 584/668 | zero in 21 of 24 readings |
| 🟠 | `yt_EiQEBYDox_k_likes_per_hour` | 462/668 | missing 7 of 24 since it started |

## Indices

| Panel | Value |
|---|---|
| attention | **null** |
| displacement | **null** |
| work | **null** |
| infrastructure | **null** |

Baseline needs 6 samples per hour-of-week bucket. **6 of 168 buckets qualify** (168 seen at all). Nulls here are correct behaviour, not a bug: the page refuses to print a number it cannot support.

## Historical backfill

| File | Readings | From | To | Size |
|---|---|---|---|---|
| `chicago_ridership.json` | 1,308 | 2023-01-01 | 2026-07-31 | 130 KB |
| `entsoe_load.json` | 70,825 in 8 series | 2022-10-01 | 2026-10-08 | 2621 KB |
| `gdelt_geography.json` | 2,340 in 30 series | 2026-07-13 | 2026-10-10 | 83 KB |
| `mta_ridership.json` | 10,917 | 2023-01-01 | 2026-10-08 | 567 KB |
| `shares.json` | 218 in 2 series | 2026-05-06 | 2026-10-09 | 12 KB |
| `stackexchange.json` | 210 in 2 series | 2023-01-01 | 2026-10-09 | 10 KB |
| `wikipedia.json` | 8,214 in 6 series | 2023-01-01 | 2026-09-30 | 290 KB |
| `wikipedia_pageviews.json` | 8,802 in 7 series | 2023-01-01 | 2026-10-09 | 276 KB |

## Front end

- 44 element ids in the HTML, 30 referenced by script
- Reads the current `indices` shape: yes
- No orphaned ids

---

Regenerate with `python3 state.py`. Edit `PLANNED` when a source is decided on, not when it is finished — the gap between intent and code is the most useful thing this file reports.
