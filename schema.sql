-- Grand Theft Attention -- the D1 schema behind worker.js.
--
-- Exported from the live database on 6 September 2026, not reconstructed
-- from the queries in worker.js. That distinction matters: the queries show
-- table and column names but not types, not the primary keys, and not the
-- UNIQUE constraint on subscribers.email that the ON CONFLICT clause in
-- handleSignup silently depends on. A schema that is almost right passes its
-- first test and then diverges, which is the failure this project cannot
-- afford anywhere.
--
-- Together with worker.js this makes the Worker redeployable from source.
-- Before today it existed only inside the Cloudflare dashboard.
--
-- Two objects in the live database are deliberately absent here:
--   _cf_KV          Cloudflare's own internal table, not ours to create.
--   sqlite_sequence Created automatically by AUTOINCREMENT.

-- Every answer, one row each. Kept alongside the aggregate rather than
-- derived from it, because the aggregate cannot be re-checked and this can.
CREATE TABLE reports (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  answer       TEXT NOT NULL,
  country      TEXT,
  industry     TEXT,
  submitted_at TEXT NOT NULL
);

CREATE INDEX reports_submitted ON reports (submitted_at);
CREATE INDEX reports_answer    ON reports (answer);

-- The running count, four rows, read by GET /counts.
--
-- It is a separate table for a reason recorded in worker.js: from
-- 1 September 2026 Cloudflare enforces the D1 free-tier row limits as hard
-- errors, so counting the reports table on every page view would take the
-- site down on precisely the day it mattered.
CREATE TABLE tallies (
  answer TEXT PRIMARY KEY,
  n      INTEGER NOT NULL DEFAULT 0
);

-- These four rows are not optional and not decoration.
--
-- handleReport increments with "UPDATE tallies SET n = n + 1 WHERE answer = ?".
-- If the row is missing, that statement matches nothing, changes nothing, and
-- raises nothing. The vote still lands in `reports`, the counter never moves,
-- and /counts under-reports for ever while looking perfectly healthy. A
-- database restored without these four rows would be silently broken from its
-- first answer.
--
-- The keys must match ANSWERS in worker.js exactly.
INSERT INTO tallies (answer, n) VALUES
  ('day_off',        0),
  ('sick',           0),
  ('in_not_working', 0),
  ('working',        0);

-- Email addresses for the two planned emails, and nothing else. No name, no
-- IP, no identifier of any kind -- Turnstile handles abuse at the edge so that
-- there is nothing personal to store, which is what lets the privacy note on
-- the site say what it says.
--
-- email is the PRIMARY KEY, which is what makes the
-- "ON CONFLICT(email) DO NOTHING" in handleSignup work: a second signup with
-- the same address is a no-op rather than a duplicate or an error.
CREATE TABLE subscribers (
  email        TEXT PRIMARY KEY,
  submitted_at TEXT NOT NULL
);
