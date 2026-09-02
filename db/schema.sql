-- UFC fighter/fight stats schema.
--
-- Design notes (the non-obvious calls):
--
-- - PKs are the trailing hash segment of each entity's ufcstats.com URL
--   (e.g. fighter-details/93fe7332d16c6ad9 -> '93fe7332d16c6ad9'), not
--   serial ints. The source already gives us a stable, unique natural
--   key; adding a meaningless surrogate on top would just be an extra
--   join for no benefit.
--
-- - fights has exactly two fixed fighter columns (fighter_1/fighter_2)
--   rather than a fight_participants join table. UFC bouts are always
--   1-on-1 - that cardinality never varies, so a many-to-many table
--   would be normalization for a case that can't happen.
--
-- - weight_class is split into a small lookup table plus is_title_bout /
--   is_interim_title booleans. The raw source column ("UFC Interim
--   Heavyweight Title Bout") conflates the weight class with title
--   status across 120 distinct strings; splitting it out is what makes
--   "win rate by weight class" or "title fights only" a plain filter
--   instead of a pile of LIKE clauses.
--
-- - Sig./total strikes, takedowns, and target/position breakdowns are
--   stored as landed/attempted integer pairs, not the source's "7 of 10"
--   strings and not the accompanying percentage strings either -
--   accuracy is landed/attempted and is cheap to compute in a query
--   (or a view), so storing it too would just be redundant data that
--   can drift from the underlying counts.
--
-- - fighter_id on fights/fight_stats is nullable, with a companion
--   *_name_raw column. The source tables only give fighter names for
--   bouts (not their stable fighter URL), and at least 8 fighters in
--   this dataset share a full name with another fighter - name-based
--   resolution during load can be genuinely ambiguous. Keeping the raw
--   name means an unresolved row is still visible and query-able
--   instead of silently dropped or mis-linked.

CREATE TYPE fight_result AS ENUM (
    'fighter_1_win',
    'fighter_2_win',
    'draw',
    'no_contest'
);

CREATE TYPE stance AS ENUM (
    'Orthodox',
    'Southpaw',
    'Switch',
    'Open Stance',
    'Sideways'
);

CREATE TABLE weight_classes (
    weight_class_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE  -- e.g. 'Lightweight', 'Women''s Flyweight', 'Catch Weight'
);

CREATE TABLE fighters (
    fighter_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    nickname TEXT,
    height_in NUMERIC(4, 1),
    weight_lbs NUMERIC(5, 1),
    reach_in NUMERIC(4, 1),
    stance stance,
    dob DATE,
    url TEXT NOT NULL UNIQUE,

    -- Sourced separately from UFC.com's athlete pages (ufcstats.com has no
    -- nationality/birthplace field at all) - see db/migrations/001 and
    -- scrape_birthplaces.py. Nullable: populated by a slow, rate-limited
    -- background scrape, so most rows start NULL and fill in over time.
    -- "Birthplace" rather than "nationality" because that's what UFC.com
    -- actually publishes, and the two can differ (dual citizenship, moved
    -- countries young, etc.) - don't conflate them in the UI.
    birthplace_raw TEXT,
    birthplace_country TEXT
);

CREATE INDEX idx_fighters_last_name ON fighters (last_name);
CREATE INDEX idx_fighters_full_name ON fighters (first_name, last_name);

CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    event_date DATE,
    location TEXT,
    url TEXT NOT NULL UNIQUE
);

CREATE INDEX idx_events_date ON events (event_date);

CREATE TABLE fights (
    fight_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events (event_id),

    fighter_1_id TEXT REFERENCES fighters (fighter_id),
    fighter_1_name_raw TEXT NOT NULL,
    fighter_2_id TEXT REFERENCES fighters (fighter_id),
    fighter_2_name_raw TEXT NOT NULL,

    result fight_result NOT NULL,
    winner_id TEXT REFERENCES fighters (fighter_id),

    weight_class_id INTEGER REFERENCES weight_classes (weight_class_id),
    is_title_bout BOOLEAN NOT NULL DEFAULT FALSE,
    is_interim_title BOOLEAN NOT NULL DEFAULT FALSE,

    method TEXT,             -- e.g. 'KO/TKO', 'Decision - Unanimous', 'Submission'
    method_detail TEXT,      -- e.g. 'Punch to Head At Distance'
    round SMALLINT,
    time_seconds INTEGER,    -- parsed from "M:SS" the fight ended at, within `round`
    time_format TEXT,        -- e.g. '3 Rnd (5-5-5)', '1 Rnd + OT (12-3)'
    referee TEXT,

    url TEXT NOT NULL UNIQUE,

    CONSTRAINT winner_is_a_participant CHECK (
        winner_id IS NULL OR winner_id IN (fighter_1_id, fighter_2_id)
    )
);

CREATE INDEX idx_fights_event ON fights (event_id);
CREATE INDEX idx_fights_fighter_1 ON fights (fighter_1_id);
CREATE INDEX idx_fights_fighter_2 ON fights (fighter_2_id);
CREATE INDEX idx_fights_weight_class ON fights (weight_class_id);

CREATE TABLE fight_stats (
    fight_stat_id SERIAL PRIMARY KEY,
    fight_id TEXT NOT NULL REFERENCES fights (fight_id),
    fighter_id TEXT REFERENCES fighters (fighter_id),
    fighter_name_raw TEXT NOT NULL,
    round SMALLINT NOT NULL,

    knockdowns SMALLINT,

    sig_str_landed SMALLINT,
    sig_str_attempted SMALLINT,
    total_str_landed SMALLINT,
    total_str_attempted SMALLINT,

    td_landed SMALLINT,
    td_attempted SMALLINT,
    sub_attempts SMALLINT,
    reversals SMALLINT,
    control_seconds INTEGER,

    head_landed SMALLINT,
    head_attempted SMALLINT,
    body_landed SMALLINT,
    body_attempted SMALLINT,
    leg_landed SMALLINT,
    leg_attempted SMALLINT,

    distance_landed SMALLINT,
    distance_attempted SMALLINT,
    clinch_landed SMALLINT,
    clinch_attempted SMALLINT,
    ground_landed SMALLINT,
    ground_attempted SMALLINT,

    UNIQUE (fight_id, fighter_name_raw, round)
);

CREATE INDEX idx_fight_stats_fight ON fight_stats (fight_id);
CREATE INDEX idx_fight_stats_fighter ON fight_stats (fighter_id);

-- Official UFC rankings (champion + top-15 contenders per division), a
-- live current-only snapshot from ufc.com/rankings - UFC doesn't publish
-- a historical rankings archive, so unlike other tables this one is
-- truncated and fully reloaded on every scrape (see scrape_rankings.py),
-- not accumulated.
CREATE TABLE current_rankings (
    ranking_id SERIAL PRIMARY KEY,
    weight_class_id INTEGER NOT NULL REFERENCES weight_classes (weight_class_id),
    rank SMALLINT NOT NULL,  -- 0 = champion, 1-15 = ranked contenders
    fighter_id TEXT REFERENCES fighters (fighter_id),
    fighter_name_raw TEXT NOT NULL,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (weight_class_id, rank)
);
