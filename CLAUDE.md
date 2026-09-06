# Grand Theft Attention — working notes

Read this before touching anything. Then run `python3 state.py`, which writes
`STATE.md` from the live code and data.

**Do not read `PROJECT.md`.** It is a hand-written description that drifted away
from reality: it claimed the eBay keys were unset while the collector was
already failing authentication with them, and it listed ENTSO-E as done when no
line of ENTSO-E code existed. It is kept only as history. This file exists
because a document that has to be remembered will always lose to a system that
keeps running — so the split is deliberate: **`state.py` reports what is,
`CLAUDE.md` records why.** Nothing here duplicates what the script can derive.

---

## 1. What this project is

On Thursday 19 November 2026, *Grand Theft Auto VI* goes on sale. The claim, in
the words of the person whose project this is:

> *November 19-én kicsit megáll az élet. Szinte senki nem veszi észre, de a
> számok igen.*
> **On 19 November, life stops for a bit. Almost nobody will notice. The numbers
> will.**

We cannot ask the world whether it is playing. So we count everything else the
modern world already counts about itself, hourly, from before the event until
after it, and see whether a single Thursday looks different from other
Thursdays.

The project belongs to Péter Kalmár, founder of [eureka] (eureka.works), an L&D
consultancy. The commercial point underneath is that one game will generate more
voluntary attention in a day than most corporate training achieves in a year.
That argument is never made explicitly on the site. It is made by the numbers.

**Repository:** github.com/kalminDR/gta-blackout
**Domains:** grandtheftattention.com, attentionheist.com (legal fallback)

---

## 2. How the front end is organised, and why

The site used to be built around the four panels the index engine computes —
Attention, Displacement, Work, Infrastructure. Those are the names of the
machinery. Nobody outside this repository has any reason to care about them.

**It is now organised around six sentences a reader could have said
themselves,** with metrics as witnesses underneath:

| | Claim | Principal witnesses |
|---|---|---|
| 01 | Fewer of us went to work | Six cities' traffic, New York subway |
| 02 | We stayed in | ENTSO-E electricity, evening traffic |
| 03 | Everything else went quiet | Steam top games, Twitch minus GTA |
| 04 | You could not buy a console | eBay resale, three markets |
| 05 | The servers buckled | PSN and Xbox service health |
| 06 | It cost somebody money | Calculator only — never gets a verdict |

The index engine is unchanged and still computes the four panels. Only the way
in is different. **Do not reorganise the front end back around panels.**

### Three markings, and the reason for them

Every number on the page is exactly one of three things, marked visibly:

- **MEASURED** — a machine recorded it, the commit is linkable
- **PREDICTED** — written down in advance, not yet known
- **ESTIMATED** — arithmetic on assumptions, with the assumptions adjustable

This is how the site can be bold in its framing and strict in its numbers at the
same time. The boldness lives in the copy. The rigour lives in the marking.

### Witnesses may speak without a baseline

A deviation needs weeks of history. A price does not. "A second-hand PS5 costs
$525 in America today" is a fact worth printing now, and printing it now is what
makes the November comparison mean anything. Witnesses therefore have two
voices: one for deviation-from-baseline, one for the raw current value. See
`NOW_SAY` in `index.html`.

Related: listing twenty-five witnesses that all say "still building baseline" is
not honesty, it is noise. Silent witnesses collapse into one line.

---

## 3. Working with Péter

He is not a programmer and does not want to become one. He directs, reviews for
accuracy and editorial judgement, and operates the consoles — GitHub, Cloudflare,
GoDaddy, the API portals. Every instruction for those needs to be explicit and
in order.

He is unusually good at catching overconfidence, and has done so repeatedly and
correctly: on GDPR wording, on hardcoded numbers in copy, on visual direction,
and on the assistant drifting into its own interests instead of his. **Take the
correction, fix it, do not get defensive, and do not over-apologise.** Say what
was wrong and move on.

Write to him in English. This was Hungarian until 6 September 2026 and
he changed it; this line is the setting, so change it here rather than
remembering a preference that dies with the session.

### The failure mode to avoid

The single most useful piece of feedback he gave in this project:

> *Az az érzésem, hogy mindig el akarsz térni attól, amit én szeretnék, és
> szeretnél prudens, okos lenni, és beleszerettél ebbe az "attention" dologba.*

The trap is treating the measurement apparatus as the subject. It is not. Nobody
cares about the variance of subway ridership. They care whether fewer people
went to work. Every technical finding must be carried back to one of the six
claims or it does not belong on the site.

---

## 4. Facts about the launch

- **19 November 2026, a Thursday.** PS5 and Xbox Series X|S only. No PC at launch.
- **Preload opens 12 November**, local midnight — a global bandwidth event a
  week early, and a free rehearsal for the site.
- Standard edition $79.99, larger edition $99.99.
- The gameplay "Extended Look" landed 27 August 2026. Two previous delays; as of
  early September the date is holding.

**The budget is not $2 billion, and must never be stated as fact.** Nothing is
confirmed by Rockstar or Take-Two. The most-cited analyst estimate puts
development at roughly $1–1.5bn, and around $2bn including marketing. The
defensible framing is stronger anyway: even at the low end it exceeds the three
biggest blockbusters of the 2010s combined, against about $265m for GTA V.

---

## 5. Things that cost real work to learn

Everything here was established from data in this repository. Do not re-derive,
and do not quietly contradict without new evidence.

### The subway threshold is 3%, not 1.5%

Memory and earlier notes claimed November Thursdays vary under 1%. **False.**
Measured from the backfill, non-holiday November Thursdays:

| Year | Std dev | Largest deviation | 3rd Thursday of Nov |
|---|---|---|---|
| 2023 | 0.93% | 1.51% | −0.82% |
| 2024 | 1.11% | 1.77% | **−1.77%** |
| 2025 | 1.92% | 3.81% | +0.27% |

A 1.5% threshold would have fired in November 2024 with no game involved. Also:
ridership grows about 5% a year (4.06M → 4.25M → 4.50M), so **19 November 2026
must be compared to other 2026 Thursdays, never to 2025.** The workable
prediction pairs a magnitude with a rank condition: lowest non-holiday Thursday
of the Oct–Dec 2026 window *and* at least 3% below the window mean.

### Six of the original eighteen traffic points were measuring nothing

They sat on segments shorter than a minute of driving. The worst, in Budapest,
was six seconds — **83 metres.** Such a point is deaf and noisy at once: exactly
zero delay most of the time, then 700% when one van stops. Every Los Angeles
point had landed on a frontage road (FRC4) rather than the freeway it was named
after.

Fixed by lowering the TomTom zoom from 10 to 8, expanding to six candidates per
city, recording `segment_metres` per reading, and rejecting points under 700m or
of class FRC4+ at aggregation time rather than averaging them in.

**Still open:** after a few days of readings, keep the best three per city on
measured evidence. Coordinates cannot be verified from a sandbox, which is
exactly why the choice was left to the data. Note TomTom volume is now 36
calls/hour (864/day) — check the plan ceiling before November.

### The Russian PlayStation Store nearly won us a prediction for free

`psn_incidents` read a permanent 1 because Sony has listed the Russian
PlayStation Store as degraded continuously since the 2022 withdrawal. The
prediction "service problems on launch day" would have been satisfied in
advance, by a war, without the launch doing anything. Russia is now excluded in
`summarise.py`; the value is 0.

### Electricity: three attempts, two of them confounded

This matters because it is the best story on the list and the weakest evidence.

1. First attempt compared the France–Morocco semi-final to surrounding
   Wednesdays: +13%. **Invalid** — the comparison days were themselves match
   days.
2. Second attempt used pre-tournament weekdays: France +52%. **Obviously not
   football.** That is electric heating; France is the most heating-dependent
   grid in Europe and December is not October. Germany and the Netherlands went
   *negative* on the same test. Four of eight measurements positive: a coin.
3. Third attempt, weather-immune: **evening peak divided by the same day's late
   afternoon.** A cold day lifts both hours, so the ratio cancels weather and
   season. This one is sound and is now implemented in `power.py`, pinned to
   the largest of 18:00–21:00 local over 16:00 local, with a regression test
   that fails if the hours are moved.

**The detection floor is per country, and wider than this file used to say.**
Measured from the backfill, coefficient of variation of the ratio on
non-holiday weekdays, computed within each October–December window separately:

| DE | FR | ES | SE | IT | PL | NL | HU |
|---|---|---|---|---|---|---|---|
| 2.2–2.6% | 1.8–3.0% | 2.2–2.9% | 2.2–3.6% | 2.9–4.6% | 3.2–4.1% | 3.7–8.0% | 6.0–7.0% |

The earlier "1.8–2.5% across seven countries" holds for the best four and is
too optimistic for the rest. **Hungary is the least sensitive instrument of the
eight** — it needs a 20% swing to reach three standard deviations. That is
worth saying out loud, because Hungary is the country a Hungarian reader looks
at first, and it is the one least able to see anything.

### The World Cup evidence was the weekend, not the football

This file recorded Spain +4.1σ on a group match and Italy +4.1σ the same
evening, and called the pattern inexplicable. It is explicable. **That match
was a Sunday, and those figures come from scoring a Sunday against a weekday
baseline.**

The ratio is structurally higher at weekends in every country — Italy by
**+3.6 weekday standard deviations**, which is the entire supposed signal.
Compared Sunday to Sunday, the like-for-like test, Spain is **+0.5σ** and Italy
**−0.1σ**. Nothing happened. The Italy puzzle dissolves: Italy has by far the
largest weekend effect of the eight and was not playing.

France on its own semi-final survives, because that was a Wednesday scored
against weekdays: **−1.7σ**, reproduced by `power.py` and locked in
`test_power.py`.

So the count is worse than "three attempts, two confounded". The method is
sound; **the evidence that it can detect a big television audience is gone.**
There are now zero positive detections of football, not two. Never compare a
day to a different weekday class — the same mistake would make 19 November 2026
look like a result whatever happened, and it is a Thursday, so it must be
scored against Thursdays.

**Working hypothesis, to be stated on the site as a hypothesis:** people watch
big football in pubs and at each other's houses, and a national grid is blind to
a crowd that gathers in one place. A game cannot be played in a pub. If that
reasoning is right, a launch should show up more clearly than a match — but it
is reasoning, not evidence, and **if November shows nothing, publish that.**

The correction above strengthens this rather than weakening it: with the Spain
and Italy readings gone, football has never once moved a national grid on this
measure. If a game launch does, that is a cleaner story than a smaller version
of an effect football already showed. It also raises the stake honestly — we
are now betting on an effect that has never been observed.

Consequence: electricity is a **second** witness under claim 02, behind traffic.
Not the headline. The baseline comes from the backfill's four October–December
windows, never from the live series — six weeks of live collection starting in
September would bake the Dutch summer solar distortion into what the site calls
normal. See the note in `power.py`.

### Twitch amplitude, and a gift

Over the first days, `twitch_top100_total` ran from 300k to 1.50M — a fivefold
swing from the daily cycle alone. **"Twice the median" is meaningless** unless
it is the same-hour, same-weekday median.

By luck the first week of collection caught **ZEVENT**, one of the largest
scheduled events on the platform: 540k concurrent viewers on one channel,
lifting the global top-100 total to 2.19× the running median. That is a real
measured yardstick for "what a huge event looks like", and it is the best
available human comparison for November.

### ENTSO-E readings are 45-60 minutes old, and the lag drifts

Found on the first live evening, 6 September 2026, which is the reason to
watch the first run of anything. Two faults, one cause.

**The reading is not from the hour you fetched it.** A snapshot collected at
14:14 UTC carries the load at 13:30. The evening ratio compares named hours,
so filing each reading under its collection hour shifted every one of them a
bucket late and made the first live ratio wrong in all eight countries. The
measurement carries its own `t`; use that, never `collected_at_utc`. The
flattened series now carries `power_XX_t` beside the load for exactly this.

**An hourly poll misses hours.** Because the lag drifts between 45 and 60
minutes, some clock hours get two readings and some get none. On that first
evening the Netherlands and Sweden had no 16:00 reading at all and dropped
out of the comparison — silently, and correctly, since the alternative is
inventing one. On 19 November that would quietly delete countries from the
evidence.

The fix costs nothing: the collector already requests a **twelve-hour
window** and was discarding all but its last point. It now keeps the hourly
means of the whole window, so every hour arrives about a dozen times and the
most settled version wins. No extra call, no extra quota. Snapshots taken
before 6 September have no window and cannot be back-filled — that data was
never saved.

### GB does not publish electricity to ENTSO-E

Post-Brexit. The backfill returns 8 of 9 countries and names the reason. If
Britain is wanted, the fallback is Elexon BMRS or the NESO data portal, both
free and key-free. Not yet written.

### GitHub Actions shows local time; snapshots are named in UTC

This caused a false alarm that the collector had stopped for three hours. It had
not. Budapest is UTC+2 in summer. Check the timezone before concluding anything
about gaps.

---

## 6. Open items

**The six predictions are published**, as of 6 September 2026, in
`predictions.py` and on the page under `#predictions`. Each carries its rule,
where its threshold came from, and how often that rule fires on an ordinary
day — that last number being the one that matters. `PUBLISHED_AT` is a
constant, never a clock: if it moved with every run, "written down in advance"
would be a phrase the file re-earned every hour.

Two of the drafted six were dropped and two were rewritten, all four on
measurement:

- **Self-reports** dropped. The endpoint has not returned a single response,
  so any threshold would have been invented — and a prediction about our own
  self-selected sample is the one a sceptic discounts first.
- **Console prices** never made it in. eBay began authenticating on
  6 September and has four daily medians behind it. Claim 04 therefore has no
  prediction, and the page says so.
- **The subway rule was broken.** As inherited it compared 19 November to the
  whole Oct–Dec window; 24 and 31 December 2026 are both Thursdays and run
  25–60% below normal, so no ordinary day could ever be "the lowest" and the
  window mean was dragged down by holidays. Now stated against November
  Thursdays alone, which are the most uniform days in the entire record
  (sd 0.68%, 0.99%, 0.45% in 2023–25; no November Thursday ever more than
  1.12% below its month).
- **The electricity rule was already true.** "At least one of eight grids
  moves two standard deviations" fires on **24.4%** of ordinary autumn
  weekdays. Two of eight: 4.7%. Three of eight: 1.4%. It now asks for three.

That second one is the Russian PlayStation Store all over again, and it is why
every threshold now has its base rate measured against the backfill and
published beside it. **Any new prediction must carry that number.**

The commitment published with them: *we expect to be wrong about at least one
of these, and we will not quietly edit them.* Being publicly wrong about two of
six is more credible than being right about all six, and it is the version a
journalist can write about twice.

**The scorer is built** — `score.py`, wired into `summarise.py`, so every run
recomputes all six verdicts from the readings and writes them into
`predictions.json`. Recomputed, never typed: a verdict is what the data says
today, including "not enough data", which is what all six say until November.

**The rule that governs that file: `failed` means we measured and it did not
happen. It never means we could not measure.** A collector outage on
19 November must not print as evidence that nothing happened — that is a false
result wearing the clothes of a real one, and it is the worst thing this
project could publish. Every scorer establishes its readings are present
before forming any opinion; missing data yields no verdict and a reason naming
what is missing. `test_score.py` asserts there is no path from absent data to
"failed", for all six, including partial data: five of the six Steam games
summed is a smaller number that would look like displacement, so an incomplete
basket is discarded rather than summed.

**Two of the six cannot be settled on the day.** Traffic and Steam are rank
tests over Thursdays between 1 October and 17 December, so a December Thursday
can still come in lower. They report `provisional` and show where they stand;
the page renders that as SO FAR. Saying so is better than implying the day
settles it.

### Corrections to published predictions

The commitment is that we will not *quietly* edit them. That is not a promise
never to correct an error — it is a promise that no correction is invisible.
`predictions.CORRECTIONS` carries each one with its date and reason, and the
page prints it beside the prediction it changed, in amber.

**A correction may fix how a rule is described. It may never make a rule
easier to satisfy.** If one turns out to be unwinnable as written, it fails as
written.

One so far, 6 September 2026: the Steam rule said "the seven tracked games
other than Grand Theft Auto V". There are eight tracked games and two of them
are GTA V — the original and Enhanced — so the set is six. The set never
changed; the count describing it was wrong. Found while writing the scorer,
which is the point of writing scorers.

That prediction also had no machine-readable set at all — only English. The
six are now `predictions.STEAM_DISPLACED`. **Any prediction scored on a set of
metrics must name that set in code**, or the next person to score it has to
guess, and "seven" would have made them guess wrong.

### Holidays in the New York series, learned the hard way

Every Thursday dip beyond 5% in four years of subway data is an identifiable
holiday, not noise: Thanksgiving (−60%), Christmas and New Year (−16 to −63%),
4 July (−47%), Juneteenth (−21%), Presidents' Day week (−7%), Passover and
Easter (−5 to −12%), the Jewish High Holidays in early October (−14 to −16%),
and late August (−5 to −9%). One outlier is not a holiday at all: 8 June 2023,
−15.7%, the Canadian wildfire smoke emergency.

**Consequence:** any rule built on an Oct–Dec window must survive early-October
High Holidays whose date moves year to year. November Thursdays alone avoid all
of it, which is why the subway prediction lives there.

**The D1 schema is not in the repository.** `worker.js` is, as of
2026-09-06 — but the three tables it writes to (`reports`, `tallies`,
`subscribers`) exist only inside the D1 database. The worker cannot be
redeployed from source alone. The DDL must be exported from the live
database, never reconstructed from the queries: a guessed schema that
almost matches is worse than none.

**`chicago`** — a second, independent transit system — is in the plan with no
code. It matters because New York is currently a single point of failure for
claim 01's strongest evidence.

**`yt_subscribers_per_hour`** is always zero because YouTube rounds the
subscriber count to 13.7M. Not broken, meaningless. Remove it.

**eBay `sample_titles`** can be dropped now that the query is confirmed to return
consoles rather than accessories. Doing so also simplifies the exemption
declaration filed with eBay, which currently discloses them.

---

## 7. Settled, do not revisit without new evidence

**Rejected sources**, each with a documented reason: Reddit (API closed,
November 2025), GitHub (bot activity dominates; issue comments fell ~98% while
pushes doubled), Stack Overflow (from ~21k questions a week in early 2023 to
roughly 40 a day by August 2026 — kept for the record, useless as a work
signal), Yahoo Finance (runner IPs blocked), Best Buy (US phone number
required), GDELT by-country (HTTP 429 from runner IPs; the by-language series
does work).

**Food delivery has no usable source.** Wolt, Uber Eats and Foodpanda publish
nothing daily and there is no free proxy. Do not spend days looking again.

**Visual direction:** dark, neon, Vice City-adjacent, on Péter's explicit
decision. No trademark forbids a colour. The residual risk is cumulative — the
domain uses "Grand Theft" *and* the palette evokes the game — and the mitigation
chosen is not a palette change but making the first screen unmistakably a
measurement project: independent-project label, hourly reading count, commit
hash. Genre signalling is the protection. Never use Rockstar artwork, trailer
stills, characters, logos, or the Pricedown typeface.

---

## 8. Conventions

- **Run `python3 state.py` before making any claim about project status.**
- Python edits: parse with `ast` afterwards. String patches use
  `assert old in s` guards to catch double-application.
- Tests: `test_indices.py`, `test_entsoe.py` (network replaced by fixtures),
  `test_power.py` (the evening ratio, including a regression lock on the hours),
  `test_predictions.py` (the six, and a re-derivation of the two thresholds
  that were rewritten), `test_score.py` (the verdicts, and the invariant that
  absent data never reads as "failed").
  Run all five after touching collection or aggregation. The counts move; the
  suites print their own totals, so read those rather than trusting a number
  written here.
- A test helper that lets a caller force the verdict will eventually be used to
  force it. `test_power.py` had an `ok=` parameter for one run, and two checks
  passed while asserting nothing. One way to state an expectation, no override.
- `collect.py --check` exercises the collectors.
- **Never invent a number.** A missing country stays missing; a dead measurement
  point is dropped, not averaged in; an index without enough baseline prints
  nothing. An empty cell is more honest than a filled false one, and the whole
  project's credibility rests on that being true every time.
- Secrets are passed to the process explicitly in the workflow `env:` block.
  Adding a secret in GitHub settings is not enough — that mistake cost a day.
- YAML edits are riskier than Python for a non-technical operator to paste.
  Replace whole files rather than asking for line edits.
