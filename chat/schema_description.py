"""Hand-written schema description fed to Claude for NL-to-SQL.

Kept as hand-curated text rather than generated from information_schema:
with only 5 tables, hand-written lets us include the semantic notes
(what's nullable and why, how to join, unit conventions) that a raw
column/type dump can't express - and those notes are exactly what steers
the model away from wrong-but-plausible SQL. Keep this in sync with
db/schema.sql when the schema changes.
"""

SCHEMA_DESCRIPTION = """\
Postgres schema for UFC fighter/fight statistics (5 tables):

fighters
  fighter_id TEXT PK, first_name, last_name, nickname
  height_in, reach_in NUMERIC (inches) - nullable, not recorded for every fighter
  weight_lbs NUMERIC
  stance TEXT enum: 'Orthodox', 'Southpaw', 'Switch', 'Open Stance', 'Sideways' - nullable
  dob DATE - nullable

events
  event_id TEXT PK, name, event_date DATE, location

weight_classes
  weight_class_id INTEGER PK, name (e.g. 'Lightweight', 'Women''s Flyweight', 'Catch Weight')

fights  (one row per bout; UFC bouts are always exactly 2 fighters)
  fight_id TEXT PK, event_id -> events
  fighter_1_id, fighter_2_id -> fighters (nullable - see note below)
  fighter_1_name_raw, fighter_2_name_raw TEXT (always populated, even when the *_id is NULL)
  result TEXT enum: 'fighter_1_win', 'fighter_2_win', 'draw', 'no_contest'
  winner_id -> fighters, NULL for draw/no_contest
  weight_class_id -> weight_classes (nullable)
  is_title_bout, is_interim_title BOOLEAN
  method TEXT (e.g. 'KO/TKO', 'Decision - Unanimous', 'Submission'), method_detail TEXT
  round SMALLINT, time_seconds INTEGER (when the fight ended, within `round`), time_format TEXT
  referee TEXT

fight_stats  (one row per fighter per round per fight - detailed strike/grapple stats)
  fight_id -> fights, fighter_id -> fighters (nullable - see note below)
  fighter_name_raw TEXT (always populated)
  round SMALLINT
  knockdowns SMALLINT
  sig_str_landed / sig_str_attempted SMALLINT   (significant strikes; accuracy = landed::numeric / NULLIF(attempted,0))
  total_str_landed / total_str_attempted SMALLINT
  td_landed / td_attempted SMALLINT             (takedowns)
  sub_attempts, reversals SMALLINT
  control_seconds INTEGER                        (ground control time that round)
  head_landed/attempted, body_landed/attempted, leg_landed/attempted SMALLINT  (strikes by target)
  distance_landed/attempted, clinch_landed/attempted, ground_landed/attempted SMALLINT  (strikes by position)

Important notes:
- To find a fighter's fights: WHERE fighter_id IN (fights.fighter_1_id, fights.fighter_2_id) or
  join fights ON f.fighter_id IN (fights.fighter_1_id, fights.fighter_2_id).
- fighter_id on fights/fight_stats can be NULL: the source data only gives fighter *names* for
  bouts, and a small number of fighters share a full name with another fighter, so name
  resolution during load was sometimes ambiguous. When filtering/joining by fighter identity,
  rows with a NULL fighter_id for that fighter are silently excluded - mention this if it's
  likely to matter for the question (e.g. counting ALL fights by name would need
  fighter_1_name_raw/fighter_2_name_raw instead of the ID, but that path is unreliable across
  fighters who share a name).
- Win rate for a fighter/group = wins / (wins + losses), typically excluding draws and
  no_contests from the denominator unless the question asks about them specifically.
- Percentages/accuracy are NOT stored as columns - compute them as landed::numeric /
  NULLIF(attempted, 0) to avoid divide-by-zero.
- Always use a Postgres-valid SELECT (or WITH ... SELECT) statement. Never modify data.
"""
