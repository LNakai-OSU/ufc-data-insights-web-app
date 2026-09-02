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
