# UFC Fighter Stats

Data pipeline + database + dashboard + natural-language query assistant
for UFC fighter and fight stats (dashboard/assistant in progress).

## Data source

Originally planned to scrape [ufcstats.com](http://ufcstats.com) directly,
but it's now behind a JavaScript proof-of-work bot-challenge gate, which is
a clear signal against automated bulk access. Instead we pull pre-scraped
CSVs from [Greco1899/scrape_ufc_stats](https://github.com/Greco1899/scrape_ufc_stats)
(GPL-3.0), an open-source project that scrapes ufcstats.com and republishes
the result, refreshed daily via CI. This also gave us round-by-round
strike/grapple stats for free, which a first-pass scraper wouldn't have had.

**License note:** the dataset is under GPL-3.0. Keep that in mind for how
you license/share any code that directly embeds or redistributes this data;
it doesn't restrict using it to build and demo your own project.

Attribution belongs in the final project README/dashboard footer.

## Status

- [x] Data ingestion (`fetch_data.py`) - downloads the 6 source CSVs
- [x] Normalized Postgres schema (`db/schema.sql`)
- [x] Load script (`db/load.py`) - raw CSVs into the schema
- [x] NL-to-SQL chat assistant (`chat/`, CLI via `ask.py`) - live model call not yet smoke-tested (needs `ANTHROPIC_API_KEY`)
- [x] Dashboard (`backend/` FastAPI + `frontend/` React) - backend fully verified live; frontend built/linted clean but not checked in an actual browser (see Dashboard section)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Fetching data

```bash
python fetch_data.py
```

Downloads six CSVs into `data/raw/` (gitignored - re-run to refresh):

| File | Rows (as of last fetch) | Contents |
|---|---|---|
| `ufc_event_details.csv` | ~786 | event name, date, location |
| `ufc_fighter_details.csv` | ~4,613 | fighter name + ufcstats URL |
| `ufc_fighter_tott.csv` | ~4,614 | height, weight, reach, stance, DOB |
| `ufc_fight_results.csv` | ~8,885 | bout outcome, weight class, method, round, time, referee |
| `ufc_fight_details.csv` | ~8,885 | event/bout to fight-details URL mapping |
| `ufc_fight_stats.csv` | ~41,774 | per-round, per-fighter strike/takedown/control stats |

## Database schema

`db/schema.sql` defines five tables: `fighters`, `events`, `fights`,
`fight_stats` (per-fighter, per-round strike/grapple detail), and a
`weight_classes` lookup. See the comment block at the top of that file for
the non-obvious design calls (why PKs are the ufcstats.com URL hash rather
than a serial, why weight class/title status is split out of the raw
120-value text field, why landed/attempted counts are stored instead of
the source's precomputed percentages, and how fighter-name ambiguity in
the fight-level source tables is handled).

Local setup (Postgres 16 via Homebrew):

```bash
brew install postgresql@16
LC_ALL="en_US.UTF-8" pg_ctl -D /opt/homebrew/var/postgresql@16 -l /tmp/postgres16.log start
createdb ufc_stats
psql -d ufc_stats -f db/schema.sql
```

## Loading data

```bash
python fetch_data.py     # if you haven't already, or to refresh
python db/load.py        # truncates + reloads all tables; safe to re-run
python db/test_parsing.py  # run after touching db/parsing.py
```

The fight-level source CSVs (`ufc_fight_results.csv`, `ufc_fight_stats.csv`)
only give fighter *names*, not their stable ufcstats ID - the loader
resolves each name against the `fighters` table and leaves `fighter_id`
NULL (keeping the raw name in a `*_name_raw` column) when a name doesn't
match or matches more than one fighter. As of the last load:

- 8,858 of 8,885 fights loaded (27 skipped - their EVENT text didn't match
  any row in `ufc_event_details.csv`, likely a sync lag between the two
  source files for very recently added events)
- 41,606 of 41,774 fight_stats rows loaded (42 blank-round rows skipped, 124
  rows skipped because they belong to one of the 27 unmatched fights, 2
  rows dropped as genuinely conflicting duplicates from a 1997 event)
- 50 fight-level and 114 stat-level fighter references are ambiguous
  (name matches 2+ fighters) and so have `fighter_id = NULL`
- 12 fight-level and 29 stat-level fighter references have no matching
  name in `fighters` at all

## NL-to-SQL chat assistant

`chat/agent.py` runs a manual agentic loop: Claude (claude-opus-5) is given a
hand-written schema description (`chat/schema_description.py`) and a single
`run_sql_query` tool, writes SQL to answer the question, and narrates the
result. Try it via `python ask.py "your question"`.

**Read-only is enforced at three layers**, not just prompted for:
1. `db/readonly_role.sql` creates a `ufc_stats_readonly` Postgres role with
   only `SELECT` granted - confirmed live: a `DELETE` through this role gets
   `permission denied for table fighters`, regardless of what SQL the model
   generates.
2. `chat/sql_tool.py` rejects anything that isn't a single `SELECT`/`WITH`
   statement or that contains a write/DDL keyword, before it reaches Postgres.
3. A 5-second statement timeout and an auto-injected `LIMIT 200` cap runaway
   or unbounded queries.

Setup:
```bash
psql -d ufc_stats -f db/readonly_role.sql   # one-time
export ANTHROPIC_API_KEY="sk-ant-..."       # add to ~/.zshrc to persist
python ask.py "Do southpaws have a higher win rate than orthodox fighters?"
```

**Verified:** `chat/sql_tool.py` (validation + execution) against the live
database - 9/9 checks passing (`python -m chat.test_sql_tool`), including that
a malformed bypass attempt is still blocked by the DB role even if the text
validator were somehow skipped.
**Not yet verified:** an actual live call through `chat/agent.py`/`ask.py` -
this needs `ANTHROPIC_API_KEY`, which isn't set in this environment yet.

## Dashboard

`backend/` (FastAPI) + `frontend/` (React + Vite + Recharts).

Needs Node.js (used v24 LTS here via `brew install node`; if Homebrew's
bottle download is blocked on your network, grab the darwin-arm64 tarball
directly from nodejs.org/dist and put its `bin/` on your PATH instead).

```bash
# Terminal 1 - backend, from project root
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2 - frontend
cd frontend
npm install
npm run dev   # http://localhost:5173
```

The backend exposes read-only stats endpoints (`/api/overview`,
`/api/stats/stance-win-rate`, `/api/stats/weight-classes`,
`/api/stats/methods`, `/api/stats/active-years`,
`/api/stats/fighters-by-country`, `/api/fighters` search + detail) plus
`/api/chat`, which wraps `chat/agent.ask()`. It uses the same
`ufc_stats_readonly` role as the chat assistant - the dashboard API has no
reason to hold write access either.

### World map: fighters by country over time

`WorldMap.jsx` renders a choropleth (react-simple-maps + a local
`world-atlas` topojson, no CDN dependency) with a year slider, showing
which countries active fighters were born in for the selected year.

**ufcstats.com has no nationality/birthplace field at all** - none of the
Kaggle/GitHub/HuggingFace UFC datasets checked have it either, since
they're all ultimately sourced from ufcstats.com too. The data comes from
a separate source: **UFC.com's athlete pages**, which do publish a "Place
of Birth" field. See `scrape_birthplaces.py` for the full writeup, but
briefly:
- `db/migrations/001_add_fighter_birthplace.sql` adds `birthplace_raw` /
  `birthplace_country` to `fighters`.
- The scraper respects UFC.com's robots.txt 15-second crawl-delay, so a
  full run over ~4,600 fighters takes about a day - it's resumable
  (only fighters with `birthplace_country IS NULL` are processed, and
  each result is committed immediately) and safe to interrupt.
- URL slugs are *guessed* (`firstname-lastname`) since there's no direct
  mapping to UFC.com's URLs - failures are logged to
  `data/birthplace_scrape_failures.csv`, not silently dropped.
- "Birthplace," not "nationality" - that's what UFC.com actually
  publishes, and the two can differ.
- `frontend/src/countryNameMap.js` reconciles UFC.com's country-name
  phrasing against the topojson's Natural Earth names (e.g. "United
  States" -> "United States of America"); anything still unrecognized is
  surfaced under the map, not dropped silently.

**Status as of this writing:** ~73% coverage (3,357+ of 4,613 fighters),
and that's close to the practical ceiling for this approach - the
remainder splits into ~445 fighters whose UFC.com page returns a genuine
HTTP 403 (a real Drupal-level access restriction, confirmed via response
headers - not a bot-block or rate limit, so retrying doesn't help) and
~800 fighters with no resolvable UFC.com slug under any guess this
scraper tries. Re-run `python scrape_birthplaces.py` any time to pick up
newly-added fighters or retry transient failures; check progress with
`SELECT count(*) FROM fighters WHERE birthplace_country IS NOT NULL;`.

### Division rankings: the official UFC rankings

`DivisionRankings.jsx` shows the champion + ranked contenders for a
division, sourced from the real UFC.com rankings panel (`scrape_rankings.py`,
`db/migrations/002_add_current_rankings.sql`) rather than anything derived
from our own fight results.

This one's a single-page scrape, not a per-fighter crawl: `ufc.com/rankings`
lists every division on one page, so there's no crawl-delay pacing to
worry about. Two things worth knowing:
- **It's a live snapshot, not history.** UFC doesn't publish a historical
  rankings archive - "rankings as of 2020" isn't a thing that exists to
  scrape. `current_rankings` is truncated and fully reloaded on every run;
  re-run `python scrape_rankings.py` to refresh it.
- **Name matching needed real Unicode handling**, not just the ASCII
  slug-guessing used for birthplaces: UFC.com's rankings page uses proper
  typography ("Jiří Procházka") against our plain-ASCII fighters table
  ("Jiri Prochazka"), and some letters (Polish ł, for one) don't have a
  Unicode decomposition to their ASCII look-alike - accent-stripping alone
  silently drops them rather than substituting the right letter. Also
  handles UFC.com occasionally inlining a fighter's nickname into their
  display name (e.g. "Michael Venom Page"). Verified live: 175 of 176
  scraped rankings matched a fighter automatically, with the one holdout
  (`Jean Silva`) a genuine name collision - two different real fighters
  share that exact name in our data.
- The page also contains a second, separate "Meta Rankings" system UFC.com
  publishes alongside the real one - only the real "All Rankings" block is
  scraped.

The two Pound-for-Pound categories aren't scraped since they span every
weight class rather than being a division our schema tracks.

**Verified:** every backend endpoint tested live against the real database
via curl, including a 404 case and confirming `/api/chat` fails with a clean
503 (not a crash) when `ANTHROPIC_API_KEY` is unset. Cross-origin requests
from the Vite dev server's origin confirmed working (`Access-Control-Allow-Origin`
header present). The frontend builds and lints clean (`npm run build`,
`npm run lint`).
**Not yet verified:** actual rendering in a browser - I don't have one
available in this environment. Before calling this done, open
`http://localhost:5173` yourself with both servers running and check that
the charts render, the fighter search/detail view works, and (once
`ANTHROPIC_API_KEY` is set) the chat panel returns a real answer.

### "More insights" - 16 additional questions

`backend/insights.py` holds 15 more endpoints (plus two new `Leaderboard`
metrics: career control time and takedowns), one per "interesting question"
idea explored in conversation - championship-rounds fade, reach advantage,
stance matchups, volume-vs-accuracy, performance by age, win streaks vs.
opponent quality, fight pace and split-decision rate over time, finishing
style by country, home-country effect, title reign length, fastest
finishes, and rivalries. Every endpoint is documented inline with what it
actually measures and any simplifying assumption behind it (e.g. fight
pace treats every round as a full 5 minutes; reign length can't detect a
still-undefeated champion's ongoing reign) - read the docstring before
trusting a number that seems off.

Building this surfaced a real, non-obvious bug worth knowing about:
**comparing `winner_id = fighter_id` is not safe** when a fighter is
joined in via `IN (fighter_1_id, fighter_2_id)` rather than a fixed side.
`winner_id` can be NULL for a *decided* fight if the winning side's own
`fighter_id` was never resolved (the ambiguous-name cases noted in
`db/schema.sql`) - so the losing fighter's `winner_id = fighter_id` check
evaluates to NULL, not `false`. Inside `count(*) FILTER (WHERE ...)` that
happens to be harmless (NULL and false are both excluded), but it broke
outright in two other shapes: a raw Python `+=` on a NULL-valued row
(crashed `home-country-effect`), and a `WHERE NOT won` clause in SQL
(`NOT NULL` is NULL, not true - so `win-streaks` would have silently
failed to recognize a real loss as ending a streak). Fixed everywhere by
deriving "did this fighter win" from `result` plus which side they're on,
which is always true/false, never null - including retrofitting the three
pre-existing endpoints (`stance-win-rate`, `division-leaderboard`, and
one `fighter_record` CTE) that used the same pattern and were only
accidentally correct today because they happened to sit inside a
`FILTER`. Also caught: `ORDER BY value DESC` on the `control_time`
leaderboard metric was surfacing fighters with entirely-missing control
data at the top, since Postgres defaults to `NULLS FIRST` for descending
sorts - fixed with an explicit `NULLS LAST` on every leaderboard metric.

**Verified:** every endpoint tested live against the real database, cross-
checked against known real-world facts where possible (Jon Jones' actual
19-fight streak, Derrick Lewis/Charles Oliveira's real all-time KO/
submission records, Brazil's real submission-heavy finishing style,
Georges St-Pierre topping career control time) - not just "did it return
200," but "is the number plausible."
