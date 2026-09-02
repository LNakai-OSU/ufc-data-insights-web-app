-- Adds birthplace columns to an already-created fighters table. See the
-- comment on these columns in db/schema.sql for why "birthplace" and not
-- "nationality", and why they're nullable.
ALTER TABLE fighters ADD COLUMN IF NOT EXISTS birthplace_raw TEXT;
ALTER TABLE fighters ADD COLUMN IF NOT EXISTS birthplace_country TEXT;
