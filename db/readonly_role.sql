-- Read-only Postgres role for the NL-to-SQL chat assistant.
--
-- The assistant lets an LLM write and execute arbitrary SQL against this
-- database. App-level validation (chat/sql_tool.py) checks the query text,
-- but text-based checks alone are not a real guarantee - a role with only
-- SELECT granted is what actually makes destructive/write queries
-- impossible, regardless of what the LLM generates. Defense in depth: DB
-- role first, text validation as a fast-fail second layer.

DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ufc_stats_readonly') THEN
      CREATE ROLE ufc_stats_readonly WITH LOGIN;
   END IF;
END
$$;

GRANT CONNECT ON DATABASE ufc_stats TO ufc_stats_readonly;
GRANT USAGE ON SCHEMA public TO ufc_stats_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ufc_stats_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ufc_stats_readonly;

-- Belt-and-suspenders against a runaway or accidentally-unbounded query.
ALTER ROLE ufc_stats_readonly SET statement_timeout = '5s';
